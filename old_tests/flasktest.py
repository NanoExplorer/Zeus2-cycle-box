import time
import threading
import random
from flask import Flask
app=Flask(__name__)



class LogicThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.mostrecent = []
        self.keepGoing=True

    def run(self):
        while self.keepGoing:
            #print("waiting for cond")
            time.sleep(2)
            #print("updating")
            self.update()

    def stop(self):
        self.keepGoing = False

    def update(self):
        self.mostrecent.append(random.random())

    
    def index(self):
        return "Hello World "+str(self.mostrecent)

worker = LogicThread()
@app.route("/")
def thisshouldntevenwork():
    return worker.index()

def main(what,ever):
    worker.start()
    app.run(host='0.0.0.0',port=4000)


if __name__=="__main__":
    main(1,2)