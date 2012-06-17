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

#XXXstroucki: for compatibility with python 2.5
from __future__ import with_statement

import logging
import threading
import os
import ConfigParser

from tashi.rpycservices.rpyctypes import Host, Network, User, TashiException, Errors, HostState, Instance
from tashi.clustermanager.data import DataInterface

class FromConfig(DataInterface):
	def __init__(self, config):
		DataInterface.__init__(self, config)
		self.log = logging.getLogger(__name__)
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
		self.hostLocks = {}
		self.hostLock = threading.Lock()
		self.idLock = threading.Lock()
		if not self.config.has_section("FromConfig"):
			return
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
		if type(instance) is not Instance:
			self.log.exception("Argument is not of type Instance, but of type %s" % (type(instance)))
			raise TypeError

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
		if type(instance) is not Instance:
			self.log.exception("Argument is not of type Instance, but of type %s" % (type(instance)))
			raise TypeError

		try:
			if (instance.id not in self.instances): # MPR: should never be true, but good to check
				raise TashiException(d={'errno':Errors.NoSuchInstanceId,'msg':"No such instanceId - %d" % (instance.id)})
		finally:
			self.releaseLock(instance._lock)
	
	def removeInstance(self, instance):
		if type(instance) is not Instance:
			self.log.exception("Argument is not of type Instance, but of type %s" % (type(instance)))
			raise TypeError

		self.acquireLock(self.instanceLock)
		try:
			del self.instances[instance.id]
			self.releaseLock(instance._lock)
		finally:
			self.releaseLock(self.instanceLock)
	
	def acquireHost(self, hostId):
		if type(hostId) is not int:
			self.log.exception("Argument is not of type int, but of type %s" % (type(hostId)))
			raise TypeError

		self.hostLock.acquire()
		host = self.hosts.get(hostId, None)
		if (host is None):
			raise TashiException(d={'errno':Errors.NoSuchHostId,'msg':"No such hostId - %s" % (hostId)})
		# hostLocks dict added when registerHost was implemented, otherwise newly added hosts don't have _lock 
		self.hostLocks[hostId] = self.hostLocks.get(hostId, threading.Lock())
		host._lock = self.hostLocks[host.id]
		self.acquireLock(host._lock)
		return host

	
	def releaseHost(self, host):
		if type(host) is not Host:
			self.log.exception("Argument is not of type Host, but of type %s" % (type(host)))
			raise TypeError

		try:
			if (host.id not in self.hosts): # MPR: should never be true, but good to check
				raise TashiException(d={'errno':Errors.NoSuchHostId,'msg':"No such hostId - %s" % (host.id)})
		finally:
			self.save()
			self.releaseLock(host._lock)
			self.hostLock.release()
	
	def getHosts(self):
		return self.hosts
	
	def getHost(self, _id):
		host = self.hosts.get(_id, None)
		if (not host):
			raise TashiException(d={'errno':Errors.NoSuchHostId,'msg':"No such hostId - %s" % (_id)})
		return host

	def getInstances(self):
		return self.instances
	
	def getInstance(self, _id):
		instance = self.instances.get(_id, None)
		if (not instance):
			raise TashiException(d={'errno':Errors.NoSuchInstanceId,'msg':"No such instanceId - %d" % (_id)})
		return instance
	
	def getNetworks(self):
		return self.networks
	
	def getNetwork(self, _id):
		return self.networks[_id]
	
	def getUsers(self):
		return self.users
	
	def getUser(self, _id):
		return self.users[_id]
		
	def registerHost(self, hostname, memory, cores, version):
		self.hostLock.acquire()
		for _id in self.hosts.keys():
			if self.hosts[_id].name == hostname:
				host = Host(d={'id':_id,'name':hostname,'state':HostState.Normal,'memory':memory,'cores':cores,'version':version})
				self.hosts[_id] = host
				self.save()
				self.hostLock.release()
				return _id, True
		_id = self.getNewId("hosts")
		self.hosts[_id] = Host(d={'id':_id,'name':hostname,'state':HostState.Normal,'memory':memory,'cores':cores,'version':version})
		self.save()
		self.hostLock.release()
		return _id, False
		
	def unregisterHost(self, hostId):
		self.hostLock.acquire()
		del self.hosts[hostId]
		self.save()
		self.hostLock.release()

	def getNewId(self, table):
		""" Generates id for a new object. For example for hosts and users.  
		"""
		self.idLock.acquire()
		maxId = 0
		l = []
		if(table == "hosts"):
			for _id in self.hosts.keys():
				l.append(_id)
				if _id >= maxId:
					maxId = _id
		l.sort() # sort to enable comparing with range output
		# check if some id is released:
		t = range(maxId + 1)
		t.remove(0)
		if l != t and l != []:
			releasedIds = filter(lambda x : x not in l, t)
			self.idLock.release()
			return releasedIds[0]
		else:
			self.idLock.release()
			return maxId + 1
		
	def save(self):
		# XXXstroucki: a relative path? Where does it go
		# and in what order does it get loaded
		fileName = "./etc/Tashi.cfg"
		if not os.path.exists(fileName):
			filehandle = open(fileName, "w")
			filehandle.write("[FromConfig]")
			filehandle.close()	
		parser = ConfigParser.ConfigParser()
		parser.read(fileName)
		
		if not parser.has_section("FromConfig"):
			parser.add_section("FromConfig")
		
		hostsInFile = []
		for (name, __value) in parser.items("FromConfig"):
			name = name.lower()
			if (name.startswith("host")):
				hostsInFile.append(name)
				
		for h in hostsInFile:
			parser.remove_option("FromConfig", h)
			
		for hId in self.hosts.keys():
			host = self.hosts[hId]
			hostPresentation = "Host(d={'id':%s,'name':'%s','state':HostState.Normal,'memory':%s,'cores':%s,'version':'%s'})" % (hId, host.name, host.memory, host.cores, host.version)
			parser.set("FromConfig", "host%s" % hId, hostPresentation)
		
		with open(fileName, 'wb') as configfile:
			parser.write(configfile)
		
		

