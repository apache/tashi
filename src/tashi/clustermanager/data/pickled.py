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
import os
import threading
from tashi.services.ttypes import *
from tashi.clustermanager.data import FromConfig, DataInterface

class Pickled(FromConfig):
	def __init__(self, config):
		DataInterface.__init__(self, config)
		self.file = self.config.get("Pickled", "file")
		self.locks = {}
		self.lockNames = {}
		self.instanceLock = threading.Lock()
		self.lockNames[self.instanceLock] = "instanceLock"
		self.instanceIdLock = threading.Lock()
		self.lockNames[self.instanceIdLock] = "instanceIdLock"
		self.maxInstanceId = 1
		self.load()
	
	def cleanInstances(self):
		ci = {}
		for i in self.instances.itervalues():
			i2 = Instance(d=i.__dict__)
			i2.hostObj = None
			i2.typeObj = None
			i2.userObj = None
			ci[i2.id] = i2
		return ci
	
	def cleanHosts(self):
		ch = {}
		for h in self.hosts.itervalues():
			h2 = Host(d=h.__dict__)
			ch[h2.id] = h2
		return ch
	
	def save(self):
		file = open(self.file, "w")
		cPickle.dump((self.cleanHosts(), self.cleanInstances(), self.machineTypes, self.networks, self.users), file)
		file.close()

	def load(self):
		if (os.access(self.file, os.F_OK)):
			file = open(self.file, "r")
			(hosts, instances, machineTypes, networks, users) = cPickle.load(file)
			file.close()
		else:
			(hosts, instances, machineTypes, networks, users) = ({}, {}, {}, {}, {})
		self.hosts = hosts
		self.instances = instances
		self.machineTypes = machineTypes
		self.networks = networks
		self.users = users
		for i in self.instances.itervalues():
			if (i.id >= self.maxInstanceId):
				self.maxInstanceId = i.id + 1
			i._lock = threading.Lock()
			self.lockNames[i._lock] = "i%d" % (i.id)
		for h in self.hosts.itervalues():
			h._lock = threading.Lock()
			self.lockNames[h._lock] = "h%d" % (h.id)
