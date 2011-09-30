"""An example plugin."""

import string

try:
	from tasbot.plugin import IPlugin
except Exception:
	from Plugin import IPlugin


class Main(IPlugin):
	"""A dummy plugin that does nothing but log function calls"""
	def __init__(self, name, tasclient):
		IPlugin.__init__(name, tasclient)

	def onconnected(self):
		self.logger.debug("onconnected()")

	def ondisconnected(self):
		self.logger.debug("ondisconnected()")

	def onmotd(self, content):
		self.logger.debug("onmotd(%s)" % (str(content)))

	def onsaid(self, channel, user, message):
		self.logger.debug("onsaid(%s,%s,%s)" % (str(channel), str(user), str(message)))

	def onsaidex(self, channel, user, message):
		self.logger.debug("onsaidex(%s,%s,%s)" % (str(channel), str(user), str(message)))

	def onsaidprivate(self, user, message):
		self.logger.debug("onsaidprivate(%s,%s)" % (str(user), str(message)))

	def onloggedin(self, socket):
		self.logger.debug("onloggedin(%s)" % (str(socket)))
		socket.send("JOIN main\n")

	def onpong(self):
		self.logger.debug("onpong()")

	def oncommandfromserver(self, command, args, socket):
		self.logger.debug("oncommandfromserver(%s,%s,%s)" %
			(str(command), str(args), str(socket)))

	def onexit(self):
		self.logger.debug("onexit()")
