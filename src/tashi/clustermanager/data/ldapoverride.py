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

import subprocess
import time
#XXXstroucki getImages requires os?
import os
from tashi.rpycservices.rpyctypes import User
from tashi.clustermanager.data import DataInterface
from tashi.util import instantiateImplementation

class LdapOverride(DataInterface):
	def __init__(self, config):
		DataInterface.__init__(self, config)
		self.baseDataObject = instantiateImplementation(config.get("LdapOverride", "baseData"), config)
		self.users = {}
		self.lastUserUpdate = 0.0
		self.fetchThreshold = float(config.get("LdapOverride", "fetchThreshold"))
		self.nameKey = config.get("LdapOverride", "nameKey")
		self.idKey = config.get("LdapOverride", "idKey")
		self.ldapCommand = config.get("LdapOverride", "ldapCommand")
	
	def registerInstance(self, instance):
		return self.baseDataObject.registerInstance(instance)
	
	def acquireInstance(self, instanceId):
		return self.baseDataObject.acquireInstance(instanceId)
	
	def releaseInstance(self, instance):
		return self.baseDataObject.releaseInstance(instance)
	
	def removeInstance(self, instance):
		return self.baseDataObject.removeInstance(instance)
	
	def acquireHost(self, hostId):
		return self.baseDataObject.acquireHost(hostId)
	
	def releaseHost(self, host):
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

	def fetchFromLdap(self):
		now = time.time()
		if (now - self.lastUserUpdate > self.fetchThreshold):
			myUsers = {}
			#p = subprocess.Popen("getent passwd".split(), stdout=subprocess.PIPE)
			p = subprocess.Popen(self.ldapCommand.split(), stdout=subprocess.PIPE)
			try:
				thisUser = {}
				for l in p.stdout.xreadlines():
					try:
						if (l.startswith("#")):
							if (self.nameKey in thisUser):
								user = User()
								user.id = int(thisUser[self.idKey])
								user.name = thisUser[self.nameKey]
								myUsers[user.id] = user
							thisUser = {}
						else:
							(key, sep, val) = l.partition(":")
							key = key.strip()
							val = val.strip()
							thisUser[key] = val
					except:
						pass
				self.users = myUsers
				self.lastUserUpdate = now
			finally:
				p.wait()
	
	def getUsers(self):
		self.fetchFromLdap()
		return self.users
	
	def getUser(self, id):
		self.fetchFromLdap()
		return self.users[id]
		
	def registerHost(self, hostname, memory, cores, version):
		return self.baseDataObject.registerHost(hostname, memory, cores, version)
	
	def unregisterHost(self, hostId):
		return self.baseDataObject.unregisterHost(hostId)

