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

import logging
import threading
import time

from tashi.rpycservices.rpyctypes import Errors, InstanceState, Instance, HostState, TashiException
from tashi import boolean, ConnectionManager, vmStates, hostStates, version, scrubString
from tashi.dfs.diskimage import QemuImage

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
		self.proxy = ConnectionManager(self.username, self.password, int(self.config.get('ClusterManager', 'nodeManagerPort')), authAndEncrypt=self.authAndEncrypt)
		self.dfs = dfs
		self.convertExceptions = boolean(config.get('ClusterManagerService', 'convertExceptions'))
		self.log = logging.getLogger(__name__)
		self.log.setLevel(logging.ERROR)
		self.hostLastContactTime = {}
		#self.hostLastUpdateTime = {}
		self.instanceLastContactTime = {}
		self.expireHostTime = float(self.config.get('ClusterManagerService', 'expireHostTime'))
		self.allowDecayed = float(self.config.get('ClusterManagerService', 'allowDecayed'))
		self.allowMismatchedVersions = boolean(self.config.get('ClusterManagerService', 'allowMismatchedVersions'))
		self.maxMemory = int(self.config.get('ClusterManagerService', 'maxMemory'))
		self.maxCores = int(self.config.get('ClusterManagerService', 'maxCores'))

		self.defaultNetwork = self.config.getint('ClusterManagerService', 'defaultNetwork', 0)

		self.allowDuplicateNames = boolean(self.config.get('ClusterManagerService', 'allowDuplicateNames'))

		self.accountingHost = None
		self.accountingPort = None
		try:
			self.accountingHost = self.config.get('ClusterManagerService', 'accountingHost')
			self.accountingPort = self.config.getint('ClusterManagerService', 'accountingPort')
		except:
			pass

		self.__initAccounting()
		self.__initCluster()

		threading.Thread(name="monitorCluster", target=self.__monitorCluster).start()

		self.qemuImage = QemuImage(self.config)

	def __initAccounting(self):
		self.accountBuffer = []
		self.accountLines = 0
		self.accountingClient = None
		try:
			if (self.accountingHost is not None) and \
					(self.accountingPort is not None):
				self.accountingClient = ConnectionManager(self.username, self.password, self.accountingPort)[self.accountingHost]
		except:
			self.log.exception("Could not init accounting")

	def __initCluster(self):
		# initialize state of VMs if restarting
		for instance in self.data.getInstances().itervalues():
			instanceId = instance.id
			instance = self.data.acquireInstance(instanceId)
			instance.decayed = False

			if instance.hostId is None:
				self.__stateTransition(instance, None, InstanceState.Pending)
			else:
				self.__stateTransition(instance, None, InstanceState.Orphaned)

			self.data.releaseInstance(instance)

		# initialize state of hosts if restarting
		for host in self.data.getHosts().itervalues():
			hostId = host.id
			host = self.data.acquireHost(hostId)
			host.up = False
			host.decayed = False
			self.data.releaseHost(host)



	def __ACCOUNTFLUSH(self):
		try:
			if (self.accountingClient is not None):
				self.accountingClient.record(self.accountBuffer)
			self.accountLines = 0
			self.accountBuffer = []
		except:
			self.log.exception("Failed to flush accounting data")


	def __ACCOUNT(self, text, instance=None, host=None):
		now = self.__now()
		instanceText = None
		hostText = None

		if instance is not None:
			try:
				instanceText = 'Instance(%s)' % (instance)
			except:
				self.log.exception("Invalid instance data")

		if host is not None:
			try:
				hostText = "Host(%s)" % (host)
			except:
				self.log.exception("Invalid host data")

		secondary = ','.join(filter(None, (hostText, instanceText)))

		line = "%s|%s|%s" % (now, text, secondary)

		self.accountBuffer.append(line)
		self.accountLines += 1

		# XXXstroucki think about autoflush by time
		if (self.accountLines > 0):
			self.__ACCOUNTFLUSH()



	def __stateTransition(self, instance, old, cur):
		if (old and instance.state != old):
			raise TashiException(d={'errno':Errors.IncorrectVmState,'msg':"VmState is not %s - it is %s" % (vmStates[old], vmStates[instance.state])})
		if (instance.state == cur):
			# don't do anything if we're already at current state
			return

		instance.state = cur
		# pass something down to the NM?

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
				self.__stateTransition(instance, None, InstanceState.Orphaned)

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
			# XXXstroucki: timing has changed with the message
			# buffering in the NM, so this wasn't being run any-
			# more because the time check was passing.
			# I should think a bit more about this, but
			# the "if True" is probably appropriate.
			#if (self.hostLastContactTime[hostId] < (self.__now() - self.allowDecayed)):
			if True:
				host.decayed = True

				self.log.debug('Fetching state from host %s because it is decayed' % (host.name))
				
				myInstancesThisHost = [i for i in myInstances.values() if i.hostId == host.id]

				# get a list of VMs running on host
				try:
					hostProxy = self.proxy[host.name]
					remoteInstances = [self.__getVmInfo(host.name, vmId) for vmId in hostProxy.listVms()]
				except:
					self.log.warning('Failure getting instances from host %s' % (host.name))
					self.data.releaseHost(host)
					continue

				# register instances I don't know about
				for instance in remoteInstances:
					if (instance.id not in myInstances):
						if instance.state == InstanceState.Exited:
							self.log.warning("%s telling me about exited instance %s, ignoring." % (host.name, instance.id))
							continue
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

			# XXXstroucki should lock instance here?
			try:
				lastContactTime = self.instanceLastContactTime[instanceId]
			except KeyError:
				continue

			if (lastContactTime < (self.__now() - self.allowDecayed)):
				try:
					instance = self.data.acquireInstance(instanceId)
					# Don't query non-running VMs. eg. if a VM
					# is suspended, and has no host, then there's
					# no one to ask
					if instance.state not in [InstanceState.Running, InstanceState.Activating, InstanceState.Orphaned]:
						self.data.releaseInstance(instance)
						continue
				except:
					continue

				instance.decayed = True
				self.log.debug('Fetching state on instance %s because it is decayed' % (instance.name))
				if instance.hostId is None:
					# XXXstroucki we should not have reached
					# here. Log state of instance and raise
					# an AssertionError
					self.log.error("Assert failed: hostId is None with instance %s" % instance)
					raise AssertionError

				# XXXstroucki check if host is down?
				host = self.data.getHost(instance.hostId)

				# get updated state on VM
				try:
					newInstance = self.__getVmInfo(host.name, instance.vmId)
				except:
					self.log.warning('Failure getting data for instance %s from host %s' % (instance.name, host.name))
					self.data.releaseInstance(instance)
					continue

				# update the information we have on the vm
				#before = instance.state
				rv = self.__vmUpdate(instance, newInstance, None)
				if (rv == "release"):
					self.data.releaseInstance(instance)

				if (rv == "remove"):
					self.data.removeInstance(instance)


	def __getVmInfo(self, host, vmid):
		hostProxy = self.proxy[host]
		rv = hostProxy.getVmInfo(vmid)
		if isinstance(rv, Exception):
			raise rv

		if not isinstance(rv, Instance):
			raise ValueError

		return rv

	def __normalize(self, instance):
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
	
	# extern
	def createVm(self, instance):
		"""Function to add a VM to the list of pending VMs"""
		# XXXstroucki: check for exception here
		instance = self.__normalize(instance)
		instance = self.data.registerInstance(instance)
		self.data.releaseInstance(instance)
		self.__ACCOUNT("CM VM REQUEST", instance=instance)
		return instance

	# extern
	def shutdownVm(self, instanceId):
		instance = self.data.acquireInstance(instanceId)
		self.__stateTransition(instance, None, InstanceState.ShuttingDown)
		self.data.releaseInstance(instance)
		self.__ACCOUNT("CM VM SHUTDOWN", instance=instance)
		hostname = self.data.getHost(instance.hostId).name
		try:
			self.proxy[hostname].shutdownVm(instance.vmId)
		except Exception:
			self.log.exception('shutdownVm failed for host %s vmId %d' % (instance.name, instance.vmId))
			raise
		return

	# extern
	def destroyVm(self, instanceId):
		instance = self.data.acquireInstance(instanceId)
		if (instance.state is InstanceState.Pending or instance.state is InstanceState.Held):
			self.__ACCOUNT("CM VM DESTROY UNSTARTED", instance=instance)
			self.data.removeInstance(instance)
		elif (instance.state is InstanceState.Activating):
			self.__ACCOUNT("CM VM DESTROY STARTING", instance=instance)
			self.__stateTransition(instance, None, InstanceState.Destroying)
			self.data.releaseInstance(instance)
		else:
			# XXXstroucki: This is a problem with keeping
			# clean state.
			self.__ACCOUNT("CM VM DESTROY", instance=instance)
			self.__stateTransition(instance, None, InstanceState.Destroying)
			if instance.hostId is None:
				self.data.removeInstance(instance)
			else:
				hostname = self.data.getHost(instance.hostId).name
				try:
					if hostname is not None:
						self.proxy[hostname].destroyVm(instance.vmId)
						self.data.releaseInstance(instance)
				except:
					self.log.warning('destroyVm failed on host %s vmId %s' % (hostname, str(instance.vmId)))
					self.data.removeInstance(instance)


		return
	
	# extern
	def suspendVm(self, instanceId):
		instance = self.data.acquireInstance(instanceId)
		try:
			self.__stateTransition(instance, InstanceState.Running, InstanceState.Suspending)
		except TashiException:
			self.data.releaseInstance(instance)
			raise

		self.data.releaseInstance(instance)
		self.__ACCOUNT("CM VM SUSPEND", instance=instance)
		hostname = self.data.getHost(instance.hostId).name
		destination = "suspend/%d_%s" % (instance.id, instance.name)
		try:
			self.proxy[hostname].suspendVm(instance.vmId, destination)
		except:
			self.log.exception('suspendVm failed for host %s vmId %d' % (hostname, instance.vmId))
			raise TashiException(d={'errno':Errors.UnableToSuspend, 'msg':'Failed to suspend %s' % (instance.name)})

		return "%s is suspending." % (instance.name)
	
	# extern
	def resumeVm(self, instanceId):
		instance = self.data.acquireInstance(instanceId)
		try:
			self.__stateTransition(instance, InstanceState.Suspended, InstanceState.Pending)
		except TashiException:
			self.data.releaseInstance(instance)
			raise

		source = "suspend/%d_%s" % (instance.id, instance.name)
		instance.hints['__resume_source'] = source
		self.data.releaseInstance(instance)
		self.__ACCOUNT("CM VM RESUME", instance=instance)
		return "%s is resuming." % (instance.name)
	
	# extern
	def migrateVm(self, instanceId, targetHostId):
		instance = self.data.acquireInstance(instanceId)
		self.__ACCOUNT("CM VM MIGRATE", instance=instance)
		try:
			# FIXME: should these be acquire/release host?
			targetHost = self.data.getHost(targetHostId)
			sourceHost = self.data.getHost(instance.hostId)
			# FIXME: Are these the correct state transitions?
		except:
			self.data.releaseInstance(instance)
			raise

		try:
			# XXXstroucki: if migration fails, we'll still
			# show MigratePrep as state...
			self.__stateTransition(instance, InstanceState.Running, InstanceState.MigratePrep)
		except TashiException:
			self.data.releaseInstance(instance)
			raise

		self.data.releaseInstance(instance)
		try:
			# Prepare the target
			self.log.info("migrateVm: Calling prepSourceVm on source host %s" % sourceHost.name)
			self.proxy[sourceHost.name].prepSourceVm(instance.vmId)
			self.log.info("migrateVm: Calling prepReceiveVm on target host %s" % targetHost.name)
			cookie = self.proxy[targetHost.name].prepReceiveVm(instance, sourceHost)
		except Exception:
			self.log.exception('prepReceiveVm failed')
			raise

		instance = self.data.acquireInstance(instance.id)
		try:
			self.__stateTransition(instance, InstanceState.MigratePrep, InstanceState.MigrateTrans)
		except TashiException:
			self.data.releaseInstance(instance)
			raise

		self.data.releaseInstance(instance)
		try:
			# Send the VM
			self.proxy[sourceHost.name].migrateVm(instance.vmId, targetHost, cookie)
		except Exception:
			self.log.exception('migrateVm failed')
			raise
		try:
			instance = self.data.acquireInstance(instance.id)
			instance.hostId = targetHost.id
		finally:
			self.data.releaseInstance(instance)

		try:
			# Notify the target
			__vmid = self.proxy[targetHost.name].receiveVm(instance, cookie)
		except Exception:
			self.log.exception('receiveVm failed')
			raise

		self.log.info("migrateVM finished")
		return

	# extern
	def pauseVm(self, instanceId):
		instance = self.data.acquireInstance(instanceId)
		try:
			self.__stateTransition(instance, InstanceState.Running, InstanceState.Pausing)
		except TashiException:
			self.data.releaseInstance(instance)
			raise

		self.data.releaseInstance(instance)
		self.__ACCOUNT("CM VM PAUSE", instance=instance)
		hostname = self.data.getHost(instance.hostId).name
		try:
			self.proxy[hostname].pauseVm(instance.vmId)
		except Exception:
			self.log.exception('pauseVm failed on host %s with vmId %d' % (hostname, instance.vmId))
			raise
		instance = self.data.acquireInstance(instanceId)
		try:
			self.__stateTransition(instance, InstanceState.Pausing, InstanceState.Paused)
		except TashiException:
			self.data.releaseInstance(instance)
			raise

		self.data.releaseInstance(instance)
		return

	# extern
	def unpauseVm(self, instanceId):
		instance = self.data.acquireInstance(instanceId)
		try:
			self.__stateTransition(instance, InstanceState.Paused, InstanceState.Unpausing)
		except TashiException:
			self.data.releaseInstance(instance)
			raise

		self.data.releaseInstance(instance)
		self.__ACCOUNT("CM VM UNPAUSE", instance=instance)
		hostname = self.data.getHost(instance.hostId).name
		try:
			self.proxy[hostname].unpauseVm(instance.vmId)
		except Exception:
			self.log.exception('unpauseVm failed on host %s with vmId %d' % (hostname, instance.vmId))
			raise
		instance = self.data.acquireInstance(instanceId)
		try:
			self.__stateTransition(instance, InstanceState.Unpausing, InstanceState.Running)
		except TashiException:
			self.data.releaseInstance(instance)
			raise

		self.data.releaseInstance(instance)
		return

	# extern
	def getHosts(self):
		return self.data.getHosts().values()
	
	# extern
	def setHostState(self, hostId, state):
		state = state.lower()
		hostState = None
		if state == "normal":
			hostState = HostState.Normal
		if state == "drained":
			hostState = HostState.Drained

		if hostState is None:
			return "%s is not a valid host state" % state

		host = self.data.acquireHost(hostId)
		try:
			host.state = hostState
		finally:
			self.data.releaseHost(host)

		return "Host state set to %s." % hostStates[hostState]

	# extern
	def setHostNotes(self, hostId, notes):
		hostNotes = notes
		host = self.data.acquireHost(hostId)
		try:
			host.notes = hostNotes
		finally:
			self.data.releaseHost(host)

		return 'Host notes set to "%s".' % hostNotes

	# extern
	def addReservation(self, hostId, userId):
		host = self.data.acquireHost(hostId)
		msg = None
		user = self.__getUser(userId)
		try:
			if userId not in host.reserved:
				host.reserved.append(userId)
				msg = "%s added to reservations of host %s" % (user.name, host.name)
			else:
				msg = "%s already in reservations of host %s" % (user.name, host.name)
		finally:
			self.data.releaseHost(host)

		if msg is not None:
			return msg
		else:
			return "Sorry, an error occurred"

	# extern
	def delReservation(self, hostId, userId):
		host = self.data.acquireHost(hostId)
		msg = None
		user = self.__getUser(userId)
		try:
			if userId not in host.reserved:
				msg = "%s not in reservations of host %s" % (user.name, host.name)
			else:
				host.reserved.remove(userId)
				msg = "%s removed from reservations of host %s" % (user.name, host.name)
		finally:
			self.data.releaseHost(host)

		if msg is not None:
			return msg
		else:
			return "Sorry, an error occurred"

	# extern
	def getReservation(self, hostId):
		host = self.data.getHost(hostId)
		users = host.reserved

		if len(users) == 0:
			return 'Host %s is not reserved for any users' % (host.name)

		namelist = []
		for u in users:
			user = self.__getUser(u)
			namelist.append(user.name)

		usersstring = ', '.join(map(str, namelist))

		return 'Host %s reserved for users %s.' % (host.name, usersstring)

	# extern
	def getNetworks(self):
		networks = self.data.getNetworks()
		for network in networks:
			if self.defaultNetwork == networks[network].id:
				setattr(networks[network], "default", True)

		return networks.values()

	# extern
	def getUsers(self):
		return self.data.getUsers().values()

	def __getUser(self, userId):
		return self.data.getUser(userId)

	# extern
	def getInstances(self):
		return self.data.getInstances().values()

	# extern
	def getImages(self):
		return self.data.getImages()
	
	# extern
	def copyImage(self, src, dst):
		imageSrc = self.dfs.getLocalHandle("images/" + src)
		imageDst = self.dfs.getLocalHandle("images/" + dst)
		try:
			#  Attempt to restrict to the image directory
			if ".." not in imageSrc and ".." not in imageDst:
				self.dfs.copy(imageSrc, imageDst)
				self.log.info('DFS image copy: %s->%s' % (imageSrc, imageDst))
			else:
				self.log.warning('DFS image copy bad path: %s->%s' % (imageSrc, imageDst))
		except Exception, e:
			self.log.exception('DFS image copy failed: %s (%s->%s)' % (e, imageSrc, imageDst))

    # extern
	def cloneImage(self, src, dst):
		imageSrc = self.dfs.getLocalHandle("images/" + src)
		imageDst = self.dfs.getLocalHandle("images/" + dst)
		self.log.info('DFS image clone: %s->%s' % (imageSrc, imageDst))
		try:
			self.qemuImage.cloneImage(imageSrc, imageDst)
		except Exception, e:
			self.log.info('DFS image clone error: %s' % (e))

    # extern
	def rebaseImage(self, src, dst):
		imageSrc = self.dfs.getLocalHandle("images/" + src)
		imageDst = self.dfs.getLocalHandle("images/" + dst)
		self.log.info('DFS image rebase: %s->%s' % (imageSrc, imageDst))
		try:
			self.qemuImage.rebaseImage(imageSrc, imageDst)
		except Exception, e:
			self.log.info('DFS image rebase error: %s' % (e))

	# extern
	def vmmSpecificCall(self, instanceId, arg):
		instance = self.data.getInstance(instanceId)
		hostname = self.data.getHost(instance.hostId).name
		self.__ACCOUNT("CM VM SPECIFIC CALL", instance=instance)
		try:
			res = self.proxy[hostname].vmmSpecificCall(instance.vmId, arg)
		except Exception:
			self.log.exception('vmmSpecificCall failed on host %s with vmId %d' % (hostname, instance.vmId))
			raise
		return res

	# extern
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
		self.hostLastContactTime[host.id] = self.__now()
		oldHost.version = host.version
		oldHost.memory = host.memory
		oldHost.cores = host.cores

		# compare whether CM / NM versions are compatible
		if (host.version != version and not self.allowMismatchedVersions):
			oldHost.state = HostState.VersionMismatch
		if (host.version == version and oldHost.state == HostState.VersionMismatch):
			oldHost.state = HostState.Normal

		# let the host communicate what it is running
		# and note that the information is not stale
		for instance in instances:
			if instance.state == InstanceState.Exited:
				self.log.warning("%s reporting exited instance %s, ignoring." % (host.name, instance.id))
				continue
			self.instanceLastContactTime.setdefault(instance.id, 0)

		self.data.releaseHost(oldHost)
		return host.id
	
	def __vmUpdate(self, oldInstance, instance, oldState):
		# this function assumes a lock is held on the instance
		# already, and will be released elsewhere

		self.instanceLastContactTime[oldInstance.id] = self.__now()
		oldInstance.decayed = False

		if (instance.state == InstanceState.Exited):
			# determine why a VM has exited
			hostname = self.data.getHost(oldInstance.hostId).name

			if (oldInstance.state not in [InstanceState.ShuttingDown, InstanceState.Destroying, InstanceState.Suspending]):
				self.log.warning('Unexpected exit on %s of instance %s (vmId %d)' % (hostname, oldInstance.name, oldInstance.vmId))

			if (oldInstance.state == InstanceState.Suspending):
				self.__stateTransition(oldInstance, InstanceState.Suspending, InstanceState.Suspended)
				oldInstance.hostId = None
				oldInstance.vmId = None
				return "release"

			if (oldInstance.state == InstanceState.MigrateTrans):
				# Just await update from target host
				return "release"

			else:
				del self.instanceLastContactTime[oldInstance.id]
				return "remove"

		else:
			if (instance.state):
				# XXXstroucki does this matter?
				if (oldState and oldInstance.state != oldState):
					self.log.warning('Doing vmUpdate of state from %s to %s, but the instance was previously %s' % (vmStates[oldState], vmStates[instance.state], vmStates[oldInstance.state]))
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

			return "release"


		return "success"

	# extern
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

		import copy
		displayInstance = copy.copy(oldInstance)
		displayInstance.state = instance.state
		self.__ACCOUNT("CM VM UPDATE", instance=displayInstance)

		rv = self.__vmUpdate(oldInstance, instance, oldState)

		if (rv == "release"):
			self.data.releaseInstance(oldInstance)

		if (rv == "remove"):
			self.data.removeInstance(oldInstance)

		return "success"

	# extern
	def activateVm(self, instanceId, host):
		# XXXstroucki: check my idea of the host's capacity before
		# trying.

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
		self.__ACCOUNT("CM VM ACTIVATE", instance=instance)

		if ('__resume_source' in instance.hints):
			self.__stateTransition(instance, None, InstanceState.Resuming)
		else:
			# XXXstroucki should held VMs be continually tried? Or be explicitly set back to pending?
			#self.__stateTransition(instance, InstanceState.Pending, InstanceState.Activating)
			self.__stateTransition(instance, None, InstanceState.Activating)

		instance.hostId = host.id
		self.data.releaseInstance(instance)

		try:
			if ('__resume_source' in instance.hints):
				vmId = self.proxy[host.name].resumeVm(instance, instance.hints['__resume_source'])
			else:
				vmId = self.proxy[host.name].instantiateVm(instance)
		except Exception:
			instance = self.data.acquireInstance(instanceId)
			if (instance.state is InstanceState.Destroying): # Special case for if destroyVm is called during initialization and initialization fails
				self.data.removeInstance(instance)
			else:
				# XXXstroucki what can we do about pending hosts in the scheduler?
				# put them at the end of the queue and keep trying?
				self.__stateTransition(instance, None, InstanceState.Held)
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
				#self.__stateTransition(instance, InstanceState.Activating, InstanceState.Running)
				pass

		self.data.releaseInstance(instance)
		return "success"

	# extern
	def registerHost(self, hostname, memory, cores, version):
		hostId, alreadyRegistered = self.data.registerHost(hostname, memory, cores, version)
		if alreadyRegistered:
			self.log.info("Host %s is already registered, it was updated now" % hostname)
		else:
			self.log.info("A host was registered - hostname: %s, version: %s, memory: %s, cores: %s" % (hostname, version, memory, cores))

		try:
			host = self.data.getHost(hostId)
			self.__ACCOUNT("CM HOST REGISTER", host=host)
		except:
			self.log.warning("Failed to lookup host %s" % hostId)

		return "Registered host %s with hostId %s" % (host.name, host.id)

	# extern
	def unregisterHost(self, hostId):
		# what about VMs that may be running on the host?
		# what about VMs attempted to be scheduled here once
		# we've removed it?

		try:
			host = self.data.getHost(hostId)
			self.__ACCOUNT("CM HOST UNREGISTER", host=host)
		except:
			self.log.warning("Failed to lookup host %s" % hostId)
			return

		self.log.info("Aborting non-implemented host unregistration for host %s" % host.name)
		return "Host removal for host %s not implemented yet" % host.name

		self.data.unregisterHost(hostId)
		self.log.info("Host %s was unregistered" % hostId)
		return

	# service thread
	def __monitorCluster(self):
		while True:
			sleepFor = min(self.expireHostTime, self.allowDecayed)

			try:
				self.__checkHosts()
				self.__checkInstances()
			except:
				self.log.exception('monitorCluster iteration failed')
			#  XXXrgass too chatty.  Remove
			# XXXstroucki the risk is that a deadlock in obtaining
			# data could prevent this loop from continuing.
			#self.log.info("Sleeping for %d seconds" % sleepFor)
			time.sleep(sleepFor)


