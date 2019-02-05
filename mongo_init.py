#This script prints the sample settings json file and uploads a sample database entry 
from pymongo import MongoClient, InsertOne
import datetime
import json

client=MongoClient('localhost',27017)
db=client.hk_data
collection=db.settings

sensors_read = {"2WIRE":[5,6],
        "4WIRE":[0,1,2,3],
        "GRT0-3":[0,1],
        "GRT4-7":[6,7]
        }
read_freq={'slow_read_freq':0.5,
           'fast_read_freq':20,
           'settling_time':0.3

} #this will be in times per minute
read_freq.update({'read':sensors_read})
#sensors_read.update({'id':'temp_settings'})

magnet_controls={'servo_mode':True,'usePID':False,'setpoint':0,'ramprate':5}
#magnet_controls.update({'id':'magnet_settings'})

pid_settings={'p':320,'i':16,'d':5,'max_current':12,'temp_set_point':.135,'grt':6,
        "i_windup_guard":20, 'ramp_rate':9}
#pid_settings.update({'id':'pid_settings'})

cycle_settings={'armed':True,                 #yyyy M d h m s
                'start_time':datetime.datetime(2019,1,31,13,48,0),
                'duration':.1,
                'heatswitch_delay':.05,
                'do_hsw_toggle':True,
                'ramprate_up':0.3,
                'ramprate_down':0.03,
                'setpoint':9.2,
                'cycle_ID':0
}
#ycle_settings.update({'id':'auto_cycler'})

settings_list={'sensors':read_freq,
               'magnet':magnet_controls,
               'pid':pid_settings,
               'cycle':cycle_settings,
               'timestamp':datetime.datetime.now()
}
print(json.dumps(settings_list, indent=4, sort_keys=True,default=str))
collection.insert(settings_list)
