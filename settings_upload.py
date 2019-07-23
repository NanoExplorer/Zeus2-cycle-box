#This script prints the sample settings json file and uploads a sample database entry 
from pymongo import MongoClient, InsertOne
from datetime import datetime, timezone
import json
import argparse

parser = argparse.ArgumentParser(description="change zeus2 cycle box settings")
parser.add_argument('settingsfile', type=str, help="the file to read settings from")
parser.add_argument('-p', type=int, help="override the P term of the pid loop")
parser.add_argument('-i', type=int, help="override the I term of the pid loop")
parser.add_argument('-d', type=int, help="override the D term of the pid loop")
parser.add_argument('-t', '--set-temp', type=float, help="override the set temp for the pid loop")
parser.add_argument('-c', '--current', type=float, help="override the magnet current")
parser.add_argument('-r', '--ramprate', type=float, help='override the magnet current ramp rate')
args=parser.parse_args()

with open(args.settingsfile,'r') as jsonfile:
    settings=json.load(jsonfile)


if args.p is not None:
    pass
if args.i is not None:
    pass
if args.d is not None:
    pass
if args.set_temp is not None:
    pass
if args.current is not None:
    pass
if args.ramprate is not None:
    pass


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
if settings['cycle']['armed']==True:
    confirm=input("Did you remember to increment the autocycle ID? [y/n]")
    if confirm!='y':
        print('aborting...')
        exit()

collection.insert_one(settings)
