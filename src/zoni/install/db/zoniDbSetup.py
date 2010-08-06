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
#
#  $Id$
#

import os 
import sys
import string
import MySQLdb
import traceback
import optparse

from zoni.extra.util import *
from zoni.version import *

def main():
	''' This file sets up the database for Zoni '''

	ver = version.split(" ")[0]
	rev = revision


	parser = optparse.OptionParser(usage="%prog -u username -p password  ", version="%prog " + ver + " " + rev)
	parser.add_option("-u", "--userName", "--username", dest="userName", help="Mysql username")
	parser.add_option("-p", "--password", dest="password", help="Admin mysql password")
	#parser.add_option("-v", "--verbose", dest="verbosity", help="Be verbose", action="store_true", default=False)
	(options, args) = parser.parse_args()

	if not options.userName or not options.password:
		parser.print_help()
		exit(1)


	configFile = getConfig()

	CreateZoniDb(configFile, options.userName, options.password)


def CreateZoniDb(config, adminUser, adminPassword):
	config = config
	host = config['dbHost']
	user = config['dbUser']
	adminUser = adminUser
	adminPassword = adminPassword
	passwd = config['dbPassword']
	#db = "`" + config['dbInst'] + "`"
	db = config['dbInst']

	if config['dbPort'] == "":
		config['dbPort'] = 3306

	port = config['dbPort']

	conn = connectDb(host, port, adminUser, adminPassword)
	createDatabase(conn, adminUser, adminPassword, db)
	setPriviledges(conn, user, passwd, db)
	conn.close()
	conn = connectDb(host, port, adminUser, adminPassword, db)
	createTables(conn)
	createRegistration(conn, config)
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


def createDatabase (conn, user, passwd, db):
	sys.stdout.write("Creating database...")
	cmd = "create database if not exists " + db + ";"
	execQuery(conn, cmd)
	sys.stdout.write("Success\n")


def setPriviledges(conn, user, passwd, db):
	sys.stdout.write("Setting user priviledges...")
	cmd = "grant select, insert, update, delete on " + db + ".* to " + user + "@\'%\' identified by \'" + passwd + "\';"
	execQuery(conn, cmd)
	sys.stdout.write("Success\n")



