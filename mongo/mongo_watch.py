from pymongo import MongoClient
import pymongo
client=MongoClient('localhost',27017)
db=client.hk_data
cursor=db.thermometry.watch(max_await_time_ms=10000)
for change in cursor:
    thing=change['fullDocument']
    print(thing)