from pymongo import MongoClient
import pymongo
with open("mongostring",'r') as mfile:
    mstring=mfile.read()
client = MongoClient(mstring)
db=client.hk_data
cursor=db.thermometry.watch(max_await_time_ms=10000)
for change in cursor:
    thing=change['fullDocument']
    print(thing)