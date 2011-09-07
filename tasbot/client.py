# -*- coding: utf-8 -*-
import socket
import string
import re
import time
import utilities
import sys
import traceback

from utilities import *
from customlog import Log


class User:
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


class Tasclient(object):
	"""the main interaction with server class"""
	def mainloop(self):
		while not self.main.dying:
			if self.error == 1:
				raise SystemExit(0)
			try:
				result = self.receive()
				if result == 1:
					self.events.ondisconnected()
					self.users = dict()
					Log.error("SERVER: Timed out, reconnecting in 40 secs")
					self.main.connected = False
					if not self.flags.norecwait:
						time.sleep(40.0)
						self.flags.norecwait = False
					try:
						self.socket.close()
					except Exception:
						pass
					self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
					self.socket.settimeout(40)
					self.socket.connect((self.lastserver, int(self.lastport)))
					self.receive()
					self.main.connected = True
					self.events.onconnectedplugin()
			except SystemExit:
				raise SystemExit(0)
			except Exception, e:
				Log.error("Command Error")
				Log.exception(e)

	def __init__(self, app):
		self.events = ServerEvents()
		self.main = app
		self.channels = []
		self.flags = Flags()
		self.error = 0
		self.lp = 0.0
		self.lpo = 0.0
		self.users = dict()
		self.socket = None

	def connect(self, server, port):
		port = int(port)
		self.lastserver = server
		self.lastport = port
		while 1:
			try:
				self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				self.socket.settimeout(40)
				self.socket.connect((server, port))
				self.events.onconnectedplugin()
				if self.main.reg:
					Log.notice("Registering nick")
					self.main.Register(self.main.config.get('tasbot', "nick"),
										self.main.config.get('tasbot', "password"))
				res = self.receive()
				if not res == 1:
					return
			except SystemExit:
				raise SystemExit(0)
			except Exception, e:
				self.main.connected = False
				Log.error("Cannot connect, retrying in 40 secs...")
				Log.exception(e)
				if self.error == 1:
					raise SystemExit(0)
				time.sleep(40.0)

	def disconnect(self, hard=False):
		try:
			self.socket.send("EXIT\n")
		except Exception, e:
			Log.exception(e)
		self.socket.close()
		self.socket = None

	def login(self, username, password, client, cpu, lanip="*"):
		Log.notice("Trying to login with username %s " % (username))
		lanip = self.socket.getsockname()[0]
		#print "LOGIN %s %s %i * %s\n" % (username,password,cpu,client)
		try:
			self.socket.send("LOGIN %s %s %i %s %s\t0\t%s\n" %
							(username, password, cpu, lanip, client, "a sp"))
		except Exception, e:
			Log.error("Cannot send login command")
			Log.exception(e)
		self.uname = username
		self.password = password
		self.channels = []
		self.receive()

	def register(self, username, password):
		try:
			Log.notice("Trying to register account")
			self.socket.send("REGISTER %s %s\n" % (username, password))
		except Exception, e:
			Log.error("Cannot send register command")
			Log.exception(e)

	def leave(self, channel):
		if channel in self.channels:
			try:
				self.socket.send("LEAVE %s\n" % channel)
				self.channels.remove(channel)
			except Exception, e:
				Log.bad("Failed to send LEAVE command")
				Log.exception(e)
		else:
			Log.bad("leave(%s) : Not in channel" % channel)

	def join(self, channel):
		if not channel in self.channels:
			self.socket.send("JOIN %s\n" % channel)

	def say(self, channel, phrase):
		self.join(channel)
		self.socket.send("SAY %s %s\n" % (channel, phrase))

	def sayex(self, channel, phrase):
		self.join(channel)
		self.socket.send("SAYEX %s %s\n" % (channel, phrase))

	def saypm(self, user, phrase):
		self.socket.send("SAYPRIVATE %s %s\n" % (user, phrase))

	def ping(self):
		if self.error == 1:
			return
		try:
			self.socket.send("PING\n")
			self.lp = time.time()
		except Exception:
			Log.error("Cannot send ping command")

	def parsecommand(self, command, args):
		if command.strip() != "":
			self.events.oncommandfromserver(command, args, self.socket)
			if command == "JOIN" and len(args) >= 1:
				if not args[0] in self.channels:
					self.channels.append(args[0])
					Log.good("Joined #%s" % args[0])
			if command == "FORCELEAVECHANNEL" and len(args) >= 2:
				if args[0] in self.channels:
					self.channels.remove(args[0])
					Log.bad("I've been kicked from #%s by <%s>" % (args[0], args[1]))
				else:
					Log.error("I've been kicked from a channel that i haven't joined")
			if command == "TASSERVER":
				Log.good("Connected to server")

				if self.flags.register:
					self.register(self.uname, self.password)
					self.receive()
				else:
					self.events.onconnected()
			if command == "AGREEMENTEND":
				Log.notice("accepting agreement")
				self.socket.send("CONFIRMAGREEMENT\n")
				self.login(self.uname, self.password, "BOT", 2000)
				self.events.onloggedin(self.socket)
			if command == "MOTD":
				self.events.onmotd(" ".join(args))
			if command == "ACCEPTED":
				self.events.onloggedin(self.socket)
			if command == "DENIED" and ' '.join(args).lower().count("already") == 0:
				Log.error("Login failed ( %s ), trying to register..." % ' '.join(args))
				Log.notice("Closing Connection")
				self.socket.close()
				self.flags.register = True
				self.connect(self.lastserver, self.lastport)
			if command == "REGISTRATIONACCEPTED":
				Log.good("Registered")
				Log.notice("Closing Connection")
				self.socket.close()
				self.flags.register = False
				self.connect(self.lastserver, self.lastport)
			if command == "PONG":
				self.lpo = time.time()
				self.events.onpong()
			if command == "JOINEDBATTLE" and len(args) >= 2:
				try:
					self.users[args[1]].battleid = int(args[0])
				except Exception:
					Log.error("Invalid JOINEDBATTLE Command from server: %s %s" %
								(command, str(args)))
					Log.error(traceback.format_exc())
			if command == "BATTLEOPENED" and len(args) >= 4:
				try:
					self.users[args[3]].battleid = int(args[0])
				except Exception:
					Log.error("Invalid BATTLEOPENED Command from server: %s %s" %
								(command, str(args)))
					Log.error(traceback.format_exc())
			if command == "LEFTBATTLE" and len(args) >= 2:
				try:
					self.users[args[1]].battleid = -1
				except Exception:
					Log.error("Invalid LEFTBATTLE Command from server: %s %s" %
								(command, str(args)))
					Log.error(traceback.format_exc())
			if command == "SAIDPRIVATE" and len(args) >= 2:
				self.events.onsaidprivate(args[0], ' '.join(args[1:]))
			if command == "ADDUSER":
				try:
					if len(args) == 4:
						#Account id
						self.users[args[0]] = User(args[0], int(args[3]), args[1], int(args[2]))
					elif len(args) == 3:
						self.users[args[0]] = User(args[0], int(-1), args[1], int(args[2]))
					else:
						Log.error("Invalid ADDUSER Command from server: %s %s" %
								(command, str(args)))
				except Exception, e:
					Log.error("Invalid ADDUSER Command from server: %s %s" %
								(command, str(args)))
					Log.exception(e)
			if command == "REMOVEUSER":
				if len(args) == 1:
					if args[0] in self.users:
						del self.users[args[0]]
					else:
						Log.error("Invalid REMOVEUSER Command: no such user %s" % args[0])
				else:
						Log.error("Invalid REMOVEUSER Command: not enough arguments")
			if command == "CLIENTSTATUS":
				if len(args) == 2:
					if args[0] in self.users:
						try:
							self.users[args[0]].clientstatus(int(args[1]))
						except Exception:
							Log.error("Malformed CLIENTSTATUS")
							Log.error(traceback.format_exc())
					else:
						Log.error("Invalid CLIENTSTATUS: No such user <%s>" % args[0])

	def receive(self):
		"""return commandname & args"""
		if not self.socket:
			return 1
		buf = ""
		try:
			while not buf.strip("\r ").endswith("\n"):
				#print "Receiving incomplete command..."
				nbuf = self.socket.recv(512)
				if nbuf == "":
					return 1
				buf += nbuf
		except Exception, e:
			#Connection broken
			Log.exception(e)
			return 1
		commands = buf.strip("\r ").split("\n")
		for cmd in commands:
			c = cmd.split(" ")[0].upper()
			args = cmd.split(" ")[1:]
			self.parsecommand(c, args)
		return 0
