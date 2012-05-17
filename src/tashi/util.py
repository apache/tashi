# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.    

#XXXstroucki: for compatibility with python 2.5
from __future__ import with_statement

import ConfigParser
#import cPickle
import os
#import select
import signal
#import struct
import sys
import threading
import time
import traceback
import types
import getpass
import functools

from tashi.rpycservices import rpycservices
from tashi.rpycservices.rpyctypes import TashiException, Errors, InstanceState, HostState
from tashi.utils.timeout import *

def broken(oldFunc):
	"""Decorator that is used to mark a function as temporarily broken"""
	def newFunc(*args, **kw):
		raise RuntimeError("%s is broken!" % (oldFunc.__name__))
	if (oldFunc.__doc__ is None):
		newFunc.__doc__ = "[Broken]"
	else:
		newFunc.__doc__ = "[Broken] " + oldFunc.__doc__
	newFunc.__name__ = oldFunc.__name__
	newFunc.__module__ = oldFunc.__module__
	return newFunc

def deprecated(oldFunc):
	"""Decorator that is used to deprecate functions"""
	def newFunc(*args, **kw):
		raise RuntimeError("%s has been deprecated!" % (oldFunc.__name__))
	newFunc.__doc__ = "[Deprecated] " + str(oldFunc.__doc__)
	newFunc.__name__ = oldFunc.__name__
	newFunc.__module__ = oldFunc.__module__
	return newFunc

def logged(oldFunc):
	"""Decorator that is used to log a function's calls -- currently uses sys.stderr"""
	def newFunc(*args, **kw):
		logMsg = "%s(%s, %s) -> " % (oldFunc.__name__, str(args).strip("[]"), str(kw).strip("{}").replace(": ", "="))
		sys.stderr.write(logMsg)
		sys.stderr.flush()
		try:
			res = oldFunc(*args, **kw)
		except Exception, e:
			logMsg = "%s\n" % (str(e))
			sys.stderr.write(logMsg)
			sys.stderr.flush()
			raise
		logMsg = "%s\n" % (str(res))
		sys.stderr.write(logMsg)
		sys.stderr.flush()
	newFunc.__doc__ = oldFunc.__doc__
	newFunc.__name__ = oldFunc.__name__
	newFunc.__module__ = oldFunc.__module__
	return newFunc

def timed(oldFunc):
	"""Decorator that is used to time a function's execution"""
	def newFunc(*args, **kw):
		start = time.time()
		try:
			res = oldFunc(*args, **kw)
		finally:
			finish = time.time()
			print "%s: %f" % (oldFunc.__name__, finish-start)
		return res
	return newFunc

def editAndContinue(file, mod, name):
	def wrapper(oldFunc):
		persist = {}
		persist['lastMod'] = time.time()
		persist['oldFunc'] = oldFunc
		persist['func'] = oldFunc
		def newFunc(*args, **kw):
			modTime = os.stat(file)[8]
			if (modTime > persist['lastMod']):
				persist['lastMod'] = modTime
				space = {}
				exec ("import %s\nreload ( %s )" % (mod, mod)) in space
				persist['func'] = eval(mod + "." + name, space)
			return persist['func'](*args, **kw)
		return newFunc
	return wrapper

class failsafe(object):
	"""Class that attempts to make RPCs, but will fall back to a local object that implements the same methods"""
	def __attempt__(self, cur, fail):
		def newFunc(*args, **kw):
			try:
				return cur(*args, **kw)
			except:
				self.__dict__['__current_obj__'] = self.__dict__['__failsafe_obj__']
				return fail(*args, **kw)
		return newFunc
	
	@deprecated
	def __init__(self, obj):
		self.__dict__['__failsafe_obj__'] = obj
		self.__dict__['__current_obj__'] = obj
	
	def __update_current__(self, obj):
		self.__dict__['__current_obj__'] = obj
	
	def __getattr__(self, name):
		return self.__attempt__(getattr(self.__dict__['__current_obj__'], name), getattr(self.__dict__['__failsafe_obj__'], name))
	
	def __setattr__(self, name, value):
		return setattr(self.__dict__['__current_obj__'], name, value)
	
	def __delattr__(self, name):
		return delattr(self.__dict__['__current_obj__'], name)

