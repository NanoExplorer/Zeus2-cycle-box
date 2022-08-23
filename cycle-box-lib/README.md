# zhklib
Library supporting new Zeus 2 Housekeeping routines

# Usage
This code runs on Python 3 and depends on the following packages:
* pymongo
* dnspython
* tabulate 
* scipy
* numpy
* matplotlib 

## Scripts
This package includes the following scripts: 

* `zhk-live-plots` displays and maintains an up-to-date plot of instrument conditions
* `zhk-live-table` displays a table of up-to-date temperature readings
* `zhk-settings` changes cycle box settings

## MongoDB interface 

You will need a file called "mongostring" from Christopher. This contains the address of our server and the password in the format `mongodb_srv://<USERNAME>:<PASSWORD>@<HOSTNAME>/options`


## Changing settings
There are several presets available in the `presets` directory. One must simply run `settings_upload.py presets/the_preset_that_you_want.json`. Use `settings_upload.py --help` to see override options that will let you easily change the PID parameters, set temperature for PID loop, or manual current set point and ramp rate.
