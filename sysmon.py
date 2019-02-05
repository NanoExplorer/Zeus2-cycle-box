import psutil
psutil.cpu_percent(interval=None)
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import datetime
from matplotlib.animation import FuncAnimation, writers

class animatedplot():
    def __init__(self,size):
        #Writer = writers['ffmpeg']
        #writer = Writer(fps=15, metadata=dict(artist='Me'), bitrate=1800)
        self.size=size
        self.utiliz=np.ones(self.size)*np.nan
        self.timearr=np.full_like(self.utiliz,
                                  matplotlib.dates.date2num(datetime.datetime.now()))

        self.memry = np.ones(self.size)*np.nan
        
        self.fig,axs = plt.subplots(2,1,sharex=True)
        self.ax1=axs[0]
        self.ax2=axs[1]
        self.ln, = self.ax1.plot(self.timearr,self.utiliz)
        self.ln2, =self.ax2.plot(self.timearr,self.memry)

        self.anim = FuncAnimation(self.fig,self.update,frames = np.arange(200),
                                  #init_func=self.animinit(),
                                  interval=200,
                                  blit=False
                                  )

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

    def update(self,frame):
        new_timearr = np.empty_like(self.timearr)
        new_utiliz = np.empty_like(self.utiliz)
        new_memry = np.empty_like(self.memry)
        new_timearr[1:] = self.timearr[:-1]
        new_utiliz[1:] = self.utiliz[:-1]
        new_memry[1:] = self.memry[:-1]

        self.timearr = new_timearr
        self.utiliz = new_utiliz
        self.memry = new_memry

        percent = psutil.cpu_percent(interval=None)
        self.utiliz[0]=percent
        self.timearr[0] = matplotlib.dates.date2num(datetime.datetime.now())
        self.memry[0]= psutil.virtual_memory().percent
        self.ln.set_data(self.timearr,self.utiliz)
        self.ln2.set_data(self.timearr,self.memry)
        self.ax1.set_xlim(np.min(self.timearr),np.max(self.timearr))
        self.ax1.set_ylim(np.nanmin(self.utiliz)-0.1,np.nanmax(self.utiliz)+0.1)

        self.ax2.set_ylim(np.nanmin(self.memry)-0.1,np.nanmax(self.memry)+0.1)
        #self.ax.figure.canvas.draw()
        return self.ln,
a = animatedplot(100)
