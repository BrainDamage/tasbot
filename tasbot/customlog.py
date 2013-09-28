# -*- coding: utf-8 -*-

import sys
import datetime
import logging
import logging.handlers
import os.path

from color_formatter import *

loggingLevelMapping = {
			'debug'    : logging.DEBUG,
			'info'     : logging.INFO,
			'error'    : logging.ERROR,
			'warn'     : logging.WARN,
			'warning'  : logging.WARNING,
			'critical' : logging.CRITICAL,
			'fatal'    : logging.FATAL,
		}

class ILogger(object):
	"""Logging interface class that (somewhat) preserves backward compat
	with the old, crappy, handcrafted logging"""
	def __init__(self,prefix=None):
		self.default_prefix = prefix

	def _prepare(self,msg,prefix):
		if prefix:
			msg = '[%s] %s'%(prefix,msg)
		if self.default_prefix:
			msg = '<%s> %s'%(self.default_prefix, msg)
		if not self._initialised:
			sys.stderr.write( str(msg) + 'Logger not initialised\n' )
			return 'WARGH! logging is NOT initialised'
		return msg

	def error(self, msg,prefix=None):
		self._logger.error( self._prepare( msg,prefix ) )

	def debug(self, msg,prefix=None):
		self._logger.debug( self._prepare( msg,prefix ) )
	def info(self, msg,prefix=None):
		self._logger.info( self._prepare( msg,prefix ) )

	def exception(self,e):
		#TODO needs prefix handling
		self._logger.exception( e )

	def loaded(self,t):
		self.info( t, "LOADED" )

	def reloaded(self,t):
		self.info( t, "RELOADED" )

	def notice(self,t):
		self.info( t )

	def good(self,t):
		self.info( t, "GOOD" )

	def bad(self,t):
		self.error( t,"BAD" )

class CLog(ILogger):
	"""Main Logging instance, forwards al logging calls to the stdlib's logging
	via a RotatingFileHandler and proper stream formatters"""
	def __init__(self):
		"""Since this is called at module import time we cannot do all
		we'd want here, see init for the rest"""
		super(CLog,self).__init__(prefix=None)
		self._initialised = False
		self._FORMAT = '$BOLD%(levelname)s$RESET - %(asctime)s - %(message)s'

	def init(self, logfile_name, level='info', stdout_log=True ):
		"""All the setup that is possible only after this module was imported."""
		logfile_name = logfile_name
		self.filehandler = logging.handlers.RotatingFileHandler(logfile_name,
								maxBytes=1048576, backupCount=5) # 1MB files
		if stdout_log:
			self.streamhandler =  logging.StreamHandler(sys.stderr)
		else:
			self.streamhandler =  logging.handlers.NullHandler()
		self.streamformatter = ColoredFormatter(formatter_message(self._FORMAT, True))
		self.fileformatter = ColoredFormatter(formatter_message(self._FORMAT, False))
		self.streamhandler.setFormatter( self.streamformatter )
		self.filehandler.setFormatter( self.fileformatter )
		self._logger = logging.getLogger('main')
		self._logger.addHandler(self.streamhandler)
		self._logger.addHandler(self.filehandler)
		try:
			self._logger.setLevel( loggingLevelMapping[level] )
		except KeyError:
			self._logger.setLevel( logging.ERROR )
			self._logger.error('unknown log level %s requested, defaulting to logging.ERROR' % level)

		self._initialised = True
		self._logger.info( 'session started' )

	def getPluginLogger(self, name):
		return PluginLogger( self, name )


class PluginLogger(ILogger):
	"""ILogger with prefix based on given plugin name.
	Shares the backend with its parent clog."""
	def __init__(self, clog,plugin):
		super(PluginLogger,self).__init__(prefix='PL %s'%plugin)
		self._logger = clog._logger
		self._initialised = True

Log = CLog()
