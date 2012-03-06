#!/usr/bin/python

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

import time
import logging.config
import sys

from tashi.rpycservices.rpyctypes import Errors, HostState, InstanceState, TashiException

from tashi.util import getConfig, createClient, instantiateImplementation, boolean
import tashi

class Primitive(object):
	def __init__(self, config):
		self.config = config
		self.cm = createClient(config)
		self.hooks = []
		self.log = logging.getLogger(__file__)
		self.scheduleDelay = float(self.config.get("Primitive", "scheduleDelay"))
		self.densePack = boolean(self.config.get("Primitive", "densePack"))
		items = self.config.items("Primitive")
		items.sort()
		for item in items:
			(name, value) = item
			name = name.lower()
			if (name.startswith("hook")):
				try:
					self.hooks.append(instantiateImplementation(value, config, cmclient, False))
				except:
					self.log.exception("Failed to load hook %s" % (value))
		self.hosts = {}
		self.load = {}
		self.instances = {}
		self.muffle = {}
		self.lastScheduledHost = 0
		self.clearHints = {}
					
					
	def __getState(self):
		# Generate a list of hosts and
		# current loading of VMs per host
		hosts = {}
		# load's keys are the host id, or None if not on a host. values are instance ids
		load = {}
		ctr = 0

		for h in self.cm.getHosts():
			#XXXstroucki get all hosts here?
			#if (h.up == True and h.state == HostState.Normal):
			hosts[ctr] = h
			ctr = ctr + 1
			load[h.id] = []
			
		load[None] = []
		_instances = self.cm.getInstances()
		instances = {}
		for i in _instances:
			instances[i.id] = i
			
		# XXXstroucki put held machines behind pending ones
		heldInstances = []
		for i in instances.itervalues():
			if (i.hostId or i.state == InstanceState.Pending):
				# Nonrunning VMs will have hostId of None
				load[i.hostId] = load[i.hostId] + [i.id]
			elif (i.hostId is None and i.state == InstanceState.Held):
				heldInstances = heldInstances + [i.id]

		load[None] = load[None] + heldInstances

		self.hosts = hosts
		self.load = load
		self.instances = instances

	def __checkCapacity(self, host, inst):
		# ensure host can carry new load
		memUsage = reduce(lambda x, y: x + self.instances[y].memory, self.load[host.id], inst.memory)
		coreUsage = reduce(lambda x, y: x + self.instances[y].cores, self.load[host.id], inst.cores)
		if (memUsage <= host.memory and coreUsage <= host.cores):
			return True
		
		return False

	def __clearHints(self, hint, name):
		#  remove the clearHint if the host comes back to normal mode
		if name in self.clearHints[hint]:
			popit = self.clearHints[hint].index(name)
			self.clearHints[hint].pop(popit)
	
	def __scheduleInstance(self, inst):

		try:

			minMax = None
			minMaxHost = None
			minMaxCtr = None

			densePack = inst.hints.get("densePack", None)
			if (densePack is None):
				densePack = self.densePack
			else:
				densePack = boolean(densePack)
			
			#  Grab the targetHost config options if passed
			targetHost = inst.hints.get("targetHost", None)
			#  Check to see if we have already handled this hint
			clearHints = self.clearHints
			clearHints["targetHost"] = clearHints.get("targetHost", [])
			#  If we handled the hint, don't look at it anymore
			if targetHost in clearHints["targetHost"]:
				targetHost = None

			try:
				allowElsewhere = boolean(inst.hints.get("allowElsewhere", "False"))
			except Exception, e:
				allowElsewhere = False
			# has a host preference been expressed?
			if (targetHost != None):
				for h in self.hosts.values():
					if (h.state == HostState.Normal):
						self.__clearHints("targetHost", h.name)
					# if this is not the host we are looking for, continue
					if ((str(h.id) != targetHost and h.name != targetHost)):
						continue
					# we found the targetHost
					#  If a host machine is reserved, only allow if userid is in reserved list
					if ((len(h.reserved) > 0) and inst.userId not in h.reserved):
						# Machine is reserved and not available for userId.
						# XXXstroucki: Should we log something here for analysis?
						break
					if self.__checkCapacity(h, inst):
						minMax = len(self.load[h.id])
						minMaxHost = h

		
			# end targethost != none
		
		
			# If we don't have a host yet, find one here
			if ((targetHost == None or allowElsewhere) and minMaxHost == None):
				# cycle list
				#  Adding this to catch if this gets set to None.  Fix
				if self.lastScheduledHost == None:
					self.lastScheduledHost = 0
				for ctr in range(self.lastScheduledHost, len(self.hosts)) + range(0, self.lastScheduledHost):
					h = self.hosts[ctr]

					# XXXstroucki if it's down, find another machine
					if (h.up == False):
						continue

					#  If the host not in normal operating state, 
					#  find another machine
					if (h.state != HostState.Normal):
						continue
					else:
						#  If the host is back to normal, get rid of the entry in clearHints
						self.__clearHints("targetHost", h.name)
		
					# if it's reserved, see if we can use it
					if ((len(h.reserved) > 0) and inst.userId not in h.reserved):
						# reserved for somebody else, so find another machine
						continue
		
					# implement dense packing policy:
					# consider this host if
					# minMax has not been modified  or
					# the number of vms here is greater than minmax if we're dense packing or
					# the number of vms here is less than minmax if we're not dense packing
					if (minMax is None or (densePack and len(self.load[h.id]) > minMax) or (not densePack and len(self.load[h.id]) < minMax)):
						if self.__checkCapacity(h, inst):
							minMax = len(self.load[h.id])
							minMaxHost = h
							minMaxCtr = ctr

					#  check that VM image isn't mounted persistent already
					#  Should set a status code to alert user
					#  Tried to update the state of the instance and set persistent=False but 
					#  couldn't do it, should work until we find a better way to do this
					if inst.disks[0].persistent == True:
						count = 0
						myDisk = inst.disks[0].uri
						for i in self.cm.getInstances():
							if myDisk == i.disks[0].uri and i.disks[0].persistent == True:
								count += 1
						if count > 1:
							minMaxHost = None

			if (minMaxHost):
				# found a host
				if (not inst.hints.get("__resume_source", None)):
					# only run preCreate hooks if newly starting
					for hook in self.hooks:
						hook.preCreate(inst)
				self.log.info("Scheduling instance %s (%d mem, %d cores, %d uid) on host %s" % (inst.name, inst.memory, inst.cores, inst.userId, minMaxHost.name))	
				rv = "fail"
				try:
					rv = self.cm.activateVm(inst.id, minMaxHost)
					if rv == "success":
						self.lastScheduledHost = minMaxCtr
						self.load[minMaxHost.id] = self.load[minMaxHost.id] + [inst.id]
						# get rid of its possible entry in muffle if VM is scheduled to a host
						if (inst.name in self.muffle):
							self.muffle.pop(inst.name)
					else:
						self.log.warning("Instance %s failed to activate on host %s" % (inst.name, minMaxHost.name))
				except TashiException, e :
					#  If we try to activate the VM and get errno 10, host not in normal mode, add it to the list
					#  check for other errors later
					if e.errno == Errors.HostStateError:
						self.clearHints["targetHost"] = self.clearHints.get("targetHost", [])
						self.clearHints["targetHost"].append(targetHost)

			else:
				# did not find a host
				if (inst.name not in self.muffle):
					self.log.info("Failed to find a suitable place to schedule %s" % (inst.name))
					self.muffle[inst.name] = True
						
		except Exception, e:
			# XXXstroucki: how can we get here?
			if (inst.name not in self.muffle):
				self.log.exception("Failed to schedule or activate %s" % (inst.name))
				self.muffle[inst.name] = True
									
	def start(self):
		oldInstances = {}

		while True:
			try:
				self.__getState()
				
				# Check for VMs that have exited and call
				# postDestroy hook
				for i in oldInstances:
					# XXXstroucki what about paused and saved VMs?
					# XXXstroucki: do we need to look at Held VMs here?
					if (i not in self.instances and (oldInstances[i].state == InstanceState.Running or oldInstances[i].state == InstanceState.Destroying or oldInstances[i].state == InstanceState.ShuttingDown)):
						self.log.info("VM exited: %s" % (oldInstances[i].name))
						for hook in self.hooks:
							hook.postDestroy(oldInstances[i])

				oldInstances = self.instances


				if (len(self.load.get(None, [])) > 0):
					# Schedule VMs if they are waiting

					# sort by id number (FIFO?)
					self.load[None].sort()
					for i in self.load[None]:
						inst = self.instances[i]
						self.__scheduleInstance(inst)
					# end for unassigned vms


			except TashiException:
				self.log.exception("Tashi exception")

			except Exception:
				self.log.warning("Scheduler iteration failed")


			# wait to do the next iteration
			time.sleep(self.scheduleDelay)

def main():
	(config, configFiles) = getConfig(["Agent"])
	publisher = instantiateImplementation(config.get("Agent", "publisher"), config)
	tashi.publisher = publisher
	logging.config.fileConfig(configFiles)
	agent = Primitive(config)

	try:
		agent.start()
	except KeyboardInterrupt:
		pass

	log = logging.getLogger(__file__)
	log.info("Primitive exiting")
	sys.exit(0)

if __name__ == "__main__":
	main()
