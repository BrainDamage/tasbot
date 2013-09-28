from utilities import (getaway, getingame, getmod,
					getbot, getrank )
from customlog import Log

class User(object):
	"""Model of an agent in the lobby protocol"""
	def __init__(self, username, id, country, cpu):
		self.username = username
		self.id = id
		self.country = country
		self.cpu = cpu
		self.afk = False
		self.ingame = False
		self.mod = False
		self.rank = 0
		self.bot = False
		self.battleid = -1

	def clientstatus(self, status):
		self.afk = bool(getaway(int(status)))
		self.ingame = bool(getingame(int(status)))
		self.mod = bool(getmod(int(status)))
		self.bot = bool(getbot(int(status)))
		self.rank = getrank(status) - 1

class Channel(object):
	def __init__(self,name):
		self.name = name
		self.topic = ""
		self.users = []
		
	def add_user(self,user):
		self.users.append(user)
		
	def del_user(self,user):
		self.users.remove(user)

class ChannelList(object):
	def __init__(self):
		self._channels = {}
	
	def __contains__(self, name):
		return name in self._channels.keys()
	
	def add(self,name):
		self._channels[name] = Channel(name)
		
	def remove(self,name):
		del self._channels[name]
		
	def __getitem__(self, key):
		return self._channels[key]

	def clear_user(self,user):
		for channel in self._channels.itervalues():
			try:
				channel.del_user(user)
			except ValueError:
				pass
class ServerEvents:
	def onconnected(self):
		Log.good("Connected to TASServer")

	def onconnectedplugin(self):
		Log.good("Connected to TASServer")

	def ondisconnected(self):
		Log.bad("Disconnected")

	def onmotd(self, content):
		Log.info("[MOTD] %s" % content)

	def onsaid(self, channel, user, message):
		Log.info("[CHANNEL] %s: <%s> %s" % (channel, user, message))

	def onsaidex(self, channel, user, message):
		Log.info("[CHANNELEX] %s: <%s> %s" % (channel, user, message))

	def onsaidprivate(self, user, message):
		Log.info("[PRIVATE] <%s> %s" % (user, message))

	def onloggedin(self, socket):
		Log.info("[LOGIN] successful")

	def onpong(self):
		#print blue+"PONG"+normal
		pass

	def oncommandfromserver(self, command, args, socket):
		#print yellow+"From Server: "+str(command)+" Args: "+str(args)+normal
		pass

	def onexit(self):
		pass


class Flags:
	norecwait = False
	register = False

