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

import rpyc
from tashi.rpycservices.rpyctypes import Instance, Host, User
import cPickle

clusterManagerRPCs = ['createVm', 'shutdownVm', 'destroyVm', 'suspendVm', 'resumeVm', 'migrateVm', 'pauseVm', 'unpauseVm', 'getHosts', 'getNetworks', 'getUsers', 'getInstances', 'vmmSpecificCall', 'registerNodeManager', 'vmUpdate', 'activateVm', 'registerHost', 'unregisterHost', 'getImages', 'copyImage', 'cloneImage', 'rebaseImage', 'setHostState', 'setHostNotes', 'addReservation', 'delReservation', 'getReservation']
nodeManagerRPCs = ['instantiateVm', 'shutdownVm', 'destroyVm', 'suspendVm', 'resumeVm', 'prepReceiveVm', 'prepSourceVm', 'migrateVm', 'receiveVm', 'pauseVm', 'unpauseVm', 'getVmInfo', 'listVms', 'vmmSpecificCall', 'getHostInfo', 'liveCheck']
accountingRPCs = ['record']

def clean(args):
	"""Cleans the object so cPickle can be used."""
	if isinstance(args, list) or isinstance(args, tuple):
		cleanArgs = []
		for arg in args:
			cleanArgs.append(clean(arg))
		if isinstance(args, tuple):
			cleanArgs = tuple(cleanArgs)
		return cleanArgs
	if isinstance(args, Instance):
		return Instance(args.__dict__)
	if isinstance(args, Host):
		return Host(args.__dict__)
	if isinstance(args, User):
		user = User(args.__dict__)
		user.passwd = None
		return user
	return args

class client:
	def __init__(self, host, port, username=None, password=None):
		"""Client for ManagerService. If username and password are provided, rpyc.tlslite_connect will be used to connect, else rpyc.connect will be used."""
		self.host = host
		self.port = int(port)
		self.username = username
		self.password = password
		self.conn = self.createConn()
	
	def createConn(self):
		"""Creates a rpyc connection."""
		if self.username != None and self.password != None:
			return rpyc.tlslite_connect(host=self.host, port=self.port, username=self.username, password=self.password)
		else:
			return rpyc.connect(host=self.host, port=self.port)

	def __getattr__(self, name):
		"""Returns a function that makes the RPC call. No keyword arguments allowed when calling this function."""
		if self.conn.closed == True:
			self.conn = self.createConn()
		if name not in clusterManagerRPCs and name not in nodeManagerRPCs and name not in accountingRPCs:
			return None
		def connectWrap(*args):
			# XXXstroucki: why not talk directly, instead
			# of using rpyc? We're already using pickle to move
			# args.
			args = cPickle.dumps(clean(args))
			try:
				res = getattr(self.conn.root, name)(args)
			except Exception, e:
				self.conn.close()
				raise e
			res = cPickle.loads(res)
			if isinstance(res, Exception):
				raise res
			return res
		return connectWrap

class ManagerService(rpyc.Service):
	"""Wrapper for rpyc service"""
	# Note: self.service and self._type are set before rpyc.utils.server.ThreadedServer is started.
	def checkValidUser(self, functionName, clientUsername, args):
		"""Checks whether the operation requested by the user is valid based on clientUsername. An exception will be thrown if not valid."""
		if self._type == 'AccountingService':
			return
		if self._type == 'NodeManagerService':
			return
		if clientUsername in ['nodeManager', 'agent', 'root']:
			return
		if functionName in ['destroyVm', 'shutdownVm', 'pauseVm', 'vmmSpecificCall', 'suspendVm', 'unpauseVm', 'migrateVm', 'resumeVm']:
			instanceId = args[0]
			instance = self.service.data.getInstance(instanceId)
			instanceUsername = self.service.data.getUser(instance.userId).name
			if clientUsername != instanceUsername:
				raise Exception('Permission Denied: %s cannot perform %s on VM owned by %s' % (clientUsername, functionName, instanceUsername))
		return
		
	def _rpyc_getattr(self, name):
		"""Returns the RPC corresponding to the function call"""
		def makeCall(args):
			args = cPickle.loads(args)
			if self._conn._config['credentials'] != None:
				try:
					self.checkValidUser(makeCall._name, self._conn._config['credentials'], args)
				except Exception, e:
					e = cPickle.dumps(clean(e))
					return e
			try:
				res = getattr(self.service, makeCall._name)(*args)
			except Exception, e:
				res = e
			res = cPickle.dumps(clean(res))
			return res
		makeCall._name = name
		if self._type == 'ClusterManagerService' and name in clusterManagerRPCs:
			return makeCall
		if self._type == 'NodeManagerService' and name in nodeManagerRPCs:
			return makeCall
		if self._type == 'AccountingService' and name in accountingRPCs:
			return makeCall

		raise AttributeError('RPC does not exist')
