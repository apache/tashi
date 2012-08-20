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

import optparse
import sys
import tashi
from tashi.utils.config import Config
from tashi.rpycservices.rpyctypes import TashiException

def checkHid(host):
	#userId = getUser()
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
	parser.add_option("--notes", help="Annotate the host with this note, e.g. 'Check fan' (mandatory)", action="store", type="string", dest="notes")
	(options, arguments) = parser.parse_args(args)
	if options.hostname is None or options.notes is None:
		print "A mandatory option is missing\n"
		parser.print_help()
		sys.exit(-1)

	hostId = checkHid(options.hostname)
	rv = remoteCommand("setHostNotes", hostId, options.notes)
	print rv
	return 0

def addHost(args):
	global scriptname
	parser = optparse.OptionParser()
	parser.set_usage("%s addHost [options]" % scriptname)
	parser.add_option("--host", help="Add this host to the cluster (mandatory)", action="store", type="string", dest="hostname")
	(options, arguments) = parser.parse_args(args)
	if options.hostname is None:
		print "A mandatory option is missing\n"
		parser.print_help()
		sys.exit(-1)

	# let the NM on the new host fill this in on its regular checkins
	memory = 0
	cores = 0
	version = "new"

	rv = remoteCommand("registerHost", options.hostname, memory, cores, version)
	print rv
	return 0

def delHost(args):
	global scriptname
	parser = optparse.OptionParser()
	parser.set_usage("%s delHost [options]" % scriptname)
	parser.add_option("--host", help="Remove this host from the cluster (mandatory)", action="store", type="string", dest="hostname")
	(options, arguments) = parser.parse_args(args)
	if options.hostname is None:
		print "A mandatory option is missing\n"
		parser.print_help()
		sys.exit(-1)

	hostId = checkHid(options.hostname)
	rv = remoteCommand("unregisterHost", hostId)
	print rv
	return 0

def addReservation(args):
	global scriptname
	parser = optparse.OptionParser()
	parser.set_usage("%s addReservation [options]" % scriptname)
	parser.add_option("--host", help="Add a reservation to this host (mandatory)", action="store", type="string", dest="hostname")
	parser.add_option("--user", help="Add this user to the host reservation (mandatory)", action="store", type="string", dest="username")
	(options, arguments) = parser.parse_args(args)
	if options.hostname is None or options.username is None:
		print "A mandatory option is missing\n"
		parser.print_help()
		sys.exit(-1)

	hostId = checkHid(options.hostname)
	rv = remoteCommand("addReservation", hostId, options.username)
	print rv
	return 0

def delReservation(args):
	global scriptname
	parser = optparse.OptionParser()
	parser.set_usage("%s addReservation [options]" % scriptname)
	parser.add_option("--host", help="Add a reservation to this host (mandatory)", action="store", type="string", dest="hostname")
	parser.add_option("--user", help="Remove this user from the host reservation (mandatory)", action="store", type="string", dest="username")
	(options, arguments) = parser.parse_args(args)
	if options.hostname is None or options.username is None:
		print "A mandatory option is missing\n"
		parser.print_help()
		sys.exit(-1)

	hostId = checkHid(options.hostname)
	rv = remoteCommand("delReservation", hostId, options.username)
	print rv
	return 0

def getReservation(args):
	global scriptname
	parser = optparse.OptionParser()
	parser.set_usage("%s getReservation [options]" % scriptname)
	parser.add_option("--host", help="Show reservations on this host (mandatory)", action="store", type="string", dest="hostname")
	(options, arguments) = parser.parse_args(args)
	if options.hostname is None:
		print "A mandatory option is missing\n"
		parser.print_help()
		sys.exit(-1)

	hostId = checkHid(options.hostname)
	rv = remoteCommand("getReservation", hostId)
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
('addReservation', 'Add a user to a host reservation'),
('delReservation', 'Remove a user from a host reservation'),
('getReservation', 'Retrieve host reservations'),
('addUser', 'Adds a user to Tashi'),
('delUser', 'Removes a user from Tashi'),
('addNet', 'Adds a network to Tashi'),
('delNet', 'Removes a network from Tashi'),
('setHostState', 'Set the state of a host, eg. Normal or Drained'),
('setHostNotes', 'Annotate a host record'),
)
"""

cmdsdesc = (
("setHostState", "Sets host state"),
("setHostNotes", "Annotates a host"),
("addHost", "Add a host to the cluster"),
("delHost", "Remove a host from the cluster"),
('addReservation', 'Add a user to a host reservation'),
('delReservation', 'Remove a user from a host reservation'),
('getReservation', 'Retrieve host reservations'),
("help", "Get list of available commands"),
)

cmds = {
'setHostState': setHostState,
'setHostNotes': setHostNotes,
'addHost': addHost,
'delHost': delHost,
'addReservation': addReservation,
'delReservation': delReservation,
'getReservation': getReservation,
'help': help,
}

def main():
	global config, client, scriptname

	config = Config(["Client"])
	client = tashi.createClient(config)
	scriptname = sys.argv[0]

	if len(sys.argv) < 2:
		print "Syntax: %s <command>" % scriptname
		help(None)
		sys.exit(-1)

	cmd = sys.argv[1]
	args = sys.argv[2:]

	# flatten case for commands
	lccmddict = dict((foo.lower(), foo) for foo in cmds.keys())

	cmdlower = cmd.lower()
	if cmdlower not in lccmddict:
		print "not a valid command"
		sys.exit(-1)

	handler = cmds[lccmddict[cmdlower]]

	rv = handler(args)
	return rv


if __name__ == "__main__":
	rv = main()
	sys.exit(rv)
