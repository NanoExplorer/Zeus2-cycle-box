#This script prints the sample settings json file and uploads a sample database entry 
from pymongo import MongoClient, InsertOne
import datetime
import json
import argparse

parser = argparse.ArgumentParser(description="change zeus2 cycle box settings")


#client=MongoClient('localhost',27017)
with open("mongostring",'r') as mfile:
    mstring=mfile.read()
client = MongoClient(mstring)
db=client.hk_data
collection=db.settings

sensors_read = {"2WIRE":[5,6,7],
        "4WIRE":[0,1,2,3],
        "GRT0-3":[0,1],
        "GRT4-7":[5,6,7]
        }
read_freq={'slow_read_freq':0.5,
           'fast_read_freq':60,
           'settling_time':0.3

} #freqs will be in times per minute, times in minutes
read_freq.update({'read':sensors_read})
#sensors_read.update({'id':'temp_settings'})

magnet_controls={'servo_mode':True,'usePID':False,'setpoint':0,'ramprate':5}
#magnet_controls.update({'id':'magnet_settings'})

pid_settings={'p':320,'i':16,'d':0,'max_current':12,
'temp_set_point':.135,'grt':6, 'ramp_rate':9}
#pid_settings.update({'id':'pid_settings'})

cycle_settings={'armed':False,                 #yyyy M d h m s
                'start_time':datetime.datetime(2019,1,31,13,48,0),
                'duration':.1,
                'heatswitch_delay':.05,
                'do_hsw_toggle':True,
                'ramprate_up':0.3,
                'ramprate_down':0.03,
                'setpoint':9.2,
                'cycle_ID':0
} #HERE though, times are in hrs
#ycle_settings.update({'id':'auto_cycler'})

settings_list={'sensors':read_freq,
               'magnet':magnet_controls,
               'pid':pid_settings,
               'cycle':cycle_settings,
               'timestamp':datetime.datetime.now()
}
print(json.dumps(settings_list, indent=4, sort_keys=True,default=str))
collection.insert_one(settings_list)
