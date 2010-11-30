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

import threading
import logging

from tashi.util import instantiateImplementation

'''  Physical cluster manager/Virtual cluster manager service '''
class pcmService(object):
	'''  Phycical cluster manager service '''
	def __init__(self, config, data):
		self.config = config
		self.data = data
		self.log = logging.getLogger(__name__)
		self.hardware = instantiateImplementation("zoni.hardware.systemmanagement.SystemManagement", self.config, self.data)

		print self.data.conn
		#if self.data._isDb:
			#threading.Thread(target=self.data.keepAlive).start()

	#  auth domain and verify it can operate on domain
	def __key2vcm(self, key):
		return self.data.getDomainFromKey(key)

	def releaseResource(self, key, nodeName):
		vcm = self.__key2vcm(key)
		'''  Check for keys later  and remove vcm '''
		self.log.info("VCM_RELEASE_RESOURCE: VCM %s RESOURCE %s" % (vcm, nodeName))
		self.data.releaseNode(nodeName)
			
	def requestResources(self, key, specs, quantity):
		vcm = self.__key2vcm(key)
		node = specs
		'''  Check for keys later  '''
		self.log.info("VCM_REQUEST_RESOURCE: VCM %s RESOURCE %s(%s)" % (vcm, specs, quantity))
		# go to scheduler val = self.agent.requestResource(specs)
		if val:
			return 1
		return 0

	def getResources(self, key):
		vcm = self.__key2vcm(key)
		self.log.info("VCM_QUERY_ALL: VCM %s" % (vcm))
		print self.data.getAvailableResources()
		return self.data.getAvailableResources()

	def getMyResources(self, key):
		vcm = self.__key2vcm(key)
		self.log.info("VCM_QUERY_OWN: VCM %s" % (vcm))
		print self.data.getMyResources(key)
		return self.data.getMyResources(key)

	def powerOn(self, key, nodeName):
		vcm = self.__key2vcm(key)
		self.log.info("VCM_COMMAND_POWER_ON: VCM %s" % (vcm))
		self.hardware.powerOn(nodeName)

	def powerReset(self, key, nodeName):
		vcm = self.__key2vcm(key)
		self.log.info("VCM_COMMAND_POWER_RESET: VCM %s" % (vcm))
		self.hardware.powerReset(nodeName)
		

	def powerOff(self, key, nodeName):
		vcm = self.__key2vcm(key)
		self.log.info("VCM_COMMAND_POWER_OFF: VCM %s" % (vcm))
		self.hardware.powerOff(nodeName)

	#def selectBootImage

class vcmService(object):
	def __init__(self, config):
		self.config = config


	def requestResource(self, nodeName):
		pass
		
