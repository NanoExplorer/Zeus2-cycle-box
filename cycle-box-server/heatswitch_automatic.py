#-------------------------------------------------------------------
# see z40_4Ksw.py 
#
#  like zheatsw.py but for MOTOR UTILITY CONSTANTS
#
# May 2012:  changed L0 check to if numb is None instead of not numb
#            and made smaller open2closedSteps
#
# ------------------------ FROM Lab logs (TN) -------------------------------
# ZEUS-2 ADR Heat Switch MOTOR uses:
#               Accel =   10 (not power-on default = 16)
#               Base  =  400 (not power-on default = 500)
#               Max   =  500 (not power-on default = 1500)
#    open2closedSteps = 1200 
#
#CR 2018: this must be outdated because we've been using 10,500,1000 for 1 year now at least
################################################################################
# Exit codes as follows:
#  1: some exception was not handled (default python behavior)
#  2: could not set base speed/max speed/acceleration
#  3: 'error getting limit switch'
#  4: you passed us an invalid command.
#  5: The limit switch refuses to go away.
#  6: could not connect


import time
import os
import etherser
import threading
import sys

#------------constants--------------------------------#
#ZEUSII values
class zmotsclass:

  ##### MOTOR UTILITY CONSTANTS #####
  #RS485addr    =   5      # chopper
  RS485addr    =   3      # ADR heat switch
  
  base_speed   = 500      #  500 = default
  max_speed    = 1000      # 1500 = default
  acceleration =  10      #   16 = default

  open2closedSteps = 2500  # 17May2014 includes clutch slip?
  #
  closedpushSteps  =  1000 # for "more" button [if not 1000 CHANGE push tooltip]
  # Connect to this address:
  # SERSERV_IP = 'localhost' # simulating Ethernet Serial-server 

  #SERSERV_IP = '10.0.6.165' # Vlinx serial server at APEX
  SERSERV_IP = '10.236.6.82' # Vlinx serial server at Cornell
  SERSERV_PORT = 4000  # Vlinx and simulator port
  
  status = ""
  ###################################

  ser = etherser.etherserial()

  ##### GUI access from threads, necessary on linux (not Windows)
  #####
  UImain = None
  RunEvent = None

  def UiPostProcess(self, evt):
     evt.fun(evt.val)

  '''def initRunEvents(self, guiframe):  # exec after gui instantiated
     self.UImain = guiframe
     self.RunEvent, EVT_RUN_EVENTS = wx.lib.newevent.NewEvent()
     self.UImain.Bind(EVT_RUN_EVENTS, self.UiPostProcess)'''

  '''def UiPost(self, widgetfun, funarg):
     evt = self.RunEvent(fun=widgetfun, val=funarg)
     wx.PostEvent(self.UImain, evt)'''
  #####

  gui = None   # set in initthis() (could be named "guical_frm")

  senddly = 0.2  # delay in seconds between motor commands
  Axis = RS485addr   # motor number on RS485 chain
  ABORT = False  # if serial timout, execute stop and abort further moves
  #
  CurrentIndex = 0  # also whatever starting index for calibrations
  Hardminus = None
  OpenFound = None
  Monitorflag = 0        # boolean monitoring motor move 
  PostMonitorMsg = None  # status message after threaded move-monitoring
  PostMonitorCmd = None  # command to run after threaded move-monitoring
  # 
  def TimeoutProc(self):  # well-known name (see etherser)
      self.SendCmd('.') 
      self.SendCmd('.') 
      self.SendCmd('.') 
      self.SendCmd('.') 
      self.SendCmd('.') 
      self.ABORT = True
      #self.gui.timeoutabort.Show()  # SetBackgroundColour('yellow')
      # self.gui.timeoutabort.SetForegroundColour('red')

  def clearTimeoutAbort(self):
      self.ABORT = False
      self.gui.timeoutabort.Hide() # SetBackgroundColour((120,140,255)) # midbg in pui
      # self.gui.timeoutabort.SetForegroundColour((120,140,255)) # midbg in pui



  def log_index(self, index):
    timestamp = time.strftime("%a, %d %b %Y %H:%M:%S")
    self.index_log.write(timestamp)
    self.index_log.write('\t')
    self.index_log.write(index)
    self.index_log.write('\n')

  def init_motor(self):
    #
    if not self.ser.connected:
        self.set_status('need connection')
        print "no connection"
        return

    axiss = str(self.Axis)
    #
    instring = '@' + axiss + 'B' + str(self.base_speed) + '\r'
    self.ser.write(instring)
    time.sleep(self.senddly)
    err = self.check_error(instring)
    if 0 != err:
        print 'ERROR SETTING BASE SPEED to ',self.base_speed
        self.set_status('ERROR: BASE SPEED')
        return
    #
    instring = '@' + axiss + 'M' + str(self.max_speed) + '\r'
    self.ser.write(instring)
    time.sleep(self.senddly)
    err = self.check_error(instring)
    if 0 != err:
        print 'ERROR SETTING MAX SPEED to ',self.max_speed
        self.set_status('ERROR: MAX SPEED')
        return
    #
    instring = '@' + axiss + 'A' + str(self.acceleration) + '\r'
    self.ser.write(instring)
    time.sleep(self.senddly)
    err= self.check_error(instring)
    if 0 != err:
        print 'ERROR SETTING ACCELERATION to ',self.acceleration
        self.set_status('ERROR: ACCELERATION')
        return

    self.getCurrentIndex()
    self.set_status('OK max=%d, base=%d, accel=%d'%(self.max_speed,self.base_speed,
                                               self.acceleration))
                                               #self.gui.initpcl501.SetBackgroundColour('gray')

    
  def connect(self):
    self.set_status('')
    if self.ser.connected:
       print 'serial server already connected'
       self.set_status('already connected (press disconnect to clear)')
       return

    self.ser.open(self.SERSERV_IP, self.SERSERV_PORT)
    print "connecting"
    if self.ser.connected:
       self.set_status('connected')
       #self.gui.connect.SetBackgroundColour('gray')
       #self.gui.initpcl501.SetBackgroundColour('red')
       self.init_motor()
    else:
       self.set_status('not connected')

  def disconnect(self):
    self.set_status('')
    if not self.ser.connected:
       self.set_status('already dis-connected')
       return
    self.ser.close()
    #self.gui.connect.SetBackgroundColour('red')
    self.set_status('dis-connected')

  def userinput(self, cmd):
    cmd = cmd.upper()
    if cmd[0] == '?':
        self.userhelp()
        return
    axiss = str(self.Axis)
    outstr = '@' + axiss + cmd + '\r'
    self.ser.write(outstr)
    self.check_return(cmd, outstr)

  def userhelp(self):
    print ' -------------------------------------'
    print ' user input to PCL501 motor controller'
    print 'An  acceleration power-on default =  16'
    print 'Bn  base speed   power-on default = 500'
    print 'Jn  jog speed                      1500'
    print 'Mn  max speed                      1500'
    print 'I   read inputs'
    print 'L0  get limit status'
    print 'LS  get soft limit input bit'
    print 'Vx  get status for x = A B J M N O P Z'
    print '!   get error code'
    print 'Zn  re-define current position        0'
    print '            -- move --'
    print '+   set CW direction (for G, small angle, short wave)'
    print '-   set CCW direction (for G, large angle, long wave)'
    print 'Nn  specify number of steps   (for G)'
    print 'Pm  set N for	absolute position m from current'
    print 'G   go n +/-   i.e. actually move'
    print ' -------------------------------------'
    print ' sim special:    quit     hw        --'
    print ' -------------------------------------'

  def verbose(self, boo):
    self.ser.verbose = boo

  def set_status(self, msg):
    self.status = msg

  '''def showCurrentIndex(self):
    self.gui.currentindex_val.SetLabel(str(self.CurrentIndex))'''
  #WHY IS THIS CAPITALIZED AND NONE OF THE OTHER METHODS ARE EXCEPT SendCmd????
  def GetNumber(self, cmd):
      ret = None
      if not self.ser.connected:
          return ret

      axiss = str(self.Axis)
      outstr = '@' + axiss + cmd + '\r'
      self.ser.write(outstr)
      time.sleep(self.senddly)
      instr = self.ser.readline().strip()
      try:
          ret = int(instr)
      except:
          rep = self.ser.phonetic(instr)
          print 'ERROR: cmd ' + cmd + ' expected number, got: ' + rep
          ret = None
      return ret

  def SendCmd(self, cmd):
      axiss = str(self.Axis)
      outstr = '@' + axiss + cmd + '\r'
      self.ser.write(outstr)
      time.sleep(self.senddly)

  def getCurrentIndex(self):
      self.CurrentIndex = self.GetNumber('VZ');
      #self.showCurrentIndex()
      self.log_index(str(self.CurrentIndex))
      self.getHardminus()
    
  def SendGoCmd(self):     # handle motor-enable output
    if self.ABORT:
        self.set_status('timeout -> moves not honored')
        print 'timeout -> shutdown state, moves not honored'
        return
    self.SendCmd('O0') # outputs off = power-on default = motor enabled
    self.SendCmd('G')  # Go

  def SendSlewCmd(self):   # handle motor-enable output
    if self.ABORT:
        self.set_status('timeout -> moves not honored')
        print 'timeout -> shutdown state, moves not honored'
        return
    self.SendCmd('O0') # outputs off = power-on default = motor enabled
    self.SendCmd('S')  # Slew

  def EndMove(self):
    nEnable = 1 & self.GetNumber('VO')
    if 0 != nEnable:
        msg = 'ERROR: End Move sees motor DISABLED! Check position!'
        print '****************************************************'
        print msg
        print msg
        print '****************************************************'
        self.set_status(msg)
    self.SendCmd('O1') # output1 on = motor disabled, no holding current

  # checks if the command sent has caused an error in the controller
  def check_error(self, instring):
    cmd = self.ser.phonetic(instring)
    self.SendCmd('!')
    errcode = self.ser.readline().strip()
    if errcode == '0':
        print 'Command ', cmd, ': OK'
        retcode = 0
    elif errcode == '':
        print 'No response from unit ', axiss
        retcode = 2
    else:
        print 'Command ', cmd, ': Error, code ', errcode
        retcode = 1
    time.sleep(self.senddly)
    return retcode    # retcode = 0: good command; ver_com = 1: bad command

  def check_return(self, usercmd, outputstr):
    outnice = self.ser.phonetic(outputstr)
    if 'V' in usercmd:
        rstr = self.ser.readline().strip()
        print 'Value requested by ', outnice, ': ', rstr
    elif usercmd == '$' or usercmd == '!' or \
         usercmd == 'L0' or usercmd == 'I':  # usercmd returns something
        rstr = self.ser.readline()
        rstr = self.ser.phonetic(rstr)
        print 'Return value from command ', outnice, ': ', rstr
    
  # [MOTOR]
  # go to specified index
  def goto_index(self, indx):
    self.set_status('')
    self.SendCmd('P' + str(indx))   # controller calculates absolute Nsteps
                                    #  and sets +/- from current position
    self.SendGoCmd()              # Go
    self.threadMonitorMove()

  def MonitorMove(self):
    self.set_status('moving...')
    time.sleep(0.2)
    while True:
        stat = self.GetNumber('VF')
        if self.ser.verbose:
            print 'Monitor-Move VF gets stat = ', stat
        if stat < 1:  # 0 = not busy,
            break     # -1 = not connected or other mis-communication
        time.sleep(0.5)
    self.getCurrentIndex()  # gets hard-limits status
    self.set_status('')
    self.EndMove()

  def MonMove4thread(self):
    self.Monitorflag = 1
    #self.UiPost(self.status,'moving.....')
    time.sleep(0.2)
    while self.Monitorflag:
        stat = self.GetNumber('VF')
        if self.ser.verbose:
            print 'Monitor-Move VF gets stat = ', stat
        if stat < 1:  # 0 = not busy,
            break     # -1 = not connected or other mis-communication
        time.sleep(0.4)
    if self.Monitorflag:
        self.getCurrentIndex()  # gets hard-limits status
        #if self.PostMonitorMsg:
           # self.UiPost(self.status,self.PostMonitorMsg)
        #else:
            #self.UiPost(self.status,'')
        self.Monitorflag = 0
        #if self.PostMonitorCmd:
            #self.PostMonitorCmd()
    self.PostMonitorMsg = None
    self.PostMonitorCMd = None
    self.EndMove()

  def threadMonitorMove(self, postmsg=None, postcmd=None):
    self.PostMonitorMsg = postmsg
    self.PostMonitorCmd = postcmd
    threading.Thread(target=self.MonMove4thread).start()

  def stop_motion(self):
    sreq = 0
    if self.Monitorflag:
      self.Monitorflag = 0
      sreq = 1
      time.sleep(0.6)
    self.SendCmd('.')
    self.getCurrentIndex()
    if sreq:
      self.set_status('stop requested')
    else: 
      self.set_status('')

  def getHardminus(self):
    numb = self.GetNumber('L0')
    if numb is None:
        time.sleep(senddly)
        numb = self.GetNumber('L0')
        if numb is None:
            self.Hardminus = None
            self.set_status('ERROR getting limit switch status')
            return
    self.Hardminus = not (1 & numb)

    #self.gui.limitsstatus.SetLabel(lab)

  '''def getguinsteps(self):  # return nsteps, failure
     nstr = self.gui.nsteps.Get().strip()
     if not nstr or 0 == str(nstr):
        return 0,1   # failure
     ns = int(nstr)
     return ns, 0'''

  def go_plusnsteps(self):
     self.set_status('')
     ############ Needs another function to get steps from
     #ns, failure = self.getguinsteps()
     ############ Needs another function to get steps from
     '''if failure:
         self.set_status('need nsteps entered under go CW / CCW buttons')
         return'''
     ns = 100
     self.SendCmd('+')            # + direction
     self.SendCmd('N' + str(ns))  # Nsteps
     self.SendGoCmd()             # Go
     self.threadMonitorMove()
     
  def go_minusnsteps(self):
     self.set_status('')
     ############ Needs another function to get steps from
     ns, failure = self.getguinsteps()
     ############ Needs another function to get steps from
     if failure:
         self.set_status('need nsteps entered for go CW / go CCW buttons')
         return
     self.SendCmd('-')            # - direction
     self.SendCmd('N' + str(ns))  # Nsteps
     self.SendGoCmd()             # Go
     self.threadMonitorMove()
 
  def goto_limitswitch(self):   # grep, openheatswitch
      backdelta = self.open2closedSteps
      self.set_status('')
      self.getHardminus()
      if self.Hardminus is None:
         return
      if 1 == self.Hardminus:      # ADR heat switch open, may be 
          self.SendCmd('+')        #  far into limit-switch range
          self.SendCmd('N500')     #  if left there when closed up
          self.SendGoCmd()         # so move up (cannot move down)
          self.MonitorMove() #this also updates the hardminus variable.
          if 1 == self.Hardminus:      # maybe still in limit
             #THREE SPACES OF INDENTATION:?!?!@?R$($#%U@)*#$%@FF
             self.set_status('retry (limit switch still asserted after +500 steps)')
             sys.exit(5)
          backdelta = 600
      self.SendCmd('-')     # ready to go (back) down (CCW) toward switch
      self.SendCmd('N'+str(backdelta))
      self.SendGoCmd()
      ############# Maybe need to deal with postcmd
      self.threadMonitorMove(postcmd=self.post_goto_limitswitch)

  def post_goto_limitswitch(self):
      if 1 != self.Hardminus:    
          self.set_status('?? limit switch is NOT asserted (SHOULD BE)')
      else:
          self.SendCmd('Z0')  # set current index = 0
          self.getCurrentIndex()
          self.set_status('OK motor index reset at limit switch')
          self.OpenFound = 1

  def tellHSbuttons(self):
    print ' The limit switch (for a HEAT SWITCH)'
    print '  is far from the heat switch being closed.'
    print ' \"heat switch open\" moves to the limit switch activation point'
    print ' \"close heat switch\" is to run starting at the limit switch'
    print ' \"more\" is to run with HEAT SWITCH already closed'

  def closeHeatswitch(self):    # grep, closeheatswitch
      if 1 != self.Hardminus:
        print("well 1!=self.Hardminus I guess")
      # if 1 != self.OpenFound:
      #   print("well 1!=self.OpenFound I guess")
      self.SendCmd('+')     # ready to go up (CW) to close heat switch 
      self.SendCmd('N'+str(self.open2closedSteps)) #
      self.SendGoCmd()
      self.threadMonitorMove(postcmd=self.post_close_heatswitch)


  def post_close_heatswitch(self):
      print(self.status,'heat switch closed (did %d CW steps)'%(
                                                 self.open2closedSteps))
  
  def pushHeatswitch(self):    # grep, pushheatswitch
      if not self.ser.connected:
        self.set_status('need communication connection')
        return
      if 1 == self.Hardminus:    
        self.set_status('exec \"close heat switch\" before this')
        ###### Not sure about this -> self.tellHSbuttons()
        return
      self.SendCmd('+')     # go up (CW) to close heat switch 
      self.SendCmd('N'+str(self.closedpushSteps)) #
      self.SendGoCmd()
      self.MonitorMove()
      self.set_status('heat switch sent another %d CW (+) steps'%(self.closedpushSteps))

  def get_gotoindex(self):
    str = self.gui.gotoindex_text.Get().strip() # user input
    if len(str) < 1:
      self.set_status('need go-to index')
      self.gotoindex = 0
      return 1
    else: 
      self.gotoindex = int(str)
      return 0

  def clear(self):
      self.set_status('')
      ret = self.ser.clear()
      if ret:
         print 'input cleared'
      else:
         print 'input clear'

  def flush(self):
      self.set_status('')
      while True:
        ret = self.ser.flush(4096)
        n = len(ret)
        if n > 0:
            strp = self.ser.phonetic(ret)
            print '%d chars flushed: %s'%(n,strp)
            if n < 4096:
              break
        else:
            print '<empty>'
            break

  # -------------------------------------------------------------------
  # -------------------------------------------------------------------
  date = time.strftime('%d%b%Y')

  logfname = ('Index_Logs/log_' + date + '.txt')
  index_log = open(logfname, 'a')
  # jog_speed = 1500   #1500 = jog speed power-on default
  # -------------------------------------------------------------------
  # -------------------------------------------------------------------
  def __init__(self):
    pass
    


