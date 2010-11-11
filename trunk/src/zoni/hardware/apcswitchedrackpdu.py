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

import sys
import os 
import warnings
warnings.filterwarnings("ignore")

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto import rfc1902


from systemmanagementinterface import SystemManagementInterface


class apcSwitchedRackPdu(SystemManagementInterface):
	def __init__(self, host):
		self.host = host['location']
		self.pdu_name = host['pdu_name']
		self.port = host['pdu_port']
		self.user = host['pdu_userid']
		self.password = host['pdu_password']
# sPDUOutletCtl
		self.oid_set = "1,3,6,1,4,1,318,1,1,4,4,2,1,3"
# sPDUOutletCtl
		self.oid_status = "1,3,6,1,4,1,318,1,1,4,4,2,1,3"
# sPDUOutletName
		self.oid_name = "1,3,6,1,4,1,318,1,1,4,5,2,1,3"

	def getPowerStatus(self):
		thisoid = eval(str(self.oid_status) + "," + str(self.port))
		errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd( \
		cmdgen.CommunityData('my-agent', self.user, 0), \
		cmdgen.UdpTransportTarget((self.pdu_name, 161)), thisoid)
		output = varBinds[0][1]
		
		if output == 1:
			self.powerStatus = 1
			powerstat = "on"
		if output == 2:
			self.powerStatus = 0
			powerstat = "off"
		if output == 4:
# the mib documentation states that if outlets are in unknown state,
# all outlets and the pdu shall be cycled
			self.powerStatus = 1
			powerstat = "unknown"

		print "PDU Power for %s is %s" % (self.host, powerstat)

		if output:
			return 1
		return 0


	def isPowered(self):
		if self.powerStatus == None:
			self.getPowerStatus()
		if self.powerStatus:
			return 1;
		if not self.powerStatus:
			return 0;
	

	def powerOn(self):
		thisoid = eval(str(self.oid_status) + "," + str(self.port)) 
		errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().setCmd( \
		cmdgen.CommunityData('my-agent', self.user, 1), \
		cmdgen.UdpTransportTarget((self.pdu_name, 161)), \
		(thisoid, rfc1902.Integer('1')))
		self.getPowerStatus()

	def powerOff(self):
		thisoid = eval(str(self.oid_status) + "," + str(self.port)) 
		errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().setCmd( \
		cmdgen.CommunityData('my-agent', self.user, 1), \
		cmdgen.UdpTransportTarget((self.pdu_name, 161)), \
		(thisoid, rfc1902.Integer('2')))
		self.getPowerStatus()

	def powerCycle(self):
		self.powerOff()
# should we sleep here, or just send "3"?
		self.powerOn()
		
	def powerReset(self):
		self.powerCycle()
