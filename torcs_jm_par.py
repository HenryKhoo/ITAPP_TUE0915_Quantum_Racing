import socket
import sys
import getopt
import os
import time
PI= 3.14159265359

data_size = 2**17

ophelp=  'Options:\n'
ophelp+= ' --host, -H <host>    TORCS server host. [localhost]\n'
ophelp+= ' --port, -p <port>    TORCS port. [3001]\n'
ophelp+= ' --id, -i <id>        ID for server. [SCR]\n'
ophelp+= ' --steps, -m <#>      Maximum simulation steps. 1 sec ~ 50 steps. [100000]\n'
ophelp+= ' --episodes, -e <#>   Maximum learning episodes. [1]\n'
ophelp+= ' --track, -t <track>  Your name for this track. Used for learning. [unknown]\n'
ophelp+= ' --stage, -s <#>      0=warm up, 1=qualifying, 2=race, 3=unknown. [3]\n'
ophelp+= ' --debug, -d          Output full telemetry.\n'
ophelp+= ' --help, -h           Show this help.\n'
ophelp+= ' --version, -v        Show current version.'
usage= 'Usage: %s [ophelp [optargs]] \n' % sys.argv[0]
usage= usage + ophelp
version= "20130505-2"

def clip(v,lo,hi):
    if v<lo: return lo
    elif v>hi: return hi
    else: return v

def bargraph(x,mn,mx,w,c='X'):
    '''Draws a simple asciiart bar graph. Very handy for
    visualizing what's going on with the data.
    x= Value from sensor, mn= minimum plottable value,
    mx= maximum plottable value, w= width of plot in chars,
    c= the character to plot with.'''
    if not w: return '' # No width!
    if x<mn: x= mn      # Clip to bounds.
    if x>mx: x= mx      # Clip to bounds.
    tx= mx-mn # Total real units possible to show on graph.
    if tx<=0: return 'backwards' # Stupid bounds.
    upw= tx/float(w) # X Units per output char width.
    if upw<=0: return 'what?' # Don't let this happen.
    negpu, pospu, negnonpu, posnonpu= 0,0,0,0
    if mn < 0: # Then there is a negative part to graph.
        if x < 0: # And the plot is on the negative side.
            negpu= -x + min(0,mx)
            negnonpu= -mn + x
        else: # Plot is on pos. Neg side is empty.
            negnonpu= -mn + min(0,mx) # But still show some empty neg.
    if mx > 0: # There is a positive part to the graph
        if x > 0: # And the plot is on the positive side.
            pospu= x - max(0,mn)
            posnonpu= mx - x
        else: # Plot is on neg. Pos side is empty.
            posnonpu= mx - max(0,mn) # But still show some empty pos.
    nnc= int(negnonpu/upw)*'-'
    npc= int(negpu/upw)*c
    ppc= int(pospu/upw)*c
    pnc= int(posnonpu/upw)*'_'
    return '[%s]' % (nnc+npc+ppc+pnc)

