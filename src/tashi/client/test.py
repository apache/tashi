#!/usr/bin/python

import optparse
import sys

def remoteCommand(command, options):
	print "Doing command %s options %s" % (command, options)
	return 0

def setHostState(args):
	parser = optparse.OptionParser()
	parser.set_usage("%s setHostState [options]" % sys.argv[0])
	parser.add_option("--host", help="Set the state of this host", action="store", type="string", dest="hostname")
	parser.add_option("--state", help="Change state to this value", action="store", type="string", dest="state")
	(options, arguments) = parser.parse_args(args)
	print options
	print arguments
	if options.hostname is None or options.state is None:
		print "A mandatory option is missing\n"
		parser.print_help()
		sys.exit(-1)

	rv = remoteCommand("shs", options)
	return 0

def setHostNotes(args):
	parser = optparse.OptionParser()
	parser.set_usage("%s setHostNotes [options]" % sys.argv[0])
	parser.add_option("--host", help="Annotate this host with the note (mandatory)", action="store", type="string", dest="hostname")
	parser.add_option("--notes", help="Annotate the host with this note (mandatory)", action="store", type="string", dest="notes")
	(options, arguments) = parser.parse_args(args)
	print options
	print arguments
	if options.hostname is None or options.notes is None:
		print "A mandatory option is missing\n"
		parser.print_help()
		sys.exit(-1)

	rv = remoteCommand("shn", options)
	return 0

def help(args):
	print "Available commands:"
	for (command, desc) in cmdsdesc:
		print "%s\t\t%s" % (command, desc)
	print "See %s <command> -h for help on these commands." % sys.argv[0] 
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
"""

cmdsdesc = (
("setHostState", "Sets host state"),
("setHostNotes", "Annotates a host"),
("help", "Get list of available commands"),
)

cmds = {
'setHostState': setHostState,
'setHostNotes': setHostNotes,
'help': help,
}

def main():
	scriptname = sys.argv[0]

	if len(sys.argv) < 2:
		print "Syntax: %s <command>" % scriptname
		help(None)
		sys.exit(-1)

	cmd = sys.argv[1]
	args = sys.argv[2:]

	print "scriptname: %s" % (scriptname)
	print "cmd: %s" % (cmd)

	# flatten case for commands
	lccmddict = dict((foo.lower(), foo) for foo in cmds.keys())

	if cmd.lower() not in lccmddict:
		print "not a valid command"
		sys.exit(-1)

	handler = cmds[lccmddict[cmd]]

	rv = handler(args)
	return rv


if __name__ == "__main__":
	rv = main()
	sys.exit(rv)
