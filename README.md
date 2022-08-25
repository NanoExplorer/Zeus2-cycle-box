# Zeus2-cycle-box
New housekeeping program written in Python for controlling and reading the Zeus2 thermometry

# Usage
## Setup
For most people, you will only need the "library," which allows viewing HK data and uploading settings. Please view its separate [README.md file](cycle-box-lib/README.md)

The server code runs on Python 3 and depends on the following packages:
* pymongo
* dnspython
* labjack and the exodriver (or windows equivalent, available from the labjack website, only required on the computer running HK_server.py)
* tabulate (for the live_table.py script)
* scipy
* numpy
* matplotlib (for the live_plot script)

Unfortunately, it also depends on a python2 installation for controlling the motor boxes. Some code will need to be updated to point correctly to the python2 binary.

Make sure that a file called "mongostring" is created in the same directory as the pytho files that includes the ip address, username and password to the mongodb database in the format `mongodb_srv://<USERNAME>:<PASSWORD>@<HOSTNAME>/options` I don't know the full story, but this is what I'm using now for an externally hosted MongoDB database. I will need to migrate back to a local database before APEX.

Make sure the mongodb database is set up following the directions in mongo/MongoDB Notes.

Once these packages have been installed and set up, plug the labjack into the computer that will be used for housekeeping and run HK_server.py.

You will see output confirming that the U6 stream was set up and that the script is reading data. It will take about 20 seconds before you see output (depending on the content of the sensors/settling time setting).

Remember that output is not displayed by the HK_server script itself.

# Internals

## Outline
Most of the important logic is in `HK_server.py`. It launches several threads. One thread talks to the labjack. One thread listens for changes to the settings database, and one thread uploads new data points to the thermometry database. The main thread coordinates all these threads, interpolating voltages into temperatures, deciding which sensors to read, etc. 

`database.py` includes a thread to watch for changes to a database and a thread that will upload changes to a database. Both use queues for communication since they're they're thread-safe. 

The database we use is Mongodb. It is a unique database: instead of storing data as tables, its native format is JSON (which is similar to a Python dictionary). 

The computer connected to the labjack will run the Mongo database server, which will keep logs of all the history of temperatures and settings.

`etherser.py` is a library used by `heatswitch_automatic.py` to allow communication with the motor box. These two scripts have not been ported from Python 2 to Python 3, so at the moment both are needed.

`labjack.py` contains the labjack communication thread. It reads in sensors in `stream` mode and sets the output digital and analog ports. *it still needs to read in the digital ports*.

`LJtreamingtest` is a sample python script provided by the labjack team. It is what the labjack interface is based on.

`mongo_init.py` is currently what I'm using to upload and change the settings for the system. It contains all the fields that you can edit, and running the script posts the settings to the settings database.

## Threading
A lot of threads are used by this code. Be careful when editing variables that are in a different thread---that's what `lock` variables are for. When in doubt, acquire the lock before editing the variable. One-shot modifications like `variable=False` are safe, and so is pushing data to a Queue, but everything else probably needs a lock. I tried to annotate this in the comments, and somewhere I put a link to a very useful slideshow. 

## Reading the Labjack
The labjack is always in stream mode. It will take  a large number of data points and return them in an array. We then average the voltage points and return a single voltage for that time period, which helps reduce noise. About three times a second, all of the sensors are read by the labjack. The main thread then decides whether to keep that voltage data point (i.e., has the sensor had time to settle?). Since the labjack is always in the same mode, we will hopefully avoid the kind of timing errors we have seen in the past.

# Next Steps
We've just added python 3 support! Most of the "live" code is now in Py3. However, py2 is still required in order for the etherser code to work (the motor box control script is started as a subprocess under python 2. That code is monstrous and I do not want to have to migrate it. Hopefully it will just work and not need modification ever.) 

We need a way to graphically edit the settings and display the temperatures. One idea is to write a python webserver that communicates with the database and a javascript plot app that you can view in a web browser. The javascript could also upload new settings to the server, which would put it in the database. This would be very cool to use, but difficult to write.

The other idea would be to just make a python ui that connects directly to the database server. Could do something like matplotlib's built-in ui and an animated plot.

The current best idea we've come up with is to use the software DashDAQ, which is built on top of plot.ly. It has all sorts of interactive gizmos that run in a web browser.