############# 
# App args: () : stdio ==> window
#           (0) or (redirect=0) : stdio ==> console
#           (1,fn) or (redirect=1, filename = 'fn') : stdio ==> file
#app=wx.App(redirect=1)
#

#Basic Automation of steps. To be fixed in the future

def runTests():
  instance = zmotsclass()
  instance.connect()
  instance.ser.doTimeoutProc = False
  instance.ser.parent = instance

  numb = instance.GetNumber('L0')
  print "numb is " + str(numb)
  if numb is None:
    instance.Hardminus = None
    print "error getting limit switch"
  instance.Hardminus = not (1 & numb)
  if instance.Hardminus:
    print "at hard limit"
  print instance.CurrentIndex

  time.sleep(2)
  instance.init_motor()
  time.sleep(2)
  
instance = zmotsclass()
instance.connect()
if not instance.ser.connected:
    sys.exit(6)
if "ERROR" in instance.status:
    sys.exit(2)
instance.ser.doTimeoutProc = False
instance.ser.parent = instance

time.sleep(2)

instance.getHardminus() 
if instance.Hardminus is None:
    sys.exit(3)
success=False
#Check if we need to open or close heatswitch
if (sys.argv[1] == "open"):
    if instance.Hardminus:
        print "at hard limit - i.e. hsw already open"
    else:
        instance.goto_limitswitch()
        time.sleep(10)
        print instance.CurrentIndex
    
        if not instance.Hardminus: #Spin the motors some more I guess
            instance.goto_limitswitch()
            time.sleep(10)
      
    print "INDEX NOW EQUALS: "+str(instance.CurrentIndex)
    success = instance.Hardminus
    #instance.go_plusnsteps()


elif (sys.argv[1] == "close"):
    if instance.Hardminus: #Hsw is open. Just need to close it.
        print("gaa")
        instance.closeHeatswitch()
        time.sleep(10)
    else:
        instance.goto_limitswitch()
        time.sleep(10)
        instance.closeHeatswitch()
        time.sleep(10)

    print "INDEX NOW EQUALS: "+str(instance.CurrentIndex)
else:
    print("Err: {} is not a valid command. use 'open' or 'close'".format(sys.argv[1]))
    sys.exit(4)
instance.flush()
instance.disconnect()
print sys.argv[1] + "d heatswitch."
  #
  #instance.gui.timeoutabort.Hide()

