import string

from tasbot.plugin import IPlugin
from tasbot.config import *


class Main(IPlugin):
	"""Automatically join all channels named in config.
	[join_channels]
	channels=springlobby,main,newbies"""
	def __init__(self, name, tasclient):
		super(Main,self).__init__(name, tasclient)
		self.joined_channels = 0
		self.admins = []
		self.channels = []

	def onloggedin(self, socket):
		for chan in self.channels:
			socket.send("JOIN %s\n" % (chan))
		self.joined_channels = 1

	def oncommandfromserver(self, command, args, socket):
		if (command == "SAID" and len(args) > 3 and
			args[1] in self.admins):
			for chan in args[3:]:
				if args[2] == "!faqchan":
					socket.send("JOIN %s\n" % (chan))
					if not chan in self.channels:
						self.channels.append(chan)
						self.saveChannels()
				if args[2] == "!faq!chan":
					socket.send("LEAVE %s\n" % (chan))
					if chan in self.channels:
						self.channels.remove(chan)
						self.saveChannels()

	def saveChannels(self):
		savestring = ""
		for channel in self.channels:
			savestring += channel + ","
		self.app.config.set('join_channels', "channels", savestring)
		self.app.config.write()

	def onload(self, tasc):
		self.app = tasc.main
		self.admins = self.app.config.get_optionlist('tasbot', "admins")
		self.channels = self.app.config.get_optionlist('join_channels', "channels")
