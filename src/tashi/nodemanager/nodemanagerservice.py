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
import socket
import sys
import threading
import time

from tashi.rpycservices.rpyctypes import Host, HostState, InstanceState, TashiException, Errors, Instance
from tashi.nodemanager import RPC
from tashi import boolean, vmStates, logged, ConnectionManager, timed
import tashi


class NodeManagerService(object):
	"""RPC handler for the NodeManager
	   
	   Perhaps in the future I can hide the dfs from the 
	   VmControlInterface and do all dfs operations here?"""
	
	def __init__(self, config, vmm):
		self.config = config
		self.vmm = vmm
		self.cmHost = config.get("NodeManagerService", "clusterManagerHost")
		self.cmPort = int(config.get("NodeManagerService", "clusterManagerPort"))
		self.authAndEncrypt = boolean(config.get('Security', 'authAndEncrypt'))
		if self.authAndEncrypt:
			self.username = config.get('AccessClusterManager', 'username')
			self.password = config.get('AccessClusterManager', 'password')
		else:
			self.username = None
			self.password = None
		self.log = logging.getLogger(__file__)
		self.convertExceptions = boolean(config.get('NodeManagerService', 'convertExceptions'))
		self.registerFrequency = float(config.get('NodeManagerService', 'registerFrequency'))
		self.infoFile = self.config.get('NodeManagerService', 'infoFile')
		self.statsInterval = float(self.config.get('NodeManagerService', 'statsInterval'))
		self.id = None
		self.notifyCM = []
		self.loadVmInfo()
		vmList = self.vmm.listVms()
		for vmId in vmList:
			if (vmId not in self.instances):
				self.log.warning('vmcontrol backend reports additional vmId %d' % (vmId))
				self.instances[vmId] = Instance(d={'vmId':vmId,'id':-1})
		for vmId in self.instances.keys():
			if (vmId not in vmList):
				self.log.warning('vmcontrol backend does not report %d' % (vmId))
				self.vmStateChange(vmId, None, InstanceState.Exited)
		self.registerHost()
		threading.Thread(target=self.backupVmInfoAndFlushNotifyCM).start()
		threading.Thread(target=self.registerWithClusterManager).start()
		threading.Thread(target=self.statsThread).start()
	
	def loadVmInfo(self):
		try:
			f = open(self.infoFile, "r")
			data = f.read()
			f.close()
			self.instances = cPickle.loads(data)
		except Exception, e:
			self.log.warning('Failed to load VM info from %s' % (self.infoFile))
			self.instances = {}
	
	def saveVmInfo(self):
		try:
			data = cPickle.dumps(self.instances)
			f = open(self.infoFile, "w")
			f.write(data)
			f.close()
		except Exception, e:
			self.log.exception('Failed to save VM info to %s' % (self.infoFile))
	
	def vmStateChange(self, vmId, old, cur):
		instance = self.getInstance(vmId)
		if (old and instance.state != old):
			self.log.warning('VM state was %s, call indicated %s' % (vmStates[instance.state], vmStates[old]))
		if (cur == InstanceState.Exited):
			del self.instances[vmId]
		instance.state = cur
		newInst = Instance(d={'state':cur})
		success = lambda: None
		try:
			cm = ConnectionManager(self.username, self.password, self.cmPort)[self.cmHost]
			cm.vmUpdate(instance.id, newInst, old)
		except Exception, e:
			self.log.exception('RPC failed for vmUpdate on CM')
			self.notifyCM.append((instance.id, newInst, old, success))
		else:
			success()
		return True
	
	def backupVmInfoAndFlushNotifyCM(self):
		cm = ConnectionManager(self.username, self.password, self.cmPort)[self.cmHost]
		while True:
			start = time.time()
			try:
				self.saveVmInfo()
			except Exception, e:
				self.log.exception('Failed to save VM info')
			try:
				notifyCM = []
				try:
					while (len(self.notifyCM) > 0):
						(instanceId, newInst, old, success) = self.notifyCM.pop(0)
						try:
							cm.vmUpdate(instanceId, newInst, old)
						except TashiException, e:
							notifyCM.append((instanceId, newInst, old, success))
							if (e.errno != Errors.IncorrectVmState):
								raise
						except:
							notifyCM.append((instanceId, newInst, old, success))
							raise
						else:
							success()
				finally:
					self.notifyCM = self.notifyCM + notifyCM
			except Exception, e:
				self.log.exception('Failed to register with the CM')
			toSleep = start - time.time() + self.registerFrequency
			if (toSleep > 0):
				time.sleep(toSleep)
	
	def registerWithClusterManager(self):
		cm = ConnectionManager(self.username, self.password, self.cmPort)[self.cmHost]
		while True:
			start = time.time()
			try:
				host = self.vmm.getHostInfo(self)
				instances = self.instances.values()
				self.id = cm.registerNodeManager(host, instances)
			except Exception, e:
				self.log.exception('Failed to register with the CM')
			toSleep = start - time.time() + self.registerFrequency
			if (toSleep > 0):
				time.sleep(toSleep)
	
	def getInstance(self, vmId):
		instance = self.instances.get(vmId, None)
		if (instance is None):
			raise TashiException(d={'errno':Errors.NoSuchVmId,'msg':"There is no vmId %d on this host" % (vmId)})
		return instance
	
	def instantiateVm(self, instance):
		vmId = self.vmm.instantiateVm(instance)
		instance.vmId = vmId
		instance.state = InstanceState.Running
		self.instances[vmId] = instance
		return vmId
	
	def suspendVm(self, vmId, destination):
		instance = self.getInstance(vmId)
		instance.state = InstanceState.Suspending
		threading.Thread(target=self.vmm.suspendVm, args=(vmId, destination)).start()
	
	def resumeVmHelper(self, instance, name):
		self.vmm.resumeVmHelper(instance, name)
		instance.state = InstanceState.Running
		newInstance = Instance(d={'id':instance.id,'state':instance.state})
		success = lambda: None
		cm = ConnectionManager(self.username, self.password, self.cmPort)[self.cmHost]
		try:
			cm.vmUpdate(newInstance.id, newInstance, InstanceState.Resuming)
		except Exception, e:
			self.log.exception('vmUpdate failed in resumeVmHelper')
			self.notifyCM.append((newInstance.id, newInstance, InstanceState.Resuming, success))
		else:
			success()
	
	def resumeVm(self, instance, name):
		instance.state = InstanceState.Resuming
		instance.hostId = self.id
		try:
			instance.vmId = self.vmm.resumeVm(instance, name)
			self.instances[instance.vmId] = instance
			threading.Thread(target=self.resumeVmHelper, args=(instance, name)).start()
		except:
			self.log.exception('resumeVm failed')
			raise TashiException(d={'errno':Errors.UnableToResume,'msg':"resumeVm failed on the node manager"})
		return instance.vmId
	
	def prepReceiveVm(self, instance, source):
		instance.vmId = -1
		transportCookie = self.vmm.prepReceiveVm(instance, source.name)
		return transportCookie

	def prepSourceVm(self, vmId):
		instance = self.getInstance(vmId)
		instance.state = InstanceState.MigratePrep
	
	def migrateVmHelper(self, instance, target, transportCookie):
		self.vmm.migrateVm(instance.vmId, target.name, transportCookie)
		del self.instances[instance.vmId]
		
	def migrateVm(self, vmId, target, transportCookie):
		instance = self.getInstance(vmId)
		instance.state = InstanceState.MigrateTrans
		threading.Thread(target=self.migrateVmHelper, args=(instance, target, transportCookie)).start()
		return
	
	def receiveVmHelper(self, instance, transportCookie):
		cm = ConnectionManager(self.username, self.password, self.cmPort)[self.cmHost]
		vmId = self.vmm.receiveVm(transportCookie)
		instance.state = InstanceState.Running
		instance.hostId = self.id
		instance.vmId = vmId
		self.instances[vmId] = instance
		newInstance = Instance(d={'id':instance.id,'state':instance.state,'vmId':instance.vmId,'hostId':instance.hostId})
		success = lambda: None
		try:
			cm.vmUpdate(newInstance.id, newInstance, InstanceState.MigrateTrans)
		except Exception, e:
			self.log.exception('vmUpdate failed in receiveVmHelper')
			self.notifyCM.append((newInstance.id, newInstance, InstanceState.MigrateTrans, success))
		else:
			success()
	
	def receiveVm(self, instance, transportCookie):
		instance.state = InstanceState.MigrateTrans
		threading.Thread(target=self.receiveVmHelper, args=(instance, transportCookie)).start()
		return
	
	def pauseVm(self, vmId):
		instance = self.getInstance(vmId)
		instance.state = InstanceState.Pausing
		self.vmm.pauseVm(vmId)
		instance.state = InstanceState.Paused
	
	def unpauseVm(self, vmId):
		instance = self.getInstance(vmId)
		instance.state = InstanceState.Unpausing
		self.vmm.unpauseVm(vmId)
		instance.state = InstanceState.Running
	
	def shutdownVm(self, vmId):
		instance = self.getInstance(vmId)
		instance.state = InstanceState.ShuttingDown
		self.vmm.shutdownVm(vmId)
	
	def destroyVm(self, vmId):
		instance = self.getInstance(vmId)
		instance.state = InstanceState.Destroying
		self.vmm.destroyVm(vmId)
	
	def getVmInfo(self, vmId):
		instance = self.getInstance(vmId)
		return instance
	
	def vmmSpecificCall(self, vmId, arg):
		return self.vmm.vmmSpecificCall(vmId, arg)
	
	def listVms(self):
		return self.instances.keys()
	
	def statsThread(self):
		if (self.statsInterval == 0):
			return
		while True:
			try:
				publishList = []
				for vmId in self.instances.keys():
					try:
						instance = self.instances.get(vmId, None)
						if (not instance):
							continue
						id = instance.id
						stats = self.vmm.getStats(vmId)
						for stat in stats:
							publishList.append({"vm_%d_%s" % (id, stat):stats[stat]})
					except:
						self.log.exception('statsThread threw an exception')
				if (len(publishList) > 0):
					tashi.publisher.publishList(publishList)
			except:
				self.log.exception('statsThread threw an exception')
			time.sleep(self.statsInterval)

        def registerHost(self):
                cm = ConnectionManager(self.username, self.password, self.cmPort)[self.cmHost]
                hostname = socket.gethostname()
		# populate some defaults
		# XXXstroucki: I think it's better if the nodemanager fills these in properly when registering with the clustermanager
		memory = 0
		cores = 0
		version = "empty"
                #cm.registerHost(hostname, memory, cores, version)
