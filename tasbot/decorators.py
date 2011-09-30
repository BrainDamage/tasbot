"""Collection of function/class based decorators."""

import warnings
import functools
import types
import inspect

from customlog import Log

def _is_decorated(func):
	return 'decorated' in dir(func)


class DecoratorBase(object):
	"""A base for all decorators that does the common automagic"""
	def __init__(self, func):
		functools.wraps(func)(self)
		func.decorated = True
		self.func = func
		assert _is_decorated(func)

	def __get__(self, obj, ownerClass=None):
		# Return a wrapper that binds self as a method of obj (!)
		self.obj = obj
		return types.MethodType(self, obj)


class DecoratorWithArgsBase(object):
	"""A base for all decorators with args that sadly can do little common automagic"""
	def mark(self, func):
		functools.wraps(func)
		func.decorated = True

	def __get__(self, obj, ownerClass=None):
		# Return a wrapper that binds self as a method of obj (!)
		self.obj = obj
		return types.MethodType(self, obj)


class Deprecated(DecoratorBase):
	"""This is a decorator which can be used to mark functions
	as deprecated. It will result in a warning being emitted
	when the function is used.
	"""

	def __init__(self,alt='no alternative given'):
		self._alt = alt

	def __call__(self,func):
		func.decorated = True
		@functools.wraps(func)
		def new_func(*args, **kwargs):
			frame = inspect.currentframe().f_back
			msg = "DeprecationWarning. Call to deprecated function %s in %s:%s\nUse %s instead" % (
							func.__name__,frame.f_code.co_filename,
							frame.f_code.co_firstlineno,self._alt)
			Log.debug(msg)
			return func(*args, **kwargs)
		return new_func


def check_and_mark_decorated(func):
	"""Check if function was already decorated and mark decorated if it wasn't."""
	if _is_decorated(func):
		return True
	func.decorated = True
	return False


class AdminOnly(DecoratorBase):
	"""this decorator only calls the wrapped function if user(==args[1]) is in admin list"""
	def __init__(self,func):
		func.admin_only = True
		super(AdminOnly,self).__init__(func)

	def __call__(self, plugin, args, tas_command):
		if plugin.tasclient.main.is_admin(args[1]):
			return self.func(plugin, args, tas_command)
		else:
			#log/respond
			pass


class DebugTrace(DecoratorBase):
	def __call__(self, *args, **kwargs):
		self.obj.logger.debug("Calling: {0}".format(self.func.__name__))
		return self.func(*args, **kwargs)


class NotSelf(DecoratorBase):
	"""This decorator will only call the decorated function if user is not myname"""
	def __call__(self, plugin, args, tas_command):
		if not plugin.tasclient.main.is_me(args[1]):
			return self.func(plugin, args, tas_command)


class MinArgs(DecoratorWithArgsBase):
	"""Ensure mandatory number of args. Only really useful for "said*" commands"""
	def __init__(self,num_args=3):
		self.num_args = num_args

	def __call__(self,func):
		if _is_decorated(func):
			Log.error( "Trying to decorate %s in %s:%d "
				"after it was already decorated. Currently "
				"_num_args must be the innermost decorator." %
				(func.__name__,func.func_code.co_filename,
					func.func_code.co_firstlineno + 1))
			raise SystemExit(1)
		#self.mark(func)
		func.decorated = True

		@functools.wraps(func)
		def decorated(plugin,args, tas_command):
			if len(args) >= self.num_args:
				return func(plugin,args, tas_command)
			else:
				plugin.logger.debug('%s called with too few args at %s:%d' %
				(func.__name__, func.func_code.co_filename,
					func.func_code.co_firstlineno + 1))
		return decorated
