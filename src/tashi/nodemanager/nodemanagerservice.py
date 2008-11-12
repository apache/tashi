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
from thrift.transport.TSocket import TSocket
from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.transport.TTransport import TBufferedTransport

from tashi.services.ttypes import ResumeVmRes, Host, HostState, InstanceState, TashiException, Errors, Instance
from tashi.services import clustermanagerservice
from tashi.nodemanager import RPC
from tashi import boolean, vmStates, logged, ConnectionManager, timed

class NodeManagerService():
	"""RPC handler for the NodeManager
	   
	   Perhaps in the future I can hide the dfs from the 
	   VmControlInterface and do all dfs operations here?"""
	
	def __init__(self, config, vmm):
		self.config = config
		self.vmm = vmm
		self.cmHost = config.get("NodeManagerService", "clusterManagerHost")
		self.cmPort = int(config.get("NodeManagerService", "clusterManagerPort"))
		self.log = logging.getLogger(__file__)
		self.convertExceptions = boolean(config.get('NodeManagerService', 'convertExceptions'))
		self.registerFrequency = float(config.get('NodeManagerService', 'registerFrequency'))
		self.infoFile = self.config.get('NodeManagerService', 'infoFile')
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
		threading.Thread(target=self.junk).start()
		threading.Thread(target=self.registerWithClusterManager).start()
	
	def loadVmInfo(self):
		try:
			f = open(self.infoFile, "r")
			data = f.read()
			f.close()
			self.instances = cPickle.loads(data)
		except Exception, e:
			self.log.exception('Failed to load VM info from %s' % (self.infoFile))
			self.instances = {}
	
	def saveVmInfo(self):
		try:
			data = cPickle.dumps(self.instances)
			f = open(self.infoFile, "w")
			f.write(data)
			f.close()
		except Exception, e:
			self.log.exception('Failed to save VM info to %s' % (self.infoFile))
	
	#@logged
	def vmStateChange(self, vmId, old, cur):
		cm = ConnectionManager(clustermanagerservice.Client, self.cmPort)[self.cmHost]
		instance = self.getInstance(vmId)
		if (old and instance.state != old):
			self.log.warning('VM state was %s, call indicated %s' % (vmStates[instance.state], vmStates[old]))
		if (cur == InstanceState.Exited):
			del self.instances[vmId]
		instance.state = cur
		newInst = Instance(d={'state':cur})
		success = lambda: None
		try:
			cm.vmUpdate(instance.id, newInst, old)
		except Exception, e:
			self.log.exception('RPC failed for vmUpdate on CM')
			self.notifyCM.append((instance.id, newInst, old, success))
		else:
			success()
		return True
	
	#@timed	
	def getHostInfo(self):
		host = Host()
		host.id = self.id
		host.name = socket.gethostname()
		memoryStr = os.popen2("head -n 1 /proc/meminfo | awk '{print $2 \" \" $3}'")[1].read().strip()
		if (memoryStr[-2:] == "kB"):
			host.memory = int(memoryStr[:-2])/1024
		elif (memoryStr[-2:] == "mB"):
			host.memory = int(memoryStr[:-2])
		elif (memoryStr[-2:] == "gB"):
			host.memory = int(memoryStr[:-2])*1024
		elif (memoryStr[-2:] == " B"):
			host.memory = int(memoryStr[:-2])/(1024*1024)
		else:
			self.log.warning('Unable to determine amount of physical memory - reporting 0')
			host.memory = 0
		host.cores = os.sysconf("SC_NPROCESSORS_ONLN")
		host.up = True
		host.decayed = False
		return host
	
	def junk(self):
		cm = ConnectionManager(clustermanagerservice.Client, self.cmPort)[self.cmHost]
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
		cm = ConnectionManager(clustermanagerservice.Client, self.cmPort)[self.cmHost]
		#@timed
		def body():
			try:
				#self.log.info('registering with CM at %f' % (time.time()))
				host = self.getHostInfo()
				instances = self.instances.values()
				#@timed
				def RPC(self):
					self.id = cm.registerNodeManager(host, instances)
				RPC(self)
			except Exception, e:
				self.log.exception('Failed to register with the CM')
		while True:
			start = time.time()
			body()
			toSleep = start - time.time() + self.registerFrequency
			if (toSleep > 0):
				time.sleep(toSleep)
	
	def getInstance(self, vmId):
		instance = self.instances.get(vmId, None)
		if (instance is None):
			raise TashiException(d={'errno':Errors.NoSuchVmId,'msg':"There is no vmId %d on this host" % (vmId)})
		return instance
	
	@RPC
	def instantiateVm(self, instance):
		vmId = self.vmm.instantiateVm(instance)
		instance.vmId = vmId
		instance.state = InstanceState.Running
		self.instances[vmId] = instance
		return vmId
	
	@RPC
	def suspendVm(self, vmId, name, suspendCookie):
		instance = self.getInstance(vmId)
		instance.state = InstanceState.Suspending
		threading.Thread(target=lambda: self.vmm.suspendVm(vmId, name, suspendCookie)).start()
	
	@RPC
	def resumeVm(self, instance, name):
		(vmId, suspendCookie) = self.vmm.resumeVm(name)
		instance.vmId = vmId
		instance.state = InstanceState.Running
		self.instances[vmId] = instance
		return ResumeVmRes(d={'vmId':vmId, 'suspendCookie':suspendCookie})
	
	@RPC
	def prepReceiveVm(self, instance, source):
		instance.state = InstanceState.MigratePrep
		instance.vmId = -1
		transportCookie = self.vmm.prepReceiveVm(instance, source.name)
		return transportCookie
	
	def migrateVmHelper(self, instance, target, transportCookie):
		self.vmm.migrateVm(instance.vmId, target.name, transportCookie)
		del self.instances[instance.vmId]
		
	@RPC
	def migrateVm(self, vmId, target, transportCookie):
		instance = self.getInstance(vmId)
		instance.state = InstanceState.MigrateTrans
		threading.Thread(target=lambda: self.migrateVmHelper(instance, target, transportCookie)).start()
		return
	
	def receiveVmHelper(self, instance, transportCookie):
		cm = ConnectionManager(clustermanagerservice.Client, self.cmPort)[self.cmHost]
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
	
	@RPC
	def receiveVm(self, instance, transportCookie):
		instance.state = InstanceState.MigrateTrans
		threading.Thread(target=lambda: self.receiveVmHelper(instance, transportCookie)).start()
		return
	
	@RPC
	def pauseVm(self, vmId):
		instance = self.getInstance(vmId)
		instance.state = InstanceState.Pausing
		self.vmm.pauseVm(vmId)
		instance.state = InstanceState.Paused
	
	@RPC
	def unpauseVm(self, vmId):
		instance = self.getInstance(vmId)
		instance.state = InstanceState.Unpausing
		self.vmm.unpauseVm(vmId)
		instance.state = InstanceState.Running
	
	@RPC
	def shutdownVm(self, vmId):
		instance = self.getInstance(vmId)
		instance.state = InstanceState.ShuttingDown
		self.vmm.shutdownVm(vmId)
	
	@RPC
	def destroyVm(self, vmId):
		instance = self.getInstance(vmId)
		instance.state = InstanceState.Destroying
		self.vmm.destroyVm(vmId)
	
	@RPC
	def getVmInfo(self, vmId):
		instance = self.getInstance(vmId)
		return instance
	
	@RPC
	def listVms(self):
		return self.instances.keys()
	

