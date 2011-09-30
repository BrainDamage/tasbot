"""plugin loader/handler and base classes for common plugin functionality"""

import sys
import traceback
import inspect
import ctypes
import threading
import functools
from collections import defaultdict

from customlog import Log
import plugins
from decorators import check_and_mark_decorated
from commands import server as ALL_COMMANDS

CHAT_COMMANDS = ('SAID', 'SAIDPRIVATE', 'SAIDEX', 'SAIDPRIVATEEX')


def _async_raise(tid, exctype):
	"""Raises an exception in the threads with id tid (note: never seen working)"""
	if not inspect.isclass(exctype):
		raise TypeError("Only types can be raised (not instances)")
	res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid,
				ctypes.py_object(exctype))
	if res == 0:
		Log.error("Cannot kill thread %i" % tid)
	if res != 1:
		#if it returns a number greater than one, you're in trouble,
		#and you should call it again with exc=NULL to revert the effect
		ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)


class PluginThread(threading.Thread):
	"""tiny wrapper to execute function with args in a thread"""
	def __init__(self, func, *args):
		super(PluginThread, self).__init__()
		self.func = func
		self.args = args

	def run(self):
		self.func(*self.args)


class ThreadContainer(object):
	"""Base for classes that need to manage a runtime variant number of child threads"""
	def __init__(self):
		super(ThreadContainer, self).__init__()
		self.dying = False
		self.threads = []
		self.logger = Log

	def ondestroy(self):
		"""tell myself i'm dying and try to stop all my threads"""
		self.dying = True
		try:
			for thread in self.threads:
				try:
					thread.join(5)
				except AttributeError:
					#if its an old style id still try to terminate it (will prolly fail tho)
					_async_raise(thread, SystemExit)
		except Exception, e:
			self.logger.error("detroying %s plugin failed" % self.name)
			self.logger.exception(e)
		self.threads = filter(lambda thread: isinstance(thread,
				PluginThread) and thread.isAlive(), self.threads)
		if len(self.threads):
			self.logger.error("%d threads left alive after destroy was called" %
					len(self.threads))

	def start_thread(self, func, *args):
		"""run a given function with args in a
		new thread that is added to the internal list"""
		self.threads.append(PluginThread(func, *args))
		#app exits if only daemon threads are left alive
		self.threads[-1].daemon = True
		self.threads[-1].start()


