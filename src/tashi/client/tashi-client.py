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
	raise ValueError("Unknown user %s" % (userStr))

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
		raise ValueError("Unknown host %s" % (str(host)))

	# XXXstroucki permissions for host related stuff?
	return hostId

def checkIid(instance):
	userId = getUser()
	instances = client.getInstances()
	instanceId = None
	try:
		instanceId = int(instance)
	except:
		for i in instances:
			if (i.name == instance):
				instanceId = i.id
	if (instanceId is None):
		raise ValueError("Unknown instance %s" % (str(instance)))
	for instance in instances:
		if (instance.id == instanceId):
			# XXXstroucki uid 0 to have superuser access
			# how about admin groups?
			if (instance.userId != userId and instance.userId != None and userId != 0):
				raise ValueError("You don't own that VM")
	return instanceId

def requiredArg(name):
	raise ValueError("Missing required argument %s" % (name))

def randomMac():
	return ("52:54:00:%2.2x:%2.2x:%2.2x" % (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

def getDefaultNetwork():
	fetchNetworks()
	networkId = 0
	for network in networks:
		if (getattr(networks[network], "default", False) is True):
			networkId = network
			break

		# Naming the network "default" is deprecated, and
		# this functionality will be removed soon
		if (networks[network].name == "default"):
			networkId = network
			break
	return networkId

def randomNetwork():
	return [NetworkConfiguration(d={'mac':randomMac(), 'network':getDefaultNetwork()})]

def parseDisks(arg):
	try:
		strDisks = arg.split(",")
		disks = []
		for strDisk in strDisks:
			strDisk = strDisk.strip()
			(l, __s, r) = stringPartition(strDisk, ":")
			if (r == ""):
				r = "False"
			r = boolean(r)
			disk = DiskConfiguration(d={'uri':l, 'persistent':r})
			disks.append(disk)
		return disks
	except:
		raise ValueError("Incorrect format for disks argument")

def parseNics(arg):
	try:
		strNics = arg.split(",")
		nics = []
		for strNic in strNics:
			strNic = strNic.strip()
			(l, __s, r) = stringPartition(strNic, ":")
			n = l
			if (n == ''):
				n = getDefaultNetwork()
			n = int(n)
			(l, __s, r) = stringPartition(r, ":")
			ip = l
			if (ip == ''):
				ip = None
			m = r
			if (m == ''):
				m = randomMac()
			nic = NetworkConfiguration(d={'mac':m, 'network':n, 'ip':ip})
			nics.append(nic)
		return nics
	except:
		raise ValueError("Incorrect format for nics argument")

def parseHints(arg):
	try:
		strHints = arg.split(",")
		hints = {}
		for strHint in strHints:
			strHint = strHint.strip()
			(l, __s, r) = stringPartition(strHint, "=")
			hints[l] = r
		return hints
	except:
		raise ValueError("Incorrect format for hints argument")

def getVmLayout():
	_hosts = client.getHosts()
	_instances = client.getInstances()
	hosts = {}
	for h in _hosts:
		h.instances = []
		h.instanceIds = []
		h.usedMemory = 0
		h.usedCores = 0
		hosts[h.id] = h
	for i in _instances:
		if (i.hostId in hosts):
			hosts[i.hostId].instanceIds.append(i.id)
			hosts[i.hostId].instances.append(i.name)
			hosts[i.hostId].usedMemory += i.memory
			hosts[i.hostId].usedCores += i.cores
	return hosts.values()

def getSlots(cores, memory):
	hosts = getVmLayout()
	count = 0

	if cores < 1:
		print "Argument to cores must be 1 or greater."
		return

	if memory <= 0:
		print "Argument to memory must be greater than 0."
		return

	for h in hosts:
		if h.up is False or h.state != HostState.Normal:
			continue
		countbycores = int((h.cores - h.usedCores) / cores)
		countbymemory = int((h.memory - h.usedMemory) / memory)
		count += max(0, min(countbycores, countbymemory))

	print "%d" % (count),
	print (lambda:"instances", lambda:"instance")[count == 1](),
	print "with %d" % (cores),
	print (lambda:"cores", lambda:"core")[cores == 1](),
	print "and %d MB memory could be created." % (memory)
	
def createMany(instance, count):
	# will create instances from 0 to count-1
	l = len(str(count - 1))
	basename = instance.name
	instances = []
	for i in range(0, count):
		for nic in instance.nics:
			nic.mac = randomMac()
		instance.name = basename + (("-%" + str(l) + "." + str(l) + "d") % (i))
		instances.append(client.createVm(instance))
	return instances

def shutdownMany(basename):
	return __shutdownOrDestroyMany("shutdown", basename)

def destroyMany(basename):
	return __shutdownOrDestroyMany("destroy", basename)

def __shutdownOrDestroyMany(method, basename):
	instances = client.getInstances()
	count = 0
	for i in instances:
		if (i.name.startswith(basename + "-") and i.name[len(basename)+1].isdigit()):
			if method == "shutdown":
				client.shutdownVm(i.id)

			elif method == "destroy":
				client.destroyVm(i.id)

			else:
				raise ValueError("Unknown method")

			count = count + 1
	if (count == 0):
		raise ValueError("That is an unused basename")
	return None

def getMyInstances():
	userId = getUser()
	_instances = client.getInstances()
	instances = []
	for i in _instances:
		if (i.userId == userId):
			instances.append(i)
	return instances

# Used to define default views on functions and to provide extra functionality (getVmLayout)
extraViews = {
'getSlots': (getSlots, None),
'getImages': (None, ['id', 'imageName', 'imageSize']), 
'copyImage': (None, None), 
'createVm': (None, ['id', 'hostId', 'name', 'user', 'state', 'disk', 'memory', 'cores']),
'createMany': (createMany, ['id', 'hostId', 'name', 'user', 'state', 'disk', 'memory', 'cores']),
'shutdownMany': (shutdownMany, None),
'destroyMany': (destroyMany, None),
'getVmLayout': (getVmLayout, ['id', 'name', 'state', 'instances', 'usedMemory', 'memory', 'usedCores', 'cores']),
'getInstances': (None, ['id', 'hostId', 'name', 'user', 'state', 'disk', 'memory', 'cores']),
'getMyInstances': (getMyInstances, ['id', 'hostId', 'name', 'user', 'state', 'disk', 'memory', 'cores'])
}

# Used to specify what args are excepted for a function, what to use to convert the string to a value, what to use as a default value if it's missing, and whether the argument was required or not
argLists = {
'createVm': [('userId', int, getUser, False), ('name', str, lambda: requiredArg('name'), True), ('cores', int, lambda: 1, False), ('memory', int, lambda: 128, False), ('disks', parseDisks, lambda: requiredArg('disks'), True), ('nics', parseNics, randomNetwork, False), ('hints', parseHints, lambda: {}, False)],
'createMany': [('userId', int, getUser, False), ('basename', str, lambda: requiredArg('basename'), True), ('cores', int, lambda: 1, False), ('memory', int, lambda: 128, False), ('disks', parseDisks, lambda: requiredArg('disks'), True), ('nics', parseNics, randomNetwork, False), ('hints', parseHints, lambda: {}, False), ('count', int, lambda: requiredArg('count'), True)],
'shutdownVm': [('instance', checkIid, lambda: requiredArg('instance'), True)],
'destroyVm': [('instance', checkIid, lambda: requiredArg('instance'), True)],
'shutdownMany': [('basename', str, lambda: requiredArg('basename'), True)],
'destroyMany': [('basename', str, lambda: requiredArg('basename'), True)],
'suspendVm': [('instance', checkIid, lambda: requiredArg('instance'), True)],
'resumeVm': [('instance', checkIid, lambda: requiredArg('instance'), True)],
'migrateVm': [('instance', checkIid, lambda: requiredArg('instance'), True), ('dst', checkHid, lambda: requiredArg('dst'), True)],
'pauseVm': [('instance', checkIid, lambda: requiredArg('instance'), True)],
'unpauseVm': [('instance', checkIid, lambda: requiredArg('instance'), True)],
'getSlots': [('cores', int, lambda: 1, False), ('memory', int, lambda: 128, False)],
'getImages': [],
'copyImage': [('src', str, lambda: requiredArg('src'),True), ('dst', str, lambda: requiredArg('dst'), True)],
'getHosts': [],
'setHostState': [('host', checkHid, lambda: requiredArg('host'), True), ('state', str, lambda: requiredArg('state'), True)],
'getUsers': [],
'getNetworks': [],
'getInstances': [],
'getMyInstances': [],
'getVmLayout': [],
'vmmSpecificCall': [('instance', checkIid, lambda: requiredArg('instance'), True), ('arg', str, lambda: requiredArg('arg'), True)],
'unregisterHost': [('hostId', int, lambda: requiredArg('hostId'), True)],
}

# Used to convert the dictionary built from the arguments into an object that can be used by rpyc
convertArgs = {
'createVm': '[Instance(d={"userId":userId,"name":name,"cores":cores,"memory":memory,"disks":disks,"nics":nics,"hints":hints})]',
'createMany': '[Instance(d={"userId":userId,"name":basename,"cores":cores,"memory":memory,"disks":disks,"nics":nics,"hints":hints}), count]',
'shutdownVm': '[instance]',
'destroyVm': '[instance]',
'shutdownMany': '[basename]',
'destroyMany': '[basename]',
'suspendVm': '[instance]',
'resumeVm': '[instance]',
'migrateVm': '[instance, dst]',
'pauseVm': '[instance]',
'unpauseVm': '[instance]',
'vmmSpecificCall': '[instance, arg]',
'unregisterHost' : '[hostId]',
'getSlots' : '[cores, memory]',
'copyImage' : '[src, dst]',
'setHostState' : '[host, state]',
}

# Descriptions
description = {
'createVm': 'Creates a new VM with a set of properties specified on the command line',
'createMany': 'Utility function that creates many VMs with the same set of parameters',
'shutdownVm': 'Attempts to shutdown a VM nicely',
'destroyVm': 'Immediately destroys a VM -- it is the same as unplugging a physical machine and should be used for non-persistent VMs or when all else fails',
'shutdownMany': 'Attempts to gracefully shut down a group of VMs created with createMany',
'destroyMany': 'Destroys a group of VMs created with createMany',
'suspendVm': 'Suspends a running VM to disk',
'resumeVm': 'Resumes a suspended VM from disk',
'migrateVm': 'Live-migrates a VM to a different host',
'pauseVm': 'Pauses a running VM',
'unpauseVm': 'Unpauses a paused VM',
'getSlots': 'Get a count of how many VMs could be started in the cluster',
'getHosts': 'Gets a list of hosts running Node Managers',
'setHostState': 'Set the state of a host, eg. Normal or Drained',
'getUsers': 'Gets a list of users',
'getNetworks': 'Gets a list of available networks for VMs to be placed on',
'getInstances': 'Gets a list of all VMs in the cluster',
'getMyInstances': 'Utility function that only lists VMs owned by the current user',
'getVmLayout': 'Utility function that displays what VMs are placed on what hosts',
'vmmSpecificCall': 'Direct access to VM manager specific functionality',
'unregisterHost' : 'Unregisters host. Registration happens when starting node manager',
'getImages' : 'Gets a list of available VM images',
'copyImage' : 'Copies a VM image',
}

# Example use strings
examples = {
'createVm': ['--name vmname --disks i386-hardy.qcow2', '--userId 3 --name vmname --cores 8 --memory 7168 --disks mpi-hardy.qcow2:True,scratch.qcow2:False --nics :1.2.3.4,1::52:54:00:00:56:78 --hints enableDisplay=True'],
'createMany': ['--basename vmname --disks i386-hardy.qcow2 --count 4'],
'shutdownVm': ['--instance 12345', '--instance vmname'],
'destroyVm': ['--instance 12345', '--instance vmname'],
'shutdownMany': ['--basename vmname'],
'destroyMany': ['--basename vmname'],
'suspendVm': ['--instance 12345', '--instance vmname'],
'resumeVm': ['--instance 12345', '--instance vmname'],
'migrateVm': ['--instance 12345 --dst vmhost1', '--instance vmname --dst 73'],
'pauseVm': ['--instance 12345', '--instance vmname'],
'unpauseVm': ['--instance 12345', '--instance vmname'],
'getSlots': ['--cores 1 --memory 128'],
'getHosts': [''],
'setHostState': ['--host vmhost1 --state Drained'],
'getUsers': [''],
'getNetworks': [''],
'getInstances': [''],
'getMyInstances': [''],
'getVmLayout': [''],
'getImages': [''],
'copyImage': ['--src src.qcow2 --dst dst.qcow2'],
'vmmSpecificCall': ['--instance 12345 --arg startVnc', '--instance vmname --arg stopVnc'],
'unregisterHost' : ['--hostId 2'],
}

show_hide = []

def usage(func = None):
	"""Print program usage"""
	if (func == None or func not in argLists):
		if (func != None):
			print "Unknown function %s" % (func)
			print
		functions = argLists
		print "%s is the client program for Tashi" % (os.path.basename(sys.argv[0]))
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
	function = matchFunction(sys.argv[1])
	config = Config(["Client"])

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

			if (arg.startswith("--hide-")):
				show_hide.append((False, arg[7:]))
				continue

			if (arg.startswith("--show-")):
				show_hide.append((True, arg[7:]))
				continue

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
		except Exception, e:
			print "Failed in calling %s: %s" % (function, e)
			print "Please run tashi-client --examples for syntax information"
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
		print "TashiException:"
		print e.msg
		exitCode = e.errno
# 	except Exception, e:
# 		print e
		# XXXstroucki: exception may be unrelated to usage of function
		# so don't print usage on exception as if there were a problem
		# with the arguments
		#usage(function)
	sys.exit(exitCode)

if __name__ == "__main__":
	main()