class Client():
    def __init__(self,H=None,p=None,i=None,e=None,t=None,s=None,d=None,vision=False):
        self.vision = vision

        self.host= 'localhost'
        self.port= 3001
        self.sid= 'SCR'
        self.maxEpisodes=1 # "Maximum number of learning episodes to perform"
        self.trackname= 'unknown'
        self.stage= 3 # 0=Warm-up, 1=Qualifying 2=Race, 3=unknown <Default=3>
        self.debug= False
        self.maxSteps= 100000  # 50steps/second
        self.parse_the_command_line()
        if H: self.host= H
        if p: self.port= p
        if i: self.sid= i
        if e: self.maxEpisodes= e
        if t: self.trackname= t
        if s: self.stage= s
        if d: self.debug= d
        self.S= ServerState()
        self.R= DriverAction()
        self.setup_connection()

    def setup_connection(self):
        try:
            self.so= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except socket.error as emsg:
            print('Error: Could not create socket...')
            sys.exit(-1)
        self.so.settimeout(1)

        n_fail = 5
        while True:
            a= "-45 -19 -12 -7 -4 -2.5 -1.7 -1 -.5 0 .5 1 1.7 2.5 4 7 12 19 45"

            initmsg='%s(init %s)' % (self.sid,a)

            try:
                self.so.sendto(initmsg.encode(), (self.host, self.port))
            except socket.error as emsg:
                sys.exit(-1)
            sockdata= str()
            try:
                sockdata,addr= self.so.recvfrom(data_size)
                sockdata = sockdata.decode('utf-8')
            except socket.error as emsg:
                print("Waiting for server on %d............" % self.port)
                print("Count Down : " + str(n_fail))
                if n_fail < 0:
                    print("relaunch torcs")
                    os.system('pkill torcs')
                    time.sleep(1.0)
                    if self.vision is False:
                        os.system('torcs -nofuel -nodamage -nolaptime &')
                    else:
                        os.system('torcs -nofuel -nodamage -nolaptime -vision &')

                    time.sleep(1.0)
                    os.system('sh autostart.sh')
                    n_fail = 5
                n_fail -= 1

            identify = '***identified***'
            if identify in sockdata:
                print("Client connected on %d.............." % self.port)
                break

    def parse_the_command_line(self):
        try:
            (opts, args) = getopt.getopt(sys.argv[1:], 'H:p:i:m:e:t:s:dhv',
                       ['host=','port=','id=','steps=',
                        'episodes=','track=','stage=',
                        'debug','help','version'])
        except getopt.error as why:
            print('getopt error: %s\n%s' % (why, usage))
            sys.exit(-1)
        try:
            for opt in opts:
                if opt[0] == '-h' or opt[0] == '--help':
                    print(usage)
                    sys.exit(0)
                if opt[0] == '-d' or opt[0] == '--debug':
                    self.debug= True
                if opt[0] == '-H' or opt[0] == '--host':
                    self.host= opt[1]
                if opt[0] == '-i' or opt[0] == '--id':
                    self.sid= opt[1]
                if opt[0] == '-t' or opt[0] == '--track':
                    self.trackname= opt[1]
                if opt[0] == '-s' or opt[0] == '--stage':
                    self.stage= int(opt[1])
                if opt[0] == '-p' or opt[0] == '--port':
                    self.port= int(opt[1])
                if opt[0] == '-e' or opt[0] == '--episodes':
                    self.maxEpisodes= int(opt[1])
                if opt[0] == '-m' or opt[0] == '--steps':
                    self.maxSteps= int(opt[1])
                if opt[0] == '-v' or opt[0] == '--version':
                    print('%s %s' % (sys.argv[0], version))
                    sys.exit(0)
        except ValueError as why:
            print('Bad parameter \'%s\' for option %s: %s\n%s' % (
                                       opt[1], opt[0], why, usage))
            sys.exit(-1)
        if len(args) > 0:
            print('Superflous input? %s\n%s' % (', '.join(args), usage))
            sys.exit(-1)

    def get_servers_input(self):
        '''Server's input is stored in a ServerState object'''
        if not self.so: return
        sockdata= str()

        while True:
            try:
                sockdata,addr= self.so.recvfrom(data_size)
                sockdata = sockdata.decode('utf-8')
            except socket.error as emsg:
                print('.', end=' ')
            if '***identified***' in sockdata:
                print("Client connected on %d.............." % self.port)
                continue
            elif '***shutdown***' in sockdata:
                print((("Server has stopped the race on %d. "+
                        "You were in %d place.") %
                        (self.port,self.S.d['racePos'])))
                self.shutdown()
                return
            elif '***restart***' in sockdata:
                print("Server has restarted the race on %d." % self.port)
                self.shutdown()
                return
            elif not sockdata: # Empty?
                continue       # Try again.
            else:
                self.S.parse_server_str(sockdata)
                if self.debug:
                    sys.stderr.write("\x1b[2J\x1b[H") # Clear for steady output.
                    print(self.S)
                break # Can now return from this function.

    def respond_to_server(self):
        if not self.so: return
        try:
            message = repr(self.R)
            self.so.sendto(message.encode(), (self.host, self.port))
        except socket.error as emsg:
            print("Error sending to server: %s Message %s" % (emsg[1],str(emsg[0])))
            sys.exit(-1)
        if self.debug: print(self.R.fancyout())

    def shutdown(self):
        if not self.so: return
        print(("Race terminated or %d steps elapsed. Shutting down %d."
               % (self.maxSteps,self.port)))
        self.so.close()
        self.so = None