class reference(object):
	"""Class used to create a replacable reference to an object"""
	@deprecated
	def __init__(self, obj):
		self.__dict__['__real_obj__'] = obj
	
	def __update__(self, obj):
		self.__dict__['__real_obj__'] = obj
	
	def __getattr__(self, name):
		return getattr(self.__dict__['__real_obj__'], name)
	
	def __setattr__(self, name, value):
		return setattr(self.__dict__['__real_obj__'], name, value)
	
	def __delattr__(self, name):
		return delattr(self.__dict__['__real_obj__'], name)

def signalHandler(signalNumber):
	"""Used to denote a particular function as the signal handler for a 
	   specific signal"""
	def __decorator(function):
		signal.signal(signalNumber, function)
		return function
	return __decorator

def boolean(value):
	"""Convert a variable to a boolean"""
	if (type(value) == types.BooleanType):
		return value
	if (type(value) == types.IntType):
		return (value != 0)

	# See if it can be expressed as a string
	try:
		value = str(value)
	except:
		raise ValueError

	lowercaseValue = value.lower()
	if lowercaseValue in ['yes', 'true', '1']:
		return True
	elif lowercaseValue in ['no', 'false', '0']:
		return False
	else:
		raise ValueError

def instantiateImplementation(className, *args):
	"""Create an instance of an object with the given class name and list 
	   of args to __init__"""
	if (className.rfind(".") != -1):
		package = className[:className.rfind(".")]
		cmd = "import %s\n" % (package)
	else:
		cmd = ""
	cmd += "obj = %s(*args)\n" % (className)
	exec cmd in locals()
	return obj

def convertExceptions(oldFunc):
	"""This converts any exception type into a TashiException so that 
	   it can be passed over an RPC"""
	def newFunc(*args, **kw):
		try:
			return oldFunc(*args, **kw)
		except TashiException:
			raise
		except:
			self = args[0]
			if (self.convertExceptions):
				raise TashiException(d={'errno':Errors.ConvertedException, 'msg': traceback.format_exc(10)})
			raise
	return newFunc

def getConfig(additionalNames=[], additionalFiles=[]):
	"""Creates many permutations of a list of locations to look for config 
	   files and then loads them"""
	config = ConfigParser.ConfigParser()
	baseLocations = ['/usr/local/tashi/etc/', '/usr/share/tashi/', '/etc/tashi/', os.path.expanduser('~/.tashi/')]
	names = ['Tashi'] + additionalNames
	names = reduce(lambda x, y: x + [y+"Defaults", y], names, [])
	allLocations = reduce(lambda x, y: x + reduce(lambda z, a: z + [y + a + ".cfg"], names, []), baseLocations, []) + additionalFiles
	configFiles = config.read(allLocations)
	if (len(configFiles) == 0):
		raise Exception("No config file could be found: %s" % (str(allLocations)))
	return (config, configFiles)

def __getShellFn():
	try:
		from IPython.Shell import IPShellEmbed
		return (1, IPShellEmbed)
	except ImportError:
		import IPython
		return (2, IPython.embed)

def debugConsole(globalDict):
	"""A debugging console that optionally uses pysh"""
	def realDebugConsole(globalDict):
		import os
		try :
			import atexit
			(calltype, shellfn) = __getShellFn()
			def resetConsole():
# XXXpipe: make input window sane
				(stdin, stdout) = os.popen2("reset")
				stdout.read()
			atexit.register(resetConsole)
			if calltype == 1:
				dbgshell=shellfn(user_ns=globalDict)
				dbgshell()
			elif calltype == 2:
				dbgshell=shellfn
				dbgshell(user_ns=globalDict)
		except Exception, e:
			CONSOLE_TEXT=">>> "
			input = " " 
			while (input != ""):
				sys.stdout.write(CONSOLE_TEXT)
				input = sys.stdin.readline()
				try:
					exec(input) in globalDict
				except Exception, e:
					sys.stdout.write(str(e) + "\n")

		os._exit(0)

	if (os.getenv("DEBUG", "0") == "1"):
		threading.Thread(target=lambda: realDebugConsole(globalDict)).start()

