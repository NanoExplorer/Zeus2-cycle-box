import time


class MagnetRamp():
    def __init__(self):
        self.lastTime = time.time()  # time at which magnet was last updated
        self.lastSP = 0  # Last set point that was sent to magnet
        self.want_current = 0  # Current set by user
        self.want_speed = 0  # *actually* in amps per hour
        self.ramp_rate_out = 0  # Ramp rate to give to the magnet.

    def update_magnet(self, current_now):
        timedelta = time.time()-self.lastTime
        self.lastTime = time.time()

        magdelta = timedelta * self.want_speed/3600
        # want speed is in amps per hour. Convert it to amps per second

        if self.lastSP < self.want_current:
            nextSP = max(self.want_current,
                         self.lastSP + magdelta)

        elif self.lastSP > self.want_current:
            nextSP = min(self.want_current,
                         self.lastSP - magdelta)

        else:
            nextSP = self.want_current

        self.lastSP = nextSP
        return nextSP

    def set_want_speed_amps_per_hr(self, speed):
        self.want_speed = speed

    def set_want_speed_amps_per_min(self, speed):
        self.want_speed = speed * 3600
