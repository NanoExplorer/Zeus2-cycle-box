import time
class MagnetRamp():
    def __init__(self):
        self.lastTime = time.time() #time at which magnet was last updated
        self.lastSP = 0 #Last set point that was sent to magnet
        self.want_current = 0 #Current set by user
        self.want_speed = 0 #*actually* in amps per hour
        self.ramp_rate_out = 0 #Ramp rate to give to the magnet.

    def update_magnet(self,current_now):
        timedelta = time.time()-self.lastTime
        magdelta = timedelta * self.want_speed/3600
        #want speed is in amps per hour. Convert it to amps per second

        if current_now < self.want_current:
            nextSP = max(self.want_current,
                         self.lastSP + magdelta)

        elif current_now > self.want_current
            nextSP = min(self.want_current,
                         self.lastSP - magdelta)

class SimpleRamp():
    def __init__(self,current,speed):
        self.start_time = time.time() #time at which magnet was started
        self.start_current = current #Current set by user
        self.want_speed = speed #*actually* in amps per hour

    def update_magnet(self):
        timedelta = time.time()-self.start_time
        magdelta = timedelta * self.want_speed/3600
        #want speed is in amps per hour. Convert it to amps per second

        if current_now < self.want_current:
            nextSP = max(self.want_current,
                         self.lastSP + magdelta)

        elif current_now > self.want_current
            nextSP = min(self.want_current,
                         self.lastSP - magdelta)
