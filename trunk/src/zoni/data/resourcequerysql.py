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
import logging

import usermanagement
from zoni.data.infostore import InfoStore
from zoni.extra.util import checkSuper
from zoni.agents.dhcpdns import DhcpDns

class ResourceQuerySql(InfoStore):
	def __init__(self, config, verbose=None):
		self.config = config
		self.verbose  = verbose
		self.host = config['dbHost']
		self.user = config['dbUser']
		self.passwd = config['dbPassword']
		self.db = config['dbInst']
		#self.log = logging.getLogger(os.path.basename(__name__))
		self.log = logging.getLogger(__name__)
		
		self.tftpRootDir = config['tftpRootDir']
		self.tftpImageDir = config['tftpImageDir']
		self.tftpBootOptionsDir = config['tftpBootOptionsDir']


		if config['dbPort'] == "":
			config['dbPort'] = 3306

		self.port = config['dbPort']

		self.vlan_max = config['vlan_max']
		#self.vlan_reserved = config['vlan_reserved']
		
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

	def getNote(self):
		return "Created by Zoni"

	def addDomain(self, name, desc, reservationId):
		#  Check if there is a reservation
		query = "select * from reservationinfo where reservation_id = %s" % (reservationId)
		result = self.__selectDb(query)
		if result.rowcount < 1:
			mesg = "Reservation does not exist : %s" % (reservationId)
			self.log.error(mesg)
			return -1

		if desc == None:
			desc = self.getNote()

		print name
		if self.__checkDup("domaininfo", "domain_name", name):
			self.log.error("Domain (%s) already exists" % (name))
			return -1
		query = "insert into domaininfo (domain_name, domain_desc, reservation_id) values ('%s','%s', '%s')" % (name, desc, reservationId)
		try:
			result = self.__insertDb(query)
			mesg = "Adding domain %s(%s)" % (name, desc)
			self.log.info(mesg)
		except Exception, e:
			mesg = "Adding domain %s(%s) failed : %s" % (name, desc, e)
			self.log.error(mesg)
		

	def removeDomain(self, name):
		mesg = "Removing domain %s" % (name)
		self.log.info(mesg)
		query = "delete from domaininfo where domain_name = '%s'" % (name)
		result = self.__deleteDb(query)
		#  Need to remove any vlans attached to this domain

	def showDomains(self):
		query = "select domain_name, domain_desc from domaininfo"
		result = self.__selectDb(query)
		desc = result.description
		if result.rowcount > 0:
			print "%s\t%s\n-------------------------------------" % (result.description[0][0], result.description[1][0])
			for row in result.fetchall():
				print "%s\t\t%s" % (row[0], row[1])
			return 0
		else:
			mesg = "No Domains exist"
			self.log.info(mesg)
			return -1

	def addVlan(self, vnumber, desc=None):
		if desc == None:
			desc = "Created by Zoni"
		if int(vnumber) > self.vlan_max:
			self.log.error("Max vlan size is %s" % (self.vlan_max))
			return -1

		if self.__checkDup("vlaninfo", "vlan_num", vnumber):
			self.log.error("Vlan %s already exists" % (vnumber))
			return -1
		query = "insert into vlaninfo (vlan_num, vlan_desc) values ('%s','%s')" % (vnumber, desc)
		try:
			result = self.__insertDb(query)
			mesg = "Adding vlan %s(%s)" % (vnumber, desc)
			self.log.info(mesg)
		except Exception, e:
			mesg = "Adding vlan %s(%s) failed : %s" % (vnumber, desc, e)
			self.log.error(mesg)
		

	def removeVlan(self, vnumber):
		query = "delete from vlaninfo where vlan_num = '%s'" % (vnumber)
		result = self.__deleteDb(query)
		if result > 0:
			mesg = "Successfully removed vlan %s" % (vnumber)
			self.log.info(mesg)
			return 0
		else:
			mesg = "Failed to removed vlan %s" % (vnumber)
			self.log.info(mesg)
			return -1
		#  Need to remove any vlans attached to this vlan 

	def showVlans (self):
		query = "select vlan_num, vlan_desc from vlaninfo order by vlan_num"
		try:
			result = self.__selectDb(query)
			print "%s\t%s\n-------------------------------------" % (result.description[0][0], result.description[1][0])
			for row in result.fetchall():
				print "%s\t\t%s" % (row[0], row[1])
			return 0
		except Exception, e:
			mesg = "No Vlans defined: %s" % (e)
			self.log.info(mesg)
			return -1

	def assignVlan(self, vlan, domain, force=None):
		domainId = self.__getSomething("domain_id", "domaininfo", "domain_name", domain)
		vlanId = self.__getSomething("vlan_id", "vlaninfo", "vlan_num", vlan)
		query = "select * from domainmembermap m, vlaninfo v, domaininfo d where d.domain_id = '%s' and v.vlan_id = %s and v.vlan_id = m.vlan_id and m.domain_id = d.domain_id" % (int(domainId), int(vlanId))
		if self.__selectDb(query).rowcount > 0:
			self.log.warning("Vlan %s already assigned to domain %s" % (vlan, domain));
			return 0

		# warning if vlan already assigned to another domain
		query = "select * from domainmembermap where vlan_id = %s" % (vlanId)
		if self.__selectDb(query).rowcount > 0:
			self.log.warning("Vlan %s already assigned to a domain" % (vlan));
			if not force:
				return -1

		self.log.info("Assigning vlan %s to domain %s" % (vlan, domain))
		query = "insert into domainmembermap (domain_id, vlan_id) values (%s, %s)" % (domainId, vlanId)
		self.__insertDb(query)

	def __getSomething(self, fieldname, table, critField, crit):
		query = "select %s from %s where %s = '%s'" % (fieldname, table, critField, crit)
		result = self.__selectDb(query)
		return result.fetchall()[0][0]


	def __checkDup (self, table, colname, value, colname2=None, value2=None):
		cond = "where %s = '%s' " % (colname, value)
		if (colname2 != None and value2 != None):
			cond += " and %s = '%s'" % (colname2, value2)
		query = "select * from %s %s" % (table, cond)
		result = self.__selectDb(query)
		if result.rowcount == 0:
			return []
		return result.fetchall()

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
				if k == "sys_id":
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
		#switchList =  ['sw1-r1r2', 'sw0-r1r1', 'sw0-r1r2', 'sw0-r1r3', 'sw0-r1r4', 'sw0-r2r3', 'sw0-r3r3', 'sw0-r3r2', 'sw0-r2r1c3', 'sw2-r1r2']
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
			self.log.info(mesg)
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
			mesg = "VLAN does not exist: " + str(vlan)
			self.log.error(mesg)
			return -1 

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


	#def showArchive(self):
		#query = "select * from allocationarchive"
		#result = self.__selectDb(query)
		#for i in result:
			#print i

	def showAllocation(self, userId=None):
		#from IPython.Shell import IPShellEmbed
		#shell = IPShellEmbed(argv="")
		#shell(local_ns=locals(), global_ns=globals())

		#  specify usermanagement - ldap or files
		usermgt = eval("usermanagement.%s" % (self.config['userManagement']) + "()")

		query = "select r.user_id, d.domain_name, s.location, s.num_cores, \
				s.mem_total, r.reservation_expiration, r.notes, r.reservation_id, a.hostname, \
				a.notes, i.image_name from \
				sysinfo s, imageinfo i, \
				allocationinfo a, domaininfo d, reservationinfo r, imagemap j where \
				i.image_id = j.image_id \
				and r.reservation_id = a.reservation_id \
				and d.domain_id = a.domain_id and s.sys_id = a.sys_id "
		if userId:
			myid = userId
			if type(userId) == str:
				#  convert username to id
				myid = usermgt.getUserId(userId)
				
			query += " and user_id = '%s' " % (myid)

		query += "order by r.reservation_id asc, s.location"

		print query
		result = self.__selectDb(query)
		
		print "NODE ALLOCATION"
		print "---------------------------------------------------------------------------------"
		if self.verbose:
			#print "Res_id\tUser    \tNode    \tCores\tMemory  \tExpiration\t\tVLAN\tHOSTNAME    \tIPADDR    \t\tReservationNotes|AllocationNotes"
			print "%-5s%-10s%-10s%-12s%-12s%-5s%-15s%-18s%-24s%s" % ("Res", "User", "Host", "Cores/Mem","Expiration", "Vlan", "Hostname", "IP Addr", "Boot Image Name", "Notes")
		else:
			print "%-10s%-10s%-13s%-12s%s" % ("User", "Node", "Cores/Mem","Expiration", "Notes")

		for i in result.fetchall():
			uid = i[0]
			domain = i[1]
			host = i[2]
			cores = i[3]
			memory = i[4]
			expire = str(i[5])[0:10]
			if expire == "None":
				expire = "0000-00-00"
			rnotes = i[6]
			resId= i[7]
			hostname = i[8]
			anotes = i[9]
			image_name = i[10]
			userName = usermgt.getUserName(uid)
			combined_notes = str(rnotes) + "|" + str(anotes)
			if self.verbose:
				vlanId = 1000
				ip_addr = "10.0.0.10"
				print "%-5s%-10s%-10s%-2s/%-10s%-12s%-5s%-15s%-18s%-24s%s" % (resId, userName, host, cores, memory,expire, vlanId, hostname, ip_addr, image_name, combined_notes)
			else:
				print "%-10s%-10s%-2s/%-10s%-12s%s" % (userName, host, cores, memory,expire, combined_notes)
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
		query = "select sys_id, mac_addr, num_procs, num_cores, mem_total, clock_speed, sys_vendor, sys_model, proc_vendor, proc_model, proc_cache, cpu_flags, bios_rev, location, system_serial_number, ip_addr from sysinfo where location = \"" + node + "\"" 
		result = self.__selectDb(query)
		if result.rowcount > 1:
			print "Multiple entries for system exist.  Please correct"
			exit()
		if result.rowcount < 1:
			mesg = "node does not exist :" + str(node) + "\n"
			sys.stderr.write(mesg)
			exit()
		
		for i in result.fetchall():
			host['mac_addr'] = host.get("mac_addr", "")
			host['sys_id'] = int(i[0])
			host['mac_addr'] = i[1]
			host['num_procs'] = int(i[2])
			host['num_cores'] = int(i[3])
			host['mem_total'] = int(i[4])
			host['clock_speed'] = int(i[5])
			host['sys_vendor'] = i[6]
			host['sys_model'] = i[7]
			host['proc_vendor'] = i[8]
			host['proc_model'] = i[9]
			host['proc_cache'] = i[10]
			host['cpu_flags'] = i[11]
			host['bios_rev'] = i[12]
			host['location'] = i[13]
			host['system_serial_number'] = i[14]
			host['ip_addr'] = i[14]
		'''
		for k, v in host.iteritems():
			print k, v, "\n"
		'''
		
		#  Get IPMI info
		query = "select h.hw_userid, h.hw_password, h.hw_ipaddr from hardwareinfo h, portmap p, sysinfo s where p.sys_id = s.sys_id and h.hw_id = p.hw_id and h.hw_type = 'ipmi' and s.sys_id = " + str(host['sys_id']) + "" 
		result = self.__selectDb(query)
		if result.rowcount> 1:
			print "Multiple entries for system exist.  Please correct"
			exit()
		for i in result.fetchall():
			host['ipmi_user'] = i[0]
			host['ipmi_password'] = i[1]
			host['ipmi_addr'] = i[2]

		#  Get image info
		query = "select image_name from imagemap i, imageinfo j where i.image_id = j.image_id" 
		result = self.__selectDb(query)
		if result.rowcount == 0:
			host['pxe_image_name'] = "None"
		else:
			for i in result.fetchall():
				host['pxe_image_name'] = i[0]

		#  Get switch info
		query = "select h.hw_id, h.hw_name, h.hw_model, h.hw_ipaddr, h.hw_userid, h.hw_password, p.port_num from hardwareinfo h, portmap p where p.hw_id = h.hw_id and hw_type = 'switch' and sys_id = " +  str(host['sys_id'])
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
		query = "select h.hw_id, h.hw_name, h.hw_model, h.hw_ipaddr, h.hw_userid, h.hw_password, p.port_num from hardwareinfo h, portmap p where p.hw_id = h.hw_id and hw_type = 'drac' and sys_id = " +  str(host['sys_id'])
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
		query = "select h.hw_id, h.hw_name, h.hw_model, h.hw_ipaddr, h.hw_userid, h.hw_password, p.port_num from hardwareinfo h, portmap p where p.hw_id = h.hw_id and h.hw_type = 'pdu' and p.sys_id = " +  str(host['sys_id'])
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
		try:
			cursor.execute (query)
			self.conn.commit()
			row = cursor.fetchall()
			desc = cursor.description
		except MySQLdb.OperationalError, e:
			msg = "%s : %s" % (e[1], query)
			self.log.error(msg)
			#traceback.print_exc(sys.exc_info())

		return row

	def execQuery(self, query):
		cursor = self.conn.cursor()
		try:
			cursor.execute (query)
			self.conn.commit()
		#except Exception:
			#traceback.print_exc(sys.exc_info())
		except MySQLdb.OperationalError, e:
			msg = "%s : %s" % (e[1], query)
			self.log.error(msg)
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
			msg = "SELECT Failed : %s : %s" % (e[1], query)
			self.log.error(msg)
			#traceback.print_exc(sys.exc_info())
			return -1 
		return cursor

	def __deleteDb(self, query):
		cursor = self.conn.cursor()
		try:
			cursor.execute (query)
			self.conn.commit()
		except MySQLdb.OperationalError, e:
			msg = "DELETE Failed : %s : %s" % (e[1], query)
			sys.stderr.write(msg)
			self.log.error(msg)
			#traceback.print_exc(sys.exc_info())
			return -1
		return cursor

	def __updateDb(self, query):
		cursor = self.conn.cursor()
		try:
			cursor.execute (query)
			self.conn.commit()
		except MySQLdb.OperationalError, e:
			msg = "UPDATE Failed : %s : %s" % (e[1], query)
			sys.stderr.write(msg)
			self.log.error(msg)
			#traceback.print_exc(sys.exc_info())
			return -1
		return cursor

	def __insertDb(self, query):
		cursor = self.conn.cursor()
		try:
			cursor.execute (query)
			self.conn.commit()
		#except Exception:
			#traceback.print_exc(sys.exc_info())
		except MySQLdb.OperationalError, e:
			msg = "INSERT Failed : %s : %s" % (e[1], query)
			self.log.error(msg)
			#traceback.print_exc(sys.exc_info())
			return -1
		return cursor


	def updateReservation (self, reservationId, userId=None, reservationDuration=None, vlanIsolate=None, allocationNotes=None):

		mesg = "Updating reservation %s" % (str(reservationId))
		self.log.info(mesg)

		if reservationDuration:
			if len(resDuration) == 8:
				expireDate = resDuration
			elif len(resDuration) < 4:
				numdays = resDuration
				cmd = "date +%Y%m%d --date=\"" + numdays + " day\""
				p = os.popen(cmd)
				expireDate = string.strip(p.read())
			else:
				mesg = "ERROR: Invalid reservation duration"
				self.log.error(mesg)
				exit()

			mesg = "Updating reservationDuration :" + resDuration
			self.log.info(mesg)
			query = "update reservationinfo set reservation_exiration = \"" + expireDate_ + "\" where reservation_id = \"" + str(reservationId) + "\""
			self.__updateDb(query)

		if allocationNotes:
			mesg = "Updating allocationNotes to " + allocationNotes 
			self.log.info(mesg)
			query = "update reservationinfo set notes = \"" + allocationNotes + "\" where reservation_id = \"" + str(reservationId) + "\""
			self.__updateDb(query)
		if vlanIsolate:
			mesg = "UPDATING Vlan: " 
			self.log.info(mesg)
			query = "update reservationinfo set vlan_num = " + vlanIsolate + " where reservation_id = \"" + str(reservationId) + "\""
			print "query is ", query
			self.__updateDb(query)
		if userId:
			mesg = "UPDATING USER:"
			self.log.info(mesg)
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
			self.log.info(mesg)
			exit()

		#  create reservation
		#  Create the reservation
		print userId, expireDate,reservationNotes
		query = "insert into reservationinfo (user_id, reservation_expiration, notes) values (\"" + str(userId) + "\", " + str(expireDate) + ", \"" + str(reservationNotes) + "\")"
		mesg = "Creating new reservation : " + query
		self.log.info(mesg)
		self.__insertDb(query)
		#  Get the res_id
		query = "select max(reservation_id) from reservationinfo"
		res_id = self.__selectDb(query).fetchone()[0]
		mesg = "  Reservation created - ID :" + str(res_id)
		self.log.info(mesg)

		return res_id


	#def archiveAllocation(self, nodeId, ip_addr, hostName, vlan_id, user_id, reservation_type, res_notes, notes):
		#combined_notes = str(res_notes) + "|" + str(notes)
		#mesg = "Insert to allocation archive:"
		#query = "insert into allocationarchive (sys_id, ip_addr, hostname, vlan_id, user_id, reservation_type, notes) \
				#values (\"" + \
				#str(nodeId) + "\", \"" + str(ip_addr) + "\", \"" + \
				#str(hostName) + "\", \"" + str(vlan_id) + "\", \"" + \
				#str(user_id) + "\", \"" + str(reservation_type) + "\", \"" + \
				#str(combined_notes) + "\")" 
