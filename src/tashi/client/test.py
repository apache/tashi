#!/usr/bin/python

import optparse
import sys

def setHostState(args):
	parser = optparse.OptionParser()
	parser.add_option("--host")
	return 0

def setHostNotes(args):
	parser = optparse.OptionParser()
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