def createTables(conn):
	sys.stdout.write("Create Zoni Database Schema...\n")
	'''  Create Tables  '''
	#  Create sysinfo 
	sys.stdout.write("    Creating sysinfo...")
	execQuery(conn, "CREATE TABLE IF NOT EXISTS `sysinfo` (`sys_id` int(8) NOT NULL auto_increment, `mac_addr` char(64) NOT NULL, `num_procs` int(10) unsigned default NULL, `num_cores` int(10) unsigned default NULL, `mem_sticks` int(10) unsigned default NULL, `mem_slots` int(10) unsigned default NULL, `mem_total` int(10) unsigned default NULL, `mem_limit` int(10) unsigned default NULL, `clock_speed` int(10) unsigned default NULL, `sys_vendor` text, `sys_model` text, `proc_vendor` char(64) default NULL, `proc_model` char(128) default NULL, `proc_cache` char(32) default NULL, `service_tag` char(64) default NULL, `express_service_code` char(64) default NULL, `cpu_flags` text, `location` text, `bios_rev` char(32) default NULL, `ip_addr` varchar(64) NOT NULL, `init_checkin` timestamp NOT NULL default CURRENT_TIMESTAMP, PRIMARY KEY  (`sys_id`))")
	sys.stdout.write("Success\n")

	#  Create hardwareinfo
	sys.stdout.write("    Creating hardwareinfo...")
	execQuery(conn, "CREATE TABLE IF NOT EXISTS `hardwareinfo` ( `hw_id` int(8) NOT NULL auto_increment, `hw_type` varchar(64) NOT NULL, `hw_mac` varchar(64) default NULL, `hw_name` varchar(256) NOT NULL, `hw_make` varchar(64) NOT NULL, `hw_model` varchar(64) NOT NULL, `hw_ipaddr` varchar(64) NOT NULL, `hw_userid` varchar(64) default NULL, `hw_password` varchar(64) default NULL, `hw_notes` longtext NOT NULL, PRIMARY KEY  (`hw_id`))") 
	sys.stdout.write("Success\n")
 	#  Create allocationinfo
	sys.stdout.write("    Creating allocationinfo...")
	execQuery(conn, "CREATE TABLE IF NOT EXISTS `allocationinfo` ( `allocation_id` int(8) NOT NULL auto_increment, `node_id` int(8) NOT NULL, `reservation_id` int(8) NOT NULL, `ip_addr` varchar(64) NOT NULL, `hostname` varchar(64) default NULL, `vlan_id` int(11) NOT NULL, `notes` tinytext, PRIMARY KEY  (`allocation_id`))")
	sys.stdout.write("Success\n")
	#  Create imageinfo
	sys.stdout.write("    Creating imageinfo...")
	execQuery(conn, "CREATE TABLE IF NOT EXISTS `imageinfo` ( `image_id` int(11) unsigned NOT NULL auto_increment, `image_name` varchar(256) NOT NULL, `dist` varchar(128) NOT NULL, `dist_ver` varchar(128) NOT NULL, `kernel_id` int(11), `initrd_id` int(11), PRIMARY KEY  (`image_id`))")
	sys.stdout.write("Success\n")
	#  Create imagemap
	sys.stdout.write("    Creating imagemap...")
	execQuery(conn, "CREATE TABLE IF NOT EXISTS `imagemap` ( `mac_addr` char(64) NOT NULL, `image_id` int(11) NOT NULL, PRIMARY KEY  (`mac_addr`))")
	sys.stdout.write("Success\n")
	#  Create reservationinfo
	sys.stdout.write("    Creating reservationinfo...")
	execQuery(conn, "CREATE TABLE IF NOT EXISTS `reservationinfo` ( `reservation_id` int(8) NOT NULL auto_increment, `user_id` int(8) NOT NULL, `reservation_date` timestamp NOT NULL default CURRENT_TIMESTAMP, `reservation_expiration` datetime NOT NULL, `notes` tinytext, PRIMARY KEY  (`reservation_id`))")
	sys.stdout.write("Success\n")
	#  Create portmap 
	sys.stdout.write("    Creating portmap...")
	execQuery(conn, "CREATE TABLE IF NOT EXISTS `portmap` ( `port_id` int(8) NOT NULL auto_increment, `hw_id` int(8) NOT NULL, `node_id` int(8) NOT NULL, `port_num` int(8) NOT NULL, PRIMARY KEY  (`port_id`))")
	sys.stdout.write("Success\n")
	#  Create vlaninfo
	sys.stdout.write("    Creating vlaninfo...")
	execQuery(conn, "CREATE TABLE IF NOT EXISTS `vlaninfo` ( `vlan_id` int(11) NOT NULL auto_increment, `vlan_num` int(11) NOT NULL, `ip_network` varchar(64) NOT NULL, `domain` varchar(64) NOT NULL, PRIMARY KEY  (`vlan_id`))")
	sys.stdout.write("Success\n")
	#  Create allocationarchive
	sys.stdout.write("    Creating allocationarchive...")
	execQuery(conn, "CREATE TABLE IF NOT EXISTS `allocationarchive` ( `ar_id` smallint(8) NOT NULL auto_increment, `node_id` int(8) NOT NULL, `ip_addr` varchar(64) NOT NULL, `hostname` varchar(64) NOT NULL, `vlan_id` int(11) NOT NULL, `user_id` int(8) NOT NULL, `cur_time` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP, `reservation_type` varchar(64) NOT NULL, `notes` tinytext, PRIMARY KEY  (`ar_id`))")
	sys.stdout.write("Success\n")
	#  Create kernelinfo 
	sys.stdout.write("    Creating kernelinfo...")
	execQuery(conn, "CREATE TABLE IF NOT EXISTS `kernelinfo` ( `kernel_id` int(11) unsigned NOT NULL auto_increment, `kernel_name` varchar(256) NOT NULL, `kernel_release` varchar(128) NOT NULL, `kernel_arch` varchar(128) NOT NULL, PRIMARY KEY  (`kernel_id`))")
	sys.stdout.write("Success\n")
	#  Create initrdinfo
	sys.stdout.write("    Creating initrdinfo...")
	execQuery(conn, "CREATE TABLE IF NOT EXISTS `initrdinfo` ( `initrd_id` int(11) unsigned NOT NULL auto_increment, `initrd_name` varchar(256) NOT NULL, `initrd_arch` varchar(128) NOT NULL, `initrd_options` varchar(1024) NOT NULL, PRIMARY KEY  (`initrd_id`))")
	sys.stdout.write("Success\n")