#
		#self.__insertDb(query)

	def allocateNode(self, reservationId, domain, sysId, vlanInfo, imageName, notes=None):
		print "reservationId", reservationId, domain, sysId, vlanInfo, imageName, notes

		#  Check if node is already allocated
		result = self.__checkDup("allocationinfo", "sys_id", sysId)
		if len(result) > 0:
			mesg = "Node already allocated : %s" % (result)
			self.log.info(mesg)
			return -1

		#  Check if reservation exists
		result = self.__checkDup("reservationinfo", "reservation_id", reservationId)
		if len(result) == 0:
			mesg = "Reservation does not exist: " + reservationId + "\n"
			self.log.error(mesg)
			return -1
		else:
			resinfo = result[0]

		#  Check if domain exists
		domainId = self.__getSomething("domain_id", "domaininfo", "domain_name", domain)
		if len(self.__checkDup("domaininfo", "domain_id", domainId)) == 0:
			mesg = "Domain does not exist: %s(%s)" % (domainId, domain)
			self.log.error(mesg)
			return -1
		
		#  Check that all the vlans exist
		for i in vlanInfo.split(","):
			v = i.split(":")[0]
			if self.getVlanId(v) < 0:
				return -1

		#  Insert to allocationinfo
		nodeName = self.getLocationFromSysId(sysId)
		mesg = "allocateNode %s : domain %s : reservation %s(%s)" % (nodeName, domain, reservationId, resinfo[4])
		self.log.info(mesg)
		query = "insert into allocationinfo (sys_id, reservation_id, domain_id, notes) values ('%s', '%s', '%s', '%s')" % (sysId, reservationId, domainId, notes)
		result = self.__insertDb(query)
		allocationId = result.lastrowid

		#  Parse vlan info and add to vlanmembermap
		for i in vlanInfo.split(","):
			print i
			v = i.split(":")[0]
			vId = self.getVlanId(v)
			t = i.split(":")[1]
			query = "insert into vlanmembermap (allocation_id, vlan_id, vlan_type) values ('%s', '%s', '%s')" % (allocationId, vId, t)
			result = self.__insertDb(query)
			mesg = "Adding vlan %s to node %s" % (v, nodeName)
			self.log.info(mesg)

		#  Insert into imagemap
		image_id = self.__getSomething("image_id", "imageinfo", "image_name", imageName)
		query = "insert into imagemap (allocation_id, image_id) values ('%s', '%s')" % (allocationId, image_id)
		result = self.__insertDb(query)

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
		query = "select sys_id, r.reservation_id, a.ip_addr, hostname, vlan_id, a.notes, r.notes,r.user_id from allocationinfo a, sysinfo s, reservationinfo r where a.sys_id = s.sys_id and a.reservation_id = r.reservation_id and location = \"" + nodeName + "\""
		print query
		result = self.__selectDb(query)
		if result.rowcount == 0:
			mesg = "ERROR:  Node not allocated\n"
			sys.stderr.write(mesg)
			exit(1)
		if result.rowcount > 1:
			mesg = "WARNING:  Node allocated multiple times (" + str(result.rowcount) + ")"
			self.log.warning(mesg)

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
		query = "select reservation_id, notes from reservationinfo where sys_id = " + str(nodeId)
		result = self.__selectDb(query)
		for i in result:
			print i
		print result.rowcount
		if result.rowcount == 0:
			mesg = "No Reservation for this node.\n  Please check"
			logit(self.logFile, mesg)
			exit(1)
		if result.rowcount > 1:
			mesg = "WARNING:  Multiple reservations exist (" + str(result.rowcount) + ")"
			logit(self.logFile, mesg)
		
		resId = int(result.fetchone()[0])
		res_notes = int(result.fetchone()[1])
		
		print resId, res_notes
		'''
		
		#  Eventually should add count =1 so deletes do get out of control
		query = "delete from allocationinfo where reservation_id = " + str(resId) + " and sys_id = " + str(nodeId)
		result = self.__deleteDb(query)

		#  Archive node release
		#reservation_type = "release"
		#self.archiveAllocation(nodeId, ip_addr, hostName, vlan_id, user_id, reservation_type, reservation_notes, allocation_notes)

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
			self.log.error(mesg)
			mesg = "Example amd64-rgass-testing:Ubuntu:8.04\n"
			mesg += "or amd64-rgass-testing::\n"
			sys.stderr.write(mesg)
			exit()

		query = "insert into imageinfo (image_name, dist, dist_ver) values(\"" + name + "\", \"" + dist + "\", \"" + dist_ver + "\")"
		self.__insertDb(query)


	def delImage(self, imageName):
		query = "delete from imageinfo where image_name = \"" + imageName + "\""
		result = self.__deleteDb(query)
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
			self.log.error(mesg)
			exit()
		new_image_id = str(row[0][0])

		#  check for entry and delete in exists
		query = "select * from imagemap where mac_addr = \"" + host['mac_addr'] + "\""
		result = self.__selectDb(query)
		if result.rowcount > 0:
			query = "delete from imagemap where mac_addr = \"" + host['mac_addr'] + "\""
			result = self.__deleteDb(query)
			

		#  update the database entry with the new image for the host
		query = "insert into imagemap (mac_addr, image_id) values (\"" + host['mac_addr'] + "\", " + new_image_id + ")"
		self.__insertDb(query)
		

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
			self.log.info(mesg)
		except Exception, e:
			if OSError:
				mesg = "Cannot modify file.  Please use sudo\n"
				sys.stderr.write(mesg)
				return 1
			print e
			return 1

		return 0

	
	def registerHardware(self, data):

		if len(self.__checkDup("hardwareinfo", "hw_name", data['hw_name'])) == 0:
			statement = "insert into hardwareinfo (" 
			fields = []
			entries = []
			for key, value in data.iteritems(): 
				fields.append(key)
				entries.append(value)
			c = len(fields)
			count = 1
			for i in fields:
				if c != count:
					statement += i + ","
				else:
					statement += i + ")"
				count += 1

			statement += "values ("
			c = len(entries)
			count = 1
			for i in entries:
				if c != count:
					statement += "'" + i + "', "
				else:
					statement += "'" + i + "') "
				count += 1
			try:
				self.__insertDb(statement)
				mesg = "Device (%s) registered successfully\n" % (data['hw_name'])
				self.log.info(mesg)
			except Exception, e:
				mesg = "Registration failed to add Device (%s) - %s\n" % (data['hw_name'], e)
				self.log.warning(mesg)
		else:
			mesg = "INFO:  Device (%s) already registered\n" % (data['hw_name'])
			sys.stderr.write(mesg)
