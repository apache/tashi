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

from thrift.transport.TSocket import TSocket, socket
from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.transport.TTransport import TBufferedTransport

class ConnectionManager(object):
	def __init__(self, clientClass, port, timeout=10000.0):
		self.clientClass = clientClass
		self.timeout = timeout
		self.port = port
	
	class anonClass(object):
		def __init__(self, clientObject):
			self.co = clientObject
		
		def __getattr__(self, name):
			if (name.startswith("_")):
				return self.__dict__[name]
			def connectWrap(*args, **kw):
				if (not self.co._iprot.trans.isOpen()):
					self.co._iprot.trans.open()
				try:
					res = getattr(self.co, name)(*args, **kw)
				except socket.error, e:
					# Force a close for the case of a "Broken pipe"
#					print "Forced a socket close"
					self.co._iprot.trans.close()
					self.co._iprot.trans.open()
					res = getattr(self.co, name)(*args, **kw)
					self.co._iprot.trans.close()
					raise
				self.co._iprot.trans.close()
				return res
			return connectWrap
	
	def __getitem__(self, hostname):
                port = self.port
                if len(hostname) == 2:
                        port = hostname[1]
                        hostname = hostname[0]
		socket = TSocket(hostname, port)
		socket.setTimeout(self.timeout)
		transport = TBufferedTransport(socket)
		protocol = TBinaryProtocol(transport)
		client = self.clientClass(protocol)
		client.__transport__ = transport
		return self.anonClass(client)
