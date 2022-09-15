from pymongo import MongoClient
import pymongo
import threading
import queue
from datetime import datetime, timezone
import logging
import time
from bson.codec_options import CodecOptions
from zhklib.common import CONFIG_FOLDER


def read_mongostring():
    with open(CONFIG_FOLDER + "mongostring", 'r') as mfile:
        mstring = mfile.read()
    return mstring


class SettingsWatcherThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        mstring = read_mongostring()
        self.client = MongoClient(mstring)
        self.db = self.client.hk_data
        options = CodecOptions(tz_aware=True)
        self.settingsdb = self.db.settings.with_options(codec_options=options)
        self.settings = {}
        self.keepGoing = True
        # The keepgoing variables don't have locks. I am not confident that this is a good
        # decision, but I think it's reasonable since they are all modified in only one place,
        # the logicclass's stop method. I think that means that all of the operations on keepGoing are
        # atomic. the only things that ever access keepGoing are "while keepgoing:" and keepgoing=False
        self.settingsLock = threading.Lock()
        self.get_settings()
        # YOU MUST ACQUIRE THE SETTINGS LOCK BEFORE ACCESSING THE SETTINGS VARIABLE.
        # Why: https://www.slideshare.net/dabeaz/an-introduction-to-python-concurrency
        # example:
        # with self.settingsLock:
        #    self.settings="WHATEVER"
        # Never acquire more than one lock at a time.

    def get_settings(self):
        with self.settingsLock:
            self.settings = self.settingsdb.find_one(sort=[("timestamp", pymongo.DESCENDING)])
            # print(self.settings)

    def run(self):
        while True:
            # This infinite loop should only execute once
            try:
                self.watch_for_changes()
            except:
                logging.exception("settings watcher experienced error")
                time.sleep(10)
                self.__init__()

    def watch_for_changes(self):
        cursor = self.settingsdb.watch()
        # This returns an iterable that blocks until the database changes. Then it returns
        # an object describing the change. I'll be adding whole documents to the database,
        # and I'll want to see them, so I'll access the 'fullDocument' part of the change obj
        for change in cursor:
            if not self.keepGoing:
                break
                # NOTE: This causes weird behavior. The program might hang on exit
                # until you send a change to the settings database.... There's no non-blocking
                # or half-blocking way to access a change cursor.
                # An ugly hack would be to have the ui server constantly update some
                # current time record, and then this method could ignore those changes...
                # Or to have the exit method publish a record to the database!
                # SOLUTION: Make this a daemonic thread!
            with self.settingsLock:
                self.settings = change['fullDocument']


class DatabaseUploaderThread(threading.Thread):
    """
    This class interfaces with a mongodb database and uploads temperature data to it
    Whenever you want to upload a data point to the thread, just add something to the q!
    """
    def __init__(self):
        threading.Thread.__init__(self)
        mstring = read_mongostring()
        self.client = MongoClient(mstring)
        self.db = self.client.hk_data
        options = CodecOptions(tz_aware=True)
        self.thermometrydb = self.db.thermometry.with_options(codec_options=options)
        self.q = queue.Queue()
        # Queues are thread safe. You do not need to use a lock to communicate with a queue.
        self.keepGoing = True

    def run(self):
        while self.keepGoing:
            try:
                self.upload()
            except:
                logging.exception("thermometry uploader experienced an error")
                time.sleep(10)
                self.__init__()

    def upload(self):
        try:
            data = self.q.get(True, None)
            data.update({'timestamp': datetime.now(timezone.utc)})
            self.thermometrydb.insert_one(data)
        except queue.Empty:
            logging.exception("Upload queue is empty?")