class ServerState():
    '''What the server is reporting right now.'''
    def __init__(self):
        self.servstr= str()
        self.d= dict()

    def parse_server_str(self, server_string):
        '''Parse the server string.'''
        self.servstr= server_string.strip()[:-1]
        sslisted= self.servstr.strip().lstrip('(').rstrip(')').split(')(')
        for i in sslisted:
            w= i.split(' ')
            self.d[w[0]]= destringify(w[1:])

    def __repr__(self):
        return self.fancyout()
        out= str()
        for k in sorted(self.d):
            strout= str(self.d[k])
            if type(self.d[k]) is list:
                strlist= [str(i) for i in self.d[k]]
                strout= ', '.join(strlist)
            out+= "%s: %s\n" % (k,strout)
        return out

    def fancyout(self):
        '''Specialty output for useful ServerState monitoring.'''
        out= str()
        sensors= [ # Select the ones you want in the order you want them.
        'stucktimer',
        'fuel',
        'distRaced',
        'distFromStart',
        'opponents',
        'wheelSpinVel',
        'z',
        'speedZ',
        'speedY',
        'speedX',
        'targetSpeed',
        'rpm',
        'skid',
        'slip',
        'track',
        'trackPos',
        'angle',
        ]

        for k in sensors:
            if type(self.d.get(k)) is list: # Handle list type data.
                if k == 'track': # Nice display for track sensors.
                    strout= str()
                    raw_tsens= ['%.1f'%x for x in self.d['track']]
                    strout+= ' '.join(raw_tsens[:9])+'_'+raw_tsens[9]+'_'+' '.join(raw_tsens[10:])
                elif k == 'opponents': # Nice display for opponent sensors.
                    strout= str()
                    for osensor in self.d['opponents']:
                        if   osensor >190: oc= '_'
                        elif osensor > 90: oc= '.'
                        elif osensor > 39: oc= chr(int(osensor/2)+97-19)
                        elif osensor > 13: oc= chr(int(osensor)+65-13)
                        elif osensor >  3: oc= chr(int(osensor)+48-3)
                        else: oc= '?'
                        strout+= oc
                    strout= ' -> '+strout[:18] + ' ' + strout[18:]+' <-'
                else:
                    strlist= [str(i) for i in self.d[k]]
                    strout= ', '.join(strlist)
            else: # Not a list type of value.
                if k == 'gear': # This is redundant now since it's part of RPM.
                    gs= '_._._._._._._._._'
                    p= int(self.d['gear']) * 2 + 2  # Position
                    l= '%d'%self.d['gear'] # Label
                    if l=='-1': l= 'R'
                    if l=='0':  l= 'N'
                    strout= gs[:p]+ '(%s)'%l + gs[p+3:]
                elif k == 'damage':
                    strout= '%6.0f %s' % (self.d[k], bargraph(self.d[k],0,10000,50,'~'))
                elif k == 'fuel':
                    strout= '%6.0f %s' % (self.d[k], bargraph(self.d[k],0,100,50,'f'))
                elif k == 'speedX':
                    cx= 'X'
                    if self.d[k]<0: cx= 'R'
                    strout= '%6.1f %s' % (self.d[k], bargraph(self.d[k],-30,300,50,cx))
                elif k == 'speedY': # This gets reversed for display to make sense.
                    strout= '%6.1f %s' % (self.d[k], bargraph(self.d[k]*-1,-25,25,50,'Y'))
                elif k == 'speedZ':
                    strout= '%6.1f %s' % (self.d[k], bargraph(self.d[k],-13,13,50,'Z'))
                elif k == 'z':
                    strout= '%6.3f %s' % (self.d[k], bargraph(self.d[k],.3,.5,50,'z'))
                elif k == 'trackPos': # This gets reversed for display to make sense.
                    cx='<'
                    if self.d[k]<0: cx= '>'
                    strout= '%6.3f %s' % (self.d[k], bargraph(self.d[k]*-1,-1,1,50,cx))
                elif k == 'stucktimer':
                    if self.d[k]:
                        strout= '%3d %s' % (self.d[k], bargraph(self.d[k],0,300,50,"'"))
                    else: strout= 'Not stuck!'
                elif k == 'rpm':
                    g= self.d['gear']
                    if g < 0:
                        g= 'R'
                    else:
                        g= '%1d'% g
                    strout= bargraph(self.d[k],0,10000,50,g)
                elif k == 'angle':
                    asyms= [
                          "  !  ", ".|'  ", "./'  ", "_.-  ", ".--  ", "..-  ",
                          "---  ", ".__  ", "-._  ", "'-.  ", "'\.  ", "'|.  ",
                          "  |  ", "  .|'", "  ./'", "  .-'", "  _.-", "  __.",
                          "  ---", "  --.", "  -._", "  -..", "  '\.", "  '|."  ]
                    rad= self.d[k]
                    deg= int(rad*180/PI)
                    symno= int(.5+ (rad+PI) / (PI/12) )
                    symno= symno % (len(asyms)-1)
                    strout= '%5.2f %3d (%s)' % (rad,deg,asyms[symno])
                elif k == 'skid': # A sensible interpretation of wheel spin.
                    frontwheelradpersec= self.d['wheelSpinVel'][0]
                    skid= 0
                    if frontwheelradpersec:
                        skid= .5555555555*self.d['speedX']/frontwheelradpersec - .66124
                    strout= bargraph(skid,-.05,.4,50,'*')
                elif k == 'slip': # A sensible interpretation of wheel spin.
                    frontwheelradpersec= self.d['wheelSpinVel'][0]
                    slip= 0
                    if frontwheelradpersec:
                        slip= ((self.d['wheelSpinVel'][2]+self.d['wheelSpinVel'][3]) -
                              (self.d['wheelSpinVel'][0]+self.d['wheelSpinVel'][1]))
                    strout= bargraph(slip,-5,150,50,'@')
                else:
                    strout= str(self.d[k])
            out+= "%s: %s\n" % (k,strout)
        return out

