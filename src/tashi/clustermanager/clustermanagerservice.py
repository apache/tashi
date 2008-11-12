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

from __future__ import with_statement

from datetime import datetime
from random import randint
from socket import gethostname
from thrift.transport.TSocket import TSocket
from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.transport.TTransport import TBufferedTransport
import logging
import threading
import time

from tashi.messaging.thriftmessaging import MessageBrokerThrift
from tashi.messaging.tashimessaging import TashiLogHandler
from tashi.services.ttypes import Errors, InstanceState, HostState, TashiException
from tashi.services import nodemanagerservice
from tashi import boolean, convertExceptions, ConnectionManager, vmStates, timed

def RPC(oldFunc):
	return convertExceptions(oldFunc)

class ClusterManagerService():
	"""RPC service for the ClusterManager"""
	
	def __init__(self, config, data):
		self.config = config
		self.data = data
		self.proxy = ConnectionManager(nodemanagerservice.Client, int(self.config.get('ClusterManager', 'nodeManagerPort')))
		self.convertExceptions = boolean(config.get('ClusterManagerService', 'convertExceptions'))
		self.log = logging.getLogger(__name__)
		self.messageHandler = TashiLogHandler(config)
		self.log.addHandler(self.messageHandler)
		self.lastContacted = {}
		self.decayedHosts = {}
		self.decayedInstances = {}
		self.expireHostTime = float(self.config.get('ClusterManagerService', 'expireHostTime'))
		self.allowDecayed = float(self.config.get('ClusterManagerService', 'allowDecayed'))
		now = time.time()
		for instance in self.data.getInstances().itervalues():
			instanceId = instance.id
			instance = self.data.acquireInstance(instanceId)
			instance.decayed = False
			self.stateTransition(instance, None, InstanceState.Orphaned)
			self.data.releaseInstance(instance)
		for host in self.data.getHosts().itervalues():
			hostId = host.id
			host = self.data.acquireHost(hostId)
			host.up = False
			host.decayed = False
			self.data.releaseHost(host)
		self.decayLock = threading.Lock()
		threading.Thread(target=self.monitorHosts).start()

	def stateTransition(self, instance, old, cur):
		if (old and instance.state != old):
			self.data.releaseInstance(instance)
			raise TashiException(d={'errno':Errors.IncorrectVmState,'msg':"VmState is not %s - it is %s" % (vmStates[old], vmStates[instance.state])})
		instance.state = cur

	def updateDecay(self, set, obj):
		now = time.time()
		self.decayLock.acquire()
		if (obj.decayed and obj.id not in set):
			set[obj.id] = now
		elif (not obj.decayed and obj.id in set):
			del set[obj.id]
		self.decayLock.release()
		

	def monitorHosts(self):
		# XXX: retry multiple hosts (iterate through them even with an exception)
		while True:
			now = time.time()
			sleepFor = min(self.expireHostTime, self.allowDecayed)
			try:
				for k in self.lastContacted.keys():
					if (self.lastContacted[k] < (now-self.expireHostTime)):
						host = self.data.acquireHost(k)
						try: 
							self.log.warning('Host %s has expired after %f seconds' % (host.name, now-self.expireHostTime))
							for instanceId in [instance.id for instance in self.data.getInstances().itervalues() if instance.hostId == host.id]:
								instance = self.data.acquireInstance(instanceId)
								instance.decayed = True
								self.stateTransition(instance, None, InstanceState.Orphaned)
								self.data.releaseInstance(instance)
							host.up = False
							host.decayed = False
						finally:
							self.data.releaseHost(host)
						del self.lastContacted[k]
					else:
						sleepFor = min(self.lastContacted[k] + self.expireHostTime - now, sleepFor)
				for hostId in self.decayedHosts.keys():
					if (self.decayedHosts[hostId] < (now-self.allowDecayed)):
						host = self.data.getHost(hostId)
						self.log.warning('Fetching state from host %s because it is decayed' % (host.name))
						hostProxy = self.proxy[host.name]
						oldInstances = [i for i in self.data.getInstances().values() if i.hostId == host.id]
						instances = [hostProxy.getVmInfo(vmId) for vmId in hostProxy.listVms()]
						instanceIds = [i.id for i in instances]
						for instance in instances:
							if (instance.id not in self.data.getInstances()):
								instance.hostId = host.id
								instance = self.data.registerInstance(instance)
								self.data.releaseInstance(instance)
						for instance in oldInstances:
							if (instance.id not in instanceIds):
								instance = self.data.acquireInstance(instance.id)
								self.data.removeInstance(instance)
						self.decayedHosts[hostId] = now
					else:
						sleepFor = min(self.decayedHosts[hostId] + self.allowDecayed - now, sleepFor)
				for instanceId in self.decayedInstances.keys():
					try:
						if (self.decayedInstances[instanceId] < (now-self.allowDecayed)):
							self.log.warning('Fetching state on instance %d because it is decayed' % (instanceId))
							try:
								instance = self.data.getInstance(instanceId)
							except TashiException, e:
								if (e.errno == Errors.NoSuchInstanceId):
									del self.decayedInstances[instanceId]
									continue
								else:
									raise
							host = self.data.getHost(instance.hostId)
							hostProxy = self.proxy[host.name]
							instance = hostProxy.getVmInfo(instance.vmId)
							oldInstance = self.data.acquireInstance(instanceId)
							oldInstance.state = instance.state
							self.data.releaseInstance(oldInstance)
							self.decayedInstances[instanceId] = now
						else:
							sleepFor = min(self.decayedInstances[instanceId] + self.allowDecayed - now, sleepFor)
					except Exception, e:
						self.log.exception('Exception in monitorHosts trying to get instance information')
			except Exception, e:
				self.log.exception('Exception in monitorHosts')
			time.sleep(sleepFor)
	
	@RPC
	def createVm(self, instance):
		"""Function to add a VM to the list of pending VMs"""
		instance.state = InstanceState.Pending
		# XXX: Synchronize on MachineType
		instance.typeObj = self.data.getMachineTypes()[instance.type]
		instance.decayed = False
		instance = self.data.registerInstance(instance)
		self.data.releaseInstance(instance)
		return instance
	
	@RPC
	def shutdownVm(self, instanceId):
		instance = self.data.acquireInstance(instanceId)
		self.stateTransition(instance, InstanceState.Running, InstanceState.ShuttingDown)
		self.data.releaseInstance(instance)
		hostname = self.data.getHost(instance.hostId).name
		try:
			self.proxy[hostname].shutdownVm(instance.vmId)
		except Exception:
			self.log.exception('shutdownVm failed for host %s vmId %d' % (instance.hostname, instance.vmId))
			raise
		return
	
	@RPC
	def destroyVm(self, instanceId):
		instance = self.data.acquireInstance(instanceId)
		if (instance.state is InstanceState.Pending or instance.state is InstanceState.Held):
			self.data.removeInstance(instance)
		elif (instance.state is InstanceState.Activating):
			self.stateTransition(instance, InstanceState.Activating, InstanceState.Destroying)
			self.data.releaseInstance(instance)
		else:
			self.stateTransition(instance, None, InstanceState.Destroying)
			self.data.releaseInstance(instance)
			hostname = self.data.getHost(instance.hostId).name
			try:
				self.proxy[hostname].destroyVm(instance.vmId)
			except Exception:
				self.log.exception('destroyVm failed for host %s vmId %d' % (hostname, instance.vmId))
				raise
		return
	
	@RPC
	def suspendVm(self, instanceId, destination):
		instance = self.data.acquireInstance(instanceId)
		self.stateTransition(instance, InstanceState.Running, InstanceState.Suspending)
		self.data.releaseInstance(instance)
		suspendCookie = ""
		hostname = self.data.getHost(instance.hostId).name
		try:
			self.proxy[hostname].suspendVm(instance.vmId, destination, suspendCookie)
		except Exception:
			self.log.exception('suspendVm failed for host %s vmId %d' % (hostname, instance.vmId))
			raise
		return
	
	@RPC
	def resumeVm(self, instance, source):
		instance.state = InstanceState.Pending
		# XXX: Synchronize on MachineType
		instance.typeObj = self.data.getMachineTypes()[instance.type]
		instance.decayed = False
		instance.hints['__resume_source'] = source
		instance = self.data.registerInstance(instance)
		self.data.releaseInstance(instance)
		return instance
	
	@RPC
	def migrateVm(self, instanceId, targetHostId):
		instance = self.data.acquireInstance(instanceId)
		try:
			# FIXME: should these be acquire/release host?
			targetHost = self.data.getHost(targetHostId)
			sourceHost = self.data.getHost(instance.hostId)
			# FIXME: Are these the correct state transitions?
		except:
			self.data.releaseInstance(instance)
			raise
		self.stateTransition(instance, InstanceState.Running, InstanceState.MigratePrep)
		self.data.releaseInstance(instance)
		try:
			# Prepare the target
			cookie = self.proxy[targetHost.name].prepReceiveVm(instance, sourceHost)
		except Exception, e:
			self.log.exception('prepReceiveVm failed')
			raise
		instance = self.data.acquireInstance(instance.id)
		self.stateTransition(instance, InstanceState.MigratePrep, InstanceState.MigrateTrans)
		self.data.releaseInstance(instance)
		try:
			# Send the VM
			self.proxy[sourceHost.name].migrateVm(instance.vmId, targetHost, cookie)
		except Exception, e:
			self.log.exception('migrateVm failed')
			raise
		#instance = self.data.acquireInstance(instance.id)
		#try:
		#	instance.hostId = targetHost.id
		#finally:
		#	self.data.releaseInstance(instance)
		try:
			# Notify the target
			vmId = self.proxy[targetHost.name].receiveVm(instance, cookie)
		except Exception, e:
			self.log.exception('receiveVm failed')
			raise
		#print 'VM %i Migrated!  New vmId=%i, new hostId=%i' % (instance.id, vmId, targetHostId)
		return
	
	@RPC
	def pauseVm(self, instanceId):
		instance = self.data.acquireInstance(instanceId)
		self.stateTransition(instance, InstanceState.Running, InstanceState.Pausing)
		self.data.releaseInstance(instance)
		hostname = self.data.getHost(instance.hostId).name
		try:
			self.proxy[hostname].pauseVm(instance.vmId)
		except Exception:
			self.log.exception('pauseVm failed on host %s with vmId %d' % (hostname, instance.vmId))
			raise
		instance = self.data.acquireInstance(instanceId)
		self.stateTransition(instance, InstanceState.Pausing, InstanceState.Paused)
		self.data.releaseInstance(instance)
		return

	@RPC
	def unpauseVm(self, instanceId):
		instance = self.data.acquireInstance(instanceId)
		self.stateTransition(instance, InstanceState.Paused, InstanceState.Unpausing)
		self.data.releaseInstance(instance)
		hostname = self.data.getHost(instance.hostId).name
		try:
			self.proxy[hostname].unpauseVm(instance.vmId)
		except Exception:
			self.log.exception('unpauseVm failed on host %s with vmId %d' % (hostname, instance.vmId))
			raise
		instance = self.data.acquireInstance(instanceId)
		self.stateTransition(instance, InstanceState.Unpausing, InstanceState.Running)
		self.data.releaseInstance(instance)
		return
	
	@RPC
	def getMachineTypes(self):
		return self.data.getMachineTypes().values()
	
	@RPC
	def getHosts(self):
		return self.data.getHosts().values()
	
	@RPC
	def getNetworks(self):
		return self.data.getNetworks().values()
	
	@RPC
	def getUsers(self):
		return self.data.getUsers().values()
	
	@RPC
	def getInstances(self):
		instances = self.data.getInstances().values()
		for instance in instances:
			if (instance.hostId):
				instance.hostObj = self.data.getHost(instance.hostId)
			else:
				instance.hostObj = None
			if (instance.userId):
				instance.userObj = self.data.getUser(instance.userId)
			else:
				instance.userObj = None
		return instances
	
