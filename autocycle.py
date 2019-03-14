from datetime import datetime, timedelta
import subprocess


class AutoCycler():
    def __init__(self):
        #Sorry that all the comments contain self.stage.
        #I made a mess and did a messy job cleaning up,
        #self.stages are as follows:
        #self.stage 0 is waiting
        #self.stage 1 is hsw closed /ramping up / before hsw toggle
        #self.stage 2 is hsw closed /after hsw toggle
        #self.stage 3 is hsw open / ramping down (includes cold)
        #self.stage 3 + done means that the thingy is now cold.
        self.stage = 0
        self.heatSwitch = HeatSwitch()
        self.cycleID=0
        self.done=False

    def update(self,settings,servoModeIn):
        """
        Params: dictionary of auto cycle settings,
                current state of servo mode switch
        returns:
                Tuple of set point for magnet current,
                         ramp rate for same
                         requested cycle/servo setting
        """
        #This has an edge case:
        #if the heat switch malfunctions while toggling,
        #then it will drain all the current after doing the toggle.
        #That *shouldn't* happen. but you know it will. Someday.
        #ideally you'd freeze the current where it is, and exit 
        #
        if self.cycleID!=settings['cycle_ID']:
            #Reset the cycle to self.stage 0 and stuff
            self.stage=0
            self.done=False
            self.cycleID=settings['cycle_ID']
         


        #This sets reasonable default values for the magnet current and ramp rate. 
        current=settings['setpoint']
        ramprate=0

        now = datetime.now()
        # if self.heatSwitch.hswError is not None:
        #     #If the heat switch had an error, best to have the magnet not ramp anywhere. (even though ramprate 0 means it might...)
        #     current = settings['setpoint']
        #     ramprate= 0
        servoMode = False

        if servoModeIn and self.stage<3:
            #If we're in servo mode, and the detector isn't really cold yet,
            # sets the ramp rate and set point of current
            #to safe values and asks for cycle mode to be activated.
            ramprate=0.1 #We're in servo mode, so high-ish ramprates are ok
            current=0

        elif self.stage==0:
            #timeready = now > settings['start_time']
            #hswready = ??
            if now > settings['start_time']:
                self.heatSwitch.closeHsw()
                #This will do nothing if the heat switch is not ready.

            self.heatSwitch.check_status()
            if self.heatSwitch.ready and self.heatSwitch.hswError is None and self.heatSwitch.hswClosed:
                self.stage=1
               
            #The heat switch hasn't successfully closed yet, so the default values will be kept


        elif self.stage==1:
            #going into self.stage 1 we've already checked that the heat switch worked successfully.
            ramprate=settings['ramprate_up']
            #TODO: add check for high temperature. Maybe run a PID on 5 K or something?
            #Note: heatswitch_delay has to be < duration even when do_hsw_toggle is false.
            #Shouldn't be much of an issue, because do toggle will be true most of the time, and the 
            #delay should not be changed even when do_toggle is.
            if now > settings['start_time']+timedelta(hours=settings['heatswitch_delay']):
                if settings['do_hsw_toggle']:
                    self.heatSwitch.toggleHsw()

                self.heatSwitch.check_status()
                if not settings['do_hsw_toggle'] or (self.heatSwitch.ready and self.heatSwitch.hswError is None):
                    self.stage=2
                    #self.hswRunning = False
            
        elif self.stage==2:
            ramprate=settings['ramprate_up']
            if now>settings['start_time']+timedelta(hours=settings['duration']):
                print("opening hsw to start rampdown")
                self.heatSwitch.openHsw()

            self.heatSwitch.check_status()
            if self.heatSwitch.hswClosed==False and self.heatSwitch.ready and self.heatSwitch.hswError is None:
                print("Hsw opened successfully, moving to stage 3")
                self.stage=3
            
        elif self.stage==3:
            ramprate=settings['ramprate_down']
            servoMode=True #current is draining, and when it gets to 0 the magnet will
            #go into servo mode. 
            print("Stage is now 3")
            if servoModeIn:
                self.done=True
                self.stage=4
                print("Stage is now 4")
        #in self.stage4 don't do anything.


        return (current,ramprate,servoMode,{'done':self.done,
                                            'stage':self.stage,
                                            'error':self.heatSwitch.hswError,
                                            'heat_switch_closed':self.heatSwitch.hswClosed,
                                            'heat_switch_ready':self.heatSwitch.ready
                                            })


class HeatSwitch():
    def __init__(self):
        self.hswClosed = False #only believe hswClosed value if no error and ready==true. (It is safe to assume the hsw is open)
        self.command = None #this will be a function.
        self.hswError = None
        self.numErrs=0
        self.ready=True
        self.pobject=None
        self.log = []
    def check_status(self):
        if self.pobject is not None:
            rc=self.pobject.poll()
            #rc is return code of the subprocess.
            if rc is None:
                return None
            elif rc == 0:
                stdout,stderr=self.pobject.communicate()
                self.log.append((stdout,stderr))
                self.ready=True
                self.numErrs=0
                self.hswError=None
                self.pobject=None
                return True
            else:
                stdout,stderr=self.pobject.communicate()
                self.log.append((stdout,stderr,rc))
                print(stdout,stderr)
                self.hswError=rc
                self.pobject=None
                if self.numErrs < 3:
                    print("MOTOR ERROR! Tryin' again...")
                    self.numErrs += 1
                    self.command(override=True)
                return False

    def _runHsw(self,command,override):
        if self.ready or override:
            self.ready=False
            #I could have imported their python code and tried to stuff it into a thread,
            #but overall I actually think this is safer. I also think they already use
            #some threads, so I'm scared to try to integrate it.
            #IN ADDITION I just migrated all this code to python3, and no way am I going
            #to try that with the automatic heatswitch code.
            self.pobject=subprocess.Popen(['python2','heatswitch_automatic.py',command],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            return True
        return False

    def closeHsw(self,override=False):
        self.command=self.closeHsw
        if self._runHsw('close',override):
            self.hswClosed = True

    def openHsw(self,override=False):
        self.command=self.openHsw
        if self._runHsw('open',override):
            self.hswClosed = False

    def toggleHsw(self,override=False):
        self.closeHsw(override=override)
        self.command=self.toggleHsw
        #if the heat switch isn't open (i.e. at hard limit), the closehsw command 
        #automatically opens the heat switch before closing it. So it 
        #does the same thing as what I think of as toggling.
