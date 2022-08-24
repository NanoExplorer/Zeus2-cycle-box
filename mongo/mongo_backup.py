query = {}
#{"$and":["GRT0-3":{"$exists":False},"GRT4-7":{"$exists":False},"4WIRE":{"$exists":False},"2WIRE":{"$exists":False}]}
import pymongo
import json
import datetime
with open("mongostring","r") as mfile:
    mstring = mfile.read()
client = pymongo.MongoClient(mstring)
db=client.hk_data
thermo = db.thermometry
j=thermo.find(query)
a=[]
for e,i in enumerate(j):
	del i["_id"]
	i['timestamp']=i['timestamp'].isoformat()
	#print(i)
	a.append(i)
	if e%100000==0:
		print(f'have backed up {e} records')
print("writing json")
with open('thermometry_apex2019.json','w') as f:
	f.write(json.dumps(a))
#__main__:1: DeprecationWarning: remove is deprecated. Use delete_one or delete_many instead.
