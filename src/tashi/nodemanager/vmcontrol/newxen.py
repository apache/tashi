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

import cPickle
import logging
import os
import threading
import random
import select
import signal
import socket
import subprocess
import sys
import time

import inspect			# used to get current function
def currentFunction(n=1):
	# get the name of our caller, e.g. the requesting function
	return inspect.stack()[n][3]

from tashi.services.ttypes import *
from tashi.util import broken, isolatedRPC
from vmcontrolinterface import VmControlInterface

log = logging.getLogger(__file__)


import xenpv

class NewXen(VmControlInterface):
	"""VM Control for Paravirtualized Xen"""

	def __init__(self, config, dfs, cm):
		"""Base init function -- it handles inserting config and dfs 
		   into the object as well as checking that the class type is 
		   not VmControlInterface"""
		print 'NewXen::init called'
		if self.__class__ is VmControlInterface:
			raise NotImplementedError
		self.config = config
		self.dfs = dfs
		self.cm = cm
		self.xenpv = xenpv.XenPV(self.config, self.dfs, self.cm)
	
	def instantiateVm(self, instance):
		"""Takes an InstanceConfiguration, creates a VM based on it, 
		   and returns the vmId"""
		print 'XenPV::%s called' % currentFunction()
		# FIXME: this is NOT the right way to get out hostId
		self.hostId = instance.hostId
		return self.xenpv.instantiateVm(instance)

	
	def suspendVm(self, vmId, target, suspendCookie=None):
		"""Suspends a vm to the target on the dfs, including the 
		   suspendCookie"""
		print 'XenPV::%s called' % currentFunction()		
		return self.xenpv.suspendVM(vmId, target, suspendCookie)


	def resumeVm(self, source):
		"""Resumes a vm from the dfs and returns the newly created 
		   vmId as well as the suspendCookie in a tuple"""
		print 'XenPV::%s called' % currentFunction()
		return self.xenpv.resumeVM(source)
	
	def prepReceiveVm(self, instance, source):
		"""First call made as part of vm migration -- it is made to 
		   the target machine and it returns a transportCookie"""
		print 'XenPV::%s called' % currentFunction()
		return self.xenpv.prepReceiveVm(instance, source)
	
	def migrateVm(self, vmId, target, transportCookie):
		"""Second call made as part of a vm migration -- it is made 
		   to the source machine and it does not return until the 
		   migration is complete"""
		print 'XenPV::%s called' % currentFunction()
		return self.xenpv.migrateVm(vmId, target,transportCookie)
	
	def receiveVm(self, transportCookie):
		"""Third call made as part of a vm migration -- it is made to 
		   the target machine and it does not return until the 
		   migration is complete, it returns the new vmId"""
		print 'XenPV::%s called' % currentFunction()
		return self.xenpv.receiveVm(transportCookie)
	
	def pauseVm(self, vmId):
		"""Pauses a vm and returns nothing"""
		print 'XenPV::%s called' % currentFunction()
		return self.xenpv.pauseVM(vmId)
	
	def unpauseVm(self, vmId):
		"""Unpauses a vm and returns nothing"""
		print 'XenPV::%s called' % currentFunction()
		return self.xenpv.unpauseVM(vmId)
	
	def shutdownVm(self, vmId):
		"""Performs a clean shutdown on a vm and returns nothing"""
		print 'XenPV::%s called' % currentFunction()
		return self.xenpv.shutdownVM(vmId)
		
	
	def destroyVm(self, vmId):
		"""Forces the exit of a vm and returns nothing"""
		print 'XenPV::%s called' % currentFunction()
		return self.xenpv.destroyVM(vmId)
	
	def getVmInfo(self, vmId):
		"""Returns the InstanceConfiguration for the given vmId"""
		print 'XenPV::%s called' % currentFunction()
		return self.xenpv.getVMInfo(vmId)
	
	def listVms(self):
		"""Returns a list of vmIds to the caller"""
		print 'XenPV::%s called' % currentFunction()
		return self.xenpv.listVMs()
