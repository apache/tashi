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
# XXXstroucki getImages needs os?
import os
from tashi.rpycservices.rpyctypes import Errors, Network, Host, User, Instance, TashiException, LocalImages, DiskConfiguration, NetworkConfiguration
from tashi.clustermanager.data.datainterface import DataInterface
from tashi.util import stringPartition, boolean, instantiateImplementation, humanReadable

class SQL(DataInterface):
	def __init__(self, config):
		DataInterface.__init__(self, config)
		self.uri = self.config.get("SQL", "uri")
		self.log = logging.getLogger(__name__)
		self.dfs = instantiateImplementation(config.get("ClusterManager", "dfs"), config)

		if (self.uri.startswith("sqlite://")):
			import sqlite
			self.dbEngine = "sqlite"
			self.conn = sqlite.connect(self.uri[9:], autocommit=1, timeout=1500)
		elif (self.uri.startswith("mysql://")):
			import MySQLdb
			self.dbEngine = "mysql"
			uri = self.uri[8:]
			(user, _, hostdb) = stringPartition(uri, '@')
			(host, _, db) = stringPartition(hostdb, '/')
			self.password = self.config.get('SQL', 'password')
			self.conn = MySQLdb.connect(host=host, user=user, passwd=self.password, db=db)
		else:
			raise TashiException, 'Unknown SQL database engine by URI: %s' % (self.uri)

		self.instanceOrder = ['id', 'vmId', 'hostId', 'decayed', 'state', 'userId', 'name', 'cores', 'memory', 'disks', 'nics', 'hints', 'groupName']
		self.hostOrder = ['id', 'name', 'up', 'decayed', 'state', 'memory', 'cores', 'version', 'notes', 'reserved']
		self.instanceLock = threading.Lock()
		self.instanceIdLock = threading.Lock()
		self.instanceLocks = {}
		self.instanceBusy = {}
		self.hostLock = threading.Lock()
		self.hostLocks = {}
		self.maxInstanceId = 1
		self.idLock = threading.Lock()
		self.sqlLock = threading.Lock()
		self.verifyStructure()

	def executeStatement(self, stmt):
		self.sqlLock.acquire()
		try:
			cur = self.conn.cursor()
			try:
				cur.execute(stmt)
			except:
				self.log.exception('Exception executing SQL statement %s' % stmt)
		finally:
			self.sqlLock.release()
		return cur
		
	def getNewInstanceId(self):
		self.instanceIdLock.acquire()
		cur = self.executeStatement("SELECT MAX(id) FROM instances")
		self.maxInstanceId = cur.fetchone()[0]
		# XXXstroucki perhaps this can be handled nicer
		if (self.maxInstanceId is None):
			self.maxInstanceId = 0
		self.maxInstanceId = self.maxInstanceId + 1
		instanceId = self.maxInstanceId
		self.instanceIdLock.release()
		return instanceId
	
	def verifyStructure(self):
		self.executeStatement("CREATE TABLE IF NOT EXISTS instances (id int(11) NOT NULL, vmId int(11), hostId int(11), decayed tinyint(1) NOT NULL, state int(11) NOT NULL, userId int(11), name varchar(256), cores int(11) NOT NULL, memory int(11) NOT NULL, disks varchar(1024) NOT NULL, nics varchar(1024) NOT NULL, hints varchar(1024) NOT NULL, groupName varchar(256))")
		self.executeStatement("CREATE TABLE IF NOT EXISTS hosts (id INTEGER PRIMARY KEY, name varchar(256) NOT NULL, up tinyint(1) DEFAULT 0, decayed tinyint(1) DEFAULT 0, state int(11) DEFAULT 1, memory int(11), cores int(11), version varchar(256), notes varchar(256), reserved varchar(1024))")
		self.executeStatement("CREATE TABLE IF NOT EXISTS networks (id int(11) NOT NULL, name varchar(256) NOT NULL)")
		self.executeStatement("CREATE TABLE IF NOT EXISTS users (id int(11) NOT NULL, name varchar(256) NOT NULL, passwd varchar(256))")
	
	def sanitizeForSql(self, s):
		if (s == '"True"'):
			return '"1"'
		if (s == '"False"'):
			return '"0"'
		if (s == '"None"'):
			return 'NULL'
		return s
	
	def makeInstanceList(self, i):
		l = []
		for e in range(0, len(self.instanceOrder)):
			l.append(i.__dict__[self.instanceOrder[e]])
		return map(lambda x: self.sanitizeForSql('"%s"' % str(x)), l)
	
	def makeListInstance(self, l):
		i = Instance()
		for e in range(0, len(self.instanceOrder)):
			i.__dict__[self.instanceOrder[e]] = l[e]
		i.state = int(i.state)
		i.decayed = boolean(i.decayed)
		i.disks = map(lambda x: DiskConfiguration(d=x), eval(i.disks))
		i.nics = map(lambda x: NetworkConfiguration(d=x), eval(i.nics))
		i.hints = eval(i.hints)
		return i
	
	def makeHostList(self, h):
		l = []
		for e in range(0, len(self.hostOrder)):
			l.append(h.__dict__[self.hostOrder[e]])
		return map(lambda x: self.sanitizeForSql('"%s"' % str(x)), l)
	
	def makeListHost(self, l):
		h = Host()
		for e in range(0, len(self.hostOrder)):
			h.__dict__[self.hostOrder[e]] = l[e]
		h.up = boolean(h.up)
		h.decayed = boolean(h.decayed)
		h.state = int(h.state)
		if h.reserved is not None:
			h.reserved = eval(h.reserved)
		else:
			h.reserved = []
		return h
	
	def registerInstance(self, instance):
		if type(instance) is not Instance:
			self.log.exception("Argument is not of type Instance, but of type %s" % (type(instance)))
			raise TypeError

		self.instanceLock.acquire()
		try:
			if (instance.id is not None and instance.id not in self.getInstances()):
				self.instanceIdLock.acquire()
				if (instance.id >= self.maxInstanceId):
					self.maxInstanceId = instance.id + 1
				self.instanceIdLock.release()
			else:
				instance.id = self.getNewInstanceId()
			instance._lock = threading.Lock()
			self.instanceLocks[instance.id] = instance._lock
			instance._lock.acquire()
			self.instanceBusy[instance.id] = True
			l = self.makeInstanceList(instance)
			# XXXstroucki nicer?
			self.executeStatement("INSERT INTO instances VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)" % tuple(l))
		finally:
			self.instanceLock.release()
		return instance
	
	def acquireInstance(self, instanceId):
		busyCheck = True
		while busyCheck == True:
			self.instanceLock.acquire()
			busyCheck = self.instanceBusy.setdefault(instanceId, False)
			if busyCheck:
				self.instanceLock.release()

		try:
			cur = self.executeStatement("SELECT * from instances WHERE id = %d" % (instanceId))
			l = cur.fetchone()
			if (not l):
				raise TashiException(d={'errno':Errors.NoSuchInstanceId,'msg':"No such instanceId - %d" % (instanceId)})
			instance = self.makeListInstance(l)
			self.instanceLocks[instance.id] = self.instanceLocks.get(instance.id, threading.Lock())
			instance._lock = self.instanceLocks[instance.id]
			instance._lock.acquire()
			self.instanceBusy[instance.id] = True
		finally:
			self.instanceLock.release()

		return instance
	
	def releaseInstance(self, instance):
		if type(instance) is not Instance:
			self.log.exception("Argument is not of type Instance, but of type %s" % (type(instance)))
			raise TypeError

		self.instanceLock.acquire()
		try:
			l = self.makeInstanceList(instance)
			s = ""
			for e in range(0, len(self.instanceOrder)):
				s = s + self.instanceOrder[e] + "=" + l[e]
				if (e < len(self.instanceOrder)-1):
					s = s + ", "
			self.executeStatement("UPDATE instances SET %s WHERE id = %d" % (s, instance.id))
			self.instanceBusy[instance.id] = False
			instance._lock.release()
		except:
			self.log.exception("Excepted while holding lock")
			raise
		finally:
			self.instanceLock.release()
	
	def removeInstance(self, instance):
		if type(instance) is not Instance:
			self.log.exception("Argument is not of type Instance, but of type %s" % (type(instance)))
			raise TypeError

		self.instanceLock.acquire()
		try:
			self.executeStatement("DELETE FROM instances WHERE id = %d" % (instance.id))
			#XXXstroucki extraneous instance won't have a lock
			try:
				instance._lock.release()
			except:
				pass
			del self.instanceLocks[instance.id]
			del self.instanceBusy[instance.id]
		finally:
			self.instanceLock.release()
	
	def acquireHost(self, hostId):
		if type(hostId) is not int:
			self.log.exception("Argument is not of type int, but of type %s" % (type(hostId)))
			raise TypeError

		host = self.getHost(hostId)
		self.hostLock.acquire()
		self.hostLocks[host.id] = self.hostLocks.get(host.id, threading.Lock())
		self.hostLock.release()
		host._lock = self.hostLocks[host.id]
		host._lock.acquire()
		return host
	
	def releaseHost(self, host):
		if type(host) is not Host:
			self.log.exception("Argument is not of type Host, but of type %s" % (type(host)))
			raise TypeError

		l = self.makeHostList(host)
		s = ""
		for e in range(0, len(self.hostOrder)):
			s = s + self.hostOrder[e] + "=" + l[e]
			if (e < len(self.hostOrder)-1):
				s = s + ", "
		self.executeStatement("UPDATE hosts SET %s WHERE id = %d" % (s, host.id))
		host._lock.release()
	
	def getHosts(self):
		cur = self.executeStatement("SELECT * FROM hosts")
		res = cur.fetchall()
		hosts = {}
		for r in res:
			host = self.makeListHost(r)
			hosts[host.id] = host
		return hosts
	
	def getHost(self, in_id):
		try:
			_id = int(in_id)
		except:
			self.log.exception("Argument to getHost was not integer: %s" % in_id)

		cur = self.executeStatement("SELECT * FROM hosts WHERE id = %d" % _id)
		r = cur.fetchone()
		if (r == None):
			raise TashiException(d={'errno':Errors.NoSuchHostId,'msg':"No such hostId - %s" % (_id)})
		host = self.makeListHost(r)
		return host
	
	def getInstances(self):
		cur = self.executeStatement("SELECT * FROM instances")
		res = cur.fetchall()
		instances = {}
		for r in res:
			instance = self.makeListInstance(r)
			instances[instance.id] = instance
		return instances
	
	def getInstance(self, in_id):
		try:
			_id = int(in_id)
		except:
			self.log.exception("Argument to getInstance was not integer: %s" % in_id)

		cur = self.executeStatement("SELECT * FROM instances WHERE id = %d" % (_id))
		# XXXstroucki should only return one row.
		# what about migration? should it be enforced?
		r = cur.fetchone()
		if (not r):
			raise TashiException(d={'errno':Errors.NoSuchInstanceId, 'msg':"No such instanceId - %d" % (_id)})
		instance = self.makeListInstance(r)
		return instance
	
	def getNetworks(self):
		cur = self.executeStatement("SELECT * FROM networks")
		res = cur.fetchall()
		networks = {}
		for r in res:
			network = Network(d={'id':r[0], 'name':r[1]})
			networks[network.id] = network
		return networks
	
	def getNetwork(self, _id):
		cur = self.executeStatement("SELECT * FROM networks WHERE id = %d" % (_id))
		r = cur.fetchone()
		network = Network(d={'id':r[0], 'name':r[1]})
		return network

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
	
	def getUsers(self):
		cur = self.executeStatement("SELECT * from users")
		res = cur.fetchall()
		users = {}
		for r in res:
			user = User(d={'id':r[0], 'name':r[1], 'passwd':r[2]})
			users[user.id] = user
		return users
	
	def getUser(self, _id):
		cur = self.executeStatement("SELECT * FROM users WHERE id = %d" % (_id))
		r = cur.fetchone()
		user = User(d={'id':r[0], 'name':r[1], 'passwd':r[2]})
		return user
		
	def registerHost(self, hostname, memory, cores, version):
		self.hostLock.acquire()
		cur = self.executeStatement("SELECT * from hosts")
		res = cur.fetchall()
		for r in res:
			if r[1] == hostname:
				_id = r[0]
				self.log.warning("Host %s already registered, update will be done" % _id)
				s = ""
				host = Host(d={'id': _id, 'up': 0, 'decayed': 0, 'state': 1, 'name': hostname, 'memory':memory, 'cores': cores, 'version':version})
				l = self.makeHostList(host)
				for e in range(0, len(self.hostOrder)):
					s = s + self.hostOrder[e] + "=" + l[e]
					if (e < len(self.hostOrder)-1):
						s = s + ", "
				self.executeStatement("UPDATE hosts SET %s WHERE id = %d" % (s, _id))
				self.hostLock.release()
				return r[0], True
		_id = self.getNewId("hosts")
		host = Host(d={'id': _id, 'up': 0, 'decayed': 0, 'state': 1, 'name': hostname, 'memory':memory, 'cores': cores, 'version':version, 'notes':'', 'reserved':[]})
		l = self.makeHostList(host)
		# XXXstroucki nicer?
		self.executeStatement("INSERT INTO hosts VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)" % tuple(l))
		self.hostLock.release()
		return _id, False
	
	def unregisterHost(self, hostId):
		self.hostLock.acquire()
		cur = self.executeStatement("SELECT * from hosts")
		res = cur.fetchall()
		for r in res:
			if r[0] == hostId:
				self.executeStatement("DELETE FROM hosts WHERE id = %d" % hostId)
		self.hostLock.release()

	def getNewId(self, table):
		""" Generates id for a new object. For example for hosts and users.  
		"""
		self.idLock.acquire()
		cur = self.executeStatement("SELECT * from %s" % table)
		res = cur.fetchall()
		maxId = 0 # the first id would be 1
		l = []
		for r in res:
			_id = r[0]
			l.append(_id)
			if _id >= maxId:
				maxId = _id
		l.sort() # sort to enable comparing with range output
		# check if some id is released:
		t = range(maxId + 1)
		t.remove(0)
		if l != t and l != []:
			releasedIds = filter(lambda x : x not in l, t)
			self.idLock.release()
			return releasedIds[0]
		else:
			self.idLock.release()
			return maxId + 1
