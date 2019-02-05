#This script prints the sample settings json file and uploads a sample database entry 
from pymongo import MongoClient, InsertOne
import datetime
import json
import random
import time
client=MongoClient('localhost',27017)
db=client.hk_data
collection=db.settings
#GRTs_list=['GRT{}'.format(x) for x in range(8)]
#wire4list=['4WIRE{}'.format(x) for x in range(4)]
#wire2list=['2WIRE{}'.format(x) for x in range(8)]
#sensors_list = GRTs_list+wire2list+wire4list
#print(sensors_list)
#sensors_read = {x:False for x in sensors_list}
def random_list_gen(min,max,maxlen):
    numrands = random.randrange(0,maxlen)
    out = []
    for i in range(numrands):
        out.append(random.randrange(min,max))
    return out
while True:
    sensors_read = {"2WIRE":random_list_gen(0,8,8),
            "4WIRE":random_list_gen(0,4,4),
            "GRT0-3":random_list_gen(0,4,4),
            "GRT4-7":random_list_gen(4,8,4)
            }
    read_freq={'slow_read_freq':random.uniform(0.2,2),
               'fast_read_freq':random.uniform(10,120),
               'settling_time':random.uniform(0.05,0.5)

    } #this will be in times per minute
    read_freq.update({'read':sensors_read})
    #sensors_read.update({'id':'temp_settings'})

    magnet_controls={'servo_mode':random.choice([True,False]),'usePID':False,'setpoint':random.uniform(0,13),'ramprate':random.uniform(0,8)}
    #magnet_controls.update({'id':'magnet_settings'})

    pid_settings={'p':320,'i':16,'d':0,'max_current':12,'temp_set_point':.130,'grt':6}
    #pid_settings.update({'id':'pid_settings'})

    cycle_settings={'armed':False,
                    'start_time':datetime.datetime(2012,2,2,6,35,6),
                    'duration':7,
                    'heatswitch_delay':3,
                    'do_hsw_toggle':True,
                    'ramprate_up':0.3,
                    'ramprate_down':0.03,
                    'setpoint':9.2}
    #ycle_settings.update({'id':'auto_cycler'})

    settings_list={'sensors':read_freq,
                   'magnet':magnet_controls,
                   'pid':pid_settings,
                   'cycle':cycle_settings,
                   'timestamp':datetime.datetime.now()
    }
    #print(json.dumps(settings_list, indent=4, sort_keys=True,default=str))
    collection.insert(settings_list)
    time.sleep(3)