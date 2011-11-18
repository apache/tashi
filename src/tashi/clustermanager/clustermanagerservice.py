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

from datetime import datetime
from random import randint
from socket import gethostname
import logging
import threading
import time

from tashi.rpycservices.rpyctypes import Errors, InstanceState, HostState, TashiException
from tashi import boolean, convertExceptions, ConnectionManager, vmStates, timed, version, scrubString

class ClusterManagerService(object):
	"""RPC service for the ClusterManager"""
	
	def __init__(self, config, data, dfs):
		self.config = config
		self.data = data
		self.authAndEncrypt = boolean(config.get('Security', 'authAndEncrypt'))
		if self.authAndEncrypt:
			self.username = config.get('AccessNodeManager', 'username')
			self.password = config.get('AccessNodeManager', 'password')
		else:
			self.username = None
			self.password = None
		self.proxy = ConnectionManager(self.username, self.password, int(self.config.get('ClusterManager', 'nodeManagerPort')))
		self.dfs = dfs
		self.convertExceptions = boolean(config.get('ClusterManagerService', 'convertExceptions'))
		self.log = logging.getLogger(__name__)
		self.hostLastContactTime = {}
		#self.hostLastUpdateTime = {}
		self.instanceLastContactTime = {}
		self.expireHostTime = float(self.config.get('ClusterManagerService', 'expireHostTime'))
		self.allowDecayed = float(self.config.get('ClusterManagerService', 'allowDecayed'))
		self.allowMismatchedVersions = boolean(self.config.get('ClusterManagerService', 'allowMismatchedVersions'))
		self.maxMemory = int(self.config.get('ClusterManagerService', 'maxMemory'))
		self.maxCores = int(self.config.get('ClusterManagerService', 'maxCores'))
		self.allowDuplicateNames = boolean(self.config.get('ClusterManagerService', 'allowDuplicateNames'))
		now = self.__now()
		for instance in self.data.getInstances().itervalues():
			instanceId = instance.id
			instance = self.data.acquireInstance(instanceId)
			instance.decayed = False

			if instance.hostId is None:
				self.stateTransition(instance, None, InstanceState.Pending)
			else:
				self.stateTransition(instance, None, InstanceState.Orphaned)

			self.data.releaseInstance(instance)
		for host in self.data.getHosts().itervalues():
			hostId = host.id
			host = self.data.acquireHost(hostId)
			host.up = False
			host.decayed = False
			self.data.releaseHost(host)
		threading.Thread(target=self.monitorCluster).start()

	def stateTransition(self, instance, old, cur):
		if (old and instance.state != old):
			raise TashiException(d={'errno':Errors.IncorrectVmState,'msg':"VmState is not %s - it is %s" % (vmStates[old], vmStates[instance.state])})
		if (instance.state == cur):
			return

		instance.state = cur
		try:
			host = self.data.getHost(instance.hostId)
			vmId = instance.vmId
			self.proxy[host.name].vmStateChange(vmId, old, cur)
		except:
			#XXXstroucki append to a list?
			pass

	def __now(self):
		return time.time()

	def __downHost(self, host):
		self.log.warning('Host %s is down' % (host.name))
		host.up = False
		host.decayed = False

		self.__orphanInstances(host)

	def __upHost(self, host):
		self.log.warning('Host %s is up' % (host.name))
		host.up = True
		host.decayed = True

	def __orphanInstances(self, host):
		# expects lock to be held on host
		instances = [instance.id for instance in self.data.getInstances().itervalues() if instance.hostId == host.id]

		for instanceId in instances:
			instance = self.data.acquireInstance(instanceId)
			if instance.hostId == host.id:
				instance.decayed = True
				self.stateTransition(instance, None, InstanceState.Orphaned)

			self.data.releaseInstance(instance)

	def __checkHosts(self):
		# Check if hosts have been heard from recently
		# Otherwise, see if it is alive

		for hostId in self.hostLastContactTime.keys():
			if (self.hostLastContactTime[hostId] < (self.__now() - self.expireHostTime)):
				host = self.data.acquireHost(hostId)
				string = None
				try:
					string = self.proxy[host.name].liveCheck()
				except:
					pass

				if string != "alive":
					self.__downHost(host)
					del self.hostLastContactTime[hostId]
				else:
					self.__upHost(host)
					self.hostLastContactTime[hostId] = self.__now()

				self.data.releaseHost(host)

	def __checkInstances(self):
		# Reconcile instances with nodes

		# obtain a list of instances I know about
		myInstancesError = False
		try:
			myInstances = self.data.getInstances()
		except:
			myInstancesError = True
			self.log.warning('Failure communicating with my database')

		if myInstancesError == True:
			return

		# iterate through all hosts I believe are up
		for hostId in self.hostLastContactTime.keys():
			#self.log.warning("iterate %d" % hostId)
			host = self.data.acquireHost(hostId)
			if (self.hostLastContactTime[hostId] < (self.__now() - self.allowDecayed)):
				host.decayed = True

				self.log.info('Fetching state from host %s because it is decayed' % (host.name))
				
				myInstancesThisHost = [i for i in myInstances.values() if i.hostId == host.id]

				# get a list of VMs running on host
				try:
					hostProxy = self.proxy[host.name]
					remoteInstances = [hostProxy.getVmInfo(vmId) for vmId in hostProxy.listVms()]
				except:
					self.log.warning('Failure getting instances from host %s' % (host.name))
					self.data.releaseHost(host)
					continue

				# register instances I don't know about
				for instance in remoteInstances:
					if (instance.id not in myInstances):
						instance.hostId = host.id
						instance = self.data.registerInstance(instance)
						self.data.releaseInstance(instance)
				remoteInstanceIds = [i.id for i in remoteInstances]
				# remove instances that shouldn't be running
				for instance in myInstancesThisHost:
					if (instance.id not in remoteInstanceIds):
						# XXXstroucki before 20110902 excepted here with host lock
						try:
							instance = self.data.acquireInstance(instance.id)
						except:
							continue

						# XXXstroucki destroy?
						try:
							del self.instanceLastContactTime[instance.id]
						except:
							pass
						self.data.removeInstance(instance)

				self.hostLastContactTime[hostId] = self.__now()
				host.decayed = False

			self.data.releaseHost(host)
			#self.log.warning("iterate %d done" % hostId)
		
		# iterate through all VMs I believe are active
		for instanceId in self.instanceLastContactTime.keys():
			if (self.instanceLastContactTime[instanceId] < (self.__now() - self.allowDecayed)):
				try:
					instance = self.data.acquireInstance(instanceId)
				except:
					continue

				instance.decayed = True
				self.log.info('Fetching state on instance %s because it is decayed' % (instance.name))
				if instance.hostId is None: raise AssertionError

				# XXXstroucki check if host is down?
				host = self.data.getHost(instance.hostId)

				# get updated state on VM
				try:
					hostProxy = self.proxy[host.name]
					newInstance = hostProxy.getVmInfo(instance.vmId)
				except:
					self.log.warning('Failure getting data for instance %s from host %s' % (instance.name, host.name))
					self.data.releaseInstance(instance)
					continue

				# replace existing state with new state
				# XXXstroucki more?
				instance.state = newInstance.state
				self.instanceLastContactTime[instanceId] = self.__now()
				instance.decayed = False
				self.data.releaseInstance(instance)



	def monitorCluster(self):
		while True:
			sleepFor = min(self.expireHostTime, self.allowDecayed)

			try:
				self.__checkHosts()
				self.__checkInstances()
			except:
				self.log.exception('monitorCluster iteration failed')
			self.log.info("Sleeping for %d seconds" % sleepFor)
			time.sleep(sleepFor)


	def normalize(self, instance):
		instance.id = None
		instance.vmId = None
		instance.hostId = None
		instance.decayed = False
		instance.name = scrubString(instance.name, allowed="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-.")
		instance.state = InstanceState.Pending
		# XXXstroucki At some point, check userId
		if (not self.allowDuplicateNames):
			for i in self.data.getInstances().itervalues():
				if (i.name == instance.name):
					raise TashiException(d={'errno':Errors.InvalidInstance,'msg':"The name %s is already in use" % (instance.name)})
		if (instance.cores < 1):
			raise TashiException(d={'errno':Errors.InvalidInstance,'msg':"Number of cores must be >= 1"})
		if (instance.cores > self.maxCores):
			raise TashiException(d={'errno':Errors.InvalidInstance,'msg':"Number of cores must be <= %d" % (self.maxCores)})
		if (instance.memory < 1):
			raise TashiException(d={'errno':Errors.InvalidInstance,'msg':"Amount of memory must be >= 1"})
		if (instance.memory > self.maxMemory):
			raise TashiException(d={'errno':Errors.InvalidInstance,'msg':"Amount of memory must be <= %d" % (self.maxMemory)})
		# Make sure disk spec is valid
		# Make sure network spec is valid
		# Ignore internal hints
		for hint in instance.hints:
			if (hint.startswith("__")):
				del instance.hints[hint]
		return instance
	
	def createVm(self, instance):
		"""Function to add a VM to the list of pending VMs"""
		# XXXstroucki: check for exception here
		instance = self.normalize(instance)
		instance = self.data.registerInstance(instance)
		self.data.releaseInstance(instance)
		return instance
	
	def shutdownVm(self, instanceId):
		instance = self.data.acquireInstance(instanceId)
		self.stateTransition(instance, InstanceState.Running, InstanceState.ShuttingDown)
		self.data.releaseInstance(instance)
		hostname = self.data.getHost(instance.hostId).name
		try:
			self.proxy[hostname].shutdownVm(instance.vmId)
		except Exception:
			self.log.exception('shutdownVm failed for host %s vmId %d' % (instance.name, instance.vmId))
			raise
		return
	
	def destroyVm(self, instanceId):
		instance = self.data.acquireInstance(instanceId)
		if (instance.state is InstanceState.Pending or instance.state is InstanceState.Held):
			self.data.removeInstance(instance)
		elif (instance.state is InstanceState.Activating):
			self.stateTransition(instance, InstanceState.Activating, InstanceState.Destroying)
			self.data.releaseInstance(instance)
		else:
			# XXXstroucki: This is a problem with keeping
			# clean state.
			self.stateTransition(instance, None, InstanceState.Destroying)
			if instance.hostId is None:
				self.data.removeInstance(instance)
			else:
				hostname = self.data.getHost(instance.hostId).name
				try:
					if hostname is not None:
						self.proxy[hostname].destroyVm(instance.vmId)
						self.data.releaseInstance(instance)
				except:
					self.log.exception('destroyVm failed on host %s vmId %s' % (hostname, str(instance.vmId)))
					self.data.removeInstance(instance)


		return
	
	def suspendVm(self, instanceId):
		instance = self.data.acquireInstance(instanceId)
		self.stateTransition(instance, InstanceState.Running, InstanceState.Suspending)
		self.data.releaseInstance(instance)
		hostname = self.data.getHost(instance.hostId).name
		destination = "suspend/%d_%s" % (instance.id, instance.name)
		try:
			self.proxy[hostname].suspendVm(instance.vmId, destination)
		except:
			self.log.exception('suspendVm failed for host %s vmId %d' % (hostname, instance.vmId))
			raise TashiException(d={'errno':Errors.UnableToSuspend, 'msg':'Failed to suspend %s' % (instance.name)})
		return
	
	def resumeVm(self, instanceId):
		instance = self.data.acquireInstance(instanceId)
		self.stateTransition(instance, InstanceState.Suspended, InstanceState.Pending)
		source = "suspend/%d_%s" % (instance.id, instance.name)
		instance.hints['__resume_source'] = source
		self.data.releaseInstance(instance)
		return instance
	
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
		from pprint import pformat
		self.log.info("A: %s" % (pformat(instance)))
		self.stateTransition(instance, InstanceState.Running, InstanceState.MigratePrep)
		self.data.releaseInstance(instance)
		try:
			# Prepare the target
			self.log.info("migrateVm: Calling prepSourceVm on source host %s" % sourceHost.name)
			self.proxy[sourceHost.name].prepSourceVm(instance.vmId)
			self.log.info("migrateVm: Calling prepReceiveVm on target host %s" % targetHost.name)
			cookie = self.proxy[targetHost.name].prepReceiveVm(instance, sourceHost)
			self.log.info("Debug: here")
		except Exception, e:
			self.log.exception('prepReceiveVm failed')
			raise
		instance = self.data.acquireInstance(instance.id)
		self.log.info("B: %s" % (pformat(instance)))
		self.stateTransition(instance, InstanceState.MigratePrep, InstanceState.MigrateTrans)
		self.log.info("C: %s" % (pformat(instance)))
		self.data.releaseInstance(instance)
		try:
			# Send the VM
			self.proxy[sourceHost.name].migrateVm(instance.vmId, targetHost, cookie)
		except Exception, e:
			self.log.exception('migrateVm failed')
			raise
		try:
			instance = self.data.acquireInstance(instance.id)
			instance.hostId = targetHost.id
		finally:
			self.data.releaseInstance(instance)

		try:
			# Notify the target
			vmId = self.proxy[targetHost.name].receiveVm(instance, cookie)
			self.log.info("D: %s notified" % targetHost.name)
		except Exception, e:
			self.log.exception('receiveVm failed')
			raise
		return
	
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
	
	def getHosts(self):
		return self.data.getHosts().values()
	
	def getNetworks(self):
		return self.data.getNetworks().values()
	
	def getUsers(self):
		return self.data.getUsers().values()
	
	def getInstances(self):
		return self.data.getInstances().values()
	
	def vmmSpecificCall(self, instanceId, arg):
		instance = self.data.getInstance(instanceId)
		hostname = self.data.getHost(instance.hostId).name
		try:
			res = self.proxy[hostname].vmmSpecificCall(instance.vmId, arg)
		except Exception:
			self.log.exception('vmmSpecificCall failed on host %s with vmId %d' % (hostname, instance.vmId))
			raise
		return res
	
