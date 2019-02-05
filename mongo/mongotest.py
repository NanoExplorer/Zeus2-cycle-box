from pymongo import MongoClient
client=MongoClient('localhost',27017)
db=client.hk_data
collection=db.thermometry
for thing in collection.find({},{'auto_cycle_status':1,'_id':0}):
    if len(thing)>0:
        print(thing)