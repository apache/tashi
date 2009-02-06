#( Licensed to the Apache Software Foundation (ASF) under one
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
import socket
import sys
import threading
import time

from tashi.services.ttypes import *
from thrift.transport.TSocket import TServerSocket, TSocket
from thrift.server.TServer import TThreadedServer
from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.transport.TTransport import TBufferedTransport
from tashi.services import clustermanagerservice
from tashi.util import getConfig, boolean

class DhcpDnsScheduler():
	def __init__(self, config, client, transport):
		self.config = config
		self.client = client
		self.transport = transport
		self.dnsKeyFile = config.get('DhcpDnsScheduler', 'dnsKeyFile')
		self.dnsServer = config.get('DhcpDnsScheduler', 'dnsServer')
		self.dnsDomain = config.get('DhcpDnsScheduler', 'dnsDomain')
		self.dnsExpire = int(config.get('DhcpDnsScheduler', 'dnsExpire'))
		self.dhcpServer = config.get('DhcpDnsScheduler', 'dhcpServer')
		self.dhcpKeyName = config.get('DhcpDnsScheduler', 'dhcpKeyName')
		self.dhcpSecretKey = config.get('DhcpDnsScheduler', 'dhcpSecretKey')
		self.ipRange = config.get('DhcpDnsScheduler', 'ipRange')
		self.reverseDns = boolean(config.get('DhcpDnsScheduler', 'reverseDns'))
		(ip, bits) = self.ipRange.split("/")
		bits = int(bits)
		ipNum = self.strToIp(ip)
		self.ipMin = ((ipNum>>(32-bits))<<(32-bits)) + 2
		self.ipMax = self.ipMin + (1<<(32-bits)) - 3
		self.usedIPs = {}
		self.currentIP = self.ipMin
		if (not self.transport.isOpen()):
			self.transport.open()
		instances = self.client.getInstances()
		for i in instances:
			try:
				ip = socket.gethostbyname(i.name)
				ipNum = self.strToIp(ip)
				self.usedIPs[ipNum] = ip
			except Exception, e:
				pass
		os.write(1, "usedIPs: %s\n" % (str(self.usedIPs)))
	
	def strToIp(self, s):
		ipNum = reduce(lambda x, y: x*256+y, map(int, s.split(".")))
		return ipNum
	
	def ipToStr(self, ip):
		return "%d.%d.%d.%d" % (ip>>24, (ip>>16)%256, (ip>>8)%256, ip%256)
	
	def allocateIP(self):
		self.currentIP = self.currentIP + 1
		while (self.currentIP in self.usedIPs or self.currentIP > self.ipMax):
			if (self.currentIP > self.ipMax):
				self.currentIP = self.ipMin
			else:
				self.currentIP = self.currentIP + 1
		ipString = self.ipToStr(self.currentIP)
		self.usedIPs[self.currentIP] = ipString
		return ipString
	
	def addDhcp(self, name, ipaddr, hwaddr):
		cmd = "omshell"
		(stdin, stdout) = os.popen2(cmd)
		stdin.write("server %s\n" % (self.dhcpServer))
		if (self.dhcpSecretKey != ""):
			stdin.write("key %s %s\n" % (self.dhcpKeyName, self.dhcpSecretKey))
		stdin.write("connect\n")
		stdin.write("new \"host\"\n")
		stdin.write("set name = \"%s\"\n" % (name))
		stdin.write("set ip-address = %s\n" % (ipaddr))
		stdin.write("set hardware-address = %s\n" % (hwaddr))
		stdin.write("set hardware-type = 00:00:00:01\n") # Ethernet
		stdin.write("create\n")
		stdin.close()
		output = stdout.read()
		stdout.close()

	def removeDhcp(self, name):
		cmd = "omshell"
		(stdin, stdout) = os.popen2(cmd)
		stdin.write("server %s\n" % (self.dhcpServer))
		if (self.dhcpSecretKey != ""):
			stdin.write("key %s %s\n" % (self.dhcpKeyName, self.dhcpSecretKey))
		stdin.write("connect\n")
		stdin.write("new \"host\"\n")
		stdin.write("set name = \"%s\"\n" % (name))
		stdin.write("open\n")
		stdin.write("remove\n")
		stdin.close()
		output = stdout.read()
		stdout.close()

	def addDns(self, name, ip):
		if (self.dnsKeyFile != ""):
			cmd = "nsupdate -k %s" % (self.dnsKeyFile)
		else:
			cmd = "nsupdate"
		(stdin, stdout) = os.popen2(cmd)
		stdin.write("server %s\n" % (self.dnsServer))
		stdin.write("update add %s.%s %d A %s\n" % (name, self.dnsDomain, self.dnsExpire, ip))
		stdin.write("\n")
		if (self.reverseDns):
			ipSegments = map(int, ip.split("."))
			ipSegments.reverse()
			reverseIpStr = ("%d.%d.%d.%d.in-addr.arpa" % (ipSegments[0], ipSegments[1], ipSegments[2], ipSegments[3]))
			stdin.write("update add %s %d IN PTR %s.%s.\n" % (reverseIpStr, self.dnsExpire, name, self.dnsDomain))
			stdin.write("\n")
		stdin.close()
		output = stdout.read()
		stdout.close()

	def removeDns(self, name):
		if (self.dnsKeyFile != ""):
			cmd = "nsupdate -k %s" % (self.dnsKeyFile)
		else:
			cmd = "nsupdate"
		(stdin, stdout) = os.popen2(cmd)
		stdin.write("server %s\n" % (self.dnsServer))
		if (self.reverseDns):
			ip = socket.gethostbyname(name)
			ipSegments = map(int, ip.split("."))
			ipSegments.reverse()
			reverseIpStr = ("%d.%d.%d.%d.in-addr.arpa" % (ipSegments[0], ipSegments[1], ipSegments[2], ipSegments[3]))
			stdin.write("update delete %s IN PTR\n" % (reverseIpStr))
			stdin.write("\n")
		stdin.write("update delete %s.%s A\n" % (name, self.dnsDomain))
		stdin.write("\n")
		stdin.close()
		output = stdout.read()
		stdout.close()

	def start(self):
		oldInstances = []
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
				instances = self.client.getInstances()
				instanceIds = [i.id for i in instances]
				for i in oldInstances:
					if (i.id not in instanceIds):
						try:
							ip = socket.gethostbyname(i.name)
							ipNum = self.strToIp(ip)
							del self.usedIPs[ipNum]
						except Exception, e:
							os.write(1, "%s\n" % (str(e)))
							os.write(1, "Failed to remove from pool of usedIPs\n")
						os.write(1, "usedIPs: %s\n" % (str(self.usedIPs)))
						os.write(1, "Removing %s from DHCP/DNS\n" % (i.name))
						self.removeDns(i.name)
						self.removeDhcp(i.name)
				oldInstances = instances
				for i in instances:
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
						inst = None
						for _inst in instances:
							if (_inst.id == i):
								inst = _inst
						ip = self.allocateIP()
						os.write(1, "Adding %s to DHCP/DNS\n" % (inst.name))
						self.addDhcp(inst.name, ip, inst.nics[0].mac)
						self.addDns(inst.name, ip)
						os.write(1, "Scheduling instance %d on host %s\n" % (i, minHost.name))
						self.client.activateVm(i, minHost)
						continue
				time.sleep(2)
			except TashiException, e:
				os.write(1, "%s\n" % (e.msg))
				try:
					self.transport.close()
				except Exception, e:
					os.write(1, "%s\n" % str(e))
				time.sleep(2)
			except Exception, e:
				os.write(1, "%s\n" % (str(e)))
				try:
					self.transport.close()
				except Exception, e:
					os.write(1, "%s\n" % (str(e)))
				time.sleep(2)

def createClient(config):
	host = config.get('Client', 'clusterManagerHost')
	port = config.get('Client', 'clusterManagerPort')
	timeout = float(config.get('Client', 'clusterManagerTimeout')) * 1000.0
	socket = TSocket(host, int(port))
	socket.setTimeout(timeout)
	transport = TBufferedTransport(socket)
	protocol = TBinaryProtocol(transport)
	client = clustermanagerservice.Client(protocol)
	transport.open()
	return (client, transport)

def main():
	(config, configFiles) = getConfig(["Agent"])
	(client, transport) = createClient(config)
	agent = DhcpDnsScheduler(config, client, transport)
	agent.start()

if __name__ == "__main__":
	main()
