#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, string, base64, md5, time, ParseConfig, thread, Plugin, traceback, Client, binascii
from customlog import *
from daemon import Daemon

class MainApp(Daemon):
	def PingLoop(self):
		while self.er == 0:
			self.tasclient.ping()
			time.sleep(10)
		raise SystemExit(0)	
	def onlogin(self,socket):
		if self.firstconnect == 1:
			thread.start_new_thread(self.tasclient.mainloop,())
			thread.start_new_thread(self.PingLoop,())
			self.firstconnect = 0
		
		#self.tasclient.events.ondisconnected = self.ph.ondisconnected 
		
		self.tasclient.events.onmotd = self.ph.onmotd  
		self.tasclient.events.onsaid = self.ph.onsaid 
		self.tasclient.events.onsaidex = self.ph.onsaidex 
		self.tasclient.events.onsaidprivate = self.ph.onsaidprivate 
		self.tasclient.events.onpong = self.ph.onpong 
		self.tasclient.events.oncommandfromserver = self.ph.oncommandfromserver
		self.tasclient.events.ondisconnected = self.ph.ondisconnected
		
		self.ph.onloggedin(socket)
		self.ph.oncommandfromserver("ACCEPTED",[],self.tasclient.sock)
		self.connected = True
		good("Logged in")
		
	def SaveConfig(self):
		ParseConfig.writeconfigfile(self.configfile,self.config)
		
	def isAdmin(self,username):
		if username in self.admins:
				return True
		elif username in self.tasclient.users:
				if "#"+str(self.tasclient.users[username].id) in self.admins:
						return True
				else:
						return False
		else:
				return False
	                
	def Dologin(self):
		if self.tasclient.fl.register:
			notice("Not logging in because a registration is in progress")
			return
		if self.verbose:
			notice("Logging in...")
		m = md5.new()
		m.update(self.config["password"])
		phash = base64.b64encode(binascii.a2b_hex(m.hexdigest()))
		self.tasclient.login(self.config["nick"],phash,"Newbot",2400,self.config["lanip"] if "lanip" in self.config else "*")
		
	def Register(self,username,password):
		m = md5.new()
		m.update(self.config["password"])
		self.tasclient.register(self.config["nick"],base64.b64encode(binascii.a2b_hex(m.hexdigest())))
		
	def destroy(self):
		self.tasclient.er = 1
		self.er = 1
		raise SystemExit(0)
	
	def ReloadConfig(self):	
		self.config = ParseConfig.readconfigfile(self.configfile)
		self.admins = ParseConfig.parselist(self.config["admins"],",")
		
	def __init__(self,configfile,pidfile,register,verbose):
		super(MainApp, self).__init__(pidfile)
		self.firstconnect = 1
		self.er = 0
		self.connected = False
		self.cwd = os.getcwd()
		self.ph = Plugin.plghandler(self)
		self.configfile = configfile
		self.config = ParseConfig.readconfigfile(configfile)
		self.admins = ParseConfig.parselist(self.config["admins"],",")
		self.verbose = verbose
		self.tasclient = Client.tasclient(self)
		
		for p in ParseConfig.parselist(self.config["plugins"],","):
			self.ph.addplugin(p,self.tasclient)

		self.tasclient.events.onconnectedplugin = self.ph.onconnected
		self.tasclient.events.onconnected = self.Dologin
		self.tasclient.events.onloggedin = self.onlogin
		self.reg = register
		
	def run(self):
		while 1:
			try:
				notice("Connecting to %s:%i" % (self.config["serveraddr"],int(self.config["serverport"])))
				self.tasclient.connect(self.config["serveraddr"],int(self.config["serverport"]))
				while 1:
					time.sleep(10)
			except SystemExit:
				return
			except KeyboardInterrupt:
				error("SIGINT, Exiting")
				inst.ph.onexit()
				return
			except Exception, e:
				error("parsing command line")
				Log.Except( e )
			time.sleep(10)

if __name__=="__main__":			
	#todo get this from config
	configfile = "Main.conf"
	config = ParseConfig.readconfigfile(configfile)
	Log.Init( config['logfile'], 'info', True )
	
	i = 0
	r = False
	for arg in sys.argv:
		if arg.strip() == "-c":
			cf = sys.argv[i+1]
		if arg.strip() == "-r":
			r = True
			notice("Registering account")
		i += 1
	inst = MainApp(configfile,"/tmp/arm.pid",r,True)
	inst.start()
	#inst.run()#exec in fg

