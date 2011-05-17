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

from socket import gethostname
import os
import socket
import sys
import threading
import time
import random
import logging.config

from tashi.rpycservices.rpyctypes import *
from tashi.util import getConfig, createClient, instantiateImplementation, boolean
import tashi

class Primitive(object):
	def __init__(self, config, client):
		self.config = config
		self.client = client
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
					self.hooks.append(instantiateImplementation(value, config, client, False))
				except:
					self.log.exception("Failed to load hook %s" % (value))
	        self.hosts = {}
		self.load = {}
		self.instances = {}
		self.muffle = {}
		self.lastScheduledHost = 0
					
					
	def __getState(self):
		# Generate a list of hosts and
		# current loading of VMs per host
		hosts = {}
		# load's keys are the host id, or None if not on a host. values are instance ids
		load = {}
		ctr = 0
		for h in self.client.getHosts():
			if (h.up == True and h.state == HostState.Normal):
				hosts[ctr] = h
				ctr = ctr + 1
				load[h.id] = []
			
		load[None] = []
		_instances = self.client.getInstances()
		instances = {}
		for i in _instances:
			instances[i.id] = i
		for i in instances.itervalues():
			# XXXstroucki: do we need to look at Held machines here?
			if (i.hostId or i.state == InstanceState.Pending):
				# Nonrunning VMs will have hostId of None
				load[i.hostId] = load[i.hostId] + [i.id]

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
	
	def __scheduleInstance(self, inst):
		try:
			minMax = None
			minMaxHost = None
			minMaxCtr = None
			
			targetHost = inst.hints.get("targetHost", None)
			try:
				allowElsewhere = boolean(inst.hints.get("allowElsewhere", "False"))
			except Exception, e:
				allowElsewhere = False
			# has a host preference been expressed?
			if (targetHost != None):
				for h in hosts.values():
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
						minMax = len(load[h.id])
						minMaxHost = h

		
			# end targethost != none
		
		
			# If we don't have a host yet, find one here
			if ((targetHost == None or allowElsewhere) and minMaxHost == None):
				# cycle list
				for ctr in range(self.lastScheduledHost, len(self.hosts)) + range(0, self.lastScheduledHost):
					h = self.hosts[ctr]
		
					# if it's reserved, see if we can use it
					if ((len(h.reserved) > 0) and inst.userId not in h.reserved):
						# reserved for somebody else, so find another machine
						continue
		
					# implement dense packing policy:
					# consider this host if
					# minMax has not been modified  or
					# the number of vms here is greater than minmax if we're dense packing or
					# the number of vms here is less than minmax if we're not dense packing
					if (minMax is None or (self.densePack and len(self.load[h.id]) > minMax) or (not self.densePack and len(self.load[h.id]) < minMax)):
						if self.__checkCapacity(h, inst):
							minMax = len(self.load[h.id])
							minMaxHost = h
							minMaxCtr = ctr
		
			if (minMaxHost):
				# found a host
				self.lastScheduledHost = minMaxCtr
				if (not inst.hints.get("__resume_source", None)):
					# only run preCreate hooks if newly starting
					for hook in self.hooks:
						hook.preCreate(inst)
				self.log.info("Scheduling instance %s (%d mem, %d cores, %d uid) on host %s" % (inst.name, inst.memory, inst.cores, inst.userId, minMaxHost.name))	
				self.client.activateVm(inst.id, minMaxHost)
				self.load[minMaxHost.id] = self.load[minMaxHost.id] + [inst.id]
				# get rid of its possible entry in muffle if VM is scheduled to a host
				if (inst.name in self.muffle):
					self.muffle.pop(inst.name)
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
					if (i not in self.instances and oldInstances[i].state == InstanceState.Running):
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


			except TashiException, e:
				self.log.exception("Tashi exception")

			except Exception, e:
				self.log.exception("General exception")


			# wait to do the next iteration
			time.sleep(self.scheduleDelay)

def main():
	(config, configFiles) = getConfig(["Agent"])
	publisher = instantiateImplementation(config.get("Agent", "publisher"), config)
	tashi.publisher = publisher
	client = createClient(config)
	logging.config.fileConfig(configFiles)
	agent = Primitive(config, client)
	agent.start()

if __name__ == "__main__":
	main()