def createRegistration(conn, config):

	sys.stdout.write("Inserting initial Registration info into DB...\n")

	#  Check if already there...
	checkVal =  entryExists(conn, "kernelinfo", "kernel_name", "linux-2.6.24-19-server")
	if checkVal:
		sys.stdout.write("    Kernel already exists in DB...\n")
		#  Get the kernel_id
		kernelId = str(checkVal[1][0][0])
	else:
		r = execQuery(conn, "INSERT into `kernelinfo` (kernel_name, kernel_release, kernel_arch) values ('linux-2.6.24-19-server', '2.6.24-19-server', 'x86_64' )")
		kernelId = str(r.lastrowid)
		sys.stdout.write("Success\n")

	#  Initrd
	checkVal =  entryExists(conn, "initrdinfo", "initrd_name", "zoni-register-64")
	sys.stdout.write("    Checking existence of initrd...")
	if not checkVal:
		sys.stdout.write("No\n") 
		optionList = "initrd=" + config['initrdRoot'] + "/x86_64/zoni-register-64.gz pxeserver=" + config['pxeServerIP'] + " imageserver=" + config['imageServerIP'] + " defaultimage=amd64-tashi_nm registerfile=register_node mode=register" 
		sys.stdout.write("    Inserting default register image into DB...")
		r = execQuery(conn, "INSERT into `initrdinfo` (initrd_name, initrd_arch, initrd_options) values ('zoni-register-64','x86_64', '" + optionList + "')")
		initrdId = str(r.lastrowid)
		sys.stdout.write("Success\n")
	else:
		sys.stdout.write("Yes\n")    
		initrdId = str(checkVal[1][0][0])
		
	#  Interactive Registration
	checkVal =  entryExists(conn, "initrdinfo", "initrd_name", "zoni-register-64-interactive")
	sys.stdout.write("    Checking existence of interactive initrd...")
	if not checkVal:
		sys.stdout.write("No\n") 
		sys.stdout.write("    Inserting default register-interactive image into DB...")
		optionList = "initrd=" + config['initrdRoot'] + "/x86_64/zoni-register-64-interactive.gz pxeserver=" + config['pxeServerIP'] + " imageserver=" + config['imageServerIP'] + " defaultimage=amd64-tashi_nm registerfile=register_node mode=register verbose=1" 
		r = execQuery(conn, "INSERT into `initrdinfo` (initrd_name, initrd_arch, initrd_options) values ('zoni-register-64-interactive','x86_64', '" + optionList + "')")
		initrdIdInteractive = str(r.lastrowid)
		sys.stdout.write("Success\n")
	else:
		sys.stdout.write("Yes\n")    
		initrdIdInteractive = str(checkVal[1][0][0])

	#  Link initrd and kernel to image
	sys.stdout.write("    Registering initrd and kernel to registration image...")
	query = "select * from imageinfo where image_name = 'zoni-register-64' and kernel_id = " + kernelId + " and initrd_id = " + initrdId
	r = execQuery(conn, query)
	if len(r.fetchall()) < 1:
		execQuery(conn, "INSERT into `imageinfo` (image_name, dist, dist_ver, kernel_id, initrd_id) values ('zoni-register-64', 'Ubuntu', 'Hardy', " + kernelId + ", " + initrdId + ")")

	query = "select * from imageinfo where image_name = 'zoni-register-64-interactive' and kernel_id = " + kernelId + " and initrd_id = " + initrdId
	r = execQuery(conn, query)
	if len(r.fetchall()) < 1:
		execQuery(conn, "INSERT into `imageinfo` (image_name, dist, dist_ver, kernel_id, initrd_id) values ('zoni-register-64-interactive', 'Ubuntu', 'Hardy', " + kernelId + ", " + initrdIdInteractive + ")")
	sys.stdout.write("Success\n")



def execQuery(conn, query):
	cursor = conn.cursor()
	try:
		cursor.execute (query)
	#except Exception:
		#traceback.print_exc(sys.exc_info())
	except MySQLdb.OperationalError, e:
		sys.stdout.write("Fail\n")
		msg = "ERROR: " + e[1]
		sys.stderr.write(msg)
		#logit(logFile, msg)
		#traceback.print_exc(sys.exc_info())
		exit()
	return cursor

def entryExists(conn, table, col, checkVal):
	query = "select * from " + table + " where " + col + " = '" + checkVal + "'"
 	r = execQuery(conn, query)
	res = r.fetchall()
	if len(res) > 0:
		return (1, res)

	return 0


if __name__ == "__main__":
    main()

