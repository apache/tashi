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

	remoteCommand("shs", options)
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

	remoteCommand("shn", options)
	return 0

cmdsdesc = (
("setHostState", "Sets host state"),
("setHostNotes", "Annotates a host"),
)

cmds = {
'setHostState': setHostState,
'setHostNotes': setHostNotes,
}

def main():
	if len(sys.argv) < 2:
		print "too few args"
		sys.exit(-1)

	scriptname = sys.argv[0]
	cmd = sys.argv[1]
	args = sys.argv[2:]

	print "scriptname: %s" % (scriptname)
	print "cmd: %s" % (cmd)

	# allow use of lower case for commands
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
