"""
Listen to serial, return most recent numeric values
Haven't implemented buffer flush :(
- if power disconnected then last value keeps pushing
"""

import time
import serial
import re
import os
import datetime
import threading
import logging
#import sys #passing cmd line arguments

l_err = 0
err = ['','Underrange','Overrange','Sensor Error','Sensor Off','No Sensor','Identification Error']

  

class MksPressure(threading.Thread):
    def __init__(self,readDelay,comport): #Constructor for the class
        threading.Thread.__init__(self)
        self.readDelay=readDelay
        self.keepGoing=True
        try:
            self.ser = serial.Serial(
                port=comport,
                #port=sys.argv[1], # Update depending on port name. Linux: /dev/tty___
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=2, # Play with this number for timeout
                xonxoff=0,
                rtscts=0,
                interCharTimeout=None #Check compatibility with particular version of PySerial
            )
        except:
            logging.exception("Exception in read_pressure.py--probably no pressure sensor detected or wrong com port")
            self.keepGoing=False
        logging.info(f'Serial Connection to MKS pressure sensor opened on {self.ser.port}')
        self.buffer=""
        self.data = queue.Queue()


    def stop(self):
        self.keepGoing=False
        logging.info("stopping pressure read")
        if self.ser:

            logging.info('Serial port closed')
            self.ser.close()

    def run(self):
        while self.keepGoing:
            time.sleep(readDelay)
            self.data.put_nowait(self.next())

    def next(self):
        if ser.isOpen():
            self.buffer = self.buffer + self.ser.read(self.ser.in_waiting())

            # We can't guarantee that the data we've read from serial
            # is a whole message. Therefore we use the "buffer" variable
            # to store recent data.
            # the data stream looks like this:
            # ...data\nmoredata\nevenmoredata\n...
            # So when we read the serial data, we might get something like
            # "dat"
            # so in that case we return nothing.
            # On the next call, we might get
            # "a\nmored"
            # so we append that to the buffer. Now the buffer contains a '\n'
            # buffer: "data\nmored"
            # so we return "data" and now the buffer contains
            # buffer: "mored", rinse and repeat.
            # If the pressure sensor is sptting out data faster than we want,
            # say we receive "data\nmoredata\nevenmo"
            # we ignore "data" return "moredata" and then wait
            if '\n' in self.buffer:
                lines = self.buffer.split('\n')
                if lines[-2]:
                    last_received = lines[-2] 
                self.buffer = lines[-1] 
            else:
                last_received="-1" #Don't have a full datapoint yet
        else:
            last_received='5'
            #return err 5 when device isn't connected
        raw_line = last_received
        id_state = re.split(',', raw_line, 4)
        while len(id_state<5):
            id_state.append(None)

        id_state.append(time.time())
        # print id_state #debug
        
        return id_state
        #Format of id_state is as follows:
        #array elem: value
        #0: error code ('0' is no error)
        #1: last message (usually a str representation of a float) 
        #5: time.time() when data was collected 

     

if __name__=='__main__':
    
    #global st_time
    header_written = False
    start_time=time.time()
    #Go to the directory where we are storing logs

    s = SerialData()
    if s.ser != None:
        # let the stream get data
        str_time = time.ctime(start_time)
        header = '# Data recording started at: '+str_time+'\n'
        print(header)

        dirname = "./PressureData/"
        if not os.path.isdir(dirname):
            os.mkdir(dirname)

        #Create separate log files for each day
        outf = open(f'{dirname}{datetime.date.today()}.dat','a')
        
        outf.write(header)
        header_written=True
        #time.sleep(1)
        
    try:
        while s.ser:
            id_state = s.next()
            err_code=int(id_state[0])
            if err_code > 0:
                l_err=err_code
                print(f"error: {err[err_code]} (code {err_code})")

            elif err_code == 0:
                pressure=id_state[1]
                timestamp=id_state[-1]
                print(f"pressure: {pressure} \t time: {timestamp}")
                outf.write(f"{timestamp}\t{pressure}\n")

            else:
                time.sleep(0.33)#depending on polling mode
                    #(fine - 100ms, normal - 1s, slow - 1 min)
            
    except KeyboardInterrupt:
        if header_written:
            end_time = time.ctime()
            footer = '\n# Data recording stopped at: '+end_time+'\n\n'
            print footer
            outf.write(footer)
            outf.close()

    finally:

        print 'Watiting one second before quit for some reason.'
        time.sleep(1)
