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
import subprocess
import time
import os
from tashi.rpycservices.rpyctypes import User, LocalImages
from tashi.clustermanager.data import DataInterface
from tashi.util import instantiateImplementation, humanReadable

class GetentOverride(DataInterface):
	def __init__(self, config):
		DataInterface.__init__(self, config)
		self.log = logging.getLogger(__name__)
		self.baseDataObject = instantiateImplementation(config.get("GetentOverride", "baseData"), config)
		self.dfs = instantiateImplementation(config.get("ClusterManager", "dfs"), config)

		self.users = {}
		self.lastUserUpdate = 0.0
		self.fetchThreshold = float(config.get("GetentOverride", "fetchThreshold"))
	
	def registerInstance(self, instance):
		if type(instance) is not Instance:
			self.log.exception("Argument is not of type Instance, but of type %s" % (type(instance)))
			raise TypeError

		return self.baseDataObject.registerInstance(instance)
	
	def acquireInstance(self, instanceId):
		return self.baseDataObject.acquireInstance(instanceId)
	
	def releaseInstance(self, instance):
		if type(instance) is not Instance:
			self.log.exception("Argument is not of type Instance, but of type %s" % (type(instance)))
			raise TypeError

		return self.baseDataObject.releaseInstance(instance)
	
	def removeInstance(self, instance):
		if type(instance) is not Instance:
			self.log.exception("Argument is not of type Instance, but of type %s" % (type(instance)))
			raise TypeError

		return self.baseDataObject.removeInstance(instance)
	
	def acquireHost(self, hostId):
		if type(hostId) is not int:
			self.log.exception("Argument is not of type int, but of type %s" % (type(hostId)))
			raise TypeError

		return self.baseDataObject.acquireHost(hostId)
	
	def releaseHost(self, host):
		if type(host) is not Instance:
			self.log.exception("Argument is not of type Host, but of type %s" % (type(host)))
			raise TypeError

		return self.baseDataObject.releaseHost(host)
	
	def getHosts(self):
		return self.baseDataObject.getHosts()
	
	def getHost(self, id):
		return self.baseDataObject.getHost(id)
	
	def getInstances(self):
		return self.baseDataObject.getInstances()
	
	def getInstance(self, id):
		return self.baseDataObject.getInstance(id)
	
	def getNetworks(self):
		return self.baseDataObject.getNetworks()
	
	def getNetwork(self, id):
		return self.baseDataObject.getNetwork(id)

	def getImages(self):
		count = 0
		myList = []
		for i in self.dfs.list("images"):
			myFile = self.dfs.getLocalHandle("images/" + i)
			if os.path.isfile(myFile):
				image = LocalImages(d={'id':count, 'imageName':i, 'imageSize':humanReadable(self.dfs.stat(myFile)[6])})
				myList.append(image)
				count += 1
		return myList
	
	def fetchFromGetent(self):
		now = time.time()
		if (now - self.lastUserUpdate > self.fetchThreshold):
			myUsers = {}
			p = subprocess.Popen("getent passwd".split(), stdout=subprocess.PIPE)
			try:
				for l in p.stdout.xreadlines():
					ws = l.strip().split(":")
					id = int(ws[2])
					name = ws[0]
					user = User()
					user.id = id
					user.name = name
					myUsers[id] = user
				self.users = myUsers
				self.lastUserUpdate = now
			finally:	
				p.wait()
	
	def getUsers(self):
		self.fetchFromGetent()
		return self.users
	
	def getUser(self, id):
		self.fetchFromGetent()
		return self.users[id]
		
	def registerHost(self, hostname, memory, cores, version):
		return self.baseDataObject.registerHost(hostname, memory, cores, version)
	
	def unregisterHost(self, hostId):
		return self.baseDataObject.unregisterHost(hostId)

