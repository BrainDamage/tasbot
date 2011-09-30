"""Configuration backend."""
import string
import traceback
import os
from ConfigParser import SafeConfigParser as ConfigParser
from ConfigParser import NoOptionError
import traceback

from customlog import Log
from decorators import Deprecated


class Config(object):
	"""Slim wrapper around python builtin config file parser
	that mostly adds defaults and list-value handling
	"""

	def __init__(self, filename):
		super(Config,self).__init__()
		self._filename = filename
		self._config = ConfigParser()
		self.has_option = self._config.has_option
		self.set = self._config.set
		try:
			open(filename, 'r').close()
			self._config.read(filename)
		except Exception, e:
			try:
				Log.error("Configfile %s invalid" % self.filename)
				Log.exception(e)
			except AttributeError, e:
				print('Error reading configfile %s and Logging not initialized' %
						filename)
			raise SystemExit(1)

	def get(self, section, key, default=None):
		#find out reason why int keys fail to load
		key = str(key)
		#if isinstance(key,int):#uncomment this to locate int keys
			#Log.error('WUT')
			#traceback.print_stack()
			#raise SystemExit(1)
		try:
			return os.path.expandvars(self._config.get(section, key))
		except NoOptionError:
			if default == None:
				Log.error('no value or default found for config item %s -- %s' %
							(section, key))
		except Exception, e:
			Log.error('Error getting config item %s -- %s' %
							(section, key))
			Log.exception(e)
		return default

	@Deprecated('Config.get')
	def GetSingleOption(self,*args, **kwargs):
		return self.get(*args, **kwargs)

	def get_optionlist(self, section, key, seperator=',', default=[]):
		try:
			return self._parselist(self._config.get(section, key), seperator)
		except Exception, e:
			Log.error('Error getting value list for key %s in section %s' %
							(key, section))
			Log.exception(e)
		return default

	@Deprecated('Config.get_optionlist')
	def GetOptionList(self,*args, **kwargs):
		return self.get_optionlist(*args, **kwargs)

	def write(self, filename=None):
		if filename == None:
			filename = self._filename
		with open(filename, 'wb') as cfile:
			self._config.write(cfile)

	def _parselist(self, string, sep):
		if string.count(sep) < 1:
			return [string]
		return [os.path.expandvars(token.strip()) for token in string.split(sep)]

	def get_bool(self, section, key, default=False):
		try:
			val = self._config.getboolean(section, key)
			return val
		except ValueError:
			Log.error('Config option %s in section [%s] must be on of "1,yes,true,on" or "0,no,false,off"'%(section,key))
		except Exception, e:
			Log.exception(e)
		return default
