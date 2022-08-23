#This script prints the sample settings json file and uploads a sample database entry 
from pymongo import MongoClient, InsertOne
from datetime import datetime, timezone, timedelta
import json
import argparse
import copy
import database
import sys
from common import DISPLAY_IN_TZ
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
    
    hsw_vars=[args.cycle_duration, args.ramp_down, args.ramp_up, args.heatswitch_delay, args.set_point]
    if any(v is not None for v in hsw_vars):
        args.update_same_cycle=True
        #print("defaulting to update same cycle")
    return args




def go():
    args=get_cmdline_args()
    settings={}

    s=database.SettingsWatcherThread()
    del s.settings['_id']
    onlinesettings = copy.deepcopy(s.settings)

    if args.settingsfile is not None:
        with open(args.settingsfile,'r') as jsonfile:
            settings=json.load(jsonfile)

    #If there were no args, there can't be any changes to the settings, so just
    # print and exit.
    if len(sys.argv) == 1:
        print_settings(onlinesettings)
        exit()


    if args.settingsfile is None or len(settings)<5 or args.update_same_cycle:
        #if anything is present in the file, use it to override what's in the database
        if 'cycle' not in settings and not args.update_same_cycle:
            #If the cycle settings aren't present, disarm the cycle.
            s.settings['cycle']['armed']=False
        if args.update_same_cycle and 'cycle' in settings:
            #If it's the same cycle, we can't allow changing the cycle id
            # or the start time.
            if "cycle" in settings:
                settings["cycle"]["start_time"] = onlinesettings["cycle"]["start_time"]
                settings["cycle"]["cycle_ID"] = onlinesettings["cycle"]["cycle_ID"]
        s.settings.update(settings)
        #NOTE: this is NOT a recursive update. just in case you thought it was (I did)
        #I think what that means is that you can't omit certain 
        #parameters from a section---it's all or nothing.
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


    write_settings(settings,onlinesettings)
    
    jstr=print_settings(settings)

    with open('presets/lastsettings.json','w') as outfile:
        outfile.write(jstr)

def print_settings(settings):
    try:
        del settings['_id']
    except KeyError:
        pass
    settings['cycle']['start_time']=settings['cycle']['start_time'].astimezone(DISPLAY_IN_TZ).isoformat()
    settings['timestamp']=settings['timestamp'].astimezone(DISPLAY_IN_TZ).isoformat()

    jstr=json.dumps(settings, indent=4, sort_keys=True)

    print(jstr)
    return jstr

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

def print_cyclestart(time,now,hrsfromnow):
    print(f"current time: {now}")
    print(f"cycle start:  {time}")
    print(f"Cycle would start {hrsfromnow:.1f} hours from now")

def handle_future(time,now,mode="set_today"):
    hrsfromnow = (time-now).total_seconds()/3600
    if hrsfromnow < 0:
        print_cyclestart(time,now,hrsfromnow)

    if -1 < hrsfromnow <= 0:
        x=input("Start time is in the near past. Continue with this start time? (y/n)")
        if x == 'y':
            return time

    if hrsfromnow < 0:
        if mode=="set_today":
            print("cycle start time must be in the future!")
            x=input("Do you want to set the date to today? [y/n]")
        elif mode=="tomorrow":
            print("start time is still in the past.")
            x=input("Do you want to set the day to tomorrow? [y/n]")
        if x == 'y':
            if mode=="set_today":
                time=time.replace(year=now.year,month=now.month,day=now.day)
            elif mode=="tomorrow":
                time=time+timedelta(days=1)
        else:
            print("exiting...")
            exit()
    return time


def start_new_cycle(settings,onlinesettings,args):
    cycle = settings['cycle']
    time=cycle['start_time']    
    now= datetime.now(tz=time.tzinfo)
    #localnow = datetime.now()
    if cycle['armed']==True and not args.update_same_cycle and args.settingsfile is not None:
        time=handle_future(time,now)
        time=handle_future(time,now,mode="tomorrow")
        hrsfromnow=(time-now).total_seconds()/3600
        print_cyclestart(time,now,hrsfromnow)
        if hrsfromnow > 12:
            print("*********WARNING: cycle start time is far in the future**********")
        settings['cycle']['start_time'] = time
        c=input("are you sure you want to start a new cycle? [y/n]")
        if c!='y':
            print('exiting...')
            exit()
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
            print (k + " as key not in d2!")
            print (f"setting to {d1[k]}")
            d2[k] = d1[k]
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
    # print("WARNING: in testing mode. Nothing modified.")
    #exit()

if __name__=="__main__":
    go()