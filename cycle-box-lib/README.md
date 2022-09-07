# zhklib
Library supporting new Zeus 2 Housekeeping routines

# Usage
## Installation
This code runs on Python 3. All of its dependencies should be installed automatically if you navigate to this folder and run `pip install -e .`

Dependencies:
* pymongo
* dnspython
* tabulate 
* scipy
* numpy
* matplotlib 

## Scripts
This package includes the following scripts, which you can call from the command line if this pip package is installed: 

* `zhk-live-plots` displays and maintains an up-to-date plot of instrument conditions
* `zhk-live-table` displays a table of up-to-date temperature readings
* `zhk-settings` changes cycle box settings

## MongoDB interface 

You will need a file called "mongostring" from Christopher. This contains the address of our server and the password in the format `mongodb_srv://<USERNAME>:<PASSWORD>@<HOSTNAME>/options`

Install this file by putting it into a directory called .zeus in your 
home folder or by running `zhk-register-mongo /path/to/your/mongo/file`.

The file `easy_thermometry.ipynb` gives an example for interfacing with the server to extract sensor data.

## Changing settings
There are several presets available in the `presets` directory. One must simply run `settings_upload.py presets/the_preset_that_you_want.json`. Use `settings_upload.py --help` to see override options that will let you easily change the PID parameters, set temperature for PID loop, or manual current set point and ramp rate.
