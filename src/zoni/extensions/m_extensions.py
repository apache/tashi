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
import logging
import string
import MySQLdb

# m_extensions - This file is created to cater for a different kind of 
# requirement in MIMOS Lab. Instead of PXE boot images, MIMOS Lab customize
# Zoni to PXE boot the servers to install a functional OS and relevant packages
# into their respective local storage using preseed (Ubuntu/Debian) or 
# kickstart (Centos/Redhat). It is also serve as a file for testing additional
# codes for the convertz script.
# Revised Version: 20111202

from zoni.data.infostore import InfoStore

class mimos(InfoStore):
	def __init__(self, config):
		self.config = config
		self.host = config['dbHost']
		self.user = config['dbUser']
		self.passwd = config['dbPassword']
		self.db = config['dbInst']
		self.port = config['dbPort']
		self._isDb = 1
		if self.port == "":
			self.port = 3306
		self.log = logging.getLogger(__name__)

		self.conn = self.createConn()

	def createConn(self):
		try:
			return MySQLdb.connect(host = self.host, port = self.port, user = self.user, passwd = self.passwd, db = self.db)
		except MySQLdb.OperationalError, e:
			msg = "Error: " + str(e[1])
			self.log.error(msg)
			return

	def keepAlive(self):
		while True:
			if not self.conn.open:
				msg = "Reinitializing DB connection"
				self.log.info(msg)
				self.conn - self.createConn()
			time.sleep(10)
		return

	def getConfig(self, configs, theconfig):
		print configs[theconfig]
		return

	def getDestFile(self, configs, host):
		return (configs['tftpImageDir'] + "/01-" + ((host['mac_addr']).replace(":","-")).lower())

	def addRoletoNode(self, configs, host, thenode, roletemplate):
		therole = configs['tftpImageDir'] + "/01-" + ((host['mac_addr']).replace(":","-")).lower()
		self.log.info("Roles: addRole for %s" % thenode)
		srctpl = configs['tftpTemplateDir'] + "/" + roletemplate
		if os.path.isfile(therole):
			mesg = "Roles: Role File Exist! Exiting!"
			self.log.error(mesg)
			exit()
		if not os.path.isfile(srctpl):
			mesg = "Roles: Role Template Missing! Exiting!"
			self.log.error(mesg)
			exit()
		#shutil.copy(srctpl,therole) #this is direct copy approach, template is not customized, retained here just in case we still need it
		#read and parse srctpl and write to therole, trying to be a bit more flexible from here on
		infile = open(srctpl,'r')
		outfile = open(therole,'w')
		# Use sys_vendor to determine HDD Type, HP servers use the /dev/cciss/c0d0 form for their storage device
		if (host['sys_vendor'] == "HP"):
			hddtype = "cciss"
		else: # Most other vendors just use standard /dev/sdxy form for storage device
			hddtype = "normal"
		for line in infile.readlines():
			line = line.replace("$IMAGEHOST",configs['imageServerIP'])
			line = line.replace("$NTPSVRIP",configs['ntpsvrIP'])
			line = line.replace("$ROLE",roletemplate)
			line = line.replace("$USEHDDTYPE",hddtype)
			outfile.write(line)
		infile.close()
		outfile.close()
		self.log.info("Roles: %s created" % therole)
		return 0

	def removeRolefromNode(self, configs, host, thenode):
		therole = configs['tftpImageDir'] + "/01-" + ((host['mac_addr']).replace(":","-")).lower()
		self.log.info("Roles: removeRole for %s" % thenode)
		if not os.path.isfile(therole):
			mesg = "No Role File for %s! Exiting!" % thenode
			log.error(mesg)
			exit()
		os.remove(therole)
		self.log.info("Roles: %s removed" % therole)
		return 0

	# This is a temp workaround instead of using assignImagetoHost
	# A new temp table rolemap added to support this but should merge back to imagemap
	def assignRoletoHost(self, host, image):
		cur_image = host['pxe_image_name']
		query = "select image_id from imageinfo where image_name = " + "\"" + image + "\""
		row = self.queryDb(query)
		if len(row) < 1:
			mesg = "assignRoletoHost: Image \"" + image + "\" does not exist in db"
			self.log.error(mesg)
			return 1
		new_image_id = str(row[0][0])
		query = "select * from rolemap where sys_id = \"" + str(host['sys_id']) + "\""
		result = self.selectDb(query)
		if result.rowcount > 0:
			mesg = "assignRoletoHost: detected assigned role - removing from db first"
			self.log.info(mesg)
			query = "delete from rolemap where sys_id = \"" + str(host['sys_id']) + "\""
			self.delDb(query)
		query = "insert into rolemap (sys_id, image_id) values (\"" + str(host['sys_id']) + "\", " + new_image_id + ")"
		self.insertDb(connection,query)
		return 0

	def unassignRolefromHost(self, host):
		query="delete from rolemap where sys_id = \"" + str(host['sys_id']) + "\""
		self.delDb(query)
		return 0

	def showRoletoHost(self):
		query="select s.location, s.mac_addr, i.image_name from sysinfo s, imageinfo i, rolemap r where r.image_id=i.image_id and r.sys_id=s.sys_id order by s.location"
		rows = self.queryDb(connection,query)
		print "Node                 MAC Address       Image Name"
		for row in rows:
			print "%-20s %-17s %-30s" % (row[0],row[1],row[2])
		return 0

	def showKernelInfo(self):
		query="select k.kernel_id, k.kernel_name, k.kernel_release, k.kernel_arch from kernelinfo k"
		rows = self.queryDb(query)
		print "Available Kernels"
		print "ID  Name                           Release           Arch"
		for row in rows:
			kid=row[0]
			kname=row[1]
			krelease=row[2]
			karch=row[3]
			print "%-3s %-30s %-17s %-6s" % (kid, kname, krelease, karch)
		return 0

	def showInitrdInfo(self):
		query="select i.initrd_id, i.initrd_name, i.initrd_arch from initrdinfo i"
		rows = self.queryDb(query)
		print 
		print "Available Initial Ramdisks"
		print "ID  Name                           Arch"
		for row in rows:
			iid=row[0]
			iname=row[1]
			iarch=row[2]
			print "%-3s %-30s %-6s" % (iid, iname, iarch)
		print
		return 0

	def getKernelInitrdID(self, info):
		query="select k.kernel_id, i.initrd_id from kernelinfo k, initrdinfo i where k.kernel_name=\"" + info.split(":")[0] + "\" and i.initrd_name=\"" + info.split(":")[1] + "\" and k.kernel_arch=\"" + info.split(":")[2] + "\" and i.initrd_arch=\"" + info.split(":")[2] + "\""
		rows=self.queryDb(query)
		if len(rows) > 0:
			for row in rows:
				kid=str(row[0])
				iid=str(row[1])
				print "%s:%s" % (kid, iid)
		return 0

	def registerKernelInitrd(self, configs, KernelInitrd):
		query="insert into kernelinfo (kernel_name, kernel_release, kernel_arch) values (\"" + KernelInitrd.split(":")[0] + "\", \"" + KernelInitrd.split(":")[1] + "\", \"" + KernelInitrd.split(":")[2] + "\")"
		k_id=self.insertDb(query)
		query="insert into initrdinfo (initrd_name, initrd_arch, initrd_options) values (\"" + KernelInitrd.split(":")[3] + "\", \"" + KernelInitrd.split(":")[4] + "\", \"boot=live toram nopersistent fetch=http://" + configs['imageServerIP'] + "/" + configs['fsImagesBaseDir'] + "/" + KernelInitrd.split(":")[5] + " initrd=" + configs['initrdRoot'] + "/" + KernelInitrd.split(":")[3] + "\")"
		i_id=self.insertDb(query)
		print "%s:%s" % (k_id, i_id)
		return 0

	def queryDb(self, thequery):
		self.conn.ping(True)
		cursor=self.conn.cursor()
		try:
			cursor.execute(thequery)
			self.conn.commit()
			row=cursor.fetchall()
		except MySQLdb.OperationalError, e:
			self.log.error("queryDb - %s", e)
			return -1
		return row

	def selectDb(self, thequery):
		self.conn.ping(True)
		cursor=self.conn.cursor()
		try:
			cursor.execute(thequery)
			self.conn.commit()
		except MySQLdb.OperationalError, e:
			self.log.error("selectDb - %s", e)
			return -1
		return cursor

	def insertDb(self, thequery):
		self.conn.ping(True)
		cursor=self.conn.cursor()
		try:
			cursor.execute(thequery)
			self.conn.commit()
		except MySQLdb.OperationalError, e:
			self.log.error("insertDb - %s", e)
			return -1
		return cursor.lastrowid

	def delDb(self, thequery):
		self.conn.ping(True)
		cursor=self.conn.cursor()
		try:
			cursor.execute(thequery)
			self.conn.commit()
		except MySQLdb.OperationalError, e:
			self.log.error("delDb - %s", e)
			return -1
		return cursor
