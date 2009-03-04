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
import os
import socket
from instancehook import InstanceHook
from tashi import boolean

class DhcpDns(InstanceHook):
	def __init__(self, config, client, transport, post=False):
		InstanceHook.__init__(self, config, client, post)
		self.dnsKeyFile = self.config.get('DhcpDns', 'dnsKeyFile')
		self.dnsServer = self.config.get('DhcpDns', 'dnsServer')
		self.dnsDomain = self.config.get('DhcpDns', 'dnsDomain')
		self.dnsExpire = int(self.config.get('DhcpDns', 'dnsExpire'))
		self.dhcpServer = self.config.get('DhcpDns', 'dhcpServer')
		self.dhcpKeyName = self.config.get('DhcpDns', 'dhcpKeyName')
		self.dhcpSecretKey = self.config.get('DhcpDns', 'dhcpSecretKey')
		self.ipRange = self.config.get('DhcpDns', 'ipRange')
		self.reverseDns = boolean(self.config.get('DhcpDns', 'reverseDns'))
		self.log = logging.getLogger(__file__)
		(ip, bits) = self.ipRange.split("/")
		bits = int(bits)
		ipNum = self.strToIp(ip)
		self.ipMin = ((ipNum>>(32-bits))<<(32-bits)) + 2
		self.ipMax = self.ipMin + (1<<(32-bits)) - 3
		self.usedIPs = {}
		self.currentIP = self.ipMin
		instances = self.client.getInstances()
		for i in instances:
			try:
				ip = socket.gethostbyname(i.name)
				ipNum = self.strToIp(ip)
				self.log.info('Added %s->%s during reinitialization' % (i.name, ip))
				self.usedIPs[ipNum] = ip
			except Exception, e:
				pass
		
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
	
	def preCreate(self, instance):
		ip = self.allocateIP()
		self.log.info("Adding %s:{%s->%s, %s->%s} to DHCP/DNS" % (instance.name, instance.nics[0].mac, ip, instance.name, ip))
		try:
			self.addDhcp(instance.name, ip, instance.nics[0].mac)
			self.addDns(instance.name, ip)
		except Exception, e:
			self.log.exception("Failed to add host %s to DHCP/DNS" % (instance.name))

	def postDestroy(self, instance):
		try:
			ip = socket.gethostbyname(instance.name)
			ipNum = self.strToIp(ip)
			del self.usedIPs[ipNum]
		except Exception, e:
			self.log.exception("Failed to remove host %s from pool of usedIPs" % (instance.name))
		self.log.info("Removing %s from DHCP/DNS" % (instance.name))
		try:
			self.removeDns(instance.name)
			self.removeDhcp(instance.name)
		except Exception, e:
			self.log.exception("Failed to remove host %s from DHCP/DNS" % (instance.name))