class ThermometryWatcherThread(threading.Thread):
    def __init__(self, num_previous=0, previous_query={}, live_query={}):
        """
        to get past results (i.e. for pre-populating
        a graph) tell us the number of events you want
        in the past and the fields you want to see (in 
        mongodb query form)

        """
        threading.Thread.__init__(self)
        mstring = read_mongostring()
        client = MongoClient(mstring)
        self.db = client.hk_data
        self.newdata = queue.Queue()
        self.live_query = live_query
        options = CodecOptions(tz_aware=True)
        self.thermometrydb = self.db.thermometry.with_options(codec_options=options)
        if num_previous > 0:
            c = self.thermometrydb.find(previous_query).sort('timestamp', -1).limit(num_previous)
            docs = [] 
            for doc in c:
                docs.append(doc)
            # I want the oldest documents first
            # earlier mongo sorted so that newest docs are first
            for doc in docs[::-1]:
                self.newdata.put_nowait(doc)

    def run(self):  # [{"$match":self.live_query}
        cursor = self.thermometrydb.watch([{"$match": self.live_query}], max_await_time_ms=10000)
        for change in cursor:
            # print("Got an update")
            self.newdata.put_nowait(change['fullDocument'])


class SettingsHistory():
    def __init__(self,
                 mongostring=CONFIG_FOLDER + "mongostring",
                 start_date=None,
                 end_date=None,
                 query=None):
        print("WORK IN PROGRESS")
        with open(mongostring,'r') as mfile:
            mstring=mfile.read()
        self.client = MongoClient(mstring)
        self.db=self.client.hk_data
        options=CodecOptions(tz_aware=True)
        self.settingsdb=self.db.settings.with_options(codec_options=options)

        q = make_mongo_query(start_date=start_date,
                             end_date=end_date,
                             custom_query=query)
        self.settings=self.settingsdb.find(q).sort("timestamp",pymongo.ASCENDING)

def make_mongo_query(start_date=None,
                     end_date=None,
                     custom_query=None):
    a = []
    q = {'$and':a}
    if start_date is not None:
        a.append({"timestamp":{"$gt":start_date}})
    if end_date is not None:
        a.append({"timestamp":{"$lt":end_date}})
    if custom_query is not None:
        a.append(custom_query)
    return q


class EasyThermometry():
    def __init__(self,
                 npts,
                 start_date=None,
                 end_date=None,
                 want_sensors='all',
                 mongostring=CONFIG_FOLDER+"mongostring"):
        """Warning:
        start_date, end_date, and want_sensors are works in progress.
        """
        self.sensors = {"2WIRE": [[] for i in range(8)],
                        "4WIRE": [[] for i in range(4)],
                        "GRT": [[] for i in range(8)],
                        "Current": [[]],
                        "Voltage": [[]]}
        if want_sensors == 'all':
            q = {'$or': [
                {'2WIRE': {'$exists': True}},
                {'4WIRE': {'$exists': True}},
                {'GRT0-3': {'$exists': True}},
                {'GRT4-7': {'$exists': True}}
            ]}
        elif want_sensors == 'magnet':
            q = {'Current': {'$exists': True}}
        else:
            print('nyi')
            raise RuntimeError('notyetimplemented')
        q = make_mongo_query(start_date=start_date,
                             end_date=end_date,
                             custom_query=q)
        with open(mongostring, 'r') as mfile:
            mstring = mfile.read()
        client = MongoClient(mstring)
        self.db = client.hk_data
        if npts != 0:
            c = self.db.thermometry.find(q).sort('timestamp', -1).limit(npts)
        else:
            c = self.db.thermometry.find(q).sort('timestamp', -1)
        docs = []
        for doc in c:
            docs.append(doc)
        # I want the oldest documents first
        # earlier mongo sorted so that newest docs are first
        for doc in docs[::-1]:
            for k in ['2WIRE', '4WIRE', 'GRT0-3', 'GRT4-7', "Voltage", "Current"]:
                try:
                    v = doc[k]
                    self.process_sensor(k, v[0], v[1], doc['timestamp'].replace(tzinfo=timezone.utc))
                except KeyError:
                    pass

    def process_sensor(self, card, num, temperature, time):
        if card == 'Voltage':
            num = 0
        elif card == 'Current':
            num = 0
        elif card == "GRT0-3":
            card = "GRT"
        elif card == "GRT4-7":
            card = "GRT"
        self.sensors[card][num].append((time, temperature))