class DriverAction():
    '''What the driver is intending to do (i.e. send to the server).
    Composes something like this for the server:
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus 0)(meta 0) or
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus -90 -45 0 45 90)(meta 0)'''
    def __init__(self):
       self.actionstr= str()
       self.d= { 'accel':0.2,
                   'brake':0,
                  'clutch':0,
                    'gear':1,
                   'steer':0,
                   'focus':[-90,-45,0,45,90],
                    'meta':0
                    }

    def clip_to_limits(self):
        """There pretty much is never a reason to send the server
        something like (steer 9483.323). This comes up all the time
        and it's probably just more sensible to always clip it than to
        worry about when to. The "clip" command is still a snakeoil
        utility function, but it should be used only for non standard
        things or non obvious limits (limit the steering to the left,
        for example). For normal limits, simply don't worry about it."""
        self.d['steer']= clip(self.d['steer'], -1, 1)
        self.d['brake']= clip(self.d['brake'], 0, 1)
        self.d['accel']= clip(self.d['accel'], 0, 1)
        self.d['clutch']= clip(self.d['clutch'], 0, 1)
        if self.d['gear'] not in [-1, 0, 1, 2, 3, 4, 5, 6]:
            self.d['gear']= 0
        if self.d['meta'] not in [0,1]:
            self.d['meta']= 0
        if type(self.d['focus']) is not list or min(self.d['focus'])<-180 or max(self.d['focus'])>180:
            self.d['focus']= 0

    def __repr__(self):
        self.clip_to_limits()
        out= str()
        for k in self.d:
            out+= '('+k+' '
            v= self.d[k]
            if not type(v) is list:
                out+= '%.3f' % v
            else:
                out+= ' '.join([str(x) for x in v])
            out+= ')'
        return out
        return out+'\n'

    def fancyout(self):
        '''Specialty output for useful monitoring of bot's effectors.'''
        out= str()
        od= self.d.copy()
        od.pop('gear','') # Not interesting.
        od.pop('meta','') # Not interesting.
        od.pop('focus','') # Not interesting. Yet.
        for k in sorted(od):
            if k == 'clutch' or k == 'brake' or k == 'accel':
                strout=''
                strout= '%6.3f %s' % (od[k], bargraph(od[k],0,1,50,k[0].upper()))
            elif k == 'steer': # Reverse the graph to make sense.
                strout= '%6.3f %s' % (od[k], bargraph(od[k]*-1,-1,1,50,'S'))
            else:
                strout= str(od[k])
            out+= "%s: %s\n" % (k,strout)
        return out

def destringify(s):
    '''makes a string into a value or a list of strings into a list of
    values (if possible)'''
    if not s: return s
    if type(s) is str:
        try:
            return float(s)
        except ValueError:
            print("Could not find a value in %s" % s)
            return s
    elif type(s) is list:
        if len(s) < 2:
            return destringify(s[0])
        else:
            return [destringify(i) for i in s]


def drive_example(c):
    '''This is only an example. It will get around the track but the
    correct thing to do is write your own `drive()` function.'''
    S,R= c.S.d,c.R.d
    target_speed=160

    R['steer']= S['angle']*25 / PI
    R['steer']-= S['trackPos']*.25

    R['accel'] = max(0.0, min(1.0, R['accel']))

    if S['speedX'] < target_speed - (R['steer']*2.5):
        R['accel']+= .4
    else:
        R['accel']-= .2
    if S['speedX']<10:
       R['accel']+= 1/(S['speedX']+.1)

    if ((S['wheelSpinVel'][2]+S['wheelSpinVel'][3]) -
       (S['wheelSpinVel'][0]+S['wheelSpinVel'][1]) > 2):
       R['accel']-= 0.1

    R['gear']=1
    if S['speedX']>60:
        R['gear']=2
    if S['speedX']>100:
        R['gear']=3
    if S['speedX']>140:
        R['gear']=4
    if S['speedX']>190:
        R['gear']=5
    if S['speedX']>220:
        R['gear']=6
    return

