import psutil
psutil.cpu_percent(interval=None)
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import numpy.ma as ma
import time as whatever
size=10
utiliz = ma.masked_array(np.random.random(size),mask=np.zeros(size))
time = ma.masked_array(np.arange(size),mask=np.zeros(size))
utiliz[0]=ma.masked
time[0]=ma.masked
curr_index = 0

fig = plt.figure()
ax=fig.add_subplot(1,1,1)
fig.canvas.draw()
graph = ax.plot(time,utiliz)[0]
ax.set_xlim(min(time)-1,max(time)+1)
ax.set_ylim(min(utiliz)-1,max(utiliz)+1)
plt.show()