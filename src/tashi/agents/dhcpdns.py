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
from tashi.rpycservices.rpyctypes import Instance
from tashi import boolean


class DhcpDns(InstanceHook):
	def __init__(self, config, client, post=False):
		InstanceHook.__init__(self, config, client, post)
		self.dnsKeyName = self.config.get('DhcpDns', 'dnsKeyName')
		self.dnsSecretKey = self.config.get('DhcpDns', 'dnsSecretKey')
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

		self.initIPs()

	def initIPs(self):
		self.usedIPs = {}
		for network in self.ipRange:
			ipRange = self.ipRange[network]
			(ipMin, ipMax) = ipRange.split("-")
			ipMin = ipMin.strip()
			ipMax = ipMax.strip()
			ipNum = self.strToIp(ipMin)
			self.ipMin[network] = self.strToIp(ipMin)
			self.ipMax[network] = self.strToIp(ipMax)
			self.currentIP[network] = self.ipMin[network]

		instances = self.client.getInstances()
		for i in instances:
			for nic in i.nics:
				try:
					ip = nic.ip
					ipNum = self.strToIp(ip)
					self.log.info('Added %s->%s during reinitialization' % (i.name, ip))
					self.usedIPs[ipNum] = ip
				except Exception:
					pass

	def strToIp(self, s):
		ipNum = -1
		try:
			ipNum = reduce(lambda x, y: x*256+y, map(int, s.split(".")))
		except:
			pass
		return ipNum

	def ipToStr(self, ip):
		return "%d.%d.%d.%d" % ((ip>>24)&0xff, (ip>>16)&0xff, (ip>>8)&0xff, ip&0xff)

	def allocateIP(self, nic):
		# XXXstroucki: if the network is not defined having an ip
		# range, this will throw a KeyError. Should be logged.
		network = nic.network
		allocatedIP = None
		requestedIP = self.strToIp(nic.ip)
		wrapToMinAlready = False
		if (requestedIP <= self.ipMax[network] and
			requestedIP >= self.ipMin[network] and
			(requestedIP not in self.usedIPs)):

			allocatedIP = requestedIP

		# nic.ip will be updated later in preCreate if chosen
		# ip not available
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
# XXXpipe: open omshell session
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
		__output = stdout.read()
		stdout.close()

	def removeDhcp(self, name, ipaddr=None):
		cmd = "omshell"
# XXXpipe: open omshell session
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
		__output = stdout.read()
		stdout.close()

	def addDns(self, name, ip):
		try:
			self.removeDns(name)
		except:
			pass
		cmd = "nsupdate"
		child = subprocess.Popen(args=cmd.split(),
					stdin=subprocess.PIPE,
					stdout=subprocess.PIPE)
		try:
			(stdin, stdout) = (child.stdin, child.stdout)
			stdin.write("server %s\n" % (self.dnsServer))
			stdin.write("key %s %s\n" % (self.dnsKeyName, self.dnsSecretKey))
			stdin.write("update add %s %d A %s\n" % (name, self.dnsExpire, ip))
			stdin.write("\n")
			if (self.reverseDns):
				ipSegments = map(int, ip.split("."))
				ipSegments.reverse()
				reverseIpStr = ("%d.%d.%d.%d.in-addr.arpa" % (ipSegments[0],
						ipSegments[1], ipSegments[2], ipSegments[3]))
				stdin.write("update add %s %d IN PTR %s.\n" % (reverseIpStr,
						self.dnsExpire, name))
				stdin.write("\n")
			stdin.close()
			__output = stdout.read()
			stdout.close()
		finally:
			os.kill(child.pid, signal.SIGTERM)
			(pid, __status) = os.waitpid(child.pid, os.WNOHANG)
			while (pid == 0):
				time.sleep(0.5)
				os.kill(child.pid, signal.SIGTERM)
				(pid, __status) = os.waitpid(child.pid, os.WNOHANG)

	def removeDns(self, name):
		cmd = "nsupdate"
		child = subprocess.Popen(args=cmd.split(), stdin=subprocess.PIPE,
					stdout=subprocess.PIPE)
		try:
			(stdin, stdout) = (child.stdin, child.stdout)
			stdin.write("server %s\n" % (self.dnsServer))
			stdin.write("key %s %s\n" % (self.dnsKeyName, self.dnsSecretKey))
			if (self.reverseDns):
				ip = socket.gethostbyname(name)
				ipSegments = map(int, ip.split("."))
				ipSegments.reverse()
				reverseIpStr = ("%d.%d.%d.%d.in-addr.arpa" % (ipSegments[0],
						ipSegments[1], ipSegments[2], ipSegments[3]))
				stdin.write("update delete %s IN PTR\n" % (reverseIpStr))
				stdin.write("\n")
			stdin.write("update delete %s A\n" % (name))
			stdin.write("\n")
			stdin.close()
			__output = stdout.read()
			stdout.close()
		finally:
			os.kill(child.pid, signal.SIGTERM)
			(pid, __status) = os.waitpid(child.pid, os.WNOHANG)
			while (pid == 0):
				time.sleep(0.5)
				os.kill(child.pid, signal.SIGTERM)
				(pid, __status) = os.waitpid(child.pid, os.WNOHANG)

	def doUpdate(self, instance):
		newInstance = Instance()
		newInstance.id = instance.id
		newInstance.nics = instance.nics
		self.client.vmUpdate(instance.id, newInstance, None)

	def getFqdn(self, instance):
		domainName = self.dnsDomain
		subDomain = instance.hints.get("subDomain", None)
		if subDomain != None:
			domainName = "%s.%s" % (subDomain, self.dnsDomain)

		fqdn = "%s.%s" % (instance.name, domainName)

		return fqdn

	def preCreate(self, instance):
		if (len(instance.nics) < 1):
			return
		for i in range(0, len(instance.nics)):
			nic = instance.nics[i]
			ip = self.allocateIP(nic)
			nic.ip = ip
			try:
				if (i == 0):
					self.log.info("Adding %s:{%s->%s} to DNS" % (instance.name,
					self.getFqdn(instance), ip))
					self.addDns(self.getFqdn(instance), ip)
				if (i == 0):
					dhcpName = instance.name
				else:
					dhcpName = instance.name + "-nic%d" % (i)
				self.log.info("Adding %s:{%s->%s} to DHCP" % (dhcpName, nic.mac, ip))
				self.addDhcp(dhcpName, ip, nic.mac)
			except Exception:
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
				# XXXstroucki: if this fails with KeyError,
				# we must have double-assigned the same IP
				# address. How does this happen?
				del self.usedIPs[ipNum]
			except Exception:
				self.log.exception("Failed to remove host %s, ip %s from pool of usedIPs" %
						(instance.name, ip))
			try:
				if (i == 0):
					dhcpName = instance.name
				else:
					dhcpName = instance.name + "-nic%d" % (i)
				self.removeDhcp(dhcpName)
			except Exception:
				self.log.exception("Failed to remove host %s from DHCP" % (instance.name))
		try:
			# XXXstroucki: this can fail if the resolver can't
			# resolve the dns server name (line 190). Perhaps
			# the hostname should be then pushed onto a list
			# to try again next time.
			self.removeDns(self.getFqdn(instance))
		except Exception:
			self.log.exception("Failed to remove host %s from DNS" % (instance.name))
