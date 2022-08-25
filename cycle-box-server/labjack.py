import threading
import u6
import queue
import logging
import copy


class LabJackController(threading.Thread):
    """
    This object wraps the low-level commands of the labjack in a slightly nicer way.
    It has no knowledge of temperature or magnet state, but it does have maps from
    logical port numbers to the names of the connected things.
    It runs in its own thread so that we can do things asynchronously.

    All it does is constantly read out the sensors and update the digital/analog outputs,
    hopefully it doesn't have any errors or problems like the old labview did.

    It takes information from the logic thread about what outputs it needs to set
    and gives information to the logic thread about all inputs it receives from the cyclebox
    but the logic thread decides how to interpret everything.
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self.device = init_device()
        self.data = queue.Queue()
        self.missed = 0
        self.keepGoing = False

        #Use the setpoint and ramprate atomically.
        self.currentSetpoint = 0
        self.currentRamprate = 0

        #servoMode is atomic.
        self.servoMode = True

        #Use sensorsLock when modifying any of the read... variables
        self.sensorsLock = threading.Lock()
        self.read0to3 = None  #don't read any sensors on the 0-3 card
        self.read4to7 = None  #if you want to read a sensor, write its number to these variables.
        self.read2wire = None
        self.read4wire = None

        #These next 4 variables should only ever be READ.
        self.cycleBoxLocal = False
        self.setPointReached = False
        self.quench = False  #AND KEEP IT THAT WAY.
        self.magnetBoxManual = False

        self.diosIn = [
            0 for x in range(16)
        ]  #don't modify this outside this class. Would be nice to have
        #private variables like Java right now.
        self.diosIn[3] = 0  #As far as I've seen, the GRT0-3 card has always been in cold mode
        #print("have not determined what the two leds hanging out of the 4wire box should be")
        self.diosIn[15] = 1  #??? check to see what mode this is usually in.
        #self.update_dios()
        #That was a bad idea. It means that we always start in servo mode
        #even if we don't want to.

    def update_dios(self):
        with self.sensorsLock:
            self.diosIn[14] = 1 if self.servoMode else 0  #convert boolean to number...

            #This is python 3 so I need to do // to have integer division.
            if self.read0to3 is not None:
                self.diosIn[0] = self.read0to3 % 2  #lsb of sensor address
                self.diosIn[1] = self.read0to3 // 2  #msb of sensor address
                self.diosIn[2] = 0
            else:
                self.diosIn[2] = 1  #if we're not reading any sensors on that card, disable it

            if self.read4to7 is not None:
                temp4to6 = self.read4to7 - 4
                self.diosIn[4] = temp4to6 % 2
                self.diosIn[5] = temp4to6 // 2
                self.diosIn[6] = 0
            else:
                self.diosIn[6] = 1

            if self.read2wire is not None:
                self.diosIn[10] = self.read2wire % 2  #lsb
                self.diosIn[11] = (self.read2wire // 2) % 2  #2s place
                self.diosIn[12] = self.read2wire // 4  #4s place / msb
                self.diosIn[13] = 0
            else:
                self.diosIn[13] = 1

            if self.read4wire is not None:
                self.diosIn[7] = self.read4wire % 2
                self.diosIn[8] = self.read4wire // 2
                self.diosIn[9] = 0
            else:
                self.diosIn[9] = 1  #if we're not reading any sensors on that card, disable it
            for dio in self.diosIn:
                if dio > 1 or dio < 0:
                    logging.error(
                        "Invalid sensor number! \n {} {} {} {} \n {}".format(
                            self.read0to3, self.read4to7, self.read2wire,
                            self.read4wire, self.diosIn))

    def run(self):
        try:
            self.main_loop()
        except:
            logging.exception("Exception in labjack.py")
        finally:
            self.device.close()

    def main_loop(self):
        logging.info("reading stream data")
        self.keepGoing = True
        try:
            self.device.streamStart()
        except u6.LowlevelErrorException:
            logging.info("cleaned up evil labjack error")
            self.device.streamStop()
            self.device.close()
            self.device = init_device()
            self.device.streamStart()

        while self.keepGoing:
            try:
                # Calling with convert = False, because we are going to convert in
                # the main thread.
                returnDict = next(self.device.streamData(convert=False))
                self.data.put_nowait(copy.deepcopy(returnDict))
                if returnDict['errors'] > 0:
                    logging.debug(f"num errors: {returnDict['errors']}")

                if returnDict['missed'] > 0:
                    logging.debug(f"Missed {returnDict['missed']}")
                #write the voltages to control magnet current and ramp rate
                self.device.writeRegister(5002, self.currentSetpoint / 20)  #dac1
                self.device.writeRegister(5000, self.currentRamprate / 2)  #dac0

                self.update_dios()
                for i, state in enumerate(self.diosIn):
                    self.device.setDOState(i, state=state)

                self.cycleBoxLocal = self.device.getDIState(
                    16) == 1  #function returns number; convert to boolean
                self.setPointReached = self.device.getDIState(17) == 1
                self.quench = self.device.getDIState(18) == 1
                self.magnetBoxManual = self.device.getDIState(19) == 1

            except u6.LowlevelErrorException:
                logging.warning("EVIL LABJACK ERROR!!!")
                self.device.streamStop()
                self.device.close()
                self.device = init_device()
                self.device.streamStart()
                logging.warning(
                    "Evil labjack error resolved successfully. No need to worry"
                )

        logging.info("stream stopped.")
        self.device.streamStop()


def init_device():
    d = u6.U6()
    #
    # For applying the proper calibration to readings.
    d.getCalibrationData()
    #
    logging.info("configuring U6 stream")
    d.streamConfig(NumChannels=6,
                   ChannelNumbers=[0, 2, 4, 6, 8, 10],
                   ChannelOptions=[128, 128, 128, 128, 128, 128],
                   SettlingFactor=1,
                   ResolutionIndex=1,
                   SampleFrequency=1000)
    return d
