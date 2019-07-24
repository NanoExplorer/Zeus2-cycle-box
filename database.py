from pymongo import MongoClient
import pymongo
import threading
import queue
from datetime import datetime

class SettingsWatcherThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        with open("mongostring",'r') as mfile:
            mstring=mfile.read()
        self.client = MongoClient(mstring)
        self.db=self.client.hk_data
        self.settingsdb=self.db.settings
        self.settings = {}
        self.keepGoing=True
        #The keepgoing variables don't have locks. I am not confident that this is a good
        #decision, but I think it's reasonable since they are all modified in only one place,
        #the logicclass's stop method. I think that means that all of the operations on keepGoing are
        #atomic. the only things that ever access keepGoing are "while keepgoing:" and keepgoing=False
        self.settingsLock = threading.Lock()
        self.get_settings()
        #YOU MUST ACQUIRE THE SETTINGS LOCK BEFORE ACCESSING THE SETTINGS VARIABLE.
        #Why: https://www.slideshare.net/dabeaz/an-introduction-to-python-concurrency
        #example:
        #with self.settingsLock:
        #    self.settings="WHATEVER"
        #Never acquire more than one lock at a time.

    def get_settings(self):
        with self.settingsLock:
            self.settings=self.settingsdb.find_one(sort=[("timestamp",pymongo.DESCENDING)])
            #print(self.settings)

    def run(self):
        cursor=self.settingsdb.watch()
        #This returns an iterable that blocks until the database changes. Then it returns
        #an object describing the change. I'll be adding whole documents to the database,
        #and I'll want to see them, so I'll access the 'fullDocument' part of the change obj
        for change in cursor:
            if not self.keepGoing:
                break
                #NOTE: This causes weird behavior. The program might hang on exit
                #until you send a change to the settings database.... There's no non-blocking
                #or half-blocking way to access a change cursor.
                #An ugly hack would be to have the ui server constantly update some
                #current time record, and then this method could ignore those changes...
                #Or to have the exit method publish a record to the database!
                #SOLUTION: Make this a daemonic thread!
            with self.settingsLock:
                self.settings=change['fullDocument']

class DatabaseUploaderThread(threading.Thread):
    """
    This class interfaces with a mongodb database and uploads temperature data to it
    Whenever you want to upload a data point to the thread, just add something to the q!
    """
    def __init__(self):
        threading.Thread.__init__(self)
        with open("mongostring",'r') as mfile:
            mstring=mfile.read()
        self.client = MongoClient(mstring)
        self.db=self.client.hk_data
        self.thermometrydb=self.db.thermometry
        self.q = queue.Queue()
        #Queues are thread safe. You do not need to use a lock to communicate with a queue.
        self.keepGoing=True

    def run(self):
        while self.keepGoing:
            self.upload()

    def upload(self):
        try:
            data = self.q.get(True,None)
            data.update({'timestamp':datetime.now()})
            self.thermometrydb.insert_one(data)
        except queue.Empty:
            print("Upload queue is empty?")


class ThermometryWatcherThread(threading.Thread):
    def __init__(self,num_previous=0,previous_query={},live_query={}):
        """
        to get past results (i.e. for pre-populating
        a graph) tell us the number of events you want
        in the past and the fields you want to see (in 
        mongodb query form)

        """
        threading.Thread.__init__(self)
        with open("mongostring",'r') as mfile:
            mstring=mfile.read()
        client = MongoClient(mstring)
        self.db=client.hk_data
        self.newdata= queue.Queue()
        self.live_query=live_query
        if num_previous>0:
            c=self.db.thermometry.find(previous_query).sort('timestamp',-1).limit(num_previous)
            docs =[]
            for doc in c:
                docs.append(doc)
            #I want the oldest documents first
            #earlier mongo sorted so that newest docs are first
            for doc in docs[::-1]:
                self.newdata.put_nowait(doc)


    def run(self): #[{"$match":self.live_query}
        cursor=self.db.thermometry.watch([{"$match":self.live_query}],max_await_time_ms=10000)
        for change in cursor:
                #print("Got an update")
                self.newdata.put_nowait(change['fullDocument'])