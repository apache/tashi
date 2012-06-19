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

import subprocess
import logging

from systemmanagementinterface import SystemManagementInterface


#class systemmagement():
	#def __init__(self, proto):
		#self.proto = proto

class Ipmi(SystemManagementInterface):
	def __init__(self, config, nodeName, hostInfo):
		#  should send data obj instead of hostInfo
		self.config = config
		self.nodeName = nodeName + "-ipmi"
		self.password = hostInfo['ipmi_password']
		self.user = hostInfo['ipmi_user']
		self.powerStatus = None
		self.verbose = False
		self.log = logging.getLogger(__name__)
		self.ipmicmd = "ipmitool -I lanplus -U %s -H %s -P %s " % (self.user, self.nodeName, self.password)
		print self.ipmicmd
		

	def setVerbose(self, verbose):
		self.verbose = verbose

	def __executeCmd(self, cmd):
		a = subprocess.Popen(args=cmd.split(), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
		out=  a.stdout.readline()
		err =  a.stderr.readline()
		if self.verbose:
			print "out is ", out
			print "err is ", err
		if err:
			self.log.info("%s %s" % (self.nodeName, err))
			return -1
			
		self.log.info("%s %s" % (self.nodeName, out))
		return 1


	def __setPowerStatus(self):
		if self.verbose:
			print self.ipmicmd
		cmd = self.ipmicmd + "chassis power status"
		a = subprocess.Popen(args=cmd.split(), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
		output = a.stdout.readline()
		myerr = a.stderr.readline()
	
		if "off" in output:
			self.powerStatus = 0
		if "on" in output:
			self.powerStatus = 1
		if "Unable" in myerr:
			self.powerStatus = -1

		return output

	def isPowered(self):
		if self.powerStatus == None:
			self.__setPowerStatus()
		self.log.info("Hardware get power status : %s", self.powerStatus)
		return self.powerStatus

	def getPowerStatus(self):
		#self.log.info("getPowerStatus :%s" % self.nodeName)
		return self.isPowered()
	

	def powerOn(self):
		self.log.info("Hardware power on : %s", self.nodeName)
		cmd = self.ipmicmd + "chassis power on"
		return self.__executeCmd(cmd)

	def powerOff(self):
		self.log.info("Hardware power off : %s", self.nodeName)
		cmd = self.ipmicmd + "chassis power off"
		return self.__executeCmd(cmd)

	def powerOffSoft(self):
		self.log.info("Hardware power off (soft): %s", self.nodeName)
		cmd = self.ipmicmd + "chassis power soft"
		return self.__executeCmd(cmd)

	def powerCycle(self):
		self.log.info("Hardware power cycle : %s", self.nodeName)
		cmd = self.ipmicmd + "chassis power cycle"
		return self.__executeCmd(cmd)
		
	def powerReset(self):
		self.log.info("Hardware power reset : %s", self.nodeName)
		cmd = self.ipmicmd + "chassis power reset"
		return self.__executeCmd(cmd)
		
	def activateConsole(self):
		self.log.info("Hardware sol activate : %s", self.nodeName)
		cmd = self.ipmicmd + "sol activate"
		return self.__executeCmd(cmd)
