#-----------------------------------------------------
#  B&B Vlinx Ethernet Serial server i/o
#
#       open, close, read, write
#
#  NOTE THIS VERSION OF etherser.py
#     IS FOR zheatsw ADR heat switch and z40_4Ksw 40K-4K heat switch,
#     NOT for z2acq grating control
#-----------------------------------------------------
import socket
import string
import sys

class etherserial:

    timeout = 0.2 # seconds; expect complete returned line from any query 
    Ser_IP   = None
    Ser_PORT = None
    serhost = (None, None)
    sersock = None
    connected = False
    verbose = False

    doTimeoutProc = False # execute timeout error procedure in caller
    parent = None  # if doTimeoutProc, assume parent.TimoutProc() is avail.

    def open(self, addr='localhost', port=4000):
        self.Ser_IP = addr
        self.Ser_PORT = port
        self.serhost=(self.Ser_IP,self.Ser_PORT)
        print 'connecting to serial host: ',self.serhost
        try:
            self.sersock = socket.create_connection(self.serhost, None) #no t.o.
        except socket.error:
            print '\n----------------------------'
            print 'failed to connect %s port %d'%(self.Ser_IP,self.Ser_PORT)
            print '----------------------------'
            return True

        self.sersock.settimeout(self.timeout) 
        self.connected = True
        return False

    def close(self):
        if self.sersock != None:
            print 'disconnecting from serial host'
            self.sersock.shutdown(socket.SHUT_RDWR)  # was 1
            self.sersock.close()
            # self.sersock = None
        self.connected = False

    def phonetic(self, aline):
        aline = string.replace(aline, '\r', '\\r')
        # aline = string.replace(aline, '\n', '\\n')
        return aline

    def write(self, strin):
        if not self.connected:
          print 'not connected to Ethernet serial server - need open()'
          strp = self.phonetic(strin)
          print '[ would write: ',strp,' ]'
          return
        if self.verbose:
          print 'SERIAL OUT: ',self.phonetic(strin)
        ret = self.sersock.send(strin)
        slen = len(strin)
        if ret != slen:
          print ' *********** error ***********\n'
          print 'send string len = %d but send() returns %d\n'%(slen, ret)
        else:
          s2 = strin.strip("\r\n")

    def clear(self):          # return 1 if anything cleared, else 0
        ret = 0
        if not self.connected:
          print 'clear: not connected to Ethernet serial server - need open()'
          return ret
        rd = ''

        self.sersock.settimeout(0.0) 
        while True:
          try:
              rd = self.sersock.recv(1024)  # dont block
          except socket.error:    
              pass
          n = len(rd) 
          if n > 0:
              ret = 1
          if n < 1024:
              break
          rd = ''
        self.sersock.settimeout(self.timeout) 
        return ret

    def flush(self, nmax):
        rd = ''
        if not self.connected:
          print 'flush: not connected to Ethernet serial server - need open()'
          return rd

        try:
            rd = self.sersock.recv(nmax) # dont block 
        except socket.error:    
            rd = ''  # prob. not needed
            errno,errstr = sys.exc_info()[:2]
            if not errno == socket.timeout:
              print 'FLUSH; socket err: %s'%(errstr) # not '..',errstr
        return rd

    def readline(self):
        if not self.connected:
          print 'read: not connected to Ethernet serial server - need open()'
          return '-1\r' # NOT a PCL501 error code
        sline = ''
        fullline = ''
        ret = 0
        while not '\r' in fullline:
           try:
               sline = self.sersock.recv(128)  # block
           except socket.error:    
               errno,errstr = sys.exc_info()[:2]
               if errno == socket.timeout:
                 if self.doTimeoutProc:
                     self.parent.TimeoutProc()
                 print 'ERROR: ****************************'
                 print 'ERROR: TIMEOUT after %f sec'%self.sersock.gettimeout()
                 print 'ERROR: ****************************'
                 return '-1\r'
               else:
                 print 'ERROR: socket err: %s'%(errstr) # not '..',errstr
                 # self.connected = False
                 return '-1\r'
           fullline += sline
        if self.verbose:
          print 'serial  IN: ',self.phonetic(fullline)
        return fullline.strip('\r')