#############################################
# MODULAR DRIVE LOGIC WITH USER PARAMETERS  #
# Corkscrew
#############################################

import math
import csv
import time


# TELEMETRY LOGGER

class TelemetryLogger:
    def __init__(self, filename=None):
        if filename is None:
            filename = "torcs_log_%s.csv" % time.strftime("%Y%m%d_%H%M%S")
        self.filename = filename
        self.file = open(self.filename, 'w', newline='')
        self.writer = csv.writer(self.file)
        self.writer.writerow([
            'step', 'distFromStart', 'speedX', 'trackPos', 'angle',
            'steer', 'accel', 'brake', 'gear',
            'track_ahead', 'track_left', 'track_right',
            'rpm', 'laptime', 'brake_reason', 'steer_capped'
        ])
        self.step = 0
        self._last_dist = 0
        self._lap_start_step = 0
        self._lap_count = 0
        print("[Logger] Writing telemetry to: %s" % self.filename)

    def log(self, S, R, extras=None):
        extras = extras or {}
        track = S.get('track', [])
        ahead = min(track[7:12]) if len(track) >= 19 else -1
        left  = min(track[0:5])  if len(track) >= 19 else -1
        right = min(track[14:19]) if len(track) >= 19 else -1
        dist  = S.get('distFromStart', 0)
        if self._last_dist > 500 and dist < 100:
            self._lap_count += 1
            steps_this_lap = self.step - self._lap_start_step
            print("[Lap %d] ~%d steps (%.1fs)"
                  % (self._lap_count, steps_this_lap, steps_this_lap / 50.0))
            self._lap_start_step = self.step
        self._last_dist = dist
        self.writer.writerow([
            self.step, round(dist, 1), round(S.get('speedX', 0), 2),
            round(S.get('trackPos', 0), 4), round(S.get('angle', 0), 4),
            round(R.get('steer', 0), 4), round(R.get('accel', 0), 4),
            round(R.get('brake', 0), 4), R.get('gear', 1),
            round(ahead, 1), round(left, 1), round(right, 1),
            round(S.get('rpm', 0), 0), round(S.get('lastLapTime', 0), 2),
            extras.get('brake_reason', ''), extras.get('steer_capped', False)
        ])
        self.step += 1

    def close(self):
        self.file.close()
        print("[Logger] Saved: %s" % self.filename)


# ================================================================
# USER CONFIGURABLE PARAMETERS
# ================================================================

TARGET_SPEED            = 220
STEER_GAIN              = 22
CENTERING_GAIN          = 0.35
BRAKE_THRESHOLD         = 0.30
GEAR_SPEEDS = [0, 45, 95, 140, 160, 190]
ENABLE_TRACTION_CONTROL = True

_CORNER_SPEED           = 72
_CORNER_STEER_THRESHOLD = 0.38
_VERY_SHARP_SPEED       = 54
_VERY_SHARP_THRESHOLD   = 0.62

_LAUNCH_STEPS           = 25


_WALL_RECOVERY_SPEED    = 32
MAX_BRAKE       = 0.72
_RAMP_DIVISOR   = 90


_HIGHSPEED_ENTRY_SPEED   = 140
_HIGHSPEED_ENTRY_AHEAD   = 52 
_HIGHSPEED_ENTRY_TARGET  = 90
_HIGHSPEED_ENTRY_CEILING = 0.82

_CORKSCREW_BRAKE_START = 2375.0
_CORKSCREW_BRAKE_END   = 2405.0
_CORKSCREW_ENTRY_TARGET = 72.0
_CORKSCREW_CREST_START = 2410.0
_CORKSCREW_CREST_END   = 2445.0
_CORKSCREW_CREST_SPEED = 70.0

_FINAL_CORNER_BRAKE_START = 3220.0
_FINAL_CORNER_BRAKE_END   = 3310.0
_FINAL_CORNER_TARGET_SPEED = 60.0
_FINAL_STRAIGHT_START = 3315.0
_FINAL_STRAIGHT_END   = 3608.0

