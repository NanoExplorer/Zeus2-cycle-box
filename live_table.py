
from database import ThermometryWatcherThread
import tabulate
import numpy as np


class CurrentStatus():
    def __init__(self):
        self.sensors_id = np.genfromtxt('calibration/Sensor_ID.txt',
                                        skip_header=2,
                                        delimiter='\t',
                                        dtype=str)
        self.sensors_temp = [0 for x in range(4+8+8+2)]
        self.card_array_offsets={'2WIRE':12,
                '4WIRE':8,
                'GRT0-3':0,
                'GRT4-7':0}
        #ordered by grt,4wire,2wire, same as sensors_id file
        self.sensor_names = self.sensors_id[:,1]
        self.sensor_names=np.append(self.sensor_names,["Current (A)","Voltage (V)"])
        self.sensor_wires = self.sensors_id[:,0]
        self.sensor_wires=np.append(self.sensor_wires,["Magnet","Magnet"])

    def update(self,card,num,temperature):
        if card == 'Voltage':
            self.sensors_temp[-1] = temperature
        elif card == 'Current':
            self.sensors_temp[-2] = temperature
        else:
            idx = self.card_array_offsets[card]+num
            self.sensors_temp[idx]=temperature

    def printTable(self):
        tablestring=tabulate.tabulate(
            [[x,y,z] for x,y,z in zip(self.sensor_wires,
                                     self.sensor_names,
                                      self.sensors_temp)],
            headers=["Sensor Wire",
                     "Sensor Name",
                     "Temperature (K)"])
        print(tablestring)

def main():
    twt = ThermometryWatcherThread(num_previous=4,
        previous_query={'$or':[{'2WIRE':{'$exists': True}},{'4WIRE':{'$exists': True}},{'GRT0-3':{'$exists': True}},{'GRT4-7':{'$exists': True}}]}
        )
    status = CurrentStatus()
    twt.setDaemon(True)
    twt.start()
    while True:
        new_data = twt.newdata.get(True,30)

        for k in ['2WIRE','4WIRE','GRT0-3','GRT4-7','Voltage','Current']:
            try:
                v=new_data[k]
                status.update(k,v[0],v[1])
            except KeyError:
                pass

        status.printTable()






if __name__ == "__main__":
    main()

