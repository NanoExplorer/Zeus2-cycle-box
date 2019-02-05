import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from matplotlib.animation import FuncAnimation, writers
import Queue
import copy
import threading
import u6
import sys
import time
import signal
import traceback

MAX_REQUESTS=25
SENSORS_MAP={'GRT0-3':'AIN0',
             'GRT4-7':'AIN2',
             '2WIRE':'AIN4',
             '4WIRE':'AIN6',
             'Voltage':'AIN8',
             'Current':'AIN10' #Note that read out value is 20x actual current
}#Maps readable name of sensor to labjack name of sensor


#Other sensors from reverse-engineered labview code:
#Listed functions are what happen when the bit is set to ON
#dio 0   LSB     \
#DIO 1   MSB      |
#DIO 2   DISABLE  | GRT 0-3
#DIO 3   COLD    /
#DIO 4   LSB     \
#DIO 5   MSB      |         dio 4 5
#DIO 6   DISABLE /  GRT 4-6     1 0 reads GRT 5 for example
#DIO 7   LSB     \
#DIO 8   MSB      | 4WIRE 
#DIO 9   DISABLE /
#DIO 10  LSB      \
#DIO 11  2s place  |
#DIO 12  4s place  | 2WIRE
#DIO 13  DISABLE  /
#DIO 14  SERVO MODE
#DIO 15  2 LEDs hanging out of the 4wire - ON=GREEN OFF=RED
#DIO 16  Cycle box local vs remote????????? MAYBE no real idea.
#DIO 17 is set point reached indicator - 0 means set point reached
#dio 18 is quench
#dio 19 is computer/manual



#Ramp rate needs to be divided by 2
#set point current needs to be divided by 20

#LJioputdigitalbit 14 controls servo vs cycle
#That is also called be eio6
#For the bitstatewrite function, it looks like io0-7 are FIO, 8-15 are EIO and 16-19 are cio.


#The control thread interfaces nicely with the LJ thread. Now all I need is to 
#interface that with the plots thread and add the following features:
"""
wait until sensor has settled
fast/slow readout i.e. buttons
choose which sensors to readout buttons
control for x axis scale

PID loop
temperature interpolation


"""


class animatedplot():
    def __init__(self,size):
        #Writer = writers['ffmpeg']
        #writer = Writer(fps=15, metadata=dict(artist='Me'), bitrate=1800)
        self.size=size
        self.utiliz=[5,10]
        self.timearr=[5,10]
        
        self.going = True
        self.initPlots()

    def initPlots(self):
        self.fig,axs = plt.subplots(1,1)
        self.ax1=axs#[0]
        self.ln, = self.ax1.plot(self.timearr,self.utiliz)
        plt.subplots_adjust(hspace=.1)
        self.ax1.grid()
        self.ax1.grid(which='minor')
        plt.minorticks_on()
        plt.locator_params(nbins=5)
        #padding = datetime.timedelta(seconds=3)
        padding=1/24/60/60
        self.ax1.set_xlim(1,10)
        self.ax1.set_ylim(-0.01,0.01)
        plt.locator_params(nbins=5)
        xfmt = matplotlib.dates.DateFormatter('%Y-%m-%d\n%H:%M:%S')
        self.ax1.xaxis.set_major_formatter(xfmt)
        self.ax1.xaxis_date()

    def update(self,frame):
        #print("ANOTHER THING!")
        self.ln.set_data(self.timearr,self.utiliz)
        #print(self.timearr)
        try:
            self.ax1.set_xlim(np.min(self.timearr),np.max(self.timearr))
        except ValueError:
            pass
        #self.ax.figure.canvas.draw()
        return self.ln,
    def go(self):
        while self.going:
            self.anim = FuncAnimation(self.fig,self.update,frames = np.arange(200),
                  #init_func=self.animinit(),
                  interval=1000,
                  blit=False
            )
            plt.show()
            print("Exit this program with CTRL-C in terminal")
            self.initPlots()

