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

import inspect
import os
import sys
import types
from tashi.services.ttypes import *
from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.transport.TTransport import TBufferedTransport
from thrift.transport.TSocket import TSocket

from tashi.services import clustermanagerservice
from tashi import vmStates

def makeHTMLTable(list):
	(stdin_r, stdin_w) = os.pipe()
	pipe = os.popen("tput cols")
	columns = pipe.read().strip()
	keys = {}
	for k in list:
		for k2 in k.__dict__.keys():
			if (not k2.endswith("Obj")):
				keys[k2] = k2
	if ('id' in keys):
		del keys['id']
		keylist = ['id'] + keys.keys()
	else:
		keylist = keys.keys()
	output = "<html>"
	output = output + "<table>"
	output = output + "<tr>"
	for k in keylist:
		output = output + "<td>%s</td>" % (k)
	output = output + "</tr>"
	for k in list:
		output = output + "<tr>"
		for k2 in keylist:
			if (k2 == "state"):
				output = output + "<td>%s</td>" % (str(vmStates[k.__dict__.get(k2, None)]))
			else:
				output = output + "<td>%s</td>" % (str(k.__dict__.get(k2, None)))
		output = output + "</tr>"
	output = output + "</table>"
	output = output + "</html>"
	pid = os.fork()
	if (pid == 0):
		os.close(stdin_w)
		os.dup2(stdin_r, 0)
		os.close(stdin_r)
		os.execl("/usr/bin/lynx", "/usr/bin/lynx", "-width=%s" % (columns), "-dump", "-stdin")
		sys.exit(-1)
	os.close(stdin_r)
	os.write(stdin_w, output)
	os.close(stdin_w)
	os.waitpid(pid, 0)

def getFunction(argv):
	"""Tries to determine the name of the function requested by the user -- may be called multiple times if the binary name is 'client'"""
	function = "None"
	if (len(argv) > 0):
		function = argv[0].strip()
		if (function.rfind("/") != -1):
			function = function[function.rfind("/")+1:]
		if (function.rfind(".") != -1):
			function = function[:function.rfind(".")]
	return function

def getFunctionInfo(m):
	"""Gets a string that describes a function from the interface"""
	f = getattr(clustermanagerservice.Iface, m)
	argspec = inspect.getargspec(f)[0][1:]
	return m + inspect.formatargspec(argspec)

def usage():
	"""Print program usage"""
	print "Available methods:"
	for m in methods:
		print "\t" + getFunctionInfo(m)
	print
	print "Examples:"
	print "\tgetInstances"
	print "\taddUser 'User(d={\"username\":\"foobar\"})'"
	print "\tremoveUser 2"
	print "\tcreateVM 1 1"

def simpleType(obj):
	"""Determines whether an object is a simple type -- used as a helper function to pprint"""
	if (type(obj) is not type([])):
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
	if (type(obj) is type([])):
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
	global INDENT, methods, exitCode
	exitCode = 0
	INDENT = (os.getenv("INDENT", 4))
	methods = filter(lambda x: not x.startswith("__"), clustermanagerservice.Iface.__dict__.keys())
	function = getFunction(sys.argv)
	if (function == "client"):
		function = getFunction(sys.argv[1:])
	if (function == "--makesyms"):
		for m in methods:
			os.symlink(sys.argv[0], m)
		sys.exit(0)
	if (function == "--rmsyms"):
		for m in methods:
			os.unlink(m)
		sys.exit(0)
	host = os.getenv('TASHI_CM_HOST', 'localhost')
	port = os.getenv('TASHI_CM_PORT', '9882')
	timeout = float(os.getenv('TASHI_CM_TIMEOUT', '5000.0'))
	socket = TSocket(host, int(port))
	socket.setTimeout(timeout)
	transport = TBufferedTransport(socket)
	protocol = TBinaryProtocol(transport)
	client = clustermanagerservice.Client(protocol)
	client._transport = transport
	client._transport.open()
	f = getattr(client, function, None)
	if not f:
		usage()
		sys.exit(-1)
	args = map(lambda x: eval(x), sys.argv[1:])
	try:
		res = f(*args)
		def cmp(x, y):
			try:
				if (x.id < y.id):
					return -1
				elif (y.id < x.id):
					return 1
				else:
					return 0
			except Exception, e:
				return 0
		if (type(res) == types.ListType):
			res.sort(cmp)
		if (os.getenv("USE_HTML_TABLES")):
			try:
				makeHTMLTable(res)
			except:
				pprint(res)
		else:
			pprint(res)
	except TashiException, e:
		print e.msg
		exitCode = e.errno
	except TypeError, e:
		print e
		print "\t" + getFunctionInfo(function)
		exitCode = -1
	finally:
		client._transport.close()
	sys.exit(exitCode)

if __name__ == "__main__":
	main()
