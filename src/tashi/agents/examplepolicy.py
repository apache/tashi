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
import threading
import time

from tashi.services.ttypes import *
from thrift.transport.TSocket import TServerSocket, TSocket
from thrift.server.TServer import TThreadedServer
from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.transport.TTransport import TBufferedTransport
from tashi.services import clustermanagerservice

class ExamplePolicy():
	def __init__(self, client, transport):
		self.client = client
		self.transport = transport
	
	def start(self):
		while True:
			try:
				if (not self.transport.isOpen()):
					self.transport.open()
				hosts = {}
				load = {}
				for h in self.client.getHosts():
					hosts[h.id] = h
					load[h.id] = []
				load[None] = []
				for i in self.client.getInstances():
					if (i.hostId or i.state == InstanceState.Pending):
						load[i.hostId] = load[i.hostId] + [i.id]
				self.hosts = hosts
				self.load = load
				if (len(self.load.get(None, [])) > 0):
					i = self.load[None][0]
					min = None
					minHost = None
					for h in self.hosts.values():
						if ((min is None or len(load[h.id]) < min) and h.up == True and h.state == HostState.Normal):
							min = len(load[h.id])
							minHost = h
					if (minHost):
						print "Scheduling instance %d on host %s" % (i, minHost.name)
						self.client.activateVm(i, minHost)
						continue
				time.sleep(2)
			except TashiException, e:
				print e.msg
				try:
					self.transport.close()
				except Exception, e:
					print e
				time.sleep(2)
			except Exception, e:
				print e
				try:
					self.transport.close()
				except Exception, e:
					print e
				time.sleep(2)

def createClient():
	host = os.getenv('TASHI_CM_HOST', 'localhost')
	port = os.getenv('TASHI_CM_PORT', '9882')
	timeout = float(os.getenv('TASHI_CM_TIMEOUT', '5000.0'))
	socket = TSocket(host, int(port))
	socket.setTimeout(timeout)
	transport = TBufferedTransport(socket)
	protocol = TBinaryProtocol(transport)
	client = clustermanagerservice.Client(protocol)
	transport.open()
	return (client, transport)

def main():
	(client, transport) = createClient()
	agent = ExamplePolicy(client, transport)
	agent.start()

if __name__ == "__main__":
	main()
