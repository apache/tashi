#! /usr/bin/env python

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

import os
import random
import sys
import types
from tashi.services.ttypes import *
from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.transport.TTransport import TBufferedTransport
from thrift.transport.TSocket import TSocket

from tashi.services import clustermanagerservice
from tashi import vmStates, hostStates, boolean, getConfig, stringPartition

users = {}
machineTypes = {}

def fetchUsers():
	if (users == {}):
		_users = client.getUsers()
		for user in _users:
			users[user.id] = user

def fetchMachineTypes():
	if (machineTypes == {}):
		_machineTypes = client.getMachineTypes()
		for machineType in _machineTypes:
			machineTypes[machineType.id] = machineType

def getUser():
	fetchUsers()
	userStr = os.getenv("USER", "unknown")
	for user in users:
		if (users[user].name == userStr):
			return users[user].id
	raise ValueError("Unknown user %s" % (userStr))

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
			if (instance.userId != userId and instance.userId != None):
				raise ValueError("You don't own that VM")
	return instanceId

def requiredArg(name):
	raise ValueError("Missing required argument %s" % (name))

def randomMac():
	return ("52:54:00:%2.2x:%2.2x:%2.2x" % (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

def randomNetwork():
	return [NetworkConfiguration(d={'mac':randomMac(), 'network':1})]

def parseDisks(arg):
	try:
		strDisks = arg.split(",")
		disks = []
		for strDisk in strDisks:
			strDisk = strDisk.strip()
			(l, s, r) = stringPartition(strDisk, ":")
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
			(l, s, r) = stringPartition(strNic, ":")
			l = int(l)
			nic = NetworkConfiguration(d={'mac':r, 'network':l})
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
			(l, s, r) = stringPartition(strHint, "=")
			hints[l] = r
		return hints
	except:
		raise ValueError("Incorrect format for hints argument")

def getVmLayout():
	fetchMachineTypes()
	_hosts = client.getHosts()
	_instances = client.getInstances()
	hosts = {}
	for h in _hosts:
		h.instances = []
		h.usedMemory = 0
		h.usedCores = 0
		hosts[h.id] = h
	for i in _instances:
		hosts[i.hostId].instances.append(i.id)
		hosts[i.hostId].usedMemory += machineTypes[i.type].memory
		hosts[i.hostId].usedCores += machineTypes[i.type].cores
	return hosts.values()

def createMany(instance, count):
	l = len(str(count))
	basename = instance.name
	instances = []
	for i in range(0, count):
		for nic in instance.nics:
			nic.mac = randomMac()
		instance.name = basename + (("-%" + str(l) + "." + str(l) + "d") % (i))
		instances.append(client.createVm(instance))
	return instances

def destroyMany(basename):
	instances = client.getInstances()
	count = 0
	for i in instances:
		if (i.name.startswith(basename + "-") and i.name[len(basename)+1].isdigit()):
			client.destroyVm(i.id)
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
'createMany': (createMany, ['id', 'hostId', 'name', 'user', 'state', 'disk', 'memory', 'cores']),
'destroyMany': (destroyMany, None),
'getVmLayout': (getVmLayout, ['id', 'name', 'state', 'instances', 'usedMemory', 'memory', 'usedCores', 'cores']),
'getInstances': (None, ['id', 'hostId', 'name', 'user', 'state', 'disk', 'memory', 'cores']),
'getMyInstances': (getMyInstances, ['id', 'hostId', 'name', 'user', 'state', 'disk', 'memory', 'cores'])
}

# Used to specify what args are excepted for a function, what to use to convert the string to a value, what to use as a default value if it's missing, and whether the argument was required or not
argLists = {
'createVm': [('userId', int, getUser, False), ('name', str, lambda: requiredArg('name'), True), ('type', int, lambda: 1, False), ('disks', parseDisks, lambda: requiredArg('disks'), True), ('nics', parseNics, randomNetwork, False), ('hints', parseHints, lambda: {}, False)],
'createMany': [('userId', int, getUser, False), ('basename', str, lambda: requiredArg('basename'), True), ('type', int, lambda: 1, False), ('disks', parseDisks, lambda: requiredArg('disks'), True), ('nics', parseNics, randomNetwork, False), ('hints', parseHints, lambda: {}, False), ('count', int, lambda: requiredArg('count'), True)],
'shutdownVm': [('instance', checkIid, lambda: requiredArg('instance'), True)],
'destroyVm': [('instance', checkIid, lambda: requiredArg('instance'), True)],
'destroyMany': [('basename', str, lambda: requiredArg('basename'), True)],
'suspendVm': [('instance', checkIid, lambda: requiredArg('instance'), True), ('destination', str, lambda: requiredArg('destination'), True)],
'resumeVm': [('userId', int, getUser, False), ('name', str, lambda: requiredArg('name'), True), ('type', int, lambda: 1, False), ('disks', parseDisks, lambda: requiredArg('disks'), True), ('nics', parseNics, randomNetwork, False), ('hints', parseHints, lambda: {}, False), ('source', str, lambda: requiredArg('source'), True)],
'migrateVm': [('instance', checkIid, lambda: requiredArg('instance'), True), ('targetHostId', int, lambda: requiredArg('targetHostId'), True)],
'pauseVm': [('instance', checkIid, lambda: requiredArg('instance'), True)],
'unpauseVm': [('instance', checkIid, lambda: requiredArg('instance'), True)],
'getMachineTypes': [],
'getHosts': [],
'getUsers': [],
'getInstances': [],
'getMyInstances': [],
'getVmLayout': [],
'vmmSpecificCall': [('instance', checkIid, lambda: requiredArg('instance'), True), ('arg', str, lambda: requiredArg('arg'), True)],
}

# Used to convert the dictionary built from the arguments into an object that can be used by thrift
convertArgs = {
'createVm': '[Instance(d={"userId":userId,"name":name,"type":type,"disks":disks,"nics":nics,"hints":hints})]',
'createMany': '[Instance(d={"userId":userId,"name":basename,"type":type,"disks":disks,"nics":nics,"hints":hints}), count]',
'shutdownVm': '[instance]',
'destroyVm': '[instance]',
'destroyMany': '[basename]',
'suspendVm': '[instance, destination]',
'resumeVm': '[Instance(d={"userId":userId,"name":name,"type":type,"disks":disks,"nics":nics,"hints":hints}), source]',
'migrateVm': '[instance, targetHostId]',
'pauseVm': '[instance]',
'unpauseVm': '[instance]',
'vmmSpecificCall': '[instance, arg]',
}

# Example use strings
examples = {
'createVm': ['--name foobar --disks i386-hardy.qcow2', '--userId 3 --name foobar --type 9 --disks mpi-hardy.qcow2:True,scratch.qcow2:False --nics 2:52:54:00:00:12:34,1:52:54:00:00:56:78 --hints enableDisplay=True'],
'createMany': ['--basename foobar --disks i386-hardy.qcow2 --count 4'],
'shutdownVm': ['--instance 12345', '--instance foobar'],
'destroyVm': ['--instance 12345', '--instance foobar'],
'destroyMany': ['--basename foobar'],
'suspendVm': ['--instance 12345 --destination imgfile', '--instance foobar --destination imgfile'],
'resumeVm': ['--name foobar --disks i386-hardy.qcow2 --nics 2:52:54:00:7a:8c:9d --source foobar'],
'migrateVm': ['--instanc 12345 --targetHostId 73', '--instance foobar --targetHostId 73'],
'pauseVm': ['--instance 12345', '--instance foobar'],
'unpauseVm': ['---instance 12345', '--instance foobar'],
'getMachineTypes': [''],
'getHosts': [''],
'getUsers': [''],
'getInstances': [''],
'getMyInstances': [''],
'getVmLayout': [''],
'vmmSpecificCall': ['--instance 12345 --arg startVnc', '--instance foobar --arg stopVnc']
}

show_hide = []

def usage(f = None):
	"""Print program usage"""
	print "Usage:"
	if (f == None):
		functions = argLists
	else:
		functions = {f: argLists[f]}
	for f in functions:
		args = argLists[f]
		line = "\t" + f
		for arg in args:
			if (arg[3]):
				line += " --%s <value>" % (arg[0])
			else:
				line += " [--%s <value>]" % (arg[0])
		print line
		if ("--examples" in sys.argv):
			print
			for example in examples.get(f, []):
				print "\t\t" + f + " " + example
			print
	print "Additionally, all functions accept --show-<name> and --hide-<name>, which show and hide columns during table generation"
	print "Use \"--examples\" to see examples of all the functions"
	sys.exit(-1)

def transformState(obj):
	if (type(obj) == Instance):
		fetchUsers()
		fetchMachineTypes()
		obj.state = vmStates[obj.state]
		if (obj.userId in users):
			obj.user = users[obj.userId].name
		else:
			obj.user = None
		obj.disk = obj.disks[0].uri
		if (obj.disks[0].persistent):
			obj.disk += ":True"
		obj.memory = machineTypes[obj.type].memory
		obj.cores = machineTypes[obj.type].cores
	elif (type(obj) == Host):
		obj.state = hostStates[obj.state]

def genKeys(list):
	keys = {}
	for row in list:
		for item in row.__dict__.keys():
			keys[item] = item
	if ('id' in keys):
		del keys['id']
		keys = ['id'] + keys.values()
	else:
		keys = keys.values()
	return keys

def makeTable(list, keys=None):
	for obj in list:
		transformState(obj)
	if (keys == None):
		keys = genKeys(list)
	for (show, k) in show_hide:
		if (show):
			if (k != "all"):
				keys.append(k)
			else:
				keys = genKeys(list)
		else:
			if (k in keys):
				keys.remove(k)
			if (k == "all"):
				keys = []
	maxWidth = {}
	for k in keys:
		maxWidth[k] = len(k)
	for row in list:
		for k in keys:
			if (k in row.__dict__):
				maxWidth[k] = max(maxWidth[k], len(str(row.__dict__[k])))
	if (keys == []):
		return
	line = ""
	for k in keys:
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
	list.sort(cmp=sortFunction)
	for row in list:
		line = ""
		for k in keys:
			row.__dict__[k] = row.__dict__.get(k, "")
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

def main():
	"""Main function for the client program"""
	global INDENT, exitCode, client
	exitCode = 0
	INDENT = (os.getenv("INDENT", 4))
	if (len(sys.argv) < 2):
		usage()
	function = sys.argv[1]
	(config,configFiles) = getConfig(["Client"])
	cfgHost = config.get('Client', 'clusterManagerHost')
	cfgPort = config.get('Client', 'clusterManagerPort')
	cfgTimeout = float(config.get('Client', 'clusterManagerTimeout'))
	host = os.getenv('TASHI_CM_HOST', cfgHost)
	port = os.getenv('TASHI_CM_PORT', cfgPort)
	timeout = float(os.getenv('TASHI_CM_TIMEOUT', cfgTimeout)) * 1000.0
	socket = TSocket(host, int(port))
	socket.setTimeout(timeout)
	transport = TBufferedTransport(socket)
	protocol = TBinaryProtocol(transport)
	client = clustermanagerservice.Client(protocol)
	client._transport = transport
	client._transport.open()
	try:
		try:
			if (function not in argLists):
				usage()
			possibleArgs = argLists[function]
			args = sys.argv[2:]
			vals = {}
			for arg in args:
				if (arg == "--help" or arg == "--examples"):
					usage(function)
			for parg in possibleArgs:
				(parg, conv, default, required) = parg
				val = None
				for i in range(0, len(args)):
					arg = args[i]
					if (arg.startswith("--") and arg[2:] == parg):
						val = conv(args[i+1])
				if (val == None):
					val = default()
				vals[parg] = val
			for arg in args:
				if (arg.startswith("--hide-")):
					show_hide.append((False, arg[7:]))
				if (arg.startswith("--show-")):
					show_hide.append((True, arg[7:]))
			f = getattr(client, function, None)
			if (f is None):
				f = extraViews[function][0]
			if (function in convertArgs):
				fargs = eval(convertArgs[function], globals(), vals)
			else:
				fargs = []
			res = f(*fargs)
			if (res != None):
				keys = extraViews.get(function, (None, None))[1]
				try:
					if (type(res) == types.ListType):
						makeTable(res, keys)
					else:
						pprint(res)
				except Exception, e:
					print e
		except TashiException, e:
			print "TashiException:"
			print e.msg
			exitCode = e.errno
		except Exception, e:
			print e
			usage(function)
	finally:
		client._transport.close()
	sys.exit(exitCode)

if __name__ == "__main__":
	main()
