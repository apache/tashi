#!/usr/bin/env python
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
import logging

from systemmanagementinterface import SystemManagementInterface
from zoni.data.resourcequerysql import *

from tashi.util import instantiateImplementation


class SystemManagement(SystemManagementInterface):

	def __init__(self, config, data):
		self.config = config
		self.data = data
		self.verbose = False
		self.host = ""
		self.log = logging.getLogger(__name__)


	def getInfo(self, nodeName):
		self.host = self.data.getHostInfo(node)
		
		
	def setVerbose(self, verbose):
		self.verbose = verbose

	def __getHostInfo(self, nodeName):
		return self.data.getHostInfo(nodeName)#, data.getHardwareCapabilities(nodeName))

	def getPowerStatus(self, nodeName):
		return self.__iterateHardware(nodeName, "getPowerStatus")
	
	def __iterateHardware(self, nodeName, cmd, *args):
		retries = 2
		print "cmd ", cmd, "args", args
		mycmd = "%s()" % (cmd)
		self.host = self.__getHostInfo(nodeName)
		hw = self.data.getHardwareCapabilities(nodeName)
		#  getHardwareCapabilities return a list of lists with 
		#  [0] = hw method
		#  [1] = hw method userid
		#  [2] = hw method password
		for i in hw:
			inst = instantiateImplementation(self.config['hardwareControl'][i[0]]['class'], self.config, nodeName, self.host)
			a = "inst.%s" % mycmd
			for count in range(retries):
				doit = eval(a)
				if doit == -1:
					self.log.error("%s method failed (%s) on %s (attempt %s)", i[0], mycmd, nodeName, count)
					continue
				if doit  > 0:
					break
				else:
					self.log.error("%s method failed (%s) on %s (attempt %s)", i[0], mycmd, nodeName, count)
			if doit > 0:
				break

		return doit

	def runCmd(self, nodeName, cmd, *args):
		self.__iterateHardware(nodeName, cmd, args)

	def powerOn(self, nodeName):
		self.__iterateHardware(nodeName, "powerOn")

	def powerOff(self, nodeName):
		self.__iterateHardware(nodeName, "powerOff")

	def powerCycle(self, nodeName):
		self.__iterateHardware(nodeName, "powerCycle")
		
	def powerReset(self, nodeName):
		self.__iterateHardware(nodeName, "powerReset")
		
	def activateConsole(self, nodeName):
		pass
