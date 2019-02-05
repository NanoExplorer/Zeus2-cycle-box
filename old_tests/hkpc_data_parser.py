import numpy as np
import datetime

def parse(line):
    line = line.strip()
    elems = line.split('\t')
    datetimestr = elems[0]+' '+elems[1]
    timestamp=datetime.datetime.strptime(datetimestr,"%m/%d/%Y %I:%M:%S %p")
    values = list(map(float,elems[2:]))
    return (timestamp,values)

def get_filename(sensor):
    return datetime.datetime.now().strftime("%Y%m%d")+"_"+sensor+".txt"