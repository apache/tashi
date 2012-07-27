#!/usr/bin/python

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

import os.path
import optparse
import random
import sys
import types
from tashi.rpycservices.rpyctypes import NetworkConfiguration,\
	DiskConfiguration, HostState, Instance, Host, TashiException
from tashi.utils.config import Config
from tashi import vmStates, hostStates, boolean, stringPartition, createClient

users = {}
networks = {}

def fetchUsers():
	if (users == {}):
		_users = client.getUsers()
		for user in _users:
			users[user.id] = user

def fetchNetworks():
	if (networks == {}):
		_networks = client.getNetworks()
		for network in _networks:
			networks[network.id] = network

def getUser():
	fetchUsers()
	if client.username != None:
		userStr = client.username
	else:
		userStr = os.getenv("USER", "unknown")
	for user in users:
		if (users[user].name == userStr):
			return users[user].id
	raise TashiException({'msg':"Unknown user %s" % (userStr)})

def checkHid(host):
	userId = getUser()
	hosts = client.getHosts()
	hostId = None
	try:
		hostId = int(host)
	except:
		for h in hosts:
			if (h.name == host):
				hostId = h.id
	if (hostId is None):
		raise TashiException({'msg':"Unknown host %s" % (str(host))})

	# XXXstroucki permissions for host related stuff?
	return hostId

def remoteCommand(command, *args):
	global client
	#print "Doing command %s args %s" % (command, args)
	f = getattr(client, command, None)

	rv = f(*args)

	return rv

def setHostState(args):
	global scriptname
	parser = optparse.OptionParser()
	parser.set_usage("%s setHostState [options]" % scriptname)
	parser.add_option("--host", help="Set the state of this host (mandatory)", action="store", type="string", dest="hostname")
	parser.add_option("--state", help="Change state to this value, e.g. Normal or Drained (mandatory)", action="store", type="string", dest="state")
	(options, arguments) = parser.parse_args(args)
	if options.hostname is None or options.state is None:
		print "A mandatory option is missing\n"
		parser.print_help()
		sys.exit(-1)

	hostId = checkHid(options.hostname)
	rv = remoteCommand("setHostState", hostId, options.state)
	print rv
	return 0

def setHostNotes(args):
	global scriptname
	parser = optparse.OptionParser()
	parser.set_usage("%s setHostNotes [options]" % scriptname)
	parser.add_option("--host", help="Annotate this host with the note (mandatory)", action="store", type="string", dest="hostname")
	parser.add_option("--notes", help="Annotate the host with this note (mandatory)", action="store", type="string", dest="notes")
	(options, arguments) = parser.parse_args(args)
	if options.hostname is None or options.notes is None:
		print "A mandatory option is missing\n"
		parser.print_help()
		sys.exit(-1)

	hostId = checkHid(options.hostname)
	rv = remoteCommand("setHostNotes", hostId, options.notes)
	print rv
	return 0

def help(args):
	global scriptname
	print "Available commands:"
	for (command, desc) in cmdsdesc:
		print "%s\t\t%s" % (command, desc)
	print "See %s <command> -h for help on these commands." % scriptname
	return 0