_MEDIUM_ENTRY_SPEED  = 85
_MEDIUM_ENTRY_TARGET = 58
_MEDIUM_ENTRY_AHEAD  = 55

# LAUNCH CONTROL

def launch_control(S, R, step):
    """Unchanged — clutch window 0–4 steps."""
    if step < _LAUNCH_STEPS and S.get('speedX', 0) < 2.0:
        R['gear']   = 1
        R['accel']  = 1.0
        R['brake']  = 0.0
        R['steer']  = 0.0
        R['clutch'] = 0.5 if step < 5 else 0.0
        return True
    return False


# TRACK READING — HELPER FUNCTIONS

def track_lookahead(S):
    """Raw minimum distance from central 5 sensors (indices 7-11)."""
    track = S.get('track', [])
    if not track or len(track) < 19:
        return 200
    return min(track[7:12])

def track_side_sensors(S):
    track = S.get('track', [])
    if not track or len(track) < 19:
        return 200, 200
    return min(track[0:5]), min(track[14:19])

def wall_filtered_lookahead(S):

    ahead     = track_lookahead(S)
    speed     = S.get('speedX', 0)
    track_pos = S.get('trackPos', 0)
    angle     = abs(S.get('angle', 0))

    if abs(track_pos) > 0.28:
        return ahead
    if angle > 0.12:
        return ahead
    if speed > 85:
        return ahead
    if ahead < 45:
        return 200

    return ahead

# STEERING CONTROL

def calculate_steering(S):
    speed = S.get('speedX', 0)
    effective_gain = 12.0 + (STEER_GAIN - 12.0) * min(speed / 160.0, 1.0)
    angle_steer  = S['angle'] * effective_gain / math.pi

    track_offset = S['trackPos']


    ahead = wall_filtered_lookahead(S)
    left, right = track_side_sensors(S)
    corner_approaching = 18 < ahead < 55 and speed > 60 and not is_corkscrew_crest(S)
    if corner_approaching:
        side_diff = left - right
        pre_rotate_gain = 0.006
        pre_rotate = pre_rotate_gain * side_diff * (ahead / 35.0)
        angle_steer += pre_rotate



    dist = S.get('distFromStart', 0)
    _in_final_exit = 3275.0 <= dist <= 3410.0

    if speed > 140 and abs(track_offset) < 0.30:
        raw_steer = angle_steer
        capped = False
        if speed > 95:
            max_steer = max(0.72, 1.0 - (speed - 95) / 200.0)
            if abs(raw_steer) > max_steer:
                raw_steer = max(-max_steer, min(max_steer, raw_steer))
                capped = True
        return max(-1.0, min(1.0, raw_steer)), capped

    wall_pinned = abs(track_offset) > 0.78 and speed < _WALL_RECOVERY_SPEED
    if wall_pinned:
        recovery_gain = 0.72
        raw_steer = angle_steer - track_offset * recovery_gain
        return max(-1.0, min(1.0, raw_steer)), False



    _in_final_entry = 3215.0 <= dist <= 3262.0
    if _in_final_entry:
        position_error = S['trackPos'] - (-0.30)
        entry_correction = position_error * 0.65
        raw_steer = angle_steer - entry_correction
        return max(-1.0, min(1.0, raw_steer)), False
    
    steer_magnitude = abs(angle_steer)



    if abs(track_offset) > 0.6:
        base_centering = 1.0 if steer_magnitude > _VERY_SHARP_THRESHOLD else 0.85
        centering = track_offset * (base_centering * 0.35 if _in_final_exit else base_centering)
    elif abs(track_offset) > 0.35:
        base_centering = 0.70 if steer_magnitude > _VERY_SHARP_THRESHOLD else 0.55
        centering = track_offset * (base_centering * 0.50 if _in_final_exit else base_centering)
    else:
        centering = track_offset * CENTERING_GAIN

    if angle_steer * centering > 0:
        raw_steer = angle_steer
    else:
        raw_steer = angle_steer - centering

    capped = False
    if speed > 95:
        max_steer = max(0.72, 1.0 - (speed - 95) / 200.0)
        if abs(raw_steer) > max_steer:
            raw_steer = max(-max_steer, min(max_steer, raw_steer))
            capped = True

    return max(-1.0, min(1.0, raw_steer)), capped

# THROTTLE CONTROL

