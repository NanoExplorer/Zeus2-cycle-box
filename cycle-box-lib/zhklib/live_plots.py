import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import datetime
# from datetime import timezone, timedelta
from matplotlib.animation import FuncAnimation  # , writers
from zhklib.database import ThermometryWatcherThread
import queue
import argparse
from zhklib.common import DISPLAY_IN_TZ
import importlib.resources as res
from zhklib import data

class RollingNumpyArrays():
    def __init__(self, size):
        # self.value is nan before the array has been fully filled
        self.value = np.ones(size)*np.nan
        self.time = np.full_like(self.value,
            matplotlib.dates.date2num(datetime.datetime.now()))  # noqa: E128

    def update(self, add_val, add_time):
        # every time a new value isadded, we shift all 
        # the other values to the left and add the new
        # value at the end.

        # Note fixed size of array and deletion of old values
        new_valuearr = np.empty_like(self.value)
        new_timearr = np.empty_like(self.time)
        new_timearr[1:] = self.time[:-1]
        new_valuearr[1:] = self.value[:-1]
        self.time = new_timearr
        self.value = new_valuearr
        self.value[0] = add_val
        self.time[0] = matplotlib.dates.date2num(add_time)


class animatedplot():
    def __init__(self, size, servo=None):
        # Writer = writers['ffmpeg']
        # writer = Writer(fps=15, metadata=dict(artist='Me'), bitrate=1800)
        self.size = size

        # These queries do the same thing. They look for documents
        # that contain at least one thermometry sensor reading.
        # Otherwise we get swamped with magent current updates.
        q2 = {'$or': [{'fullDocument.2WIRE': {'$exists': True}},
                      {'fullDocument.4WIRE': {'$exists': True}},
                      {'fullDocument.GRT0-3': {'$exists': True}},
                      {'fullDocument.GRT4-7': {'$exists': True}}]}
        q = {'$or': [{'2WIRE': {'$exists': True}}, 
                     {'4WIRE': {'$exists': True}}, 
                     {'GRT0-3': {'$exists': True}}, 
                     {'GRT4-7': {'$exists': True}}]}
        self.servo = servo
        self.twt = ThermometryWatcherThread(num_previous=size*4,
                                            previous_query=q,
                                            live_query=q2
                                            )
        # Daemon mode means the twt will quit when the program
        # exits, I think.
        self.twt.setDaemon(True)
        self.twt.start()
        with res.open_text(data,"Sensor_ID.txt") as idfile:
            self.sensors_id = np.genfromtxt(idfile,
                                            skip_header=2,
                                            delimiter='\t',
                                            dtype=str)
        self.sensor_names = self.sensors_id[:, 1]
        self.sensor_names = np.append(self.sensor_names, ["Current (A)", "Voltage (V)"])
        self.sensor_arrays = [RollingNumpyArrays(size) for i in self.sensor_names]
        # Every thermometry update contains a magnet update.
        # So if you're reading out 3 sensors per card,
        # you'll get 3 magnet updates for every sensor update
        self.sensor_arrays[-1] = RollingNumpyArrays(size*3)
        self.sensor_arrays[-2] = RollingNumpyArrays(size*3)
        if self.servo is not None:
            for s in self.servo:
                self.sensor_arrays[s] = RollingNumpyArrays(size * 10)
            self.sensor_arrays[-1] = RollingNumpyArrays(size * 10)
            self.sensor_arrays[-2] = RollingNumpyArrays(size * 10)
        
        # To access the self.sensor_arrays value for 4WIRE3, 
        # the index in that array is card_offsets['4WIRE']+3
        self.card_array_offsets = {'2WIRE': 12,
                                   '4WIRE': 8,
                                   'GRT0-3': 0,
                                   'GRT4-7': 0}

        self.process_queue()
        # Move grt0 and grt7 onto the "3rd cold stage" plot
        # while servoing, just like we did in the labview program
        if self.servo is None:
            self.plots = [4, 1, -1, -1, -1, 1, 4, 4, 0, 0, 3, 3, -1, -1, -1, -1, -1, 3, 3, 0, 2, 5]
        else:
            self.plots = [1, 1, -1, -1, -1, 1, 4, 1, 0, 0, 3, 3, -1, -1, -1, -1, -1, 3, 3, 0, 2, 5]
        self.fig, axs = plt.subplots(2, 3, sharex=True)
        self.fig.tight_layout()
        ((self.ax1, self.ax2, self.ax3), (self.ax4, self.ax5, self.ax6)) = axs
        self.axes = [self.ax1, self.ax2, self.ax3, self.ax4, self.ax5, self.ax6]
         
        self.lns = []
        for i, p in enumerate(self.plots):
            if p == -1:
                self.lns.append(None)
            else:
                ax = self.axes[p]
                ln, = ax.plot(self.sensor_arrays[i].time,
                              self.sensor_arrays[i].value,
                              label=self.sensor_names[i])
                self.lns.append(ln)

        self.anim = FuncAnimation(self.fig, self.update, frames = np.arange(200),
                                  # init_func=self.animinit(),
                                  interval=1200,
                                  blit=False
                                  )

        plt.subplots_adjust(hspace=.1)

        xfmt = matplotlib.dates.DateFormatter('%m-%d\n%H:%M:%S', tz=DISPLAY_IN_TZ)

        for ax in self.axes:
            ax.grid()
            # ax.grid(which='minor')
            # ax.minorticks_on()
            # ax.locator_params(nbins=5)
            ax.xaxis.set_major_formatter(xfmt)
            ax.legend()
        self.set_min_max()

        plt.show()

    def minmaxdate(self):
        if self.servo is None:
            mins = []
            maxs = []
            # idxs = []
            for plot, rnparr in zip(self.plots, self.sensor_arrays):
                if plot != -1 and not np.isnan(rnparr.value).all():
                    mins.append(np.min(rnparr.time[np.logical_not(np.isnan(rnparr.value))]))
                    maxs.append(np.max(rnparr.time[np.logical_not(np.isnan(rnparr.value))]))
            return min(mins), max(maxs)
        else:

            servoarray = self.sensor_arrays[self.servo[0]].value
            servotime = self.sensor_arrays[self.servo[0]].time
            nonnantimes = servotime[np.logical_not(np.isnan(servoarray))]
            return min(nonnantimes), max(nonnantimes)

    def process_sensor(self, card, num, temperature, time):
        if card == 'Voltage':
            idx = -1
        elif card == 'Current':
            idx = -2 
        else:
            idx = self.card_array_offsets[card]+num
        self.sensor_arrays[idx].update(temperature, time)

    def process_queue(self):
        try:
            while True:
                d = self.twt.newdata.get_nowait()
                # print(d)
                for k in ['2WIRE', '4WIRE', 'GRT0-3', 'GRT4-7', "Voltage", "Current"]:
                    try:
                        v = d[k]
                        self.process_sensor(k, v[0], v[1], d['timestamp'])
                    except KeyError:
                        pass

        except queue.Empty:
            pass

    def set_min_max(self):
        mintime, maxtime = self.minmaxdate()
        padding = 1/24/60/60
        for ax in self.axes:
            ax.set_xlim(mintime-padding, maxtime+padding)

    def update(self, frame):
        self.process_queue()
        for ln, data in zip(self.lns, self.sensor_arrays):
            if ln is not None:
                ln.set_data(data.time, data.value)
        self.set_min_max()
        # self.ax1.set_ylim(np.nanmin(self.utiliz)-0.1,np.nanmax(self.utiliz)+0.1)

        # self.ax2.set_ylim(np.nanmin(self.memry)-0.1,np.nanmax(self.memry)+0.1)
        # self.ax.figure.canvas.draw()
        return self.lns[0],


def main():
    parser = argparse.ArgumentParser(description="view Zeus2 thermometry data in graphical plot form")
    parser.add_argument('-s', '--servo', type=int, nargs='+', help="indicate you're in servo mode. Takes 1 integer argument: the sensor(s) you're reading fast")
    parser.add_argument('-n', '--numpts', type=int, help="Number of points to display on plot. Default 100", default=100)
    args = parser.parse_args()
    if args.servo is not None:
        print("in servo mode")
        animatedplot(int(args.numpts*3/10), servo=args.servo)
    else:
        animatedplot(args.numpts)


if __name__ == "__main__":
    main()