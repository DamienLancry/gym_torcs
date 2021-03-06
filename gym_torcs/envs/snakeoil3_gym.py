#!/usr/bin/python
# Inspired by snakeoil.py by Chris Edward
# for Python3-based torcs python robot client
import socket
import sys
PI = 3.14159265359
data_size = 1024


def clip(v, lo, hi):
    if v < lo:
        return lo
    elif v > hi:
        return hi
    else:
        return v


class Client():
    def __init__(self, port=3001):
        self.host = 'localhost'
        self.sid = 'SCR'
        self.maxEpisodes = 1  # Maximum number of learning episodes to perform
        self.trackname = 'unknown'
        self.stage = 3        # 0=Warm-up, 1=Qualifying 2=Race, 3=unknown
        self.port = port
        self.S = ServerState()
        self.R = DriverAction()
        self.setup_connection()

    def setup_connection(self):
        # == Set Up UDP Socket ==
        self.so = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # == Initialize Connection To Server ==
        self.so.settimeout(1)
        while True:
            a = "-90 -80 -70 -60 -50 -40 -30 -20 -10 0 10 20 30 40 50 60 70 80 90"
            initmsg = '%s(init %s)' % (self.sid, a)
            # try:
            # print('\033[93m'+'Client sending initmsg'+'\033[0m')
            self.so.sendto(initmsg.encode(), (self.host, self.port))
            sockdata = str()
            try:
                sockdata, addr = self.so.recvfrom(16)
                sockdata = sockdata.decode('utf-8')
                # print("Client receiving identified")
            except socket.error as emsg:
                continue

            identify = '***identified***'  # 16 bits
            if identify in sockdata:
                # print("Client connected on %d.............." % self.port)
                break

    def get_servers_input(self):
        '''Server's input is stored in a ServerState object'''
        sockdata = str()

        while True:
            sockdata, addr = self.so.recvfrom(data_size)  # ~600 bits
            sockdata = sockdata.decode('utf-8')
            if '***identified***' in sockdata:
                print("Client connected on %d.............." % self.port)
                continue
            elif '***shutdown***' in sockdata:
                self.shutdown()
                return
            elif '***restart***' in sockdata:
                print("Server has restarted the race on %d." % self.port)
                return
            else:
                self.S.str_to_dict(sockdata)
                break

    def respond_to_server(self):
        if not self.so:
            return
        try:
            message = repr(self.R)  # dict to string understandable by server
            self.so.sendto(message.encode(), (self.host, self.port))
            # print("Client sent ",end='')
            # print(message.encode())
        except socket.error as emsg:
            print("Error sending to server: %s Message %s" % (emsg[1], str(emsg[0])))
            sys.exit(-1)

    def shutdown(self):
        if not self.so:
            return
        print("Race terminated. Shutting down %d." % self.port)
        self.so.close()
        self.so = None
        exit(0)


class ServerState():
    '''What the server is reporting right now.'''
    def __init__(self):
        self.servstr = str()
        self.d = dict()

    def str_to_dict(self, server_string):
        '''Parse the server string.'''
        keyvalues_str = server_string[1:-2].split(')(')
        for i in keyvalues_str:
            kv = i.split(' ')
            self.d[kv[0]] = float(kv[1]) if len(kv[1:]) == 1 else [float(item) for item in kv[1:]]


class DriverAction():
    '''
    What the driver is intending to do (i.e. send to the server).
    Composes something like this for the server:
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus 0)(meta 0) or
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus -90 -45 0 45 90)(meta 0)
    '''
    def __init__(self):
        self.d = {'accel' : .2,
                  'brake' : 0.,
                  'clutch': 0.,
                  'gear'  : 1.,
                  'steer' : 0.,
                  'focus' : [-90, -45, 0, 45, 90],
                  'meta'  : 0.
                  }

    def __repr__(self):  # convert dict to string understandable by server
        out = str()
        for key, value in self.d.items():
            if not type(value) is list:
                value_str = '%.3f' % value
            else:
                value_str = ' '.join([str(x) for x in value])
            out += '(%s %s)' % (key, value_str)
        return out

def drive_example(c):
    '''This is only an example. It will get around the track but the
    correct thing to do is write your own `drive()` function.'''
    S, R = c.S.d, c.R.d
    target_speed = 100
    # Steer To Corner
    R['steer'] = S['angle']*10 / PI
    # Steer To Center
    R['steer'] -= S['trackPos']*.10
    # Throttle Control
    if S['speedX'] < target_speed - (R['steer']*50):
        R['accel'] += .01
    else:
        R['accel'] -= .01
    if S['speedX'] < 10:
        R['accel'] += 1/(S['speedX']+.1)
    # Clip to limits
    R['steer'] = clip(R['steer'], -1, 1)
    R['brake'] = clip(R['brake'], 0, 1)
    R['accel'] = clip(R['accel'], 0, 1)
    R['clutch'] = clip(R['clutch'], 0, 1)
    if R['gear'] not in [-1, 0, 1, 2, 3, 4, 5, 6]:
        R['gear'] = 0
    if R['meta'] not in [0, 1]:
        R['meta'] = 0
    if type(R['focus']) is not list or min(R['focus']) < -180 or max(R['focus']) > 180:
        R['focus'] = 0
    return


if __name__ == "__main__":
    C = Client()
    while(True):
        C.get_servers_input()
        drive_example(C)
        C.respond_to_server()
    C.shutdown()
