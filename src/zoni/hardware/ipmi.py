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

from systemmanagementinterface import SystemManagementInterface


#class systemmagement():
	#def __init__(self, proto):
		#self.proto = proto

class Ipmi(SystemManagementInterface):
	def __init__(self, host, user, password):
		self.host = host + "-ipmi"
		self.password = password
		self.user = user
		self.powerStatus = None
		self.verbose = False
		self.ipmicmd = "ipmitool -I lanplus -U" + self.user + " -H" + self.host + \
						" -P " + self.password  + " "
		

	def setVerbose(self, verbose):
		self.verbose = verbose

	def getPowerStatus(self):
		if self.verbose:
			print self.ipmicmd
		cmd = self.ipmicmd + "chassis power status"
		a = os.popen(cmd)
		output = a.read()

		print "%s\n%s" % (self.host, output)
		if "off" in output:
			self.powerStatus = 0
		if "on" in output:
			self.powerStatus = 1
		if "Unable" in output:
			print "unable to get the status"
			self.powerStatus = 0
	
		return output
		#return a.read()
		#for line in a.readlines():
			#print line 	

	def isPowered(self):
		if self.powerStatus == None:
			self.getPowerStatus()
		if self.powerStatus:
			return 1;
		if not self.powerStatus:
			return 0;
	

	def powerOn(self):
		cmd = self.ipmicmd + "chassis power on"
		a = os.popen(cmd)
		output = a.read()
		print "output is ", output

	def powerOff(self):
		cmd = self.ipmicmd + "chassis power off"
		a = os.popen(cmd)
		output = a.read()
		print "output is ", output

	def powerCycle(self):
		cmd = self.ipmicmd + "chassis power cycle"
		a = os.popen(cmd)
		output = a.read()
		print "output is ", output
		
	def powerReset(self):
		cmd = self.ipmicmd + "chassis power reset"
		a = os.popen(cmd)
		output = a.read()
		print "output is ", output
		
	def activateConsole(self):
		cmd = self.ipmicmd + "sol activate"
		a = os.popen(cmd)
		output = a.read()
		print "output is ", output
		
#ipmitool -I lanplus -E -H r2r1c3b0-ipmi -U root chassis power status
