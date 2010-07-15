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
import subprocess
import traceback

import usermanagement

from zoni.data.infostore import InfoStore
from zoni.extra.util import logit, checkSuper
from zoni.agents.dhcpdns import DhcpDns

class ResourceQuerySql(InfoStore):
	def __init__(self, config, verbose=None):
		self.config = config
		self.verbose  = verbose
		self.host = config['dbHost']
		self.user = config['dbUser']
		self.passwd = config['dbPassword']
		self.db = config['dbInst']
		
		self.tftpRootDir = config['tftpRootDir']
		self.tftpImageDir = config['tftpImageDir']
		self.tftpBootOptionsDir = config['tftpBootOptionsDir']

		self.logFile = config['logFile']

		if config['dbPort'] == "":
			config['dbPort'] = 3306

		self.port = config['dbPort']

		self.vlan_max = config['vlan_max']
		self.vlan_reserved = config['vlan_reserved']
		
		#  Connect to DB
		try:
			self.conn = MySQLdb.connect(host = self.host, port = self.port, user = self.user, passwd = self.passwd, db = self.db)
		except MySQLdb.OperationalError, e:
			if e[0] == 2005:
				print "ERROR :" + str(e[1])
				exit(1)
			else:
				print "ERROR : ", e
				exit(1)

	def __create_queryopts(self, cmdargs, extra=None):
		cmdlen = len(cmdargs)
		queryopt = ""

		if extra:
			queryopt += extra 

		if cmdlen == 0:
			pass
		else:
			num = cmdlen
			if extra:
				queryopt += " and "
			for k, v in cmdargs.iteritems():
				if k == "num_procs":
					queryopt += k + " = " + v + " "
				if k == "mem_total":
					queryopt += k + " >= " + v + " "
				if k == "clock_speed":
					queryopt += k + " >= " + v + " "
				if k == "num_cores":
					queryopt += k + " = " + v + " "
				if k == "cpu_flags":
					queryopt += k + " like \"%" + v + "%\" "
				if k == "node_id":
					queryopt += " location = " + "\'" + v + "\' "

				if num > 1:
					queryopt += " and "

				num -= 1

		if queryopt:
			tmp = " where " + queryopt
			queryopt = tmp

		return queryopt

	def updateDatabase(self, table, query):
		pass
		

	def showResources(self, cmdargs):

		queryopt = ""
		defaultFields = "mac_addr, location, num_procs, num_cores, clock_speed, mem_total "
		#defaultFields = "*"
		
		queryopt = self.__create_queryopts(cmdargs)				
				
		#query = "show fields from sysinfo"
		#results = self.__selectDb(query)
		
		query = "select " + defaultFields + "from sysinfo " + queryopt
		result = self.__selectDb(query)	

		line = ""
		for i in defaultFields.split(","):
			#line += string.strip(str(i)) + "\t"
			line += str(i.center(20))
		print line

		for row in result.fetchall():
			line = ""
			for val in row:
				line += str(val).center(20)
			print line
		print str(result.rowcount) + " systems returned"

		#mysql -h rodimus -u reader irp-cluster -e "select * from sysinfo where location like 'r1%' and num_procs = 1"

	def getLocationFromSysId (self, nodeId):
		query = "select location from sysinfo where sys_id = \"" + str(nodeId) + "\""
		result = self.__selectDb(query)
		return result.fetchall()[0][0]

	def getMacFromSysId(self, nodeId):
		query = "select mac_addr from sysinfo where sys_id = \"" + str(nodeId) + "\""
		result = self.__selectDb(query)
		return result.fetchall()[0][0]

	def getIpFromSysId(self, nodeId):
		query = "select ip_addr from sysinfo where sys_id = \"" + str(nodeId) + "\""
		result = self.__selectDb(query)
		return result.fetchall()[0][0]
		

	def getAllSwitches(self):
		switchList = []
		query = "select hw_name from hardwareinfo where hw_type = \"switch\""
		result = self.__selectDb(query)
		for switch in result.fetchall():
			switchList.append(switch[0])

		#  Use static list until we get all switches installed
		switchList =  ['sw1-r1r2', 'sw0-r1r1', 'sw0-r1r2', 'sw0-r1r3', 'sw0-r1r4', 'sw0-r2r3', 'sw0-r3r3', 'sw0-r3r2', 'sw0-r2r1c3', 'sw2-r1r2']
		#switchList =  ['sw2-r1r2']
		#switchList =  ['sw1-r1r2']


		print switchList
	
		return switchList

	def getAvailableVlan(self):
		#  Get list of available vlans
		query = "select vlan_num from vlaninfo where domain = 'private'"
		result = self.__selectDb(query)
		for vlan in result.fetchall()[0]:
			avail = self.isVlanAvailable(vlan)
			if avail:
				myvlan = vlan
				break
		if not myvlan:
			mesg = "No Vlans for you!  You Go Now\n"
			logit(self.logFile, mesg)
		return myvlan
	
	def isVlanAvailable(self, vlan):
		query = "select a.vlan_id, v.vlan_num from allocationinfo a, vlaninfo v where a.vlan_id = v.vlan_id and v.vlan_num = " + str(vlan)
		result = self.__selectDb(query)
		if result.rowcount > 1:
			return 0
		else:
			return 1

	def getVlanId(self, vlan):
		query = "select vlan_id from vlaninfo where vlan_num = \"" +  str(vlan) + "\""
		result = self.__selectDb(query)
		#print result.rowcount 
		if result.rowcount > 0:
			return result.fetchall()[0][0]
		else:
			mesg = "ERROR: VLAN does not exist: " + str(vlan)
			logit(self.logFile, mesg)
			exit()

	def isIpAvailable(self, ip_addr, vlan_id):
		query = "select * from allocationinfo where ip_addr = \"" + str(ip_addr) + "\" and vlan_id = \"" + str(vlan_id) + "\""
		#print "query ", query
		result = self.__selectDb(query)
		#print "select row count is ", result.rowcount
		if result.rowcount > 0:
			return 0
		else:
			return 1


	def getDomainIp(self, vlan):
		ip_start = 30
		query = "select ip_network from vlaninfo where vlan_num = " + str(vlan)
		result = self.__selectDb(query)
		ip_network = result.fetchall()[0][0]
		v = ip_network.split(".")
		ip_base = v[0] + "." + v[1] + "." + v[2]
		
		#  Check for other allocations and assign IP address
		query = "select a.vlan_id, v.vlan_num from allocationinfo a, vlaninfo v where a.vlan_id = v.vlan_id and v.vlan_num = " + str(vlan)
		#print "ip is ", ip_network 

		query = "select a.ip_addr from allocationinfo a, vlaninfo v where a.vlan_id = v.vlan_id and v.vlan_num = " + str(vlan);
		result = self.__selectDb(query)
		#print "row count is ", result.rowcount
		if result.rowcount > 0:
			for ip in xrange(ip_start, 255):
				ip_check = ip_base + "." + str(ip)
				check = self.isIpAvailable(ip_check, self.getVlanId(vlan))
				if check:
					ip_addr = ip_check
					break
		else:
			ip_addr = ip_base + "." + str(ip_start)
			#print "ip_addr", ip_addr

		return ip_addr


	def showArchive(self):
		query = "select * from allocationarchive"
		result = self.__selectDb(query)
		for i in result:
			print i

	def showAllocation(self, userId=None):
		#from IPython.Shell import IPShellEmbed
		#shell = IPShellEmbed(argv="")
		#shell(local_ns=locals(), global_ns=globals())

		#  specify usermanagement - ldap or files
		usermgt = usermanagement.ldap()

		query = "select r.user_id, s.location, s.num_cores, s.mem_total, \
				r.reservation_expiration, r.notes, r.reservation_id, v.vlan_num, a.ip_addr, a.hostname,\
				a.notes, i.image_name \
				from allocationinfo a, sysinfo s, reservationinfo r, vlaninfo v, imageinfo i, imagemap m where \
				s.mac_addr = m.mac_addr and \
				m.image_id = i.image_id and \
				s.sys_id = a.node_id  and \
				v.vlan_id = a.vlan_id and \
				r.reservation_id = a.reservation_id "
		if userId:
			myid = userId
			if type(userId) == str:
				#  convert username to id
				myid = usermgt.getUserId(userId)
				
			query += " and user_id = " + myid + " " 

		query += "order by r.reservation_id asc, s.location"

		result = self.__selectDb(query)
		
		print "NODE ALLOCATION"
		print "---------------------------------------------------------------------------------"
		if self.verbose:
			#print "Res_id\tUser    \tNode    \tCores\tMemory  \tExpiration\t\tVLAN\tHOSTNAME    \tIPADDR    \t\tReservationNotes|AllocationNotes"
			print "%-5s%-10s%-10s%-12s%-12s%-5s%-15s%-18s%-24s%s" % ("Res", "User", "Host", "Cores/Mem","Expiration", "Vlan", "Hostname", "IP Addr", "Boot Image Name", "Notes")
		else:
			print "%-10s%-10s%-12s%-12s%s" % ("User", "Node", "Cores/Mem","Expiration", "Notes")

		for i in result.fetchall():
			uid = i[0]
			host = i[1]
			cores = i[2]
			memory = i[3]
			expire = str(i[4])[0:10]
			if expire == "None":
				expire = "0000-00-00"
			rnotes = i[5]
			resId= i[6]
			vlanId= i[7]
			ip_addr = i[8]
			hostname = i[9]
			anotes = i[10]
			image_name = i[11]
			userName = usermgt.getUserName(uid)
			combined_notes = str(rnotes) + "|" + str(anotes)
			if self.verbose:
				#print "%s\t%s    \t%s    \t%s\t%s  \t%s\t%s\t%s    \t%s    \t%s" % (resId, userName, host, cores, memory,expire, vlanId, hostname, ip_addr, combined_notes)
				print "%-5s%-10s%-10s%-2s%-10s%-12s%-5s%-15s%-18s%-24s%s" % (resId, userName, host, cores, memory,expire, vlanId, hostname, ip_addr, image_name, combined_notes)
			else:
				print "%-10s%-10s%-2s%-10s%-12s%s" % (userName, host, cores, memory,expire, combined_notes)
		print "---------------------------------------------------------------------------------"
		print str(result.rowcount) + " systems returned"

	def showReservation(self, userId=None):
		#from IPython.Shell import IPShellEmbed
		#shell = IPShellEmbed(argv="")
		#shell(local_ns=locals(), global_ns=globals())

		#  specify usermanagement - ldap or files
		usermgt = usermanagement.ldap()

		query = "select reservation_id, user_id, \
				reservation_expiration, notes \
				from reservationinfo order by reservation_id" 
		if self.verbose:
			query = "select r.reservation_id, r.user_id, r.reservation_expiration, r.notes, count(a.reservation_id) \
					from reservationinfo r, allocationinfo a \
					where r.reservation_id = a.reservation_id \
					group by r.reservation_id order by reservation_id"
		#if userId:
			#myid = userId
			#if type(userId) == str:
				##  convert username to id
				#myid = usermgt.getUserId(userId)
				
			#query += " and user_id = " + myid + " " 

		#query += "order by r.user_id, s.location"

		result = self.__selectDb(query)
		
		print "RESERVATIONS"
		print "---------------------------------------------------------------------------------"
		if self.verbose:
			print "%-7s%-10s%-12s%-7s%s" % ("ResId", "UserName", "Expire", "Total", "Notes")
		else:
			print "%-7s%-10s%-12s%s" % ("ResId", "UserName", "Expire", "Notes")

		total = 0
		for i in result.fetchall():
			resId= i[0]
			uid = i[1]
			expire = str(i[2])[0:10]
			if expire == "None":
				expire = "0000-00-00"
			notes = i[3]
			userName = usermgt.getUserName(uid)
			if self.verbose:
				num_nodes = i[4]
				total += num_nodes
				#print "%s    \t%s   \t%s\t%s\t\t%s " % (resId, userName, expire, num_nodes, notes)
				print "%-7s%-10s%-12s%-7s%s" % (resId, userName, expire, num_nodes, notes)
			else:
				print "%-7s%-10s%-12s%s" % (resId, userName, expire, notes)
		if self.verbose:
			print "---------------------------------------------------------------------------------"
			print "Total number of nodes - %s" % (total)

	
	def getPxeImages(self):
		cursor = self.conn.cursor ()
		line = "select image_name from imageinfo"
		cursor.execute (line)
		row = cursor.fetchall()
		desc = cursor.description

		imagelist = []
		for i in row:
			imagelist.append(i[0])

		return imagelist
		
		
	def showPxeImages(self):
		cursor = self.conn.cursor ()
		line = "select image_name, dist, dist_ver  from imageinfo"
		cursor.execute (line)
		row = cursor.fetchall()
		desc = cursor.description

		for i in row:
			print i

		cursor.close ()

	def showPxeImagesToSystemMap(self, cmdargs):
		extra = "l.mac_addr = j.mac_addr and j.image_id = i.image_id"
		queryopt = self.__create_queryopts(cmdargs, extra=extra)
		print queryopt

		query = "select  l.location, j.mac_addr, i.image_name from sysinfo l , imageinfo i, imagemap j " + queryopt + " order by l.location"
		#print query
		result = self.__selectDb(query)

		for i in result.fetchall():
			print i

	def close(self):
		self.conn.close()

	def getHwAccessMethod(self):
		pass

		mylist = []
		
		return  mylist

	def getHostInfo(self, node):
		host = {}
		query = "select * from sysinfo where location = \"" + node + "\"" 
		#print "query is ", query
		result = self.__selectDb(query)
		if result.rowcount > 1:
			print "Mulitple entries for system exist.  Please correct"
			exit()
		if result.rowcount < 1:
			mesg = "node does not exist :" + str(node) + "\n"
			sys.stderr.write(mesg)
			exit()
		
		for i in result.fetchall():
			host['mac_addr'] = host.get("mac_addr", "")
			host['node_id'] = int(i[0])
			host['mac_addr'] = i[1]
			host['num_procs'] = int(i[2])
			host['num_cores'] = int(i[3])
			host['mem_total'] = int(i[6])
			host['clock_speed'] = int(i[8])
			host['sys_vendor'] = i[9]
			host['sys_model'] = i[10]
			host['proc_vendor'] = i[11]
			host['proc_model'] = i[12]
			host['proc_cache'] = i[13]
			host['cpu_flags'] = i[15]
			host['bios_rev'] = i[17]
			host['location'] = i[16]
			host['dell_tag'] = host.get("dell_tag", "")
			host['dell_tag'] = i[14]
		'''
		for k, v in host.iteritems():
			print k, v, "\n"
		'''
		
		#  Get IPMI info
		query = "select * from ipmiinfo where node_id = " + str(host['node_id']) + "" 
		result = self.__selectDb(query)
		if result.rowcount> 1:
			print "Mulitple entries for system exist.  Please correct"
			exit()
		for i in result.fetchall():
			host['ipmi_user'] = i[2]
			host['ipmi_password'] = i[3]
			host['ipmi_addr'] = i[1]

		#  Get image info
		query = "select image_name from imagemap i, imageinfo j where i.image_id = j.image_id and mac_addr = \"" + host['mac_addr'] + "\"" 
		result = self.__selectDb(query)
		if result.rowcount == 0:
			host['pxe_image_name'] = "None"
		else:
			for i in result.fetchall():
				host['pxe_image_name'] = i[0]

		#  Get switch info
		query = "select h.hw_id, h.hw_name, h.hw_model, h.hw_ipaddr, h.hw_userid, h.hw_password, p.port_num from hardwareinfo h, portmap p where p.hw_id = h.hw_id and hw_type = 'switch' and node_id = " +  str(host['node_id'])
		result = self.__selectDb(query)
		for i in result.fetchall():
			host['hw_id'] = int(i[0])
			host['hw_name'] = i[1]
			host['hw_model'] = i[2]
			host['hw_ipaddr'] = i[3]
			host['hw_userid'] = i[4]
			host['hw_password'] = i[5]
			host['hw_port'] = int(i[6])

		#  Get drac info
		query = "select h.hw_id, h.hw_name, h.hw_model, h.hw_ipaddr, h.hw_userid, h.hw_password, p.port_num from hardwareinfo h, portmap p where p.hw_id = h.hw_id and hw_type = 'drac' and node_id = " +  str(host['node_id'])
		result = self.__selectDb(query)
		if result.rowcount > 0:
			for i in result.fetchall():
				host['drac_id'] = int(i[0])
				host['drac_name'] = i[1]
				host['drac_model'] = i[2]
				host['drac_ipaddr'] = i[3]
				host['drac_userid'] = i[4]
				host['drac_password'] = i[5]
				host['drac_port'] = int(i[6])

		#  Get PDU info
		query = "select h.hw_id, h.hw_name, h.hw_model, h.hw_ipaddr, h.hw_userid, h.hw_password, p.port_num from hardwareinfo h, portmap p where p.hw_id = h.hw_id and hw_type = 'pdu' and node_id = " +  str(host['node_id'])
		result = self.__selectDb(query)
		for i in result.fetchall():
			host['pdu_id'] = int(i[0])
			host['pdu_name'] = i[1]
			host['pdu_model'] = i[2]
			host['pdu_ipaddr'] = i[3]
			host['pdu_userid'] = i[4]
			host['pdu_password'] = i[5]
			host['pdu_port'] = int(i[6])


		#print "host is ", host
		return host

	def getSwitchInfo(self, switchName):
		host = {}
		#  Get switch info
		#switchList = self.getAllSwitches()
		query = "select h.hw_id, h.hw_name, h.hw_model, h.hw_ipaddr, h.hw_userid, h.hw_password from hardwareinfo h where h.hw_name  = \"" +  str(switchName) + "\""
		#print "query is ", query
		result = self.__selectDb(query)
		#desc = cursor.description
		for i in result.fetchall():
			host['hw_id'] = int(i[0])
			host['hw_name'] = i[1]
			host['hw_model'] = i[2]
			host['hw_ipaddr'] = i[3]
			host['hw_userid'] = i[4]
			host['hw_password'] = i[5]
		return host

	def __queryDb(self, query):
		cursor = self.conn.cursor()
		cursor.execute (query)
		row = cursor.fetchall()
		desc = cursor.description
		return row

	def execQuery(self, query):
		cursor = self.conn.cursor()
		try:
			cursor.execute (query)
		#except Exception:
			#traceback.print_exc(sys.exc_info())
		except MySQLdb.OperationalError, e:
			msg = "ERROR: " + e[1]
			sys.stderr.write(msg)
			logit(self.logFile, msg)
			#traceback.print_exc(sys.exc_info())
			exit()
		return cursor

	def __selectDb(self, query):
		cursor = self.conn.cursor()
		try:
			cursor.execute (query)
		#except Exception:
			#traceback.print_exc(sys.exc_info())
		except MySQLdb.OperationalError, e:
			msg = "ERROR: " + e[1]
			sys.stderr.write(msg)
			logit(self.logFile, msg)
			#traceback.print_exc(sys.exc_info())
			exit()
		return cursor

	def __updateDb(self, query):
		cursor = self.conn.cursor()
		try:
			cursor.execute (query)
		except MySQLdb.OperationalError, e:
			msg = "ERROR: " + e[1]
			sys.stderr.write(msg)
			logit(self.logFile, msg)
			#traceback.print_exc(sys.exc_info())
			exit()

	def __insertDb(self, query):
		cursor = self.conn.cursor()
		try:
			cursor.execute (query)
		#except Exception:
			#traceback.print_exc(sys.exc_info())
		except MySQLdb.OperationalError, e:
			msg = "ERROR: " + e[1]
			sys.stderr.write(msg)
			logit(self.logFile, msg)
			#traceback.print_exc(sys.exc_info())
			exit()


	def updateReservation (self, reservationId, userId=None, reservationDuration=None, vlanIsolate=None, allocationNotes=None):


		mesg = "Updating reservation"
		logit(self.logFile, mesg)

		if reservationDuration:
			if len(resDuration) == 8:
				expireDate = resDuration
			elif len(resDuration) < 4:
				numdays = resDuration
				cmd = "date +%Y%m%d --date=\"" + numdays + " day\""
				p = os.popen(cmd)
				expireDate = string.strip(p.read())
			else:
				mesg = "ERROR: Invalid reservation duration\n"
				sys.stderr.write(mesg)
				logit(self.logFile, mesg)
				exit()

			mesg = "Updating reservationDuration :" + resDuration
			logit(self.logFile, mesg)
			query = "update reservationinfo set reservation_exiration = \"" + expireDate_ + "\" where reservation_id = \"" + str(reservationId) + "\""
			self.__updateDb(query)

		if allocationNotes:
			mesg = "Updating allocationNotes to " + allocationNotes 
			logit(self.logFile, mesg)
			query = "update reservationinfo set notes = \"" + allocationNotes + "\" where reservation_id = \"" + str(reservationId) + "\""
			self.__updateDb(query)
		if vlanIsolate:
			mesg = "UPDATING Vlan: " 
			logit(self.logFile, mesg)
			query = "update reservationinfo set vlan_num = " + vlanIsolate + " where reservation_id = \"" + str(reservationId) + "\""
			print "query is ", query
			self.__updateDb(query)
		if userId:
			mesg = "UPDATING USER:"
			logit(self.logFile, mesg)
			query = "update reservationinfo set user_id = " + userId + " where reservation_id = \"" + str(reservationId) + "\""
			self.__updateDb(query)

	def addReservation (self, userId, reservationDuration=None, reservationNotes=None):

		# set default for reservation duration to 15 days
		if not reservationDuration:
			resDuration = str(15)
		else:
			resDuration = str(reservationDuration)


		if len(resDuration) == 8:
			expireDate = resDuration
		elif len(resDuration) < 4:
			numdays = resDuration
			cmd = "date +%Y%m%d --date=\"" + numdays + " day\""
			p = os.popen(cmd)
			expireDate = string.strip(p.read())
		else:
			mesg = "ERROR: Invalid reservation duration\n"
			sys.stderr.write(mesg)
			logit(self.logFile, mesg)
			exit()

		#  create reservation
		#  Create the reservation
		print userId, expireDate,reservationNotes
		query = "insert into reservationinfo (user_id, reservation_expiration, notes) values (\"" + str(userId) + "\", " + str(expireDate) + ", \"" + reservationNotes + "\")"
		mesg = "Creating new reservation\n" + query
		logit(self.logFile, mesg)
		self.__selectDb(query)
		#  Get the res_id
		query = "select max(reservation_id) from reservationinfo"
		res_id = self.__selectDb(query).fetchone()[0]
		mesg = "  Reservation created - ID :" + str(res_id)
		logit(self.logFile, mesg) 
		return res_id


	def archiveAllocation(self, nodeId, ip_addr, hostName, vlan_id, user_id, reservation_type, res_notes, notes):
		combined_notes = str(res_notes) + "|" + str(notes)
		mesg = "Insert to allocation archive:"
		query = "insert into allocationarchive (node_id, ip_addr, hostname, vlan_id, user_id, reservation_type, notes) \
				values (\"" + \
				str(nodeId) + "\", \"" + str(ip_addr) + "\", \"" + \
				str(hostName) + "\", \"" + str(vlan_id) + "\", \"" + \
				str(user_id) + "\", \"" + str(reservation_type) + "\", \"" + \
				str(combined_notes) + "\")" 

		self.__insertDb(query)

	@checkSuper
	def allocateNode(self, reservationId, nodeId, hostName, vlanIsolate=None, ip_addr=None, notes=None):
		#print "nodeId", nodeId, self.getMacFromSysId(nodeId)

		#  Check if node is already allocated
		query = "select * from allocationinfo where node_id = \"" + str(nodeId) + "\""
		result = self.__selectDb(query)
		if result.rowcount > 0:
			val = str(result.fetchone())
			mesg = "ERROR:  Node already allocated " + val + "\n"
			logit(self.logFile, mesg)
			exit()


		#  Check if reservation exists

		query = "select reservation_id, user_id, reservation_date, \
				reservation_expiration, notes  from reservationinfo \
				where reservation_id = \"" + str(reservationId) + "\""
		result = self.__selectDb(query)

		if result.rowcount > 0:
			res_results = result.fetchall()[0]
			val = str(res_results)
			res_id= res_results[0]
			user_id = res_results[1]
			res_notes = res_results[4]
			if self.verbose:
				mesg = "Reservation: " + val
				logit(self.logFile, mesg)
		else:
			mesg = "ERROR: Reservation does not exist: " + reservationId + "\n"
			logit(self.logFile, mesg)
			exit()

		
		if not vlanIsolate:
			vlan = self.getAvailableVlan()
		else:
			vlan = vlanIsolate

		#  Allocate nodes to the reservation
		#  Reserve the node and assign to user
		vlan_id = self.getVlanId(vlan)
		if vlan != 999:
			if not ip_addr:
				ip_addr  = self.getDomainIp(vlan)
			else:
				# Check to see if IP is free
				query = "select * from allocationinfo where ip_addr = \"" + str(ip_addr) + "\""
				result = self.__selectDb(query)
				if result.rowcount > 0:
					mesg = "ERROR: IP Address specified (" + str(ip_addr) + ") already in use\n"
					mesg += str(result.fetchone())
					logit(self.logFile, mesg)
					exit()
		else:
			ip_addr = self.getIpFromSysId(nodeId)	
		#print "ip is ", ip_addr

		#  If there is no hostname, set to default
		if not hostName:
			hostName = self.getLocationFromSysId(nodeId)

		#print "hostname is ", hostName, "ip is ", ip_addr, "vlan is ", vlan_id

		#  Assign IP address to node
		dhcpdns = DhcpDns(self.config, verbose=1)
		dnscheck = dhcpdns.addDhcp(hostName, ip_addr, self.getMacFromSysId(nodeId))
		dhcpdns.addDns(hostName, ip_addr)


		mesg = "Insert to Node allocation:"
		query = "insert into allocationinfo (reservation_id, node_id, ip_addr, hostname, vlan_id, notes) \
				values (\"" + str(reservationId) + "\", \"" +  str(nodeId) + "\", \"" + \
				str(ip_addr) + "\", \"" + str(hostName) + "\", \"" + str(vlan_id) + "\", \"" + \
				str(notes) + "\")"
		self.__insertDb(query)

		#Archive
		reservation_type = "allocation"
		self.archiveAllocation(nodeId, ip_addr, hostName, vlan_id, user_id, reservation_type, res_notes, notes)


	def rgasstest(self, vlan_num):
		query = "select * from vlaninfo where vlan_num = " + vlan_num
		res = self.__selectDb(query).fetchall()
		print res
		
		
			
	def removeReservation(self, res):
		query = "delete from reservationinfo where reservation_id = " + str(res)
		self.__updateDb(query)
		query = "delete from allocationinfo where reservation_id = " + str(res)
		self.__updateDb(query)
		
	@checkSuper
	def releaseNode(self, nodeName):
		#  Get the nodeId
		query = "select node_id, r.reservation_id, a.ip_addr, hostname, vlan_id, a.notes, r.notes,r.user_id from allocationinfo a, sysinfo s, reservationinfo r where a.node_id = s.sys_id and a.reservation_id = r.reservation_id and location = \"" + nodeName + "\""
		print query
		result = self.__selectDb(query)
		if result.rowcount == 0:
			mesg = "ERROR:  Node not allocated\n"
			sys.stderr.write(mesg)
			exit(1)
		if result.rowcount > 1:
			mesg = "WARNING:  Node allocated multiple times (" + str(result.rowcount) + ")"
			logit(self.logFile, mesg)

		val = result.fetchone()
		nodeId = int(val[0])
		resId = int(val[1])
		ip_addr = val[2]
		hostName = val[3]
		vlan_id = int(val[4])
		allocation_notes = val[5]
		reservation_notes = val[6]
		user_id = val[7]

		print "hostname is ", hostName
		#  Assign IP address to node
		dhcpdns = DhcpDns(self.config, verbose=1)
		dnscheck = dhcpdns.removeDns(hostName)
		dhcpdns.removeDhcp(hostName)

		'''
		query = "select reservation_id, notes from reservationinfo where node_id = " + str(nodeId)
		result = self.__selectDb(query)
		for i in result:
			print i
		print result.rowcount
		if result.rowcount == 0:
			mesg = "No Reservation for this node.\n  Please check"
			logit(self.logFile, mesg)
			exit(1)
		if result.rowcount > 1:
			mesg = "WARNING:  Muliple reservations exist (" + str(result.rowcount) + ")"
			logit(self.logFile, mesg)
		
		resId = int(result.fetchone()[0])
		res_notes = int(result.fetchone()[1])
		
		print resId, res_notes
		'''
		
		#  Eventually should add count =1 so deletes do get out of control
		query = "delete from allocationinfo where reservation_id = " + str(resId) + " and node_id = " + str(nodeId)
		result = self.__selectDb(query)

		#  Archive node release
		reservation_type = "release"
		self.archiveAllocation(nodeId, ip_addr, hostName, vlan_id, user_id, reservation_type, reservation_notes, allocation_notes)

	def addImage(self, imageName):
		name = ""
		dist = ""
		dist_ver = ""

		if len(imageName.split(":")) > 1:
			name = imageName.split(":")[0]
		if len(imageName.split(":")) > 2:
			dist = imageName.split(":")[1]
		if len(imageName.split(":")) >= 3:
			dist_ver = imageName.split(":")[2]

		query = "select * from imageinfo where image_name = \"" + name + "\""
		result = self.__selectDb(query)
		if result.rowcount > 0:
			mesg = "ERROR:  Image already exists\n"
			sys.stderr.write(mesg)
			exit()
		
		if name == "":
			mesg = "ERROR:  Image details not specified\n"
			logit(self.logFile, mesg)
			mesg = "Example amd64-rgass-testing:Ubuntu:8.04\n"
			mesg += "or amd64-rgass-testing::\n"
			sys.stderr.write(mesg)
			exit()

		query = "insert into imageinfo (image_name, dist, dist_ver) values(\"" + name + "\", \"" + dist + "\", \"" + dist_ver + "\")"
		self.__insertDb(query)


	def delImage(self, imageName):
		query = "delete from imageinfo where image_name = \"" + imageName + "\""
		result = self.__selectDb(query)
		if result.rowcount == 0:
			mesg = "ERROR:  No images match your entry\n"
			sys.stderr.write(mesg)
			exit()

	def assignImagetoHost(self, host, image):
		#  imagemap db should be sys_id instead of mac_addr
		#  change later

		cur_image = host['pxe_image_name']
		#  Get the id of the new image
		query = "select image_id from imageinfo where image_name = " + "\"" + image + "\""
		row = self.__queryDb(query)
		if len(row) < 1: 
			mesg = "ERROR: Image \"" + image + "\" does not exist"
			logit(self.logFile, mesg)
			exit()
		new_image_id = str(row[0][0])

		#  check for entry and delete in exists
		query = "select * from imagemap where mac_addr = \"" + host['mac_addr'] + "\""
		result = self.__selectDb(query)
		if result.rowcount > 0:
			query = "delete from imagemap where mac_addr = \"" + host['mac_addr'] + "\""
			result = self.__selectDb(query)
			

		#  update the database entry with the new image for the host
		query = "insert into imagemap (mac_addr, image_id) values (\"" + host['mac_addr'] + "\", " + new_image_id + ")"
		self.__selectDb(query)
		

		#  Update tftp link
		mac_addr = "01-" + string.lower(string.replace(host['mac_addr'], ":", "-"))
		maclink = self.tftpImageDir + "/" + mac_addr
		#print "mac link is ", maclink
		#  Check if it exists first
		if os.path.exists(maclink):
			try:
				os.unlink(maclink)
			except Exception, e:
				traceback.print_exc(sys.exc_info())
				if OSError:
					print OSError
					mesg = "Cannot modify file.  Please use sudo\n"
					sys.stderr.write(mesg)
					return 1
				print e
				return 1
		#  Relink
		newlink = os.path.basename(self.tftpBootOptionsDir) + "/" + image
		try:
			os.symlink(newlink, maclink)
			mesg = "Image assignment Successful " +  host['location'] + " " + host['mac_addr'] + " " + image
			logit(self.logFile, mesg)
		except Exception, e:
			if OSError:
				mesg = "Cannot modify file.  Please use sudo\n"
				sys.stderr.write(mesg)
				return 1
			print e
			return 1

		return 0

