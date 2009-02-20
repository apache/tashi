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

import threading

from tashi.services.ttypes import *
from tashi.clustermanager.data import DataInterface

class FromConfig(DataInterface):
	def __init__(self, config):
		DataInterface.__init__(self, config)
		self.hosts = {}
		self.instances = {}
		self.networks = {}
		self.users = {}
#		self.locks = {}
		self.lockNames = {}
		self.instanceLock = threading.Lock()
		self.lockNames[self.instanceLock] = "instanceLock"
		self.instanceIdLock = threading.Lock()
		self.lockNames[self.instanceIdLock] = "instanceIdLock"
		self.maxInstanceId = 1
		for (name, value) in self.config.items("FromConfig"):
			name = name.lower()
			if (name.startswith("host")):
				host = eval(value)
				if (host.__class__ is not Host):
					raise ValueError, "Entry %s is not a Host" % (name)
				host._lock = threading.Lock()
				self.lockNames[host._lock] = "h%d" % (host.id)
				self.hosts[host.id] = host
			if (name.startswith("network")):
				network = eval(value)
				if (network.__class__ is not Network):
					raise ValueError, "Entry %s is not a Network" % (name)
				self.networks[network.id] = network
			if (name.startswith("user")):
				user = eval(value)
				if (user.__class__ is not User):
					raise ValueError, "Entry %s is not a User" % (name)
				self.users[user.id] = user
	
	def acquireLock(self, l):
		l.acquire()
#		self.locks[l] = threading.currentThread()
	
	def releaseLock(self, l):
#		del self.locks[l]
		l.release()
	
	def getNewInstanceId(self):
		self.acquireLock(self.instanceIdLock)
		instanceId = self.maxInstanceId
		self.maxInstanceId = self.maxInstanceId + 1
		self.releaseLock(self.instanceIdLock)
		return instanceId
	
	def registerInstance(self, instance):
		self.acquireLock(self.instanceLock)
		try:
			if (instance.id is not None and instance.id not in self.instances):
				self.acquireLock(self.instanceIdLock)
				if (instance.id >= self.maxInstanceId):
					self.maxInstanceId = instance.id + 1
				self.releaseLock(self.instanceIdLock)
			else:
				instance.id = self.getNewInstanceId()
			instance._lock = threading.Lock()
			self.lockNames[instance._lock] = "i%d" % (instance.id)
			self.acquireLock(instance._lock)
			self.instances[instance.id] = instance
		finally:
			self.releaseLock(self.instanceLock)
		return instance
	
	def acquireInstance(self, instanceId):
		self.acquireLock(self.instanceLock)
		try:
			instance = self.instances.get(instanceId, None)
			if (instance is None):
				raise TashiException(d={'errno':Errors.NoSuchInstanceId,'msg':"No such instanceId - %d" % (instanceId)})
			self.acquireLock(instance._lock)
		finally:
			self.releaseLock(self.instanceLock)
		return instance
	
	def releaseInstance(self, instance):
		try:
			if (instance.id not in self.instances): # MPR: should never be true, but good to check
				raise TashiException(d={'errno':Errors.NoSuchInstanceId,'msg':"No such instanceId - %d" % (instanceId)})
		finally:
			self.releaseLock(instance._lock)
	
	def removeInstance(self, instance):
		self.acquireLock(self.instanceLock)
		try:
			del self.instances[instance.id]
			self.releaseLock(instance._lock)
		finally:
			self.releaseLock(self.instanceLock)
	
	def acquireHost(self, hostId):
		host = self.hosts.get(hostId, None)
		if (host is None):
			raise TashiException(d={'errno':Errors.NoSuchHostId,'msg':"No such hostId - %s" % (hostId)})
		self.acquireLock(host._lock)
		return host
	
	def releaseHost(self, host):
		try:
			if (host.id not in self.hosts): # MPR: should never be true, but good to check
				raise TashiException(d={'errno':Errors.NoSuchHostId,'msg':"No such hostId - %s" % (hostId)})
		finally:
			self.releaseLock(host._lock)
	
	def getHosts(self):
		return self.hosts
	
	def getHost(self, id):
		host = self.hosts.get(id, None)
		if (not host):
			raise TashiException(d={'errno':Errors.NoSuchHostId,'msg':"No such hostId - %s" % (id)})
		return host

	def getInstances(self):
		return self.instances
	
	def getInstance(self, id):
		instance = self.instances.get(id, None)
		if (not instance):
			raise TashiException(d={'errno':Errors.NoSuchInstanceId,'msg':"No such instanceId - %d" % (id)})
		return instance
	
	def getNetworks(self):
		return self.networks
	
	def getNetwork(self, id):
		return self.networks[id]
	
	def getUsers(self):
		return self.users
	
	def getUser(self, id):
		return self.users[id]
