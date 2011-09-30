#!/usr/bin/env python
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
#
#  $Id$
#


import rpyc

pcmRPCs = ['releaseResource', 'requestResources', 'getResources', 'getMyResources', 'powerOn', 'powerReset', 'powerOff']
hardwareRPCs = ['getPowerStatus']

class client:
	def __init__(self, host, port, username=None, password=None):
		"""Client for ManagerService. If username and password are provided, rpyc.tls_connect will be used to connect, else rpyc.connect will be used."""
		self.host = host
		self.port = int(port)
		self.username = username
		self.password = password
		self.conn = self.createConn()

	def createConn(self):
		"""Creates a rpyc connection."""
		if self.username != None and self.password != None:
			return rpyc.tls_connect(host=self.host, port=self.port, username=self.username, password=self.password)
		else:
			return rpyc.connect(host=self.host, port=self.port)

	def __getattr__(self, name):
		"""Returns a function that makes the RPC call. No keyword arguments allowed when calling this function."""
		if self.conn.closed == True:
			self.conn = self.createConn()
		def connectWrap(*args):
			print "INSIDE CLIENT  connectWroap__getattr__", self, name, "args ", args
			try:
				res = getattr(self.conn.root, name)(args)
			except Exception, e:
				self.conn.close()
				raise e
			if isinstance(res, Exception):
				raise res
			return res
		return connectWrap

class ManagerService(rpyc.Service):
	"""Custom access to attributes of this object"""

	def _rpyc_getattr(self, name):
		if name in pcmRPCs:
			res = getattr(self.service, name)	
		elif name in hardwareRPCs:
			res = getattr(self.hardware, name)	
		else:
			raise AttributeError("RPC '%s' not supported" % name)
		return res