def calculate_throttle(S, steer):
    """ahead < 75 cap. Unchanged."""
    if abs(steer) > _VERY_SHARP_THRESHOLD:
        speed_target = _VERY_SHARP_SPEED
    elif abs(steer) > _CORNER_STEER_THRESHOLD:
        speed_target = _CORNER_SPEED
    else:
        speed_target = TARGET_SPEED

    ahead = wall_filtered_lookahead(S)

    if ahead < 20:
        speed_target = min(speed_target, _VERY_SHARP_SPEED)
    elif ahead < 50:
        speed_target = min(speed_target, _CORNER_SPEED)
    elif ahead < 75:
        speed_target = min(speed_target, TARGET_SPEED * 0.92)   # = 202.4 km/h

    if S['speedX'] < speed_target * 0.93:
        accel = 1.0
    elif S['speedX'] < speed_target:
        accel = 0.82
    else:
        accel = max(0.0, 1.0 - (S['speedX'] - speed_target) / 18.0)

    if S['speedX'] < 5:
        accel = 0.8
    return accel


# BRAKE CONTROL

def apply_brakes(S, steer):
    angle_danger = abs(S['angle']) > BRAKE_THRESHOLD
    very_near_edge = abs(S['trackPos']) > 0.80
    very_sharp_corner = (abs(steer) > _VERY_SHARP_THRESHOLD and S['speedX'] > _VERY_SHARP_SPEED + 10)
    sharp_corner = (abs(steer) > _CORNER_STEER_THRESHOLD and S['speedX'] > _CORNER_SPEED + 15)

    ahead_raw = track_lookahead(S)
    ahead_filtered = wall_filtered_lookahead(S)
    dist = S.get('distFromStart', 0)

    if _FINAL_CORNER_BRAKE_START <= dist <= _FINAL_CORNER_BRAKE_END:
        excess = max(S['speedX'] - _FINAL_CORNER_TARGET_SPEED, 0)
        if excess > 0:
            force = min(excess / 60.0, 0.92)
            return force, 'final_corner_zone'



    if _CORKSCREW_BRAKE_START <= dist <= _CORKSCREW_BRAKE_END:
        excess = max(S['speedX'] - _CORKSCREW_ENTRY_TARGET, 0)
        if excess > 0:
            force = min(excess / 48.0, 0.78)
            return force, 'corkscrew_pre_crest'

    angle_danger = abs(S['angle']) > BRAKE_THRESHOLD

    if _FINAL_STRAIGHT_START <= dist <= _FINAL_STRAIGHT_END:
        return 0.0, ''
    if ahead_filtered < 20 and S['speedX'] > 55:

        if _CORKSCREW_CREST_START <= dist <= _CORKSCREW_CREST_END:
            return 0.0, 'corkscrew_crest_gate'

        already_turning = abs(steer) > 0.25 or abs(S.get('angle', 0)) > 0.04
        if already_turning:
            return 0.0, ''

        proximity = max(0.0, (20 - ahead_filtered) / 15.0)
        force = 0.5 + 0.4 * proximity
        return min(force, 0.9), 'emergency_wall'

    def compute_brake_force(target_speed, ceiling=MAX_BRAKE):
        excess = max(S['speedX'] - target_speed, 0)
        return min(excess / _RAMP_DIVISOR, ceiling)

    if ahead_filtered < _HIGHSPEED_ENTRY_AHEAD and S['speedX'] > _HIGHSPEED_ENTRY_SPEED:
        excess = max(S['speedX'] - _HIGHSPEED_ENTRY_TARGET, 0)
        force  = min(excess / 55.0, _HIGHSPEED_ENTRY_CEILING)
        return force, 'highspeed_entry'
    if _CORKSCREW_CREST_START <= dist <= _CORKSCREW_CREST_END:
        return 0.0, 'corkscrew_crest_gate'

    if ahead_filtered < 40 and S['speedX'] > 105:
        return compute_brake_force(105), 'mid_range_wall'

    if ahead_filtered < 80 and S['speedX'] > 155:
        return compute_brake_force(155), 'pre_corner_far'

    if ahead_filtered < 65 and S['speedX'] > 125:
        return compute_brake_force(115), 'pre_corner_near'


    if very_near_edge and S['speedX'] > 30:
        if _FINAL_STRAIGHT_START <= dist <= _FINAL_STRAIGHT_END:
            return 0.0, ''
        if abs(steer) < 0.55:
            edge_depth = max(0.0, abs(S['trackPos']) - 0.80) / 0.30
            edge_brake = 0.12 + 0.23 * min(edge_depth, 1.0)
            return edge_brake, 'edge_danger'
        return 0.0, ''

    if angle_danger and S['speedX'] > _CORNER_SPEED:
        return compute_brake_force(_CORNER_SPEED, 0.5), 'angle_danger'

    if very_sharp_corner:
        return compute_brake_force(_VERY_SHARP_SPEED + 10, 0.5), 'very_sharp'

    if sharp_corner and S['speedX'] > 80:
        return compute_brake_force(80), 'sharp_fast'

    if sharp_corner:
        return compute_brake_force(70, 0.35), 'sharp_slow'


    
    return 0.0, ''


