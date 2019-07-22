import numpy as np
from datetime import datetime, timedelta
import queue
import copy
import sys
import signal
import traceback
import tabulate
from database import SettingsWatcherThread, DatabaseUploaderThread
from labjack import LabJackController
from pid import PID 
from autocycle import AutoCycler
from interpolators import Interpolators

from common import getGRTSuffix


QUEUE_TIMEOUT=30 #Change to None in production.
#If this is a number, then there will be polling going on.
#If it's None, we could have a hard time exiting if there's an error because some
#threads may refuse to die. Which shouldn't be an issue if we decide this program is mature

"""

I'm using threads because this program does an awful lot of IO.
The two database threads and the labjack thread are almost constantly just waiting around,
and the only place that any serious calculations occur is in the logicclass.

TODO:
get digital inputs from the labjack to the database too though they're not v. important.
finish auto cycle
  *heat switch integration (CHECK)
  *exiting automation gracefully in preparation for servoing and subsequently next auto cycle.
"""


SENSORS_MAP={'AIN4': '4WIRE',
'AIN6': '2WIRE',
'AIN0': 'GRT0-3',
'AIN2': 'GRT4-7',
'AIN8': 'Voltage',
'AIN10': 'Current'}

class LogicClass():#threading.Thread): Logic Thread is now going to run in the main thread
    """LogicThread takes care of the "logic" of running the cyclebox.

    It has the following jobs:
    pass a magnet current set point to the labjackcontroller
    pass a magnet ramp rate to the ljc
        By extension to these two it will do things like run the pid loop (and auto cycle?)
    tell the ljc which sensors to read (i.e. provide digital outputs to the ljc)
        So this object controls switching between the sensors that are on the same card
        that you want to read.
    decide whether to throw out data from a sensor because t<t_settling
    pass data to database uploader
    get data from settings downloader
    go from voltage to temperature via interpolated calibration data.
    """
    def __init__(self,lj):
        #threading.Thread.__init__(self)
        self.keepGoing = True
        self.lj=lj
        self.sensorsReadingNow = 0 #0th sensor in every list of readout cards
        self.timeLastFastRead =datetime.now()
        self.timeLastSlowRead =datetime.now()
        self.dbuploader = DatabaseUploaderThread()
        self.dbuploader.setDaemon(True)
        self.dbuploader.start()
        self.settings = SettingsWatcherThread()
        self.settings.setDaemon(True)
        self.lastAutoCycleStatus={}
        self.settings.start()
        self.interp = Interpolators()
        #The first element in these is whether to ignore that card. (boolean)
        #The second element is whether that card should be reading in fast mode. (boolean)
        #The third element is the last time that card's mux was changed. (datetime) (ignored for magnet sensors)
        self.sensorsFast={'GRT0-3': False,
                          'GRT4-7': False,
                          '2WIRE' : False,
                          '4WIRE' : False,
                          'Voltage':True,
                          'Current':True
        }
        self.sensorsIgnore={'GRT0-3':False,
                          'GRT4-7':  False,
                          '2WIRE' :  False,
                          '4WIRE' :  False,
                          'Voltage': False,
                          'Current': False
        }
        self.sensorsLast={'GRT0-3': 0,
                          'GRT4-7': 0,
                          '2WIRE' : 0,
                          '4WIRE' : 0,
                          'Voltage':0,
                          'Current':0
        }
        self.sensorsTime={'GRT0-3': datetime.now(),
                          'GRT4-7': datetime.now(),
                          '2WIRE' : datetime.now(),
                          '4WIRE' : datetime.now(),
                          'Voltage':datetime.now(),
                          'Current':datetime.now()
        }
        self.numSlowCards=4
        self.slowValues = {}
        self.autoCycler = AutoCycler()
        self.current=0
        #I have not made locks for any of the LogicClass's variables
        #They should not be accessed outside of the LogicClass.
        #Instead, the LogicClass should modify the variables of other threads and pay
        #attention to their locks.


        #The labjack thread has not started yet, so we might as well initialize its settings for it,
        #We have already grabbed the most recent settings from the database, which protects us if
        #this program crashes and is restarted - i.e., the first thing we write to the labjack should
        #be the same as the last thing we wrote to the labjack. 
        #TODO: UNLESS WE WERE IN AUTO CYCLE. POSSIBLE FIX: push servo/cycle info to thermometry and read it here
        #I wonder if you can read from write-only pins on the labjack. That means we could get our info
        #Straight from the horse's mouth...
        with self.settings.settingsLock:
            servoMode=self.settings.settings["magnet"]["servo_mode"]
            pids=self.settings.settings["pid"]
            self.pid = PID(P=pids['p'],I=pids['i'],D=pids['d'],cap=pids['max_current'])
            self.pid.setWindup(pids['max_current'])
            self.pid.SetPoint = pids['temp_set_point']

        self.lj.servoMode=servoMode #atomic operation doesn't need lock

    def run(self):
        with self.settings.settingsLock:
            self.next_sensor(self.settings.settings) #set up sensors for the first time
        while self.keepGoing:
            #print("updating")
            self.update()

    def stop(self):
        self.keepGoing = False
        self.lj.keepGoing=False
        self.dbuploader.keepGoing=False
        self.settings.keepGoing=False

    def do_pid_step(self,pids,temperature):
        #their interface doesn't make 100% sense for my use case.
        #it might've been better to just import their update method
        #into here, but whatever. I have to do less work this way.
        self.pid.setKp(pids['p'])
        self.pid.setKi(pids['i'])
        self.pid.setKd(pids['d'])
        self.pid.setWindup(pids['i_windup_guard'])
        self.pid.output_cap=pids['max_current']
        self.pid.SetPoint = pids['temp_set_point']

        self.pid.update(temperature)
        pid_fmt_str="{:.3f} {:.5f} {:.3f} {:.5f} {:.5f} {:.5f}"
        self.update_temperatures({'PID_status': {
                                'request_current':self.pid.output,
                                'temp_now':temperature,
                                'set_point':self.pid.SetPoint,
                                'P_term':self.pid.PTerm,
                                'I_term':self.pid.Ki*self.pid.ITerm,
                                'D_term':self.pid.Kd * self.pid.DTerm}})
        return(self.pid.output,pids['ramp_rate'])


    def update_magnet(self,settings,temperature=None):
        """This communicates the magnet set point and ramprate to the lj controls."""

        
        #The autocycler only gets updated when it's running, so we have to detect the start of a new cycle here.
        #I.E. cycle finishes, user requests new cycle, 
        onSameCycle=self.autoCycler.cycleID==settings['cycle']['cycle_ID']

        #If cycle is not armed, we must not follow this conditional branch.
        #If cycle is finished, we must not follow this branch unless a new cycle has been started. I.E. when finished is true but onsamecycle is not, the second 
        #part of this conditional is true.
        if settings["cycle"]["armed"] and not (self.autoCycler.done and onSameCycle):
            current,ramprate,servoMode,status = self.autoCycler.update(settings["cycle"],self.lj.servoMode)
            self.switch_servo_cycle(servoMode)
            if self.lastAutoCycleStatus != status:
                self.lastAutoCycleStatus = status
                self.update_temperatures({'auto_cycle_status':status})
        elif settings["magnet"]["usePID"]:
            self.switch_servo_cycle(True)
            assert(temperature is not None)
            current,ramprate = self.do_pid_step(settings['pid'],temperature)
        else:
            self.switch_servo_cycle(settings['magnet']['servo_mode'])
            current = settings["magnet"]["setpoint"]
            ramprate = settings["magnet"]["ramprate"]
        self.lj.currentRamprate=ramprate
        self.lj.currentSetpoint=current
    def update_temperatures(self,tempdict):
        #I guess this is here in case you
        #ever want to do something else with this 
        #data before uploading it...
        self.dbuploader.q.put_nowait(tempdict)

    def switch_servo_cycle(self,new_mode):
        """
        It feels weird to me to have this method here instead of in the labjack
        controller interface. However, when I tried to move it I remembered that 
        the labjack controller interface doesn't actually know the values of any
        of the voltages that it's reading in, so this needs to stay in logic.
        """
        if new_mode != self.lj.servoMode:
            if self.current < 0.05:
                self.lj.servoMode = new_mode
                self.update_temperatures({'currently_in_servo': new_mode})

    def next_sensor(self,settings):
        """Decide which sensor needs to be read out next, and tell that to the lj

        This is where the brains of the multiplexing occur. The method is as follows:
        "slow" readout cards are the ones that are reading multiple sensors on the same
        card, and "fast" readout cards are only reading one sensor. Every time the
        next_sensor function is called, it will cycle to the next sensor on the list
        for that readout card.
        """
        toRead = {}
        self.numSlowCards=0
        for name,sensors in settings["sensors"]['read'].items():
            #print(sensors)
            nsensors = len(sensors)
            if nsensors == 0:
                toRead[name]=None #sensor is off

            elif nsensors == 1:
                toRead[name]=sensors[0] #sensor is in fast mode

            elif self.sensorsReadingNow >= nsensors:
                toRead[name]=sensors[0] #sensor will be ignored b/c all sensors on that 
                #card that we want  to read have already been read.

            else:
                toRead[name] = sensors[self.sensorsReadingNow]
                self.numSlowCards+=1

            if self.sensorsLast[name] != toRead[name]:
                self.sensorsTime[name]=datetime.now()

            self.sensorsFast[name]  = (nsensors==1)
            self.sensorsIgnore[name]= (nsensors == 0 or nsensors<=self.sensorsReadingNow)
            self.sensorsLast[name]  = toRead[name]

        with self.lj.sensorsLock:
            self.lj.read0to3 = toRead["GRT0-3"]
            self.lj.read4to7 = toRead["GRT4-7"]
            self.lj.read2wire = toRead["2WIRE"]
            self.lj.read4wire = toRead["4WIRE"]
        self.sensorsReadingNow+= 1

    def update(self):
        """High-level control flow

        This update function calls the other functions in this class and makes
        sure that the housekeeping is going smoothly.
        """
        try:
            #lj.data is a queue. Grab latest data from it and  block until it's available
            ljdata = self.lj.data.get(True,QUEUE_TIMEOUT)
            #Apply lj device calibration
            r = self.lj.device.processStreamData(ljdata['result'])
            #Grab settings from database 
            with self.settings.settingsLock:
                settings = copy.deepcopy(self.settings.settings)
            
            settlingTime=timedelta(minutes=settings['sensors']['settling_time'])
            fastTime =   timedelta(minutes=settings['sensors']['fast_read_freq']**(-1))
            slowTime =   timedelta(minutes=settings['sensors']['slow_read_freq']**(-1))
            
            if settings['magnet']['usePID']:
                grtForPid=settings['pid']['grt']
                cardForPid = 'GRT'+getGRTSuffix(grtForPid)
                #override in case I'm forgetful or sleepy or whatever.
                #The sensor settings are overridden for the pid card
                #so that the pid card only reads out the one "grt for pid" sensor
                settings['sensors'][cardForPid] = [grtForPid]

            fastValues = {}
            pidControlTemp=None

            #r is a dictionary, with keys being sensors like 'AIN0'
            #the meaning of those sensors is in SENSORS_MAP.
            #The next thing we need to do is convert voltages to temperatures and send them
            #to the database uploader. And also save the one used for the PID loop in a member
            #variable so it can be used by do_pid_step

            #This loop runs always. It goes through all sensors and decides which ones need to go where.
            for k,v in r.items():
                #r is the labjack sensor data after calibration
                sensor = SENSORS_MAP[k]
                now = datetime.now()

                #IF THIS SENSOR IS IN FAST MODE, read it if it's time
                if self.sensorsFast[sensor]:
                    if now-self.timeLastFastRead > fastTime and now-self.sensorsTime[sensor] > settlingTime:
                        fastValues[sensor] = (self.sensorsLast[sensor],self.process(v,sensor,self.sensorsLast[sensor]))
                #If it's not fast or ignored, it's slow. Read it if it's time.
                elif not self.sensorsIgnore[sensor]:
                    if now-self.sensorsTime[sensor] > settlingTime:
                        self.slowValues[sensor] = (self.sensorsLast[sensor],self.process(v,sensor,self.sensorsLast[sensor]))
                
                #If we're using a PID loop, read the PID sensor regardless
                if settings['magnet']['usePID'] and sensor == cardForPid:
                    pidControlTemp=self.process(v,sensor,grtForPid)
                #always read the current also.
                if sensor=="Current":
                    self.current = self.process(v,sensor,self.sensorsLast[sensor])
                if sensor=="Voltage":
                    voltage = self.process(v,sensor,self.sensorsLast[sensor])

            #Once we've read all the slow cards, we push them to the database
            if len(self.slowValues)==self.numSlowCards and self.numSlowCards >0:
                #push fastvalues too if any.
                self.slowValues.update(fastValues)
                if len(fastValues)==0:
                    #add magnet current and voltage info
                    self.slowValues.update({"Voltage":[0,voltage],"Current":[0,self.current]})
                self.update_temperatures(self.slowValues)
                self.slowValues = {}
                #reinitialize the slow values array only after pushing it to the database.
                if len(fastValues)>0:
                    self.timeLastFastRead = now
                #Now start reading out the next set of sensors!
                self.next_sensor(settings)
            #If the slow cards aren't being uploaded, we upload fast cards if any.
            #(if slow cards are being uploaded, we bundle fast card info with it.)
            elif len(fastValues)>0:
                #print(self.numSlowCards)
                #print(self.sensorsTime)
                #print(len(self.slowValues))
                self.timeLastFastRead = now
                self.update_temperatures(fastValues)
            #Once it's time to start taking the next set of measurements
            #reset the readout card counter to the beginning and start over.
            if now-self.timeLastSlowRead>slowTime and self.numSlowCards == 0:
                self.sensorsReadingNow=0
                self.timeLastSlowRead =now
                self.next_sensor(settings)
            self.update_magnet(settings,temperature=pidControlTemp)


        except queue.Empty:
            print("Queue is empty?")
        except Exception:
            traceback.print_exc()
            self.stop()
        if not self.lj.data.empty():
            print("""[WARN] The logic thread may be behind by up to {} records.
[WARN] Don't panic unless that number is increasing quickly,
[WARN] or stays very large for long periods of time""".format(self.lj.data.qsize()))
            #Use the following if it becomes clear that the logic thread really cannot keep up.
            # n_records_skipped=0
            # try:
            #     while not self.lj.data.empty():
            #         self.lj.data.get_nowait()
            #         n_records_skipped+= 1
            # except Queue.Empty:
            #     pass
            # print("Logic fell behind and skipped {} records. This just means readout will be a bit on the slow side")
    def process(self,voltage, card, sensornum):
        #read in files corresponding to sensornum and card
        #make numpy interpolator
        #run voltage through that.
        if np.any(np.array(voltage)<-9000):
            print("THAT's the problem. We're under -9000!")
        v = np.mean(voltage) 
        #print(v,card,sensornum)
        #print(repr(v))
        if card =='Voltage': 
            return v
        elif card=='Current':
            return v*20
        else:
            return self.interp.go(v,card,sensornum)


def ctrlc_handler(signal,frame):
    worker.stop()
    sys.exit()

def main():
    global worker #Worker is global so that the ctrlc_handler can call its stop function.

    lj = LabJackController()
    worker=LogicClass(lj)

    # Start the stream and begin loading the result into a Queue
    print("starting lj thread")

    lj.start()
    worker.run()#Since the worker isn't actually a thread, this passes the
    #execution to the worker.


    

if __name__ == "__main__":
    
    signal.signal(signal.SIGINT,ctrlc_handler)
    main()

