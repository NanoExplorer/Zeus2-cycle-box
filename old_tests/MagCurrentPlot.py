import psutil
psutil.cpu_percent(interval=None)
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import datetime
from matplotlib.animation import FuncAnimation, writers
import hkpc_data_parser
import traceback

class animatedplot():
    def __init__(self,
                 size,
                 hkpath,
                 interval=2000
                ):
        #Writer = writers['ffmpeg']
        #writer = Writer(fps=15, metadata=dict(artist='Me'), bitrate=1800)
        self.size=size
        self.utiliz=np.ones(self.size)*np.nan
        #fillerdate = datetime.datetime.now()
        fillerdate = datetime.datetime.strptime("9/4/2018 12:00:02 AM","%m/%d/%Y %I:%M:%S %p")
        self.timearr=np.full_like(self.utiliz,
                                  matplotlib.dates.date2num(fillerdate))
        self.timearr2 = np.full_like(self.utiliz,matplotlib.dates.date2num(fillerdate))
        self.memry = np.ones(self.size)*np.nan
        
        self.fig,axs = plt.subplots(2,1,sharex=True)
        self.ax1=axs[0]
        self.ax2=axs[1]
        self.ln, = self.ax1.plot(self.timearr,self.utiliz)
        self.ln2, =self.ax2.plot(self.timearr,self.memry)

        self.anim = FuncAnimation(self.fig,self.update,frames = np.arange(200),
                                  #init_func=self.animinit(),
                                  interval=interval,
                                  blit=False
                                  )
        self.sensors = ['MagnetCurrent','GRT6']
        self.files_to_watch = [hkpath+hkpc_data_parser.get_filename(s) for s in self.sensors]
        self.filesizes = dict([(f,0) for f in self.files_to_watch])
        self.want_cols = dict([(f,0 if s=='MagnetCurrent' else 1) for s,f in zip(self.sensors,self.files_to_watch)])

        assert(len(self.filesizes) == 2) #because we have 2 sub axes right now. Maybe at some point
        #update this program to have dynamic number of sub plots. Would be nice. 
        plt.subplots_adjust(hspace=.1)
        self.ax1.grid()
        self.ax1.grid(which='minor')
        plt.minorticks_on()
        self.ax2.grid()
        plt.locator_params(nbins=5)
        xfmt = matplotlib.dates.DateFormatter('%Y-%m-%d\n%H:%M:%S')
        self.ax1.xaxis.set_major_formatter(xfmt)
        #padding = datetime.timedelta(seconds=3)
        padding=1/24/60/60
        self.ax1.set_xlim(np.min(self.timearr)-padding,np.max(self.timearr)+padding)
        plt.show()



    """
        new_timearr = np.empty_like(self.timearr)
        new_timearr2 = np.empty_like(self.timearr2)
        new_utiliz = np.empty_like(self.utiliz)
        new_memry = np.empty_like(self.memry)

        new_timearr2[1:] = self.timearr2[:-1]
        new_timearr[1:] = self.timearr[:-1]
        new_utiliz[1:] = self.utiliz[:-1]
        new_memry[1:] = self.memry[:-1]

        self.timearr = new_timearr
        self.timearr2=new_timearr2
        self.utiliz = new_utiliz
        self.memry = new_memry

        self.timearr2[0]=matplotlib.dates.date2num(time2)
        self.timearr[0]=matplotlib.dates.date2num(time1)
        self.memry[0]=valu2
        self.utiliz[0]=valu1
    """
    def update(self,frame):
        #self.add_value(datetime.datetime.now(), psutil.cpu_percent(interval=None),
        #               datetime.datetime.now(), psutil.virtual_memory().percent)
        for filename in self.filesizes:
            with open(filename,'r') as thefile:
                thefile.seek(self.filesizes[filename])
                newtimes = []
                newvalues=[]
                for line in thefile:
                    try:
                        #print(line)
                        parsed_line = hkpc_data_parser.parse(line)
                        newvalues.append(parsed_line[1][self.want_cols[filename]])
                        newtimes.append(matplotlib.dates.date2num(parsed_line[0]))
                    except:
                        print("LINE THAT CAUSED ERROR:")
                        print(line)
                        print("END LINE THAT CAUSED ERROR")
                        traceback.print_exc()
                #UGLY HACK THAT WILL PERSIST UNTIL I MAKE THIS A MORE DYNAMIC FUNCTION:
                #SORRY TO ALL FUTURE READERS, PLEASE DON'T POST TO r/programminghorror
                self.filesizes[filename]=thefile.tell()
            if len(newvalues) > self.size:
                newvalues = newvalues[-self.size+1:] #I don't actually know if the +1 is necessary, but just in case.
                newtimes = newtimes[-self.size+1:]
            if len(newvalues) > 0:
                if self.want_cols[filename] == 0:
                    self.utiliz = add_values(self.utiliz,newvalues)
                    self.timearr = add_values(self.timearr,newtimes)
                else:
                    self.memry = add_values(self.memry,newvalues)
                    self.timearr2=add_values(self.timearr2,newtimes)



        self.ln.set_data(self.timearr,self.utiliz)
        self.ln2.set_data(self.timearr2,self.memry)
        self.ax1.set_xlim(np.min(self.timearr),np.max(self.timearr))
        self.ax1.set_ylim(np.nanmin(self.utiliz)-0.1,np.nanmax(self.utiliz)+0.1)

        self.ax2.set_ylim(np.nanmin(self.memry)-0.1,np.nanmax(self.memry)+0.1)
        #self.ax.figure.canvas.draw()
        return self.ln,

def add_values(arr,values):
    num_values=len(values)
    new_arr = np.empty_like(arr)
    new_arr[num_values:]=arr[:-num_values]
    new_arr[:num_values]=values[::-1]
    return new_arr



a = animatedplot(30*60,'/home/christopher/Desktop/',interval=2000)