""" Possible functions:
description = (
('addHost', 'Adds a new host to Tashi'),
('delHost', 'Removes a host from Tashi'),
('addUser', 'Adds a user to Tashi'),
('delUser', 'Removes a user from Tashi'),
('addNet', 'Adds a network to Tashi'),
('delNet', 'Removes a network from Tashi'),
('setHostState', 'Set the state of a host, eg. Normal or Drained'),
('setHostNotes', 'Annotate a host record'),
)

# Example use strings
examples = (
('addHost', ('--name <host name>',)),
('delHost', ('--name <host name>',)),
('addUser', ('--name <user name>',)),
('delUser', ('--name <user name>',)),
('addNet', ('--name <network name> --id <VLAN ID>',)),
('delNet', ('--name <network name>','--id <VLAN ID>',)),
('setHostState', ('--host <host name> --state <new state>',)),
('setHostNotes', ('--host <host name> --text <text string>',)),
)

show_hide = []

def usage(func = None):
	"""Print program usage"""
	if (func == None or func not in argLists):
		if (func != None):
			print "Unknown function %s" % (func)
			print
		functions = argLists
		print "%s is the administrative tool for Tashi" % (os.path.basename(sys.argv[0]))
		print "Tashi, a system for cloud-computing on BigData"
		print "Visit http://incubator.apache.org/tashi/ for more information."
		print
	else:
		functions = {func: argLists[func]}
	print "Usage:"
	for f in functions:
		args = argLists[f]
		line = "\t" + f
		for arg in args:
			if (arg[3]):
				line += " --%s <value>" % (arg[0])
			else:
				line += " [--%s <value>]" % (arg[0])
		print line
		if ("--help" in sys.argv and f in description):
			print
			print "\t\t" + description[f]
			print
		if ("--examples" in sys.argv):
			if ("--help" not in sys.argv or f not in description):
				print
			for example in examples.get(f, []):
				print "\t\t" + f + " " + example
			print
	if ("--help" not in sys.argv and "--examples" not in sys.argv):
		print
	print "Additionally, all functions accept --show-<name> and --hide-<name>, which show and hide columns during table generation"
	if ("--examples" not in sys.argv):
		print "Use \"--examples\" to see examples"
	sys.exit(-1)

def transformState(obj):
	if (type(obj) == Instance):
		fetchUsers()
		try:
			obj.state = vmStates[obj.state]
		except:
			obj.state = 'Unknown'
		if (obj.userId in users):
			obj.user = users[obj.userId].name
		else:
			obj.user = None
		obj.disk = obj.disks[0].uri
		if (obj.disks[0].persistent):
			obj.disk += ":True"
	elif (type(obj) == Host):
		try:
			obj.state = hostStates[obj.state]
		except:
			obj.state = 'Unknown'

def genKeys(_list):
	keys = {}
	for row in _list:
		for item in row.__dict__.keys():
			keys[item] = item
	if ('id' in keys):
		del keys['id']
		keys = ['id'] + keys.values()
	else:
		keys = keys.values()
	return keys

def makeTable(_list, keys=None):
	(consoleWidth, __consoleHeight) = (9999, 9999)
	try:
# XXXpipe: get number of rows and column on current window
		stdout = os.popen("stty size")
		__r = stdout.read()
		stdout.close()
	except:
		pass
	for obj in _list:
		transformState(obj)
	if (keys == None):
		keys = genKeys(_list)
	for (show, k) in show_hide:
		if (show):
			if (k != "all"):
				keys.append(k)
			else:
				keys = genKeys(_list)
		else:
			if (k in keys):
				keys.remove(k)
			if (k == "all"):
				keys = []
	maxWidth = {}
	for k in keys:
		maxWidth[k] = len(k)
	for row in _list:
		for k in keys:
			if (k in row.__dict__):
				maxWidth[k] = max(maxWidth[k], len(str(row.__dict__[k])))
	if (keys == []):
		return
	totalWidth = reduce(lambda x, y: x + y + 1, maxWidth.values(), 0)
	while (totalWidth > consoleWidth):
		widths = maxWidth.items()
		widths.sort(cmp=lambda x, y: cmp(x[1], y[1]))
		widths.reverse()
		maxWidth[widths[0][0]] = widths[0][1]-1
		totalWidth = reduce(lambda x, y: x + y + 1, maxWidth.values(), 0)
	line = ""
	for k in keys:
		if (len(str(k)) > maxWidth[k]):
			line += (" %-" + str(maxWidth[k]-3) + "." + str(maxWidth[k]-3) + "s...") % (k)
		else:
			line += (" %-" + str(maxWidth[k]) + "." + str(maxWidth[k]) + "s") % (k)
	print line
	line = ""
	for k in keys:
		line += ("-" * (maxWidth[k]+1))
	print line
	def sortFunction(a, b):
		av = a.__dict__[keys[0]]
		bv = b.__dict__[keys[0]]
		if (av < bv):
			return -1
		elif (av > bv):
			return 1
		else:
			return 0
	_list.sort(cmp=sortFunction)
	for row in _list:
		line = ""
		for k in keys:
			row.__dict__[k] = row.__dict__.get(k, "")
			if (len(str(row.__dict__[k])) > maxWidth[k]):
				line += (" %-" + str(maxWidth[k]-3) + "." + str(maxWidth[k]-3) + "s...") % (str(row.__dict__[k]))
			else:
				line += (" %-" + str(maxWidth[k]) + "." + str(maxWidth[k]) + "s") % (str(row.__dict__[k]))
		print line
		
def simpleType(obj):
	"""Determines whether an object is a simple type -- used as a helper function to pprint"""
	if (type(obj) is not types.ListType):
		if (not getattr(obj, "__dict__", None)):
			return True
	return False

def pprint(obj, depth = 0, key = None):
	"""My own version of pprint that prints out a dict in a readable, but slightly more compact format"""
	valueManip = lambda x: x
	if (key):
		keyString = key + ": "
		if (key == "state"):
			valueManip = lambda x: vmStates[x]
	else:
		keyString = ""
	if (type(obj) is types.ListType):
		if (reduce(lambda x, y: x and simpleType(y), obj, True)):
			print (" " * (depth * INDENT)) + keyString + str(obj)
		else:
			print (" " * (depth * INDENT)) + keyString + "["
			for o in obj:
				pprint(o, depth + 1)
			print (" " * (depth * INDENT)) + "]"
	elif (getattr(obj, "__dict__", None)):
		if (reduce(lambda x, y: x and simpleType(y), obj.__dict__.itervalues(), True)):
			print (" " * (depth * INDENT)) + keyString + str(obj)
		else:
			print (" " * (depth * INDENT)) + keyString + "{"
			for (k, v) in obj.__dict__.iteritems():
				pprint(v, depth + 1, k)
			print (" " * (depth * INDENT)) + "}"
	else:
		print (" " * (depth * INDENT)) + keyString + str(valueManip(obj))

def matchFunction(func):
	if (func == "--help" or func == "--examples"):
		usage()
	lowerFunc = func.lower()
	lowerFuncsList = map(lambda x: (x.lower(), x), argLists.keys())
	lowerFuncs = {}
	for (l, f) in lowerFuncsList:
		lowerFuncs[l] = f
	if (lowerFunc in lowerFuncs):
		return lowerFuncs[lowerFunc]
	usage(func)

def main():
	"""Main function for the client program"""
	global INDENT, exitCode, client
	exitCode = 0
	exception = None
	INDENT = (os.getenv("INDENT", 4))
	if (len(sys.argv) < 2):
		usage()

	config = Config(["Client"])

	# get command name
	function = matchFunction(sys.argv[1])

	# build a structure of possible arguments
	possibleArgs = {}
	argList = argLists[function]
	for i in range(0, len(argList)):
		possibleArgs[argList[i][0]]=argList[i]

	args = sys.argv[2:]

	vals = {}

	try:
		# create client handle
		client = createClient(config)

		# set defaults
		for parg in possibleArgs.values():
			(parg, conv, default, required) = parg
			if (required is False):
				vals[parg] = default()

		while (len(args) > 0):
			arg = args.pop(0)

			if (arg == "--help" or arg == "--examples"):
				usage(function)
				# this exits

			if (arg.startswith("--")):
				if (arg[2:] in possibleArgs):
					(parg, conv, default, required) = possibleArgs[arg[2:]]
					try:
						val = None
						lookahead = args[0]
						if not lookahead.startswith("--"):
							val = args.pop(0)
					except:
						pass

					val = conv(val)
					if (val == None):
						val = default()

					vals[parg] = val
					continue
			# somewhat lame, but i don't want to rewrite the fn at this time
			exception = ValueError("Unknown argument %s" % (arg)) 

		f = None
		try:
			f = extraViews[function][0]
		except:
			pass

		if (f is None):
			f = getattr(client, function, None)

		try:
			if exception is not None:
				raise exception

			if (function in convertArgs):
				fargs = eval(convertArgs[function], globals(), vals)
			else:
				fargs = []

			res = f(*fargs)

		except TashiException, e:
			print "Failed in calling %s: %s" % (function, e.msg)
			sys.exit(-1)

		except Exception, e:
			print "Failed in calling %s: %s" % (function, e)
			print "Please run tashi-admin --examples for syntax information"
			sys.exit(-1)

		if (res != None):
			keys = extraViews.get(function, (None, None))[1]
			try:
				if (type(res) == types.ListType):
					makeTable(res, keys)
				elif (type(res) == types.StringType):
					print res
				else:
					makeTable([res], keys)
					
			except IOError:
				pass
			except Exception, e:
				print e
	except TashiException, e:
		print "Tashi could not complete your request:"
		print e.msg
		exitCode = e.errno
 	except Exception, e:
 		print e
		print "Please run tashi-admin --examples for syntax information"
	sys.exit(exitCode)

if __name__ == "__main__":
	main()
