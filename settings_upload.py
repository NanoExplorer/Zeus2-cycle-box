#This script prints the sample settings json file and uploads a sample database entry 
from pymongo import MongoClient, InsertOne
from datetime import datetime, timezone, timedelta
import json
import argparse
import copy
import database
import sys

def get_cmdline_args():
    parser = argparse.ArgumentParser(description="change zeus2 cycle box settings")
    parser.add_argument('settingsfile', type=str, nargs='?', help="the file to read settings from")
    parser.add_argument('-p', type=int, help="override the P term of the pid loop")
    parser.add_argument('-i', type=int, help="override the I term of the pid loop")
    parser.add_argument('-d', type=int, help="override the D term of the pid loop")
    parser.add_argument('-t', '--set-temp', type=float, help="override the set temp for the pid loop")
    parser.add_argument('-c', '--current', type=float, help="override the magnet current")
    parser.add_argument('-r', '--ramprate', type=float, help='override the magnet current ramp rate')
    parser.add_argument('--update-same-cycle',action='store_true')
    parser.add_argument('-D', '--cycle-duration', type=float,help="Number of hours between start of ramp up to start of ramp down")
    parser.add_argument('-R', '--ramp-down', type=float,help="Cycle ramp rate down")
    parser.add_argument('-U', '--ramp-up', type=float,help="Cycle ramp rate up")
    parser.add_argument('-H', '--heatswitch-delay', type=float,help="Number of hours between start of ramp up to heatswitch toggle")
    parser.add_argument('-S', '--set-point', type=float,help="Magnet set point for cycle")

    args=parser.parse_args()
    return args



def go():
    args=get_cmdline_args()
    settings={}
    if args.settingsfile is not None:
        with open(args.settingsfile,'r') as jsonfile:
            settings=json.load(jsonfile)
        onlinesettings=None

    if args.settingsfile is None or len(settings)<5:
        s=database.SettingsWatcherThread()
        del s.settings['_id']
        onlinesettings = copy.deepcopy(s.settings)
        #if anything is present in the file, use it to override what's in the database
        if 'cycle' not in settings and not args.update_same_cycle:
            #If the cycle settings aren't present, disarm the cycle.
            s.settings['cycle']['armed']=False
        s.settings.update(settings)
        settings=s.settings

    
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
    if args.cycle_duration is not None:
        settings['cycle']['duration']=args.cycle_duration
    if args.ramp_down is not None:
        settings['cycle']['ramprate_down']=args.ramp_down
    if args.ramp_up is not None:
        settings['cycle']['ramprate_up']=args.ramp_up
    if args.heatswitch_delay is not None:
        settings['cycle']['heatswitch_delay']=args.heatswitch_delay
    if args.set_point is not None:
        settings['cycle']['setpoint']=args.set_point
    sort_out_timestamps(settings)

    onlinesettings=start_new_cycle(settings,onlinesettings,args) # This decides whether a new cycle is being started
    writeout = copy.deepcopy(settings)
    #If there were no args, there can't be any changes to the settings, so don't write anything
    if len(sys.argv) > 1:
        write_settings(settings,onlinesettings)
    
    writeout['cycle']['start_time']=writeout['cycle']['start_time'].isoformat()
    writeout['timestamp']=writeout['timestamp'].isoformat()
    #print(writeout)
    jstr=json.dumps(writeout, indent=4, sort_keys=True)
    print(jstr)
    with open('presets/lastsettings.json','w') as outfile:
        outfile.write(jstr)

def sort_out_timestamps(settings):
    """Modifies the settings argument"""
    #we ignore the value of timestame set in the json file
    now= datetime.now(tz=timezone.utc)
    cycle = settings['cycle'] 
    time=cycle['start_time']    
    settings['timestamp'] =now


    if type(cycle['start_time']) is str:
        cycle['start_time']=datetime.fromisoformat(time)
    if cycle['heatswitch_delay'] >= cycle['duration']:
        print("Heatswitch delay must be less than duration. ")
        exit()

def start_new_cycle(settings,onlinesettings,args):
    cycle = settings['cycle']
    time=cycle['start_time']    
    now= datetime.now(tz=timezone.utc)
    localnow = datetime.now()
    if cycle['armed']==True and not args.update_same_cycle and args.settingsfile is not None:
        if time < now:
            print(f"current time: {localnow}")
            print(f"cycle start:  {time}")
            print("cycle start time must be in the future!")
            x=input("Do you want to set the date to today? [y/n]")
            if x == 'y':
                newtime=time.replace(year=localnow.year,month=localnow.month,day=localnow.day)
                if newtime < now:
                    print(f"current time: {now}")
                    print(f"cycle start:  {newtime}")
                    z=input("The start time would still be in the past. Set date to tomorrow? [y/n]")
                    if z=="y":
                        newtime=newtime.replace(day=localnow.day+1)
                        print(f"current time: {now}")
                        print(f"cycle start:  {newtime}")
                    else:
                        exit()
                settings['cycle']['start_time'] = newtime
            else:
                exit()
        c=input("are you sure you want to start a new cycle? [y/n]")
        if c!='y':
            print('exiting...')
            exit()
        if onlinesettings is None:
            s=database.SettingsWatcherThread()
            onlinesettings = s.settings
            del onlinesettings['_id']
        cycle['cycle_ID']=onlinesettings['cycle']['cycle_ID']+1
        # with open(args.settingsfile,'w') as autocyclesettingsfile:
        #     writeout = copy.deepcopy(settings)
        #     writeout['cycle']['start_time']=writeout['cycle']['start_time'].isoformat()
        #     writeout['timestamp']=writeout['timestamp'].isoformat()
        #     autocyclesettingsfile.write(json.dumps(writeout, indent=4, sort_keys=True))
    return onlinesettings
# from https://stackoverflow.com/questions/27265939/comparing-python-dictionaries-and-nested-dictionaries#27266178
def findDiff(d1, d2, path=""):
    for k in d1.keys():
        if not k in d2:
            print (path, ":")
            print (k + " as key not in d2", "\n")
        else:
            if type(d1[k]) is dict:
                if path == "":
                    nested_path = k
                else:
                    nested_path = path + "->" + k
                findDiff(d1[k],d2[k], nested_path)
            else:
                if d1[k] != d2[k]:
                    if path!="":
                        print(f"{path}: {k} changed from {d1[k]} to {d2[k]}")
                    else:
                        print(f"{k} changed from {d1[k]} to {d2[k]}")
def write_settings(settings,onlinesettings):

    findDiff(onlinesettings,settings)
    x=input("Accept these changes? [y/n]")
    if x!= 'y':
        exit()
    client=MongoClient('localhost',27017)
    with open("mongostring",'r') as mfile:
        mstring=mfile.read()
    client = MongoClient(mstring)
    db=client.hk_data
    collection=db.settings

    collection.insert_one(settings)

if __name__=="__main__":
    go()