class LogicThread(threading.Thread):
    def __init__(self,sdr,dataCollectionCond,plot):
        threading.Thread.__init__(self)
        self.keepGoing = True
        self.dcc=dataCollectionCond
        self.sdr=sdr
        self.data_archives = {}
        self.mostrecent = []
        self.current_setpoint = 0
        self.current_ramprate = 0
        self.plot = plot

    def run(self):
        with(self.dcc):
            while self.keepGoing:
                #print("waiting for cond")
                self.dcc.wait()

                #print("updating")
                self.update()

                
    def stop(self):
        #print("trying to stop?")
        with self.dcc:
            #print("got lock?")
            self.keepGoing = False
            self.sdr.running=False
            self.dcc.notifyAll()
    def update(self):
        #this is the brains of the program. It needs to:
        # grab data from the sdr, average, convert, add it to a list
        #  manage sensors and settling times...
        # tell the animated plot that there's an update
        if not self.sdr.running:
            keepGoing=False
            return
        try:
            sdrdata = self.sdr.data.get(False)

            r = self.sdr.device.processStreamData(sdrdata['result'])
            for k, v in r.items():
                #print(k)
                if k not in self.data_archives:
                    self.data_archives[k]=[]
                self.data_archives[k].append(np.mean(v))
            self.plot.utiliz = self.data_archives['AIN0']
            if not 'time' in self.data_archives:
                print("1st time steup")
                self.data_archives['time']=[]
                self.data_archives['mpltime']=[]
            self.data_archives['time'].append(datetime.now())
            self.data_archives['mpltime'].append(matplotlib.dates.date2num(datetime.now()))
            self.plot.timearr = self.data_archives['mpltime']

            
            
            #print(new_utiliz.shape)
            
        except Queue.Empty:
            #pass
            print "Queue is empty"
        except Exception:
            traceback.print_exc()
            self.sdr.running = False        


class StreamDataReader(object): #This class is really more of a general purpose talk to the labjack class
    def __init__(self, device,dataCollectionCond):
        self.device = device
        self.cond=dataCollectionCond
        self.data = Queue.Queue()
        self.dataCount = 0
        self.missed = 0
        self.running = False

    def readStreamData(self):
        print("reading stream data")
        self.running = True
        
        start = datetime.now()
        try:
            self.device.streamStart()
        except u6.LowlevelErrorException:
            print("cleaned up evil labjack error")
            self.device.streamStop()
            self.device.close()
            self.device = initdevice()
            self.device.streamStart()

        while self.running:
            # Calling with convert = False, because we are going to convert in
            # the main thread.
            returnDict = self.device.streamData(convert = False).next()
            
            self.data.put_nowait(copy.deepcopy(returnDict))
            self.device.writeRegister(5002,self.dataCount*.001)
            self.device.writeRegister(5000,self.dataCount*.001)
            #Those above lines write the voltages out to the output terminals. 
            self.dataCount += 1
            #self.device.setDOState(4,state=0)
            #The above works! 
            #self.device.getDIState(4) 
            #print("Acquiring lock")
            with self.cond:
                #print("notifying cond")
                self.cond.notifyAll()
            #if self.dataCount > MAX_REQUESTS:
            #    self.running = False
        print "stream stopped."
        self.device.streamStop()
        stop = datetime.now()

        total = self.dataCount * self.device.packetsPerRequest * self.device.streamSamplesPerPacket
        print "%s requests with %s packets per request with %s samples per packet = %s samples total." % ( self.dataCount, self.device.packetsPerRequest, self.device.streamSamplesPerPacket, total )
        
        print "%s samples were lost due to errors." % self.missed
        total -= self.missed
        print "Adjusted number of samples = %s" % total
        
        runTime = (stop-start).seconds + float((stop-start).microseconds)/1000000
        print "The experiment took %s seconds." % runTime
        print "%s samples / %s seconds = %s Hz" % ( total, runTime, float(total)/runTime )


def ctrlc_handler(signal,frame):
    #print("got ctrlc?")
    worker.stop()
    sys.exit()

def initdevice():
    d = u6.U6()
    #
    ## For applying the proper calibration to readings.
    d.getCalibrationData()
    #
    print "configuring U6 stream"
    d.streamConfig( NumChannels = 6, 
                   ChannelNumbers = [ 0,2,4,6,8,10 ], 
                   ChannelOptions = [ 128,128,128,128,128,128 ], 
                   SettlingFactor = 1, 
                   ResolutionIndex = 1, 
                   SampleFrequency = 1000 )
    return d

def main():
    global worker
    
    d = initdevice()
    dcc = threading.Condition()
    a = animatedplot(300)

    sdr = StreamDataReader(d,dcc)
    worker=LogicThread(sdr,dcc,a)
    sdrThread = threading.Thread(target = sdr.readStreamData)

    # Start the stream and begin loading the result into a Queue
    print("starting sdr thread")

    sdrThread.start()
    worker.start()
    a.go()
    while(True):
        # Without this while loop I can't have a working CTRL-C handler. http://www.dabeaz.com/python/GIL.pdf
        time.sleep(30)


    

if __name__ == "__main__":
    
    signal.signal(signal.SIGINT,ctrlc_handler)
    main()

