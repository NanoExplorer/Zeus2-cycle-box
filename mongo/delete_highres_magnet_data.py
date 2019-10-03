query = {"$and":[{"GRT0-3":{"$exists":False}},
				 {"GRT4-7":{"$exists":False}},
				 {"4WIRE":{"$exists":False}},
				 {"2WIRE":{"$exists":False}},
				 {"auto_cycle_status":{"$exists":False}},
				 {"currently_in_servo":{"$exists":False}}
]}

# {$and:[{"GRT0-3":{$exists:false}},{"GRT4-7":{$exists:false}},{"4WIRE":{$exists:false}},{"2WIRE":{$exists:false}}]}
#{"$and":["GRT0-3":{"$exists":False},"GRT4-7":{"$exists":False},"4WIRE":{"$exists":False},"2WIRE":{"$exists":False}]}
import pymongo
with open("mongostring","r") as mfile:
    mstring = mfile.read()
client = pymongo.MongoClient(mstring)
db=client.hk_data
thermo = db.thermometry
thermo.remove(query)
#__main__:1: DeprecationWarning: remove is deprecated. Use delete_one or delete_many instead.
