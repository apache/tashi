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

class VmControlInterface(object):
	"""Interface description for VM controllers -- like Qemu, Xen, etc"""

	def __init__(self, config, dfs, nm):
		"""Base init function -- it handles inserting config and dfs 
		   into the object as well as checking that the class type is 
		   not VmControlInterface"""
		if self.__class__ is VmControlInterface:
			raise NotImplementedError
		self.config = config
		self.dfs = dfs
		self.nm = nm

	def getInstances(self):
		"""Will return a dict of instances by vmId to the caller"""
		raise NotImplementedError
	
	def instantiateVm(self, instance):
		"""Takes an InstanceConfiguration, creates a VM based on it, 
		   and returns the vmId"""
		raise NotImplementedError
	
	def suspendVm(self, vmId, target, suspendCookie=None):
		"""Suspends a vm to the target on the dfs, including the 
		   suspendCookie"""
		raise NotImplementedError
	
	def resumeVmHelper(self, instance, source):
		"""Used to finish up the resume process, it is called outside 
		   of the original RPC to avoid timeouts, it returns nothing"""
		raise NotImplementedError
	
	def resumeVm(self, instance, source):
		"""Resumes a vm from the dfs and returns the vmId"""
		raise NotImplementedError
	
	def prepReceiveVm(self, instance, source):
		"""First call made as part of vm migration -- it is made to 
		   the target machine and it returns a transportCookie"""
		raise NotImplementedError
	
	def migrateVm(self, vmId, target, transportCookie):
		"""Second call made as part of a vm migration -- it is made 
		   to the source machine and it does not return until the 
		   migration is complete"""
		raise NotImplementedError
	
	def receiveVm(self, transportCookie):
		"""Third call made as part of a vm migration -- it is made to 
		   the target machine and it does not return until the 
		   migration is complete, it returns the new vmId"""
		raise NotImplementedError
	
	def pauseVm(self, vmId):
		"""Pauses a vm and returns nothing"""
		raise NotImplementedError
	
	def unpauseVm(self, vmId):
		"""Unpauses a vm and returns nothing"""
		raise NotImplementedError
	
	def shutdownVm(self, vmId):
		"""Performs a clean shutdown on a vm and returns nothing"""
		raise NotImplementedError
	
	def destroyVm(self, vmId):
		"""Forces the exit of a vm and returns nothing"""
		raise NotImplementedError
	
	def listVms(self):
		"""Returns a list of vmIds to the caller"""
		raise NotImplementedError
	
	def getHostInfo(self, service):
		"""Returns a Host object for the current host"""
		raise NotImplementedError
	
	def getStats(self, vmId):
		"""Returns a dictionary containing stats about the guest (ie. 
		   CPU utilization, network utilization, memory usage, etc.)"""
		raise NotImplementedError