#	@timed
	@RPC
	def registerNodeManager(self, host, instances):
		"""Called by the NM every so often as a keep-alive/state polling -- state changes here are NOT AUTHORITATIVE"""
		if (host.id == None):
			hostList = [h for h in self.data.getHosts().itervalues() if h.name == host.name]
			if (len(hostList) != 1):
				raise TashiException(d={'errno':Errors.NoSuchHost, 'msg':'A host with name %s is not identifiable' % (host.name)})
			host.id = hostList[0].id
		oldHost = self.data.acquireHost(host.id)
		if (oldHost.name != host.name):
			self.data.releaseHost(oldHost)
			raise TashiException(d={'errno':Errors.NoSuchHostId, 'msg':'Host id and hostname mismatch'})
		try:
			self.lastContacted[host.id] = time.time()
			oldHost.memory = host.memory
			oldHost.cores = host.cores
			oldHost.up = True
			oldHost.decayed = False
			for instance in instances:
				try:
					oldInstance = self.data.acquireInstance(instance.id)
				except TashiException, e:
					if (e.errno == Errors.NoSuchInstanceId):
						self.log.info('Host %s reported an instance %d that did not previously exist (decay)' % (host.name, instance.id))
						oldHost.decayed = True
						continue
						#oldInstance = self.data.registerInstance(instance)
					else:
						raise
				try:
					if (oldInstance.hostId != host.id):
						self.log.info('Host %s is claiming instance %d actually owned by hostId %s (decay)' % (host.name, oldInstance.id, str(oldInstance.hostId)))
						oldHost.decayed = True
						continue
					oldInstance.decayed = (oldInstance.state != instance.state)
					self.updateDecay(self.decayedInstances, oldInstance)
					if (oldInstance.decayed):
						self.log.info('State reported as %s instead of %s for instance %d on host %s (decay)' % (vmStates[instance.state], vmStates[oldInstance.state], instance.id, host.name))
				finally:
					self.data.releaseInstance(oldInstance)
			instanceIds = [instance.id for instance in instances]
			for instanceId in [instance.id for instance in self.data.getInstances().itervalues() if instance.hostId == host.id]:
				if (instanceId not in instanceIds):
					self.log.info('instance %d was not reported by host %s as expected (decay)' % (instanceId, host.name))
					instance = self.data.acquireInstance(instanceId)
					instance.decayed = True
					self.updateDecay(self.decayedInstances, instance)
					oldHost.decayed = True
					self.data.releaseInstance(instance)
		except Exception, e:
			oldHost.decayed = True
			raise
		finally:
			self.updateDecay(self.decayedHosts, oldHost)
			self.data.releaseHost(oldHost)
		return host.id
	
	@RPC
	def vmUpdate(self, instanceId, instance, oldState):
		try:
			oldInstance = self.data.acquireInstance(instanceId)
		except TashiException, e:
			if (e.errno == Errors.NoSuchInstanceId):
				self.log.exception('Got vmUpdate for unknown instanceId %d' % (instanceId))
				return
			else:
				raise
		if (instance.state == InstanceState.Exited):
			oldInstance.decayed = False
			self.updateDecay(self.decayedInstances, oldInstance)
			self.data.removeInstance(oldInstance)
			hostname = self.data.getHost(oldInstance.hostId).name
			if (oldInstance.state not in [InstanceState.ShuttingDown, InstanceState.Destroying, InstanceState.Suspending]):
				self.log.warning('Unexpected exit on %s of instance %d (vmId %d)' % (hostname, instanceId, oldInstance.vmId))
		else:
			if (instance.state):
				if (oldState and oldInstance.state != oldState):
					self.log.warning('Got vmUpdate of state from %s to %s, but the instance was previously %s' % (vmStates[oldState], vmStates[instance.state], vmStates[oldInstance.state]))
				oldInstance.state = instance.state
			if (instance.vmId):
				oldInstance.vmId = instance.vmId
			if (instance.hostId):
				oldInstance.hostId = instance.hostId
			oldInstance.decayed = False
			self.updateDecay(self.decayedInstances, oldInstance)
			self.data.releaseInstance(oldInstance)
		return
	
	@RPC
	def activateVm(self, instanceId, host):
		dataHost = self.data.acquireHost(host.id)
		if (dataHost.name != host.name):
			self.data.releaseHost(dataHost)
			raise TashiException(d={'errno':Errors.HostNameMismatch,'msg':"Mismatched target host"})
		if (not dataHost.up):
			self.data.releaseHost(dataHost)
			raise TashiException(d={'errno':Errors.HostNotUp,'msg':"Target host is not up"})
		if (dataHost.state != HostState.Normal):
			self.data.releaseHost(dataHost)
			raise TashiException(d={'errno':Errors.HostStateError,'msg':"Target host state is not normal"})
		self.data.releaseHost(dataHost)
		instance = self.data.acquireInstance(instanceId)
		self.stateTransition(instance, InstanceState.Pending, InstanceState.Activating)
		instance.hostId = host.id
		self.data.releaseInstance(instance)
		try:
			if ('__resume_source' in instance.hints):
				resumeVmId = self.proxy[host.name].resumeVm(instance, instance.hints['__resume_source'])
				vmId = resumeVmId.vmId
				suspendCookie = resumeVmId.suspendCookie
			else:
				vmId = self.proxy[host.name].instantiateVm(instance)
		except Exception, e:
			instance = self.data.acquireInstance(instanceId)
			if (instance.state is InstanceState.Destroying): # Special case for if destroyVm is called during initialization and initialization fails
				self.data.removeInstance(instance)
			else:
				self.stateTransition(instance, None, InstanceState.Held)
				instance.hostId = None
				self.data.releaseInstance(instance)
			raise
		instance = self.data.acquireInstance(instanceId)
		instance.vmId = vmId
		if (instance.state is InstanceState.Destroying): # Special case for if destroyVm is called during initialization
			self.data.releaseInstnace(instance)
			try:
				self.proxy[host.name].destroyVm(vmId)
			except Exception:
				self.log.exception('destroyVm failed for host %s vmId %d' % (host.name, instance.vmId))
				raise
		else:
			self.stateTransition(instance, InstanceState.Activating, InstanceState.Running)
			self.data.releaseInstance(instance)
		return
