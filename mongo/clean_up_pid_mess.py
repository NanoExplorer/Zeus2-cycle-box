query = {"PID_status":{"$exists":True}}
import pymongo
with open("mongostring","r") as mfile:
    mstring = mfile.read()
client = pymongo.MongoClient(mstring)
db=client.hk_data
thermo = db.thermometry
thermo.remove(query)
#__main__:1: DeprecationWarning: remove is deprecated. Use delete_one or delete_many instead.
