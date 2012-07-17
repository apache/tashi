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

import warnings
import logging
import string
import sys
import time

warnings.filterwarnings("ignore")

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto import rfc1902
from zoni.data.resourcequerysql import ResourceQuerySql
from zoni.hardware.systemmanagementinterface import SystemManagementInterface
from zoni.agents.dhcpdns import DhcpDns

#class systemmagement():
	#def __init__(self, proto):
		#self.proto = proto

class raritanDominionPx(SystemManagementInterface):
	def __init__(self, config, nodeName, hostInfo):
		#  Register
		self.config = config
		self.nodeName = nodeName
		self.log = logging.getLogger(__name__)
		self.verbose = False
		self.powerStatus = None

		if hostInfo != None:
			self.host = nodeName
			self.pdu_name = hostInfo['pdu_name']
			self.port = hostInfo['pdu_port']
			self.user = hostInfo['pdu_userid']
			self.password = hostInfo['pdu_password']

			self.oid = "1,3,6,1,4,1,13742,4,1,2,2,1"
			self.oid_name = ",2"
			self.oid_set = ",3"
			self.oid_status = ",3"

			if self.getOffset():
				self.port = hostInfo['pdu_port'] - 1


		#  this works
		#errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(cmdgen.CommunityData('my-agent', 'public', 0), cmdgen.UdpTransportTarget(('pdu0-r1r1', 161)), (1,3,6,1,4,1,13742,4,1,2,2,1,3,2))

		#print varBinds
		#oid = netsnmp.Varbind('sysDescr')
		#result = netsnmp.snmpwalk(oid, Version = 2,DestHost="localhost",Community="public")
		#print result

		#var = netsnmp.Varbind('sysDescr.0')
		#res = netsnmp.snmpget(var, ...:Version=1,...:DestHost = 'pdu0-r1r1',...: Community = 'prs-domain')
		#print res

		#print cmdgen
		#set snmp = /usr/bin/snmpset -v 2c -c intel pdu .1.3.6.1.4.1.13742.4.1.2.2.1.3.$outletnumber i $state
		#name snmp = /usr/bin/snmpset -v 2c -c intel pdu .1.3.6.1.4.1.13742.4.1.2.2.1.2.$outletnumber i $state
		#status snmp = /usr/bin/snmpset -v 2c -c intel pdu .1.3.6.1.4.1.13742.4.1.2.2.1.1.$outletnumber i $state
		#self.snmp_status_oid = ".1.3.6.1.4.1.13742.4.1.2.2.1.1."
		#self.powerStatus = None
		#print self.__dict__

	def setVerbose(self, verbose):
		self.verbose = verbose
	''' 
	Just discovered that some PDUs start numbering ports in the SNMP mib
	with 0.  Adding a check to update the port number to match the labels on the
	physical plugs which start numbering with 1.
	'''
	def getOffset(self):
		thisoid = eval(str(self.oid) + str(self.oid_status) + "," + str(0))
		__errorIndication, __errorStatus, __errorIndex, varBinds = cmdgen.CommandGenerator().getCmd( \
		cmdgen.CommunityData('my-agent', self.user, 0), \
		cmdgen.UdpTransportTarget((self.pdu_name, 161)), thisoid)
		output = varBinds[0][1]
		if output == -1:
			return 0
		else:
			return 1


	def __setPowerStatus(self):
		thisoid = eval(str(self.oid) + str(self.oid_status) + "," + str(self.port))
		__errorIndication, __errorStatus, __errorIndex, varBinds = cmdgen.CommandGenerator().getCmd( \
		cmdgen.CommunityData('my-agent', self.user, 0), \
		cmdgen.UdpTransportTarget((self.pdu_name, 161)), thisoid)
		output = varBinds[0][1]
		print output, varBinds
		
		if output == 1:
			self.powerStatus = 1
			powerstat = "on"
		if output == 0:
			self.powerStatus = 0
			powerstat = "off"
		print "pwerstat", powerstat 
		self.log.info("hardware setPowerStatus %s : %s" % (powerstat, self.nodeName))

		if output:
			return 1
		return 0


	def isPowered(self):
		if self.powerStatus == None:
			self.__setPowerStatus()
		if self.powerStatus:
			return 1;
		return 0;
	
	def getPowerStatus(self):
		return self.isPowered()

	def powerOn(self):
		thisoid = eval(str(self.oid) + str(self.oid_status) + "," + str(self.port)) 
		__errorIndication, __errorStatus, __errorIndex, __varBinds = cmdgen.CommandGenerator().setCmd( \
		cmdgen.CommunityData('my-agent', self.user, 1), \
		cmdgen.UdpTransportTarget((self.pdu_name, 161)), \
		(thisoid, rfc1902.Integer('1')))
		return self.getPowerStatus()

	def powerOff(self):
		thisoid = eval(str(self.oid) + str(self.oid_status) + "," + str(self.port)) 
		__errorIndication, __errorStatus, __errorIndex, __varBinds = cmdgen.CommandGenerator().setCmd( \
		cmdgen.CommunityData('my-agent', self.user, 1), \
		cmdgen.UdpTransportTarget((self.pdu_name, 161)), \
		(thisoid, rfc1902.Integer('0')))
		return self.getPowerStatus()

	def powerCycle(self):
		self.powerOff()
		self.powerOn()
		
	def powerReset(self):
		self.powerCycle()

	def registerToZoni(self, user, password, host):
		import socket

		host = string.strip(str(host))
		#  Get hostname of the switch
		if len(host.split(".")) == 4:
			ip = host
			try:
				host = string.strip(socket.gethostbyaddr(ip)[0].split(".")[0])
			except Exception, e:
				mesg = "WARNING:  Host (" + host + ") not registered in DNS " + str(e) + "\n"
				sys.stderr.write(mesg)
		else:
			#  Maybe a hostname was entered...
			try:
				ip = socket.gethostbyname(host)
			except Exception, e:
				mesg = "ERROR:  Host (" + host + ") not registered in DNS " + str(e) + "\n"
				sys.stderr.write(mesg)
				mesg = "Unable to resolve hostname" + "\n"
				sys.stderr.write(mesg)
				exit()


		a={}
		oid = eval(str("1,3,6,1,2,1,1,1,0"))
		__errorIndication, __errorStatus, __errorIndex, varBinds = cmdgen.CommandGenerator().getCmd( \
		cmdgen.CommunityData('my-agent', user, 0), \
		cmdgen.UdpTransportTarget((host, 161)), oid)

		if len(varBinds) < 1:
			mesg = "Incorrect authentication details"
			self.log.error(mesg)
			return -1

		a['hw_make'] = str(varBinds[0][1])

		oid = eval("1,3,6,1,4,1,13742,4,1,1,6,0")
		__errorIndication, __errorStatus, __errorIndex, varBinds = cmdgen.CommandGenerator().getCmd( \
		cmdgen.CommunityData('my-agent', user, 0), \
		cmdgen.UdpTransportTarget((host, 161)), oid)
		x = []
		for d in ['%x' % ord(i) for i in varBinds[0][1]]:
			if len(d) == 1:
				d = "0" + str(d)
			x.append(d)
		a['hw_mac'] = ":".join(['%s' % d for d in x])

		oid = eval("1,3,6,1,4,1,13742,4,1,1,2,0")
		__errorIndication, __errorStatus, __errorIndex, varBinds = cmdgen.CommandGenerator().getCmd( \
		cmdgen.CommunityData('my-agent', user, 0), \
		cmdgen.UdpTransportTarget((host, 161)), oid)
		serial = str(varBinds[0][1])

		datime = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.localtime())
		val = "Registered by Zoni on : " + datime
		a['hw_notes'] = val + "; Serial " + serial

		oid = eval("1,3,6,1,4,1,13742,4,1,1,1,0")
		__errorIndication, __errorStatus, __errorIndex, varBinds = cmdgen.CommandGenerator().getCmd( \
		cmdgen.CommunityData('my-agent', user, 0), \
		cmdgen.UdpTransportTarget((host, 161)), oid)
		a['hw_version_fw'] = str(varBinds[0][1])

		oid = eval("1,3,6,1,4,1,13742,4,1,1,12,0")
		__errorIndication, __errorStatus, __errorIndex, varBinds = cmdgen.CommandGenerator().getCmd( \
		cmdgen.CommunityData('my-agent', user, 0), \
		cmdgen.UdpTransportTarget((host, 161)), oid)
		a['hw_model'] = str(varBinds[0][1])

		a['hw_type'] = "pdu"
		a['hw_name'] = host
		a['hw_ipaddr'] = ip
		a['hw_userid'] = user
		a['hw_password'] = password

		#  Register in dns
		if self.config['dnsEnabled']:
			try:
				mesg = "Adding %s(%s) to dns" % (host, ip)
				self.log.info(mesg)
				DhcpDns(self.config, verbose=self.verbose).addDns(host, ip)
				mesg = "Adding %s(%s) to dhcp" % (host, ip)
				self.log.info(mesg)
				DhcpDns(self.config, verbose=self.verbose).addDhcp(host, ip, a['hw_mac'])
			except:
				mesg = "Adding %s(%s) %s to dhcp/dns failed" % (host, ip, a['hw_mac'])
				self.log.error(mesg)

		#  Add to db
		#  Register to DB
		query = ResourceQuerySql(self.config, self.verbose)
		query.registerHardware(a)