# GEAR SHIFTING

def shift_gears(S):
    """Unchanged."""
    gear = 1
    for i, speed in enumerate(GEAR_SPEEDS):
        if S['speedX'] > speed:
            gear = i + 1
    return min(gear, 6)


# TRACTION CONTROL

def traction_control(S, accel):
    """Unchanged."""
    if ENABLE_TRACTION_CONTROL:
        spin_diff = ((S['wheelSpinVel'][2] + S['wheelSpinVel'][3]) -
                     (S['wheelSpinVel'][0] + S['wheelSpinVel'][1]))
        if spin_diff > 3:
            accel -= 0.05
    return max(0.0, accel)


# STUCK RECOVERY

_stuck_counter = 0

def recover_if_stuck(S, R):
    """Unchanged."""
    global _stuck_counter
    going_backward     = S['speedX'] < -2.0
    crawling_near_wall = S['speedX'] < 3.0 and abs(S['trackPos']) > 0.82
    if going_backward or crawling_near_wall:
        _stuck_counter += 1
    else:
        _stuck_counter = 0

    if _stuck_counter > 20:
        R['gear']  = -1
        R['accel'] = 0.6
        R['brake'] = 0.0
        R['steer'] = -R['steer']
        if _stuck_counter > 70:
            _stuck_counter = 0
        return True
    return False



# CORKSCREW CREST

def is_corkscrew_crest(S):
    """Returns True only when car is on-track in the blind-crest zone.
    If trackPos is dangerously off-centre, normal steering must resume."""
    d = S.get('distFromStart', 0)
    track_pos = S.get('trackPos', 0)
    # NEW: if car is off-track or badly off-centre, never suppress steering
    if abs(track_pos) > 0.55 or track_pos < -3.0:
        return False
    return _CORKSCREW_CREST_START <= d <= _CORKSCREW_CREST_END

# MAIN DRIVE FUNCTION
def drive_modular(c, logger=None):
    S, R = c.S.d, c.R.d
    step = logger.step if logger else 0

    if launch_control(S, R, step):
        if logger:
            logger.log(S, R, {'brake_reason': 'launch', 'steer_capped': False})
        return

    if recover_if_stuck(S, R):
        if logger:
            logger.log(S, R, {'brake_reason': 'stuck_recovery', 'steer_capped': False})
        return

    steer, capped = calculate_steering(S)
    R['steer']    = steer

    #  CORKSCREW CREST: suppress all braking
    if is_corkscrew_crest(S):
        speed_now = S.get('speedX', 0)
        if speed_now > _CORKSCREW_CREST_SPEED:
            excess = speed_now - _CORKSCREW_CREST_SPEED
            R['brake'] = min(0.12 + excess / 120.0, 0.45)
            R['accel'] = 0.0
        else:
            R['brake'] = 0.0
            R['accel'] = 0.35 



        track_pos = S.get('trackPos', 0)

        centering_correction = track_pos * 0.55
        raw_crest_steer = S['angle'] * 8.0 / math.pi - centering_correction
        raw_crest_steer = max(-0.30, min(0.30, raw_crest_steer))

        R['steer'] = raw_crest_steer
        R['gear'] = shift_gears(S)
        if logger:
            logger.log(S, R, {'brake_reason': 'corkscrew_crest_gate', 'steer_capped': capped})
        return

    R['accel']    = calculate_throttle(S, steer)
    brake, reason = apply_brakes(S, steer)
    R['brake']    = brake

    if R['brake'] > 0.2:
        R['accel'] = 0.0

    R['accel'] = traction_control(S, R['accel'])
    R['gear']  = shift_gears(S)

    if logger:
        logger.log(S, R, {'brake_reason': reason, 'steer_capped': capped})

# MAIN LOOP

if __name__ == "__main__":
    logger = TelemetryLogger()
    C = Client(p=3001)
    try:
        for step in range(C.maxSteps, 0, -1):
            C.get_servers_input()
            drive_modular(C, logger=logger)
            C.respond_to_server()
    finally:
        C.shutdown()
        logger.close()