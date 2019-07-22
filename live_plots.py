import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import datetime
from matplotlib.animation import FuncAnimation, writers
from database import ThermometryWatcherThread
import queue

class RollingNumpyArrays():
    def __init__(self,size):
        self.value=np.ones(size)*np.nan
        self.time=np.full_like(self.value,
            matplotlib.dates.date2num(datetime.datetime.now()))
    def update(self,add_val,add_time):
        new_valuearr = np.empty_like(self.value)
        new_timearr = np.empty_like(self.time)
        new_timearr[1:] = self.time[:-1]
        new_valuearr[1:] = self.value[:-1]
        self.time=new_timearr
        self.value=new_valuearr
        self.value[0]=add_val
        self.time[0]=matplotlib.dates.date2num(add_time)



class animatedplot():
    def __init__(self,size):
        #Writer = writers['ffmpeg']
        #writer = Writer(fps=15, metadata=dict(artist='Me'), bitrate=1800)
        self.size=size
        q={'$or':[{'2WIRE':{'$exists': True}},{'4WIRE':{'$exists': True}},{'GRT0-3':{'$exists': True}},{'GRT4-7':{'$exists': True}}]}
        self.twt = ThermometryWatcherThread(num_previous=600,
        previous_query=q,
        #live_query=q
        )
        self.twt.setDaemon(True)
        self.twt.start()

        self.sensors_id=np.genfromtxt('calibration/Sensor_ID.txt',
                                    skip_header=2,
                                    delimiter='\t',
                                    dtype=str)
        self.sensor_names = self.sensors_id[:,1]
        self.sensor_names=np.append(self.sensor_names,["Current (A)","Voltage (V)"])
        self.sensor_arrays = [RollingNumpyArrays(size) for i in self.sensor_names]
        self.card_array_offsets={'2WIRE':12,
                '4WIRE':8,
                'GRT0-3':0,
                'GRT4-7':0}
        #self.plots = [[8,9,12+7],[1,5],[-2],
        #              [8+2,8+3,12+4,12+5,12+6],[0,6,7],[-1]]
        
        self.process_queue()

        self.plots = [4,1,-1,-1,-1,1,4,4,0,0,3,3,-1,-1,-1,-1,-1,3,3,0,2,5]
        
        self.fig,axs = plt.subplots(2,3,sharex=True)
        self.fig.tight_layout()
        ((self.ax1,self.ax2,self.ax3),(self.ax4,self.ax5,self.ax6))=axs
        self.axes=[self.ax1,self.ax2,self.ax3,self.ax4,self.ax5,self.ax6]
        
        self.lns=[]
        for i,p in enumerate(self.plots):
            if p==-1:
                self.lns.append(None)
            else:
                ax=self.axes[p]
                ln,=ax.plot(self.sensor_arrays[i].time,
                           self.sensor_arrays[i].value,
                           label=self.sensor_names[i])
                self.lns.append(ln)

        self.anim = FuncAnimation(self.fig,self.update,frames = np.arange(200),
                                  #init_func=self.animinit(),
                                  interval=200,
                                  blit=False
                                  )

        plt.subplots_adjust(hspace=.1)
        
        plt.minorticks_on()
        plt.locator_params(nbins=5)
        xfmt = matplotlib.dates.DateFormatter('%m-%d\n%H:%M:%S')

        for ax in self.axes:
            ax.grid()
            ax.grid(which='minor')
            ax.xaxis.set_major_formatter(xfmt)
            ax.legend()
        self.set_min_max()

        plt.show()
    def minmaxdate(self):
        mins=[]
        maxs=[]
        idxs=[]
        for plot,rnparr in zip(self.plots,self.sensor_arrays):
            if plot!=-1 and not np.isnan(rnparr.value).all():
                mins.append(np.min(rnparr.time))
                maxs.append(np.max(rnparr.time))
        return min(mins),max(maxs)
    def process_sensor(self,card,num,temperature,time):
        if card == 'Voltage':
            idx=-1
        elif card == 'Current':
            idx=-2 
        else:
            idx = self.card_array_offsets[card]+num
        self.sensor_arrays[idx].update(temperature,time)
    def process_queue(self):
        try:
            while True:
                d=self.twt.newdata.get_nowait()
                #print(d)
                for k in ['2WIRE','4WIRE','GRT0-3','GRT4-7',"Voltage","Current"]:
                    try:
                        v=d[k]
                        self.process_sensor(k,v[0],v[1],d['timestamp'])
                    except KeyError:
                        pass

        except queue.Empty:
            pass
    def set_min_max(self):
        mintime,maxtime=self.minmaxdate()
        padding=1/24/60/60
        for ax in self.axes:
            ax.set_xlim(mintime-padding,maxtime+padding)
    def update(self,frame):
        self.process_queue()
        for ln,data in zip(self.lns,self.sensor_arrays):
            if ln is not None:
                ln.set_data(data.time,data.value)
        self.set_min_max()
        #self.ax1.set_ylim(np.nanmin(self.utiliz)-0.1,np.nanmax(self.utiliz)+0.1)

        #self.ax2.set_ylim(np.nanmin(self.memry)-0.1,np.nanmax(self.memry)+0.1)
        #self.ax.figure.canvas.draw()
        return self.lns[0],

if __name__=="__main__":
    a = animatedplot(100)
