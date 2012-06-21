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
import cPickle
import os
import threading
from tashi.rpycservices.rpyctypes import Instance, Host
from tashi.clustermanager.data import FromConfig, DataInterface

class Pickled(FromConfig):
	def __init__(self, config):
		DataInterface.__init__(self, config)
		self.log = logging.getLogger(__name__)
		self.file = self.config.get("Pickled", "file")
		self.locks = {}
		self.lockNames = {}
		self.instanceLock = threading.Lock()
		self.lockNames[self.instanceLock] = "instanceLock"
		self.instanceIdLock = threading.Lock()
		self.lockNames[self.instanceIdLock] = "instanceIdLock"
		self.maxInstanceId = 1
		self.hostLock = threading.Lock()
		self.hostLocks = {}
		self.idLock = threading.Lock()
		self.dbLock = threading.Lock()
		self.load()
	
	def cleanInstances(self):
		ci = {}
		for __ignore, i in self.instances.items():
			i2 = Instance(d=i.__dict__)
			ci[i2.id] = i2
		return ci
	
	def cleanHosts(self):
		ch = {}
		for __ignore, h in self.hosts.items():
			h2 = Host(d=h.__dict__)
			ch[h2.id] = h2
		return ch
	
	def save(self):
		filename = self.file
		# XXXstroucki could be better
		tempfile = "%s.new" % filename

		self.dbLock.acquire()
		try:
			filehandle = open(tempfile, "w")
			cPickle.dump((self.cleanHosts(), self.cleanInstances(), self.networks, self.users), filehandle)
			filehandle.close()
			os.rename(tempfile, filename)

		except OSError:
			self.log.exception("Error saving database")

		finally:
			self.dbLock.release()

	def load(self):
		if (os.access(self.file, os.F_OK)):
			filehandle = open(self.file, "r")
			(hosts, instances, networks, users) = cPickle.load(filehandle)
			filehandle.close()
		else:
			(hosts, instances, networks, users) = ({}, {}, {}, {})
		self.hosts = hosts
		self.instances = instances
		self.networks = networks
		self.users = users
		for __ignore, i in self.instances.items():
			if (i.id >= self.maxInstanceId):
				self.maxInstanceId = i.id + 1
			i._lock = threading.Lock()
			self.lockNames[i._lock] = "i%d" % (i.id)
		for __ignore, h in self.hosts.items():
			h._lock = threading.Lock()
			self.lockNames[h._lock] = "h%d" % (h.id)
