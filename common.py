from datetime import timezone, timedelta
def getGRTSuffix(n):
    if n<4:
        return '0-3'
    else:
        return '4-7'

#These values are used to safely arrive at 0 current  
#when  user requests a switch from servo to cycle or vice versa.
#with current still in the magnet.
CYCLE_MODE_SAFE_RAMP_RATE=0
CYCLE_MODE_SAFE_SET_POINT=0
SERVO_MODE_SAFE_RAMP_RATE=5
SERVO_MODE_SAFE_SET_POINT=0
DISPLAY_IN_TZ=timezone(timedelta(hours=-5))