#! /usr/bin/env python

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
import logging.config

from tashi.services.ttypes import *
from tashi.util import getConfig, createClient, instantiateImplementation, boolean
import tashi

class Primitive(object):
	def __init__(self, config, client, transport):
		self.config = config
		self.client = client
		self.transport = transport
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
					self.hooks.append(instantiateImplementation(value, config, client, transport, False))
				except:
					self.log.exception("Failed to load hook %s" % (value))
	
	def start(self):
		oldInstances = {}
		while True:
			try:
				# Make sure transport is open
				if (not self.transport.isOpen()):
					self.transport.open()
				# Generate a list of VMs/host
				hosts = {}
				load = {}
				for h in self.client.getHosts():
					hosts[h.id] = h
					load[h.id] = []
				load[None] = []
				_instances = self.client.getInstances()
				instances = {}
				for i in _instances:
					instances[i.id] = i
				for i in instances.itervalues():
					if (i.hostId or i.state == InstanceState.Pending):
						load[i.hostId] = load[i.hostId] + [i.id]
				# Check for VMs that have exited
				for i in oldInstances:
					if (i not in instances):
						for hook in self.hooks:
							hook.postDestroy(oldInstances[i])
				# Schedule new VMs
				oldInstances = instances
				if (len(load.get(None, [])) > 0):
					for i in load[None]:
						inst = instances[i]
						try:
							minMax = None
							minMaxHost = None
							targetHost = inst.hints.get("targetHost", None)
							try:
								allowElsewhere = boolean(inst.hints.get("allowElsewhere", "False"))
							except Exception, e:
								allowElsewhere = False
							if (targetHost != None):
								for h in hosts.values():
									if ((str(h.id) == targetHost or h.name == targetHost)):
										if (h.up == True and h.state == HostState.Normal):
											memUsage = reduce(lambda x, y: x + instances[y].memory, load[h.id], inst.memory)
											coreUsage = reduce(lambda x, y: x + instances[y].cores, load[h.id], inst.cores)
											if (memUsage <= h.memory and coreUsage <= h.cores):
												minMax = len(load[h.id])
												minMaxHost = h
							if ((targetHost == None or allowElsewhere) and minMaxHost == None):
								for h in hosts.values():
									if (h.up == True and h.state == HostState.Normal):
										if (minMax is None or (self.densePack and len(load[h.id]) > minMax) or (not self.densePack and len(load[h.id]) < minMax)):
											memUsage = reduce(lambda x, y: x + instances[y].memory, load[h.id], inst.memory)
											coreUsage = reduce(lambda x, y: x + instances[y].cores, load[h.id], inst.cores)
											if (memUsage <= h.memory and coreUsage <= h.cores):
												minMax = len(load[h.id])
												minMaxHost = h
							if (minMaxHost):
								if (not inst.hints.get("__resume_source", None)):
									for hook in self.hooks:
										hook.preCreate(inst)
								self.log.info("Scheduling instance %s (%d mem, %d cores, %d uid) on host %s" % (inst.name, inst.memory, inst.cores, inst.userId, minMaxHost.name))	
								self.client.activateVm(i, minMaxHost)
								load[minMaxHost.id] = load[minMaxHost.id] + [i]
							else:
								self.log.info("Failed to find a suitable place to schedule %s" % (inst.name))
						except Exception, e:
							self.log.exception("Failed to schedule or activate %s" % (inst.name))
				time.sleep(self.scheduleDelay)
			except TashiException, e:
				self.log.exception("Tashi exception")
				try:
					self.transport.close()
				except Exception, e:
					self.log.exception("Failed to close the transport")
				time.sleep(self.scheduleDelay)
			except Exception, e:
				self.log.exception("General exception")
				try:
					self.transport.close()
				except Exception, e:
					self.log.exception("Failed to close the transport")
				time.sleep(self.scheduleDelay)

def main():
	(config, configFiles) = getConfig(["Agent"])
	publisher = instantiateImplementation(config.get("Primitive", "publisher"), config)
	tashi.publisher = publisher
	(client, transport) = createClient(config)
	logging.config.fileConfig(configFiles)
	agent = Primitive(config, client, transport)
	agent.start()

if __name__ == "__main__":
	main()