def stringPartition(s, field):
	index = s.find(field)
	if (index == -1):
		return (s, "", "")
	l = s[:index]
	sep = s[index:index+len(field)]
	r = s[index+len(field):]
	return (l, sep, r)

def scrubString(s, allowed="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_."):
	ns = ""
	for c in s:
		if (c in allowed):
			ns = ns + c
	return ns

class Connection:

	def __init__(self, host, port, authAndEncrypt=False, credentials=None):
		self.host = host
		self.port = port
		self.credentials = credentials
		self.authAndEncrypt = authAndEncrypt
		self.connection = None
		# XXXstroucki some thing may still depend on this (client)
		self.username = None
		if credentials is not None:
			self.username = credentials[0]

	def __connect(self):
		# create new connection

		username = None
		password = None

		if self.credentials is not None:
			username = self.credentials[0]
			password = self.credentials[1]

		if self.authAndEncrypt:
			if username is None:
				username = raw_input("Enter Username:")

			if password is None:
				password = raw_input("Enter Password:")

			if self.credentials != (username, password):
				self.credentials = (username, password)

			client = rpycservices.client(self.host, self.port, username=username, password=password)
		else:
			client = rpycservices.client(self.host, self.port)

		self.connection = client


	def __do(self, name, *args, **kwargs):
		if self.connection is None:
			self.__connect()

		# XXXstroucki: Use 10 second timeout, ok?
		# XXXstroucki: does this fn touch the network?
		t = TimeoutThread(getattr, (self.connection, name, None))
		threading.Thread(target=t.run).start()

		try:
			remotefn = t.wait(timeout=10)
		except TimeoutException:
			self.connection = None
			raise

		try:
			if callable(remotefn):
				# XXXstroucki: Use 10 second timeout, ok?
				t = TimeoutThread(remotefn, args, kwargs)
				threading.Thread(target=t.run).start()
				returns = t.wait(timeout=10.0)

			else:
				raise TashiException({'msg':'%s not callable' % name})

		except:
			self.connection = None
			raise

		return returns

	def __getattr__(self, name):
		return functools.partial(self.__do, name)


def createClient(config):
	cfgHost = config.get('Client', 'clusterManagerHost')
	cfgPort = config.get('Client', 'clusterManagerPort')
	#XXXstroucki nothing uses timeout right now
	#cfgTimeout = config.get('Client', 'clusterManagerTimeout')
	host = os.getenv('TASHI_CM_HOST', cfgHost)
	port = os.getenv('TASHI_CM_PORT', cfgPort)
	#XXXstroucki nothing uses timeout right now
	#timeout = float(os.getenv('TASHI_CM_TIMEOUT', cfgTimeout)) * 1000.0

	authAndEncrypt = boolean(config.get('Security', 'authAndEncrypt'))
	if authAndEncrypt:
		username = config.get('AccessClusterManager', 'username')
		password = config.get('AccessClusterManager', 'password')
		client = Connection(host, port, authAndEncrypt, (username, password))

	else:
		client = Connection(host, port)

	return client

def enumToStringDict(cls):
	d = {}
	for i in cls.__dict__:
		if (type(cls.__dict__[i]) is int):
			d[cls.__dict__[i]] = i
	return d

def humanReadable(size):
	suffixes = [("B",2**10), ("K",2**20), ("M",2**30), ("G",2**40), ("T",2**50)]
	for suf, lim in suffixes:
		if size > lim:
			continue
		else:
			return round(size/float(lim/2**10),2).__str__()+suf


vmStates = enumToStringDict(InstanceState)
hostStates = enumToStringDict(HostState)
