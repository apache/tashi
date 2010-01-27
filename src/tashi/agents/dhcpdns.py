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
import signal
import socket
import subprocess
import time
from instancehook import InstanceHook
from tashi.rpycservices.rpyctypes import Instance, NetworkConfiguration
from tashi import boolean

class DhcpDns(InstanceHook):
	def __init__(self, config, client, post=False):
		InstanceHook.__init__(self, config, client, post)
		self.dnsKeyFile = self.config.get('DhcpDns', 'dnsKeyFile')
		self.dnsServer = self.config.get('DhcpDns', 'dnsServer')
		self.dnsDomain = self.config.get('DhcpDns', 'dnsDomain')
		self.dnsExpire = int(self.config.get('DhcpDns', 'dnsExpire'))
		self.dhcpServer = self.config.get('DhcpDns', 'dhcpServer')
		self.dhcpKeyName = self.config.get('DhcpDns', 'dhcpKeyName')
		self.dhcpSecretKey = self.config.get('DhcpDns', 'dhcpSecretKey')
		items = self.config.items('DhcpDns')
		items.sort()
		self.ipRange = {}
		for item in items:
			(name, value) = item
			name = name.lower()
			if (name.startswith('iprange')):
				network = name[7:]
				try:
					network = int(network)
				except:
					continue
				self.ipRange[network] = value	
		self.reverseDns = boolean(self.config.get('DhcpDns', 'reverseDns'))
		self.log = logging.getLogger(__file__)
		self.ipMin = {}
		self.ipMax = {}
		self.currentIP = {}
		self.usedIPs = {}
		for k in self.ipRange:
			ipRange = self.ipRange[k]
			(min, max) = ipRange.split("-")	
			min = min.strip()
			max = max.strip()
			ipNum = self.strToIp(min)
			self.ipMin[k] = self.strToIp(min)
			self.ipMax[k] = self.strToIp(max)
			self.currentIP[k] = self.ipMin[k]
		instances = self.client.getInstances()
		for i in instances:
			for nic in i.nics:
				try:
					ip = nic.ip
					ipNum = self.strToIp(ip)
					self.log.info('Added %s->%s during reinitialization' % (i.name, ip))
					self.usedIPs[ipNum] = ip
				except Exception, e:
					pass
		
	def strToIp(self, s):
		ipNum = -1
		try:
			ipNum = reduce(lambda x, y: x*256+y, map(int, s.split(".")))
		except:
			pass
		return ipNum
	
	def ipToStr(self, ip):
		return "%d.%d.%d.%d" % (ip>>24, (ip>>16)%256, (ip>>8)%256, ip%256)
	
	def allocateIP(self, nic):
		network = nic.network
		allocatedIP = None
		requestedIP = self.strToIp(nic.ip)
		wrapToMinAlready = False
		if (requestedIP <= self.ipMax[network] and requestedIP >= self.ipMin[network] and (requestedIP not in self.usedIPs)):
			allocatedIP = requestedIP
		while (allocatedIP == None):
			if (self.currentIP[network] > self.ipMax[network] and wrapToMinAlready):
				raise UserWarning("No available IP addresses for network %d" % (network))
			if (self.currentIP[network] > self.ipMax[network]):
				self.currentIP[network] = self.ipMin[network]
				wrapToMinAlready = True
			elif (self.currentIP[network] in self.usedIPs):
				self.currentIP[network] = self.currentIP[network] + 1
			else:
				allocatedIP = self.currentIP[network]
		ipString = self.ipToStr(allocatedIP)
		self.usedIPs[allocatedIP] = ipString
		return ipString
	
	def addDhcp(self, name, ipaddr, hwaddr):
		try:
			self.removeDhcp(name)
			self.removeDhcp(name, ipaddr)
		except:
			pass
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

	def removeDhcp(self, name, ipaddr=None):
		cmd = "omshell"
		(stdin, stdout) = os.popen2(cmd)
		stdin.write("server %s\n" % (self.dhcpServer))
		if (self.dhcpSecretKey != ""):
			stdin.write("key %s %s\n" % (self.dhcpKeyName, self.dhcpSecretKey))
		stdin.write("connect\n")
		stdin.write("new \"host\"\n")
		if (ipaddr == None):
			stdin.write("set name = \"%s\"\n" % (name))
		else:
			stdin.write("set ip-address = %s\n"%(ipaddr))
		stdin.write("open\n")
		stdin.write("remove\n")
		stdin.close()
		output = stdout.read()
		stdout.close()
	
	def addDns(self, name, ip):
		try:
			self.removeDns(name)
		except:
			pass
		if (self.dnsKeyFile != ""):
			cmd = "nsupdate -k %s" % (self.dnsKeyFile)
		else:
			cmd = "nsupdate"
		child = subprocess.Popen(args=cmd.split(), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
		try:
			(stdin, stdout) = (child.stdin, child.stdout)
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
		finally:
			os.kill(child.pid, signal.SIGTERM)
			(pid, status) = os.waitpid(child.pid, os.WNOHANG)
			while (pid == 0): 
				time.sleep(0.5)
				os.kill(child.pid, signal.SIGTERM)
				(pid, status) = os.waitpid(child.pid, os.WNOHANG)
	
	def removeDns(self, name):
		if (self.dnsKeyFile != ""):
			cmd = "nsupdate -k %s" % (self.dnsKeyFile)
		else:
			cmd = "nsupdate"
		child = subprocess.Popen(args=cmd.split(), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
		try:
			(stdin, stdout) = (child.stdin, child.stdout)
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
		finally:
			os.kill(child.pid, signal.SIGTERM)
			(pid, status) = os.waitpid(child.pid, os.WNOHANG)
			while (pid == 0): 
				time.sleep(0.5)
				os.kill(child.pid, signal.SIGTERM)
				(pid, status) = os.waitpid(child.pid, os.WNOHANG)
	
	def doUpdate(self, instance):
		newInstance = Instance()
		newInstance.id = instance.id
		newInstance.nics = instance.nics
		self.client.vmUpdate(instance.id, newInstance, None)

	def preCreate(self, instance):
		if (len(instance.nics) < 1):
			return
		for i in range(0, len(instance.nics)):
			nic = instance.nics[i]
			ip = self.allocateIP(nic)
			nic.ip = ip
			try:
				if (i == 0):
					self.log.info("Adding %s:{%s->%s} to DNS" % (instance.name, instance.name, ip))
					self.addDns(instance.name, ip)
				if (i == 0):
					dhcpName = instance.name
				else:
					dhcpName = instance.name + "-nic%d" % (i)
				self.log.info("Adding %s:{%s->%s} to DHCP" % (dhcpName, nic.mac, ip))
				self.addDhcp(dhcpName, ip, nic.mac)
			except Exception, e:
				self.log.exception("Failed to add host %s to DHCP/DNS" % (instance.name))
		self.doUpdate(instance)

	def postDestroy(self, instance):
		if (len(instance.nics) < 1):
			return
		self.log.info("Removing %s from DHCP/DNS" % (instance.name))
		for i in range(0, len(instance.nics)):
			nic = instance.nics[i]
			ip = nic.ip
			try:
				ipNum = self.strToIp(ip)
				del self.usedIPs[ipNum]
			except Exception, e:
				self.log.exception("Failed to remove host %s, ip %s from pool of usedIPs" % (instance.name, ip))
			try:
				if (i == 0):
					dhcpName = instance.name
				else:
					dhcpName = instance.name + "-nic%d" % (i)
				self.removeDhcp(dhcpName)
			except Exception, e:
				self.log.exception("Failed to remove host %s from DHCP" % (instance.name))
		try:
			self.removeDns(instance.name)
		except Exception, e:
			self.log.exception("Failed to remove host %s from DNS" % (instance.name))