class IPlugin(ThreadContainer):
	"""base class all plugins should derive from (and expose fitting ctor)"""
	def __init__(self, name, tasclient):
		super(IPlugin, self).__init__()
		self.tasclient = tasclient
		self.name = name
		self.logger = Log.getPluginLogger(name)
		self.commands = defaultdict(list)
		#this registers all cmd_* where * matches an actualLobby command in our command dict
		foreign_cmd_count = 0
		cmd_count = 0
		for f in filter( lambda f: f.startswith('cmd_'), dir(self)):
			try:
				name_tokens = f.split('_')
				cmd = name_tokens[1].upper()
				if len(name_tokens) >= 3 and cmd in CHAT_COMMANDS:
					self.commands[cmd].append(('!%s'%name_tokens[2],f))
				elif cmd in ALL_COMMANDS:
					self.commands[cmd].append((None,f))
				else:
					self.logger.error('trying to register function for unknown command %s'%cmd)
				foreign_cmd_count += f != 'cmd_said_help' and f != 'cmd_saidprivate_help'
				cmd_count += 1
			except IndexError,e:
				self.logger.debug(f)
				self.logger.exception(e)
		#if no oncommand is present in derived class we can safely move our generic on in
		if 'oncommandfromserver' in dir(self):
			if foreign_cmd_count:
				self.logger.error('mixing old and new style command handling')
		else:
			self.oncommandfromserver = self._oncommandfromserver
		self.logger.debug('registered %d commands' % (cmd_count - foreign_cmd_count))

	def _trim_chat_args(self, _args, tas_command):
		""" remove cruft from SAID* responses
			SAID[EX] channame username message becomes
			SAID[EX] channame message[1:]
			and
			SAIDPRIVATE[EX] userame message becomes
			SAIDPRIVATE[EX] username message[1:]
		"""
		args = _args[:]
		del args[1]
		if tas_command.find('PRIVATE') == -1:
			del args[1]
		return args

	def cmd_said_help(self, args, tas_command):
		"""Respond with a list of available chat commands or
		a command specific help
		"""
		args = self._trim_chat_args(args, tas_command)
		#either way we're left with: user/channel [item]
		target = args[0]
		if len(args) > 1:
			helpitem = args[1]
			for command in CHAT_COMMANDS:
				for trigger,funcname in self.commands[command]:
					#allow both '!item' and 'item' to trigger the help
					if trigger == None or trigger.replace('!','') != helpitem.replace('!',''):
						continue
					try:
						func = getattr(self, funcname)
						self.tasclient.say_pm_or_channel(tas_command, target, func.__doc__)
						return
					except Exception,e:
						self.logger.exception(e)
						continue
			self.tasclient.say_pm_or_channel(tas_command, target, 'No further help available for \'%s\'.' % helpitem)
		else:
			self.tasclient.say_pm_or_channel(tas_command, target, 'available commands:')
			for command in CHAT_COMMANDS:
				for trigger,funcname in self.commands[command]:
					if trigger == '!help':
						continue
					func = getattr(self,funcname)
					if 'admin_only' in dir(func):
						self.tasclient.say_pm_or_channel(tas_command, target, trigger + ' (admin-only)')
					else:
						self.tasclient.say_pm_or_channel(tas_command, target, trigger)
			self.tasclient.say_pm_or_channel(tas_command, target, 'for further help try "!help [item]"')

	cmd_saidprivate_help = cmd_said_help

	def _oncommandfromserver(self, command, args, socket):
		"""Automagically calls registered function matching command and args."""
		try:
			for trigger,funcname in self.commands[command]:
				do_call = (trigger == None) or (
					(command.find('PRIVATE') == -1 and trigger == args[2]) or
					(command.find('PRIVATE') > -1 and trigger == args[1]))
				if do_call:
					func = getattr(self, funcname)
					func(args, command)
		except KeyError, k:
			self.logger.exception(k)
		except Exception, e:
			self.logger.exception(e)


