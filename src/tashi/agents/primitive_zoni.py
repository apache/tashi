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

# XXXstroucki: this apparently originated from a copy of the primitive
# scheduler code sometime in 2010. It aims to keep a pool of tashi servers
# available, and other servers shut down. Could this be better suited for
# a hook function of the scheduler?

from socket import gethostname
import os
import socket
import sys
import threading
import time
import logging.config
import pickle

from tashi.rpycservices.rpyctypes import *
from tashi.util import getConfig, createClient, instantiateImplementation, boolean
import tashi

from zoni.services.rpycservices import *
import zoni

class Primitive(object):
	def __init__(self, config, client):
		self.config = config
		self.client = client
		self.hooks = []
		self.log = logging.getLogger(__file__)
		self.scheduleDelay = float(self.config.get("Primitive", "scheduleDelay"))
		self.densePack = boolean(self.config.get("Primitive", "densePack"))
		self.hosts = {}

		#  Zoni
		self.minServersOn = 3
		self.shutdownDelay = 300
		self.pcm = zoni.services.rpycservices.client("zoni", 12345).createConn()
		self.zoniStateFile = "/var/tmp/zoniStateFile"
		if os.path.exists(self.zoniStateFile):
			self.zoniState = self.__loadZoniState(self.zoniStateFile)
		else:
			self.zoniState = {}
			self.__initState()

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

	def __loadZoniState(self, filename):
		pkl_file = open(filename, "rb")
		data = pickle.load(pkl_file)
		pkl_file.close()
		return data

	def __saveZoniState(self, array, filename):
		f = open(filename, "wb")
		pickle.dump(array, f)
		f.close()

	def __initState(self):
		hosts = {}
		_instances = self.client.getInstances()
		for h in self.client.getHosts():
			hosts[h.id] = h
			
		self.hosts = hosts
		used_hosts = []
			
		for k,v in hosts.iteritems():
			print "k is ", k
			if v.state == 1:
				self.zoniState[k] = self.zoniState.get(k, {})
				self.zoniState[k]["powerState"] = self.zoniState[k].get("powerState", "On")
				self.zoniState[k]["state"] = self.zoniState[k].get("state", "Available")
			if v.state > 1:
				self.zoniState[k] = self.zoniState.get(k, {})
				self.zoniState[k]["powerState"] = self.zoniState[k].get("powerState", "On")
				self.zoniState[k]["state"] = self.zoniState[k].get("state", "Not Available")

		#  Look and mark nodes free of VM instances
		for i in _instances:
			if i.hostId != None and i.hostId not in used_hosts:
				used_hosts.append(i.hostId)
				self.zoniState[i.hostId]["state"] = "In Use"
		self.__saveZoniState(self.zoniState, self.zoniStateFile)

	def __updateState(self):
		hosts = {}
		used_hosts = []
		_instances = self.client.getInstances()

		for h in self.client.getHosts():
			hosts[h.id] = h
		self.hosts = hosts
		for k,v in hosts.iteritems():
			if v.state == 1:
				self.zoniState[k]["state"] = "Available"
			if v.state > 1:
				self.zoniState[k]["state"] = "Not Available"
		#  Look and mark nodes free of VM instances
		for i in _instances:
			if i.hostId != None and i.hostId not in used_hosts:
				used_hosts.append(i.hostId)
				self.zoniState[i.hostId]["state"] = "In Use"
		self.__saveZoniState(self.zoniState, self.zoniStateFile)

	def __getAvail(self):
		availCount = 0
		for host, val in self.zoniState.iteritems():
			if val['state'] == "Available" and val['powerState'] == "On":
				availCount += 1
		return availCount

	def conservePower(self):
		self.__updateState()
		key = "Tashi"
		try:
			#  Get a list of available hosts
			for host, val in self.zoniState.iteritems():
				if val['state'] == "Available" and self.__getAvail() > self.minServersOn:
					#print "working on host ", host, val, self.hosts[host].name
					self.log.info("VCM SHUTDOWN_REQUEST %s (%s)" %  (self.hosts[host].name, str(host)))
					self.zoniState[host]["powerState"] = "Off"
					self.zoniState[host]["stateTime"]= int(time.time())
					self.pcm.root.powerOff(key, self.hosts[host].name)
					self.__saveZoniState(self.zoniState, self.zoniStateFile)
		except Exception, e:
			print "except", e

		for host, val in self.zoniState.iteritems():

			if self.__getAvail() < self.minServersOn:
				if val['powerState'] == "Off":
					#  Bring up a node
					self.log.info("VCM POWERON_REQUEST %s (%s) - Min Servers requirement not met" %  (self.hosts[host].name, str(host)))
					self.pcm.root.powerOn(key, self.hosts[host].name)
					self.zoniState[host]["powerState"] = "On"
					self.zoniState[host]["stateTime"]= int(time.time())
					self.__saveZoniState(self.zoniState, self.zoniStateFile)

		


	
	def start(self):
		oldInstances = {}
		muffle = {}
		while True:
			try:
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
					if (i not in instances and oldInstances[i].state != InstanceState.Pending):
						for hook in self.hooks:
							hook.postDestroy(oldInstances[i])
				# Schedule new VMs
				oldInstances = instances
				if (len(load.get(None, [])) > 0):
					load[None].sort()
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
							#  TargetHost specified
							if (targetHost != None):
								for h in hosts.values():
									if ((str(h.id) == targetHost or h.name == targetHost)):
										#  make sure that host is up, in a normal state and is not reserved
										if (h.up == True and h.state == HostState.Normal and len(h.reserved) == 0):
											memUsage = reduce(lambda x, y: x + instances[y].memory, load[h.id], inst.memory)
											coreUsage = reduce(lambda x, y: x + instances[y].cores, load[h.id], inst.cores)
											if (memUsage <= h.memory and coreUsage <= h.cores):
												minMax = len(load[h.id])
												minMaxHost = h
								
										#  If a host machine is reserved, only allow if userid is in reserved list
										if ((len(h.reserved) > 0) and inst.userId in h.reserved):
											memUsage = reduce(lambda x, y: x + instances[y].memory, load[h.id], inst.memory)
											coreUsage = reduce(lambda x, y: x + instances[y].cores, load[h.id], inst.cores)
											if (memUsage <= h.memory and coreUsage <= h.cores):
												minMax = len(load[h.id])
												minMaxHost = h


							if ((targetHost == None or allowElsewhere) and minMaxHost == None):
								for h in hosts.values():
									if (h.up == True and h.state == HostState.Normal and len(h.reserved) == 0):
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
								muffle.clear()
							else:
								if (inst.name not in muffle):
									self.log.info("Failed to find a suitable place to schedule %s" % (inst.name))
									muffle[inst.name] = True
						except Exception, e:
							if (inst.name not in muffle):
								self.log.exception("Failed to schedule or activate %s" % (inst.name))
								muffle[inst.name] = True
				time.sleep(self.scheduleDelay)
				self.conservePower()
			except TashiException, e:
				self.log.exception("Tashi exception")
				time.sleep(self.scheduleDelay)
			except Exception, e:
				self.log.exception("General exception")
				time.sleep(self.scheduleDelay)

def main():
	(config, configFiles) = getConfig(["Agent"])
	publisher = instantiateImplementation(config.get("Agent", "publisher"), config)
	tashi.publisher = publisher
	client = createClient(config)
	logging.config.fileConfig(configFiles)
	agent = Primitive(config, client)
	#agent.conservePower()
	agent.start()

if __name__ == "__main__":
	main()