#	@timed
	def registerNodeManager(self, host, instances):
		"""Called by the NM every so often as a keep-alive/state polling -- state changes here are NOT AUTHORITATIVE"""

		# Handle a new registration
		if (host.id == None):
			hostList = [h for h in self.data.getHosts().itervalues() if h.name == host.name]
			if (len(hostList) != 1):
				raise TashiException(d={'errno':Errors.NoSuchHost, 'msg':'A host with name %s is not identifiable' % (host.name)})
			host.id = hostList[0].id

		# Check if remote host information matches mine
		oldHost = self.data.acquireHost(host.id)
		if (oldHost.name != host.name):
			self.data.releaseHost(oldHost)
			raise TashiException(d={'errno':Errors.NoSuchHostId, 'msg':'Host id and hostname mismatch'})

		if oldHost.up == False:
			self.__upHost(oldHost)
		self.hostLastContactTime[host.id] = time.time()
		#self.hostLastUpdateTime[host.id] = time.time()
		oldHost.version = host.version
		oldHost.memory = host.memory
		oldHost.cores = host.cores

		# compare whether CM / NM versions are compatible
		if (host.version != version and not self.allowMismatchedVersions):
			oldHost.state = HostState.VersionMismatch
		if (host.version == version and oldHost.state == HostState.VersionMismatch):
			oldHost.state = HostState.Normal

		# let the host communicate what it is running
		for instance in instances:
			self.log.info('Accounting: id %d host %d vmId %d user %d cores %d memory %d' % (instance.id, host.id, instance.vmId, instance.userId, instance.cores, instance.memory))
			self.instanceLastContactTime.setdefault(instance.id, 0)

		self.data.releaseHost(oldHost)
		return host.id
	
	def vmUpdate(self, instanceId, instance, oldState):
		try:
			oldInstance = self.data.acquireInstance(instanceId)
		except TashiException, e:
			# shouldn't have a lock to clean up after here
			if (e.errno == Errors.NoSuchInstanceId):
				self.log.warning('Got vmUpdate for unknown instanceId %d' % (instanceId))
				return
		except:
			self.log.exception("Could not acquire instance")
			raise

		self.instanceLastContactTime[instanceId] = time.time()
		oldInstance.decayed = False

		if (instance.state == InstanceState.Exited):
			# determine why a VM has exited
			hostname = self.data.getHost(oldInstance.hostId).name
			if (oldInstance.state not in [InstanceState.ShuttingDown, InstanceState.Destroying, InstanceState.Suspending]):
				self.log.warning('Unexpected exit on %s of instance %s (vmId %d)' % (hostname, oldInstance.name, oldInstance.vmId))
			if (oldInstance.state == InstanceState.Suspending):
				self.stateTransition(oldInstance, InstanceState.Suspending, InstanceState.Suspended)
				oldInstance.hostId = None
				oldInstance.vmId = None
				self.data.releaseInstance(oldInstance)
			else:
				del self.instanceLastContactTime[oldInstance.id]
				self.data.removeInstance(oldInstance)
		else:
			if (instance.state):
				# XXXstroucki does this matter?
				if (oldState and oldInstance.state != oldState):
					self.log.warning('Got vmUpdate of state from %s to %s, but the instance was previously %s' % (vmStates[oldState], vmStates[instance.state], vmStates[oldInstance.state]))
				oldInstance.state = instance.state
			if (instance.vmId):
				oldInstance.vmId = instance.vmId
			if (instance.hostId):
				oldInstance.hostId = instance.hostId
			if (instance.nics):
				for nic in instance.nics:
					if (nic.ip):
						for oldNic in oldInstance.nics:
							if (oldNic.mac == nic.mac):
								oldNic.ip = nic.ip

			self.data.releaseInstance(oldInstance)

		return "success"
	
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

		if ('__resume_source' in instance.hints):
			self.stateTransition(instance, InstanceState.Pending, InstanceState.Resuming)
		else:
			# XXXstroucki should held VMs be continually tried? Or be explicitly set back to pending?
			#self.stateTransition(instance, InstanceState.Pending, InstanceState.Activating)
			self.stateTransition(instance, None, InstanceState.Activating)

		instance.hostId = host.id
		self.data.releaseInstance(instance)

		try:
			if ('__resume_source' in instance.hints):
				vmId = self.proxy[host.name].resumeVm(instance, instance.hints['__resume_source'])
			else:
				vmId = self.proxy[host.name].instantiateVm(instance)
		except Exception, e:
			instance = self.data.acquireInstance(instanceId)
			if (instance.state is InstanceState.Destroying): # Special case for if destroyVm is called during initialization and initialization fails
				self.data.removeInstance(instance)
			else:
				# XXXstroucki what can we do about pending hosts in the scheduler?
				# put them at the end of the queue and keep trying?
				self.stateTransition(instance, None, InstanceState.Held)
				instance.hostId = None
				self.data.releaseInstance(instance)
			return "failure"

		instance = self.data.acquireInstance(instanceId)
		instance.vmId = vmId

		if (instance.state is InstanceState.Destroying): # Special case for if destroyVm is called during initialization
			try:
				self.proxy[host.name].destroyVm(vmId)
				self.data.removeInstance(instance)
			except Exception:
				self.log.exception('destroyVm failed for host %s vmId %d' % (host.name, instance.vmId))
				self.data.releaseInstance(instance)
				return "failure"
		else:
			if ('__resume_source' not in instance.hints):
				# XXXstroucki should we just wait for NM to update?
				#self.stateTransition(instance, InstanceState.Activating, InstanceState.Running)
				pass

		self.data.releaseInstance(instance)
		return "success"

        def registerHost(self, hostname, memory, cores, version):
                hostId, alreadyRegistered = self.data.registerHost(hostname, memory, cores, version)
                if alreadyRegistered:
                        self.log.info("Host %s is already registered, it was updated now" % hostname)
                else:
                        self.log.info("A host was registered - hostname: %s, version: %s, memory: %s, cores: %s" % (hostname, version, memory, cores))
                return hostId

        def unregisterHost(self, hostId):
                self.data.unregisterHost(hostId)
                self.log.info("Host %s was unregistered" % hostId)
                return