class PluginHandler(object):
	""" manage runtime loaded modules (plugins) """

	def __init__(self, main):
		super(PluginHandler, self).__init__()
		self.app = main
		self.plugins = dict()
		self.pluginthreads = dict()

	def addplugin(self, name, tasc):
		"""try to import module name and init it"""
		if name in self.plugins:
			Log.bad("Plugin %s is already loaded" % name)
			return
		try:
			code = __import__(name)
		except ImportError:
			Log.debug('trying to load plugin %s from plugins subdir' % name )
			try:
				pname = 'tasbot.plugins.%s' % name
				__import__(pname)
				code = sys.modules[pname]
			except ImportError, imp:
				Log.error("Cannot load plugin %s" % name)
				Log.exception(imp)
				raise SystemExit(1)
		try:
			self.plugins.update([(name, code.Main(name, tasc))])
		except TypeError, t:
			Log.exception(t)
			self.plugins.update([(name, code.Main())])
			Log.error('loaded old-style plugin %s. Please derive from IPlugin' % name)
		self.plugins[name].socket = tasc.socket

		try:
			if "onload" in dir(self.plugins[name]):
				self.plugins[name].onload(tasc)
			if "onloggedin" in dir(self.plugins[name]) and self.app.connected:
				self.plugins[name].onloggedin(tasc.socket)
		except Exception, e:
			Log.exception(e)
			return
		Log.loaded("Plugin " + name)

	def unloadplugin(self, name):
		""" unload plugin, stop all its threads
		via ondestroy and remove from interal list"""
		if not name in self.plugins:
			Log.error("Plugin %s not loaded" % name)
			return
		try:
			if "ondestroy" in dir(self.plugins[name]):
				self.plugins[name].ondestroy()
			self.plugins.pop(name)
			Log.notice("%s Unloaded" % name)
		except Exception, e:
			Log.error("Cannot unload plugin %s" % name)
			Log.error("Use forceunload to remove it anyway")
			Log.exception(e)

	def unloadAll(self):
		"""convenience function to unload all plugins at once"""
		#make copy because unload changes the dict
		names = [name for name in self.plugins]
		for name in names:
			self.unloadplugin(name)

	def forceunloadplugin(self, name, tasc):
		"""simply removes name from internal list, only call if unload else fails"""
		if not name in self.plugins:
			Log.error("Plugin %s not loaded" % name)
			return
		self.plugins.pop(name)
		Log.bad("%s UnLog.loaded(Forced)" % name)

	def reloadplugin(self, name):
		"""broken"""
		if not name in self.plugins:
			Log.error("Plugin %s not loaded" % name)
			return
		try:
			if "ondestroy" in dir(self.plugins[name]):
				self.plugins[name].ondestroy()
			Log.notice("%s Unloaded" % name)
		except Exception:
			Log.error("Cannot unload plugin %s" % name)
			Log.error("Use forceunload to remove it anyway")
			Log.error(traceback.print_exc())
		try:
			code = reload(sys.modules[name])
		except Exception:
			Log.error("Cannot reload plugin %s!" % name)
			return
		self.plugins.update([(name, code.Main())])
		self.plugins[name].socket = self.app.tasclient.socket
		try:
			if "onload" in dir(self.plugins[name]):
				self.plugins[name].onload(self.app.tasclient)
		except Exception:
			Log.error("Cannot load plugin   " + name)
			Log.error(traceback.print_exc())
			return
		Log.loaded("Plugin " + name)

	def forall(self, func_name, *args, **kwargs):
		""" execute a given function(name) on all plugins that expose it"""
		for name, plugin in filter(lambda (name, plugin):
				func_name in dir(plugin), self.plugins.iteritems()):
			try:
				func = getattr(plugin, func_name)
				func(*args, **kwargs)
			except SystemExit:
				raise SystemExit(0)
			except Exception, e:
				Log.error("PLUGIN %s ERROR calling  %s" %
					(func_name, name))
				Log.exception(e)

	def onconnected(self):
		self.forall("onconnected")

	def ondisconnected(self):
		self.forall("ondisconnected")

	def onmotd(self, content):
		self.forall("onmotd", content)

	def onsaid(self, channel, user, message):
		self.forall("onsaid", channel, user, message)

	def onsaidex(self, channel, user, message):
		self.forall("onsaidex", channel, user, message)

	def onsaidprivate(self, user, message):
		"""react on a few given keywords and also pass the call to all plugins"""
		args = message.split(" ")
		if args[0].lower() == "!reloadconfig" and user in self.app.admins:
			self.app.ReloadConfig()
		if (args[0].lower() == "!unloadplugin" and
				user in self.app.admins and len(args) == 2):
			try:
				self.unloadplugin(args[1])
			except Exception:
				Log.bad("Unloadplugin failed")
				Log.error(traceback.print_exc())

		if (args[0].lower() == "!loadplugin" and
				user in self.app.admins and len(args) == 2):
			try:
				self.addplugin(args[1], self.app.tasclient)
			except Exception:
				Log.bad("addplugin failed")
				Log.error(traceback.print_exc())

		if (args[0].lower() == "!reloadplugin" and
				user in self.app.admins and len(args) == 2):
			try:
				self.reloadplugin(args[1])
			except Exception:
				Log.bad("Unloadplugin failed")
				Log.error(traceback.print_exc())

		self.forall("onsaidprivate", user, message)

	def onloggedin(self, socket):
		self.forall("onloggedin", socket)

	def onpong(self):
		self.forall("onpong")

	def oncommandfromserver(self, command, args, socket):
		self.forall("oncommandfromserver", command, args, socket)

	def onexit(self):
		self.forall("onexit")

	def ondisconnected(self):
		self.forall("ondisconnected")
