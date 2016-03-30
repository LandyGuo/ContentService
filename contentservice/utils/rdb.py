'''
Python Remote Debugger

Debug on a remote running python process

@author: Yu Xia
'''

import pdb, signal, sys, os, socket, select, time

_ADDR = (("127.0.0.1", 31017))
_SERVER = None
_CLIENT = None

class Rdb(pdb.Pdb):

    def __init__(self, addr):
        self.old_stdout = sys.stdout
        self.old_stdin = sys.stdin

        #open a socket listening for debugger
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.serversocket.bind(addr)
        self.serversocket.listen(1)
        (self.clientsocket, address) = self.serversocket.accept()
        self.serversocket.close()
        
        #redirect stdin/stdout to the debugger socket
        handle = self.clientsocket.makefile('rw')
        pdb.Pdb.__init__(self, stdin=handle, stdout=handle)
        sys.stdout = sys.stdin = handle
    
    def shutdown(self):
        #close socket
        self.clientsocket.close()

        #restore stdin/stdout
        sys.stdout = self.old_stdout
        sys.stdin = self.old_stdin
        self.stdout = sys.stdout
        self.stdin = sys.stdin
        
        #clear all breaks and continue running
        self.clear_all_breaks()
        self.set_continue()


def on_debugger_connect(sig, frame):
    global _SERVER
    if not _SERVER:
        _SERVER = Rdb(_ADDR)
        _SERVER.set_trace(frame)

def on_debugger_disconnect(sig, frame):
    global _SERVER
    if _SERVER:
        _SERVER.shutdown()
        _SERVER = None

def listen():
    signal.signal(signal.SIGUSR1, on_debugger_connect)
    signal.signal(signal.SIGUSR2, on_debugger_disconnect)
    
    

class RdbClient(object):
    
    def __init__(self, pid):
        self.pid = pid
        self.sock = None

    def start_debug(self):
        #Send open signal to server
        os.kill(pid, signal.SIGUSR1)
    
        #wait for server to open socket
        time.sleep(0.5)
        
        #connect to server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect(_ADDR)
        except:
            os.kill(pid, signal.SIGUSR2) #connect error. Send close signal
            raise
    
        print "Connected to process %s" % self.pid
        print "Press ^C to exit debugger. (The target program will resume running)"
    
        while True:
            socket_list = [sys.stdin, self.sock]

            try:
                read_sockets, write_sockets, error_sockets = select.select(socket_list , [], [])
            except select.error:
                #interrupted exception on exit 
                return
            
            for sock in read_sockets:
                #incoming message from server
                if sock == self.sock:
                    data = sock.recv(8192)
                    if not data :
                        print 'Connection closed by server'
                        return
                    else :
                        sys.stdout.write(data)
                        sys.stdout.flush()
                        
                #user enter commands 
                else :
                    msg = sys.stdin.readline()
                    self.sock.send(msg)
                        
    def end_debug(self):
        if self.sock:
            #clear all breakpoints (with confirm) and continue running
            self.sock.send("clear\n")
            self.sock.send("y\n")
            self.sock.send("c\n")
            
            #wait for server to finish processing commands
            time.sleep(0.5) 
            
            #send close signal to server
            os.kill(pid, signal.SIGUSR2)


def on_end_debug(sig, frame):
    if _CLIENT:
        _CLIENT.end_debug()
        print "\nConnection closed"


if __name__=='__main__':
    if len(sys.argv) != 2:
        print "Error: Must provide process id to debug"
    else:    
        pid = int(sys.argv[1])
        
        signal.signal(signal.SIGINT, on_end_debug)
        signal.signal(signal.SIGTERM, on_end_debug)
        
        _CLIENT = RdbClient(pid)
        _CLIENT.start_debug()
