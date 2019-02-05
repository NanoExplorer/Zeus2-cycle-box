import psutil
psutil.cpu_percent(interval=None)
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import numpy.ma as ma
import time
from matplotlib.animation import FuncAnimation, writers

def masked_test():
    size=10
    utiliz = ma.masked_array(np.zeros(size),mask=np.ones(size))
    timearr = ma.masked_array(np.zeros(size),mask=np.ones(size))
    curr_index = 0

    fig = plt.figure()
    ax=fig.add_subplot(1,1,1)
    fig.canvas.draw()
    graph = ax.plot(timearr,utiliz)[0]
    ax.set_xlim(min(timearr)-1,max(timearr)+1)
    ax.set_ylim(min(utiliz)-1,max(utiliz)+1)

    axbg = fig.canvas.copy_from_bbox(ax.bbox)

    for x in range(800):
        curr_index = x % size
        percent = psutil.cpu_percent(interval=None)
        utiliz[curr_index]=percent
        timearr[curr_index] = time.time()
        utiliz[(curr_index+1)%size]=ma.masked
        timearr[(curr_index+1)%size] = ma.masked
        graph.set_ydata(utiliz)
        graph.set_xdata(timearr)
        ax.set_xlim(min(timearr)-1,max(timearr)+1)
        ax.set_ylim(min(utiliz)-1,max(utiliz)+1)
        fig.canvas.restore_region(axbg)
        ax.draw_artist(graph)
        fig.canvas.blit(ax.bbox)
        plt.pause(0.01)
        time.sleep(0.5)

        print(utiliz)
        print(timearr)

def nan_roll_test():
    size=100
    utiliz =np.ones(size)*np.nan
    timearr = np.ones(size)*np.nan

    fig = plt.figure()
    ax=fig.add_subplot(1,1,1)
    fig.canvas.draw()
    graph = ax.plot(timearr,utiliz)[0]
    #ax.set_xlim(np.nanmin(timearr)-1,np.nanmax(timearr)+1)
    #ax.set_ylim(np.nanmin(utiliz)-1,np.nanmax(utiliz)+1)

    axbg = fig.canvas.copy_from_bbox(ax.bbox)
    plt.pause(0.1)
    for x in range(800):
        new_timearr = np.empty_like(timearr)
        new_utiliz = np.empty_like(utiliz)
        new_timearr[1:] = timearr[:-1]
        new_utiliz[1:] = utiliz[:-1]
        timearr = new_timearr
        utiliz = new_utiliz
        percent = psutil.cpu_percent(interval=None)
        utiliz[0]=percent
        timearr[0] = time.time()
        graph.set_ydata(utiliz)
        graph.set_xdata(timearr)
        ax.set_xlim(np.nanmin(timearr)-1,np.nanmax(timearr)+1)
        ax.set_ylim(np.nanmin(utiliz)-1,np.nanmax(utiliz)+1)
        fig.canvas.restore_region(axbg)
        ax.draw_artist(graph)
        fig.canvas.blit(ax.bbox)
        #plt.pause(0.1)
        time.sleep(0.5)

        #print(utiliz)
        #print(timearr)




        #print(utiliz)
        #print(timearr)
class animatedplot():
    def __init__(self,size):
        Writer = writers['ffmpeg']
        writer = Writer(fps=15, metadata=dict(artist='Me'), bitrate=1800)
        self.size=size
        self.utiliz=np.ones(self.size)*np.nan
        self.timearr=np.ones(self.size)*np.nan
        self.memry = np.ones(self.size)*np.nan
        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(2,1,1)
        self.ln, = self.ax1.plot(self.utiliz,self.timearr)
        self.ax2 = self.fig.add_subplot(2,1,2)
        self.ln2, =self.ax2.plot(self.memry,self.timearr)
        self.anim = FuncAnimation(self.fig,self.update,frames = np.arange(200),
                                  #init_func=self.animinit(),
                                  blit=False
                                  )
        #plt.show()
        self.anim.save('video.mp4',writer=writer)

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
        self.timearr[0] = time.time()
        self.memry[0]= psutil.virtual_memory().percent

        self.ln.set_data(self.timearr,self.utiliz)
        self.ln2.set_data(self.timearr,self.memry)
        self.ax1.set_xlim(np.nanmin(self.timearr)-0.1,np.nanmax(self.timearr)+0.1)
        self.ax1.set_ylim(np.nanmin(self.utiliz)-0.1,np.nanmax(self.utiliz)+0.1)

        self.ax2.set_xlim(np.nanmin(self.timearr)-0.1,np.nanmax(self.timearr)+0.1)
        self.ax2.set_ylim(np.nanmin(self.memry)-0.1,np.nanmax(self.memry)+0.1)
        #self.ax.figure.canvas.draw()
        return self.ln,
a = animatedplot(100)
