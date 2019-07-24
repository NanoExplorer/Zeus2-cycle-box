#This script prints the sample settings json file and uploads a sample database entry 
from pymongo import MongoClient, InsertOne
from datetime import datetime, timezone
import json
import argparse
import copy

parser = argparse.ArgumentParser(description="change zeus2 cycle box settings")
parser.add_argument('settingsfile', type=str, help="the file to read settings from")
parser.add_argument('-p', type=int, help="override the P term of the pid loop")
parser.add_argument('-i', type=int, help="override the I term of the pid loop")
parser.add_argument('-d', type=int, help="override the D term of the pid loop")
parser.add_argument('-t', '--set-temp', type=float, help="override the set temp for the pid loop")
parser.add_argument('-c', '--current', type=float, help="override the magnet current")
parser.add_argument('-r', '--ramprate', type=float, help='override the magnet current ramp rate')
parser.add_argument('--update-same-cycle',action='store_true')
args=parser.parse_args()

with open(args.settingsfile,'r') as jsonfile:
    settings=json.load(jsonfile)

#Modify the settings dictionary 
#based on overrides given by user
servo=settings['pid']
if args.p is not None:
    servo['p']=args.p
if args.i is not None:
    servo['i']=args.i
if args.d is not None:
    servo['d']=args.d
if args.set_temp is not None:
    servo['temp_set_point']=args.set_temp
if args.current is not None:
    settings['magnet']['setpoint']=args.current
if args.ramprate is not None:
    settings['magnet']['ramprate']=args.ramprate


#client=MongoClient('localhost',27017)
with open("mongostring",'r') as mfile:
    mstring=mfile.read()
client = MongoClient(mstring)
db=client.hk_data
collection=db.settings

#we ignore the value of timestame set n the json file
settings['timestamp'] = datetime.now(tz=timezone.utc)
time=settings['cycle']['start_time']
settings['cycle']['start_time']=datetime.fromisoformat(time)
cycle = settings['cycle'] # less typing
if cycle['heatswitch_delay'] >= cycle['duration']:
    print("Heatswitch delay must be less than duration. ")
    exit()

if settings['cycle']['armed']==True and not args.update_same_cycle:
    if settings['cycle']['start_time'] < settings['timestamp']:
        print(settings['timestamp'])
        print("cycle start time must be in the future!")
        exit()
    c=input("are you sure you want to start a new cycle? [y/n]")
    if c!='y':
        print('exiting...')
        exit()
    cycle['cycle_ID']+=1
    with open(args.settingsfile,'w') as autocyclesettingsfile:
        writeout = copy.deepcopy(settings)
        writeout['cycle']['start_time']=writeout['cycle']['start_time'].isoformat()
        writeout['timestamp']=writeout['timestamp'].isoformat()
        autocyclesettingsfile.write(json.dumps(writeout, indent=4, sort_keys=True))

collection.insert_one(settings)
