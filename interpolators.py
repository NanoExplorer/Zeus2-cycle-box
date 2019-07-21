from scipy.interpolate import interp1d
import numpy as np
from common import getGRTSuffix

class Interpolators:
    def __init__(self):

        sensors_id = np.genfromtxt('calibration/Sensor_ID.txt',
                                   skip_header=2,
                                   delimiter='\t',
                                   dtype=str)
        self.sensors_interp = {'2WIRE':[None for x in range(8)],
                '4WIRE':[None for x in range(4)],
                'GRT0-3':[None for x in range(4)],
                'GRT4-7':[None for x in range(8)]}#lower half of this array stays none 
                #and will not be populated so that you can say var['GRT4-7'][6] 
                #where 6 is the grt number
        self.pre_functions = {'2WIRE':[None for x in range(8)],
                '4WIRE':[None for x in range(4)],
                'GRT0-3':[None for x in range(4)],
                'GRT4-7':[None for x in range(8)]}
        for sensor in sensors_id:
            snum=int(sensor[0][-1])
            card = sensor[0][0:-1].replace('-','')
            if card == 'GRT':
                card = card+getGRTSuffix(snum)
            card_calib = np.genfromtxt('calibration/'+card,skip_header=3).T

            card_interps = interp1d(card_calib[1],card_calib[0],fill_value='extrapolate')
            #reversed because first col is resistance in file. I'll be putting in a voltage
            #and expecting to get out a resistance.
            if sensor[2] == 'R':
                self.pre_functions[card][snum] = card_interps

            else:
                self.pre_functions[card][snum] = preFunction = lambda x: x

            sensor_calib = np.genfromtxt('calibration/'+sensor[3],skip_header=3).T
            #print(sensor_calib)
            sensor_interp = interp1d(sensor_calib[1],sensor_calib[0],fill_value='extrapolate')
            self.sensors_interp[card][snum]=sensor_interp


    def go(self,v,card,num):
        a = self.sensors_interp[card][num](self.pre_functions[card][num](v))
        b = float(a)
        #print(f"Just interpolated {v:.3f} volts to {b:.3f} K on sensor {card} {num}")
        #print(repr(a))
        return b
        #interpolators apparently return 0 dimensional numpy arrays...
