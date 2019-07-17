# Zeus2-cycle-box
New housekeeping program written in Python for controlling and reading the Zeus2 thermometry

## Outline
Most of the important logic is in `HK_server.py`. It launches several threads. One thread talks to the labjack. One thread listens for changes to the settings database, and one thread uploads new data points to the thermometry database. The main thread coordinates all these threads, interpolating voltages into temperatures, deciding which sensors to read, etc. 

`database.py` includes a thread to watch for changes to a database and a thread that will upload changes to a database. Both use queues for communication since they're they're thread-safe. 

The database we use is Mongodb. It is a unique database. Instead of storing data as tables, its native format is JSON (basically the same as a Python dictionary). 

The computer connected to the labjack will run the Mongo database server, which will keep logs of all the history of temperatures and settings.

`etherser.py` is a library used by `heatswitch_automatic.py` to allow communication with the motor box. 

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



