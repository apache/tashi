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
import sys
import string
import re
try:   
	import MySQLdb
	import traceback
	import optparse
	import getpass
except ImportError, e:
	print "Module not installed : %s" % e
	exit()

import MySQLdb
import traceback
import optparse
import getpass

a = os.path.join("../")
sys.path.append(a)
a = os.path.join("../../")
sys.path.append(a)
a = os.path.join("../../..")
sys.path.append(a)
a = os.path.join("../../../..")
sys.path.append(a)

from zoni.version import *
from zoni.extra.util import *

def main():
	''' This file extends the database for Zoni '''

	ver = version.split(" ")[0]
	rev = revision

	parser = optparse.OptionParser(usage="%prog -u username ", version="%prog " + ver + " " + rev)
	parser.add_option("-u", "--userName", "--username", dest="userName", help="Mysql username")
	parser.add_option("-p", "--password", dest="password", help="Admin mysql password")
	(options, args) = parser.parse_args()

#	if not options.userName:
#		parser.print_help()
#		exit(1)

#	password = options.password
#	if not options.password:
#		password = getpass.getpass()

	(configs, configFiles) = getConfig()

#	extendZoniDb(configs, options.userName, password)
	extendZoniDb(configs)
	entryExists(configs)

#def extendZoniDb(config, adminUser, adminPassword):
def extendZoniDb(config):
	config = config
	host = config['dbHost']
	user = config['dbUser']
#	adminUser = adminUser
#	adminPassword = adminPassword
	passwd = config['dbPassword']
	db = config['dbInst']

	if config['dbPort'] == "":
		config['dbPort'] = 3306

	port = config['dbPort']

	conn = connectDb(host, port, user, passwd, db)
	extendTables(conn)
	conn.commit()
	conn.close()
	sys.stdout.write("Finished\n")

def connectDb (host, port, user, passwd, db=None):
	#  Connect to DB
	try:
		if db:
			conn = MySQLdb.connect(host = host, port = port, user = user , passwd = passwd, db = db)
		else:
			conn = MySQLdb.connect(host = host, port = port, user = user , passwd = passwd)

	except MySQLdb.OperationalError, e:
		if e[0] == 2005:
			print "ERROR :" + str(e[1])
			exit(1)
		else:
			print "Connection Error : ", e
			exit(1)
	return conn

def extendTables(conn):
	sys.stdout.write("    Extend Zoni Database Schema...\n")
	'''  Create Tables  '''
	#  Add a new field to hardwareinfo 
	sys.stdout.write("    Adding new field to hardwareinfo...")
	execQuery(conn, "ALTER TABLE `hardwareinfo` ADD `hw_blenc` TEXT NULL DEFAULT NULL AFTER `hw_password`")
	sys.stdout.write("Success\n")

	#  Create rolemap
	sys.stdout.write("    Creating rolemap...")
	execQuery(conn, "CREATE TABLE IF NOT EXISTS `rolemap` ( `sys_id` int(11) unsigned NOT NULL, `image_id` int(11) unsigned NOT NULL )") 
	sys.stdout.write("Success\n")

def execQuery(conn, query):
	cursor = conn.cursor()
	try:
		cursor.execute (query)
		conn.commit()
	except MySQLdb.OperationalError, e:
		sys.stdout.write("Fail\n")
		msg = "ERROR: " + e[1]
		sys.stderr.write(msg)
		exit()
	return cursor

def entryExists(config):
	config = config
	host = config['dbHost']
	user = config['dbUser']
	passwd = config['dbPassword']
	db = config['dbInst']

	if config['dbPort'] == "":
		config['dbPort'] = 3306

	port = config['dbPort']

	conn = connectDb(host, port, user, passwd, db)

	sys.stdout.write("    Checking if hardwareinfo's hw_notes is populated...\n\n")
	query = "select hw_notes from hardwareinfo where hw_notes is not NULL"
 	r = execQuery(conn, query)
	res = r.fetchall()
	if len(res) > 0:
		sys.stdout.write("    Found %d record(s) in hw_notes...\n" % len(res))
		for i in range(len(res)):
			print "    %(#)05d\t%(theres)s" % { "#":i+1, "theres":res[i][0] }
		sys.stdout.write("\n    Please review if the record(s) refer(s) to blade enclosure info. Do you want sync to hw_blenc?\n")
		ans = raw_input("    Yes? (Any other responce will cancel the sync) ")
		if re.match(r"[Yy][Ee][Ss]",ans) or re.match(r"[Yy]",ans):
			sys.stdout.write("\n    I am syncing now...\n")
			query = "UPDATE hardwareinfo set hw_blenc = hw_notes"
			r = execQuery(conn, query)
			for repl in res:
				query="update hardwareinfo set hw_notes = NULL where hw_notes = \"" + repl[0] + "\""
				execQuery(conn, query)
			sys.stdout.write("    Sync and Update Success\n\n")
		else:
			sys.stdout.write("\n    Not syncing...\n\n")
	return 0


if __name__ == "__main__":
    main()

