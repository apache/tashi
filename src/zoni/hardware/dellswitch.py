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

import os
import sys
import pexpect
import datetime
import time
import thread
import string
import getpass
import socket
import tempfile
import logging

#import zoni
from zoni.data.resourcequerysql import *
from zoni.hardware.hwswitchinterface import HwSwitchInterface
from zoni.data.resourcequerysql import ResourceQuerySql
from zoni.agents.dhcpdns import DhcpDns
from zoni.extra.util import *


'''  Using pexpect to control switches because couldn't get snmp to work 
'''

class HwDellSwitch(HwSwitchInterface):
	def __init__(self, config, host=None):
		self.config = config
		self.host = host
		self.verbose = False
		self.log = logging.getLogger(os.path.basename(__file__))

		try:
			self.switchModel = host['hw_model']
		except:
			pass


	def setVerbose(self, verbose):
		self.verbose = verbose

	def __login(self):
		# ssh
		if self.config['hardwareControl']['dellswitch']['accessmode'] == "ssh":
			switchIp = "ssh " +  self.host['hw_userid'] + "@" + self.host['hw_name']
		# telnet 
		else:
			switchIp = "telnet " +  self.host['hw_name'] 



		child = pexpect.spawn(switchIp)

		#  Be Verbose and print everything
		if self.verbose:
			child.logfile = sys.stdout

		opt = child.expect(['Name:', 'assword:', 'Are you sure.*', 'User:', 'No route to host', pexpect.EOF, pexpect.TIMEOUT])

		#  Unable to connect
		if opt == 4:
			mesg = "ERROR:  Login to %s failed\n" % (self.host['hw_name'])
			self.log.error(mesg)
			exit(1)
			
		#XXX  Doesn't seem to do what I want:(
		child.setecho(False)

		#  Send a yes to register authenticity of host for ssh
		if opt == 2:
			child.sendline("yes")
			opt = child.expect(['Name:', 'assword:', 'Are you sure.*', pexpect.EOF, pexpect.TIMEOUT])
			
		if opt == 0 or opt == 3:
			child.sendline(self.host['hw_userid'])
			i = child.expect(['assword:', 'Connection',  pexpect.EOF, pexpect.TIMEOUT])
			child.sendline(self.host['hw_password'])
			i=child.expect(['console','#', 'Name:', '>',pexpect.EOF, pexpect.TIMEOUT])
			if i == 2:
				mesg = "ERROR:  Login to %s failed\n" % (self.host['hw_name'])
				self.log.error(mesg)
				exit(1)

		if opt == 1:
			#  the 6448 doesn't prompt for username
			child.sendline(self.host['hw_password'])
			i=child.expect(['console','>', 'Name:', pexpect.EOF, pexpect.TIMEOUT])
			#  on the 6448 dell, need to send enable, just send to all
		
		if opt == 1 or opt == 3:
			child.sendline('enable')
			i=child.expect(['#', pexpect.EOF, pexpect.TIMEOUT])

		return child

	def __getPrsLabel(self):
		dadate = datetime.datetime.now().strftime("%Y%m%d-%H%M-%S")
		return "Zoni_" + dadate

	def __genPortName(self, port):
		if "62" in self.switchModel:
			return "1/g%s" % str(port)
		elif "54" in self.switchModel:
			return "g%s" % str(port)
		else:
			return "g%s" % str(port)

	def labelPort(self, desc=None):
		mydesc = "%s-%s" % (self.host['location'], desc)
		if desc == None or desc == " ":
			mydesc = "%s" % (self.host['location'])
		child = self.__login()
		child.sendline('config')
		portname = self.__genPortName(self.host['hw_port'])
		cmd = "interface ethernet %s" % str(portname)
		child.sendline(cmd)
		cmd = "description \"%s\"" % mydesc
		child.sendline(cmd)
		child.sendline('exit')
		child.terminate()
	
	def enableHostPort(self):
		child = self.__login()
		child.sendline('config')
		portname = self.__genPortName(self.host['hw_port'])
		cmd = "interface ethernet %s" % str(portname)
		child.sendline(cmd)
		cmd = "no shutdown" 
		child.sendline(cmd)
		child.sendline('exit')
		child.terminate()
		self.log.info("Host port enabled %s:%s" % (self.host['hw_name'], self.host['hw_port']))
		
	def disableHostPort(self):
		child = self.__login()
		child.sendline('config')
		portname = self.__genPortName(self.host['hw_port'])
		cmd = "interface ethernet %s" % str(portname)
		child.sendline(cmd)
		cmd = "shutdown"
		child.sendline(cmd)
		child.sendline('exit')
		child.terminate()
		self.log.info("Host port disabled %s:%s" % (self.host['hw_name'], self.host['hw_port']))

	def removeVlan(self, num):
		#  Check for important vlans
		
		cmd = "no vlan " + num
		child = self.__login()
		child.sendline('config')
		child.sendline('vlan database')
		child.sendline(cmd)
		child.sendline('exit')
		child.terminate()
		self.log.info("Vlan %s removed from switch %s" % (num, self.host['hw_name']))
	
	def addVlanToTrunk(self, vlan):
		mesg = "Adding Vlan %s to trunks on switch" % (vlan)
		self.log.info(mesg)
		child = self.__login()
		child.sendline('config')
		cmd = "interface range port-channel all"
		child.sendline(cmd)
		child.expect(["config-if", pexpect.EOF])
		cmd = "switchport trunk allowed vlan add " + vlan
		child.sendline(cmd)
		child.sendline('exit')

	def createVlansThread(self, vlan, switch,host):
		mesg = "Creating vlan %s on switch %s" % (str(vlan),str(switch))
		self.log(mesg)
		self.createVlan(vlan)
		self.addVlanToTrunk(vlan);
		thread.exit()

	def createVlans(self, vlan, switchlist, query):
		for switch in switchlist:
			#print "working on switch ", switch
			#self.host = query.getSwitchInfo(switch)
			#thread.start_new_thread(self.createVlansThread, (vlan, switch, self.host))
			mesg = "Creating vlan %s on switch %s" % (str(vlan), str(switch))
			self.log.info(mesg)
			self.host = query.getSwitchInfo(switch)
			self.createVlan(vlan)
			self.addVlanToTrunk(vlan);
		
	def removeVlans(self, vlan, switchlist, query):
		for switch in switchlist:
			mesg = "Deleting vlan %s on switch %s" % (str(vlan),str(switch))
			self.log.info(mesg)
			self.host = query.getSwitchInfo(switch)
			self.removeVlan(vlan)
		
	def createVlan(self, val):

		vlanname = False
		if ":" in val:
			num = int(val.split(":")[0])
			vlanname = val.split(":")[1]
		else:
			vlanname = self.__getPrsLabel()
			num = int(val)

		#if type(num) != int:
			#mesg = "ERROR:  Vlan must be a number (0-4095)\n"
			#sys.stderr.write(mesg)
			#exit(1)
		if num > 4095 or num < 0:
			mesg = "Vlan out of range.  Must be < %s" % (self.config['vlan_max'])
			self.log.error(mesg)
			exit(1)
		
		child = self.__login()
		child.sendline('config')
		child.expect(["config",pexpect.EOF, pexpect.TIMEOUT])
		child.sendline('vlan database')
		child.expect(["config-vlan",pexpect.EOF, pexpect.TIMEOUT])
		cmd = "vlan " + str(num)
		child.sendline(cmd)
		child.sendline('exit')
		child.expect(["config",pexpect.EOF, pexpect.TIMEOUT])

		if vlanname:
			cmd = "interface vlan " + str(num)
			child.sendline(cmd)
			child.expect(["config-if",pexpect.EOF, pexpect.TIMEOUT])
			cmd = "name " + vlanname
			child.sendline(cmd)
			child.expect(["config-if",pexpect.EOF, pexpect.TIMEOUT])

		child.sendline('exit')
		child.sendline('exit')

	#  Raw Switch commands.  DEBUG ONLY!, Doesn't work!
	def sendSwitchCommand(self, cmds):
		if len(cmds) > 0:
			child = self.__login()
			child.logfile = sys.stdout
		for cmd in cmds.split(";"):
			child.sendline(cmd)
			try:
				i=child.expect(['console','#', 'Name:', pexpect.EOF, pexpect.TIMEOUT], timeout=2)
				i=child.expect(['console','#', 'Name:', pexpect.EOF, pexpect.TIMEOUT], timeout=2)
				
			except EOF:
				print "EOF", i
				#child.sendline()
			except TIMEOUT:
				print "TIMEOUT", i
		#child.interact(escape_character='\x1d', input_filter=None, output_filter=None)

		child.terminate()

	def addNodeToVlan(self, vlan, tag="untagged"):
		if tag == "native":
			self.setNativeVlan(vlan)
			tag = "untagged"
		
		mesg = "Adding switchport (%s:%s) to vlan %s:%s" % (str(self.host['hw_name']), str(self.host['hw_port']), str(vlan), str(tag))
		self.log.info(mesg)
		
		child = self.__login()
		child.sendline('config')
		portname = self.__genPortName(self.host['hw_port'])
		cmd = "interface ethernet %s" % str(portname)
		child.sendline(cmd)
		child.expect(["config-if", pexpect.EOF])
		#cmd = "switchport trunk allowed vlan add " + vlan
		cmd = "switchport mode general"
		child.sendline(cmd)
		cmd = "switchport general allowed vlan add %s %s" % (str(vlan), str(tag))
		child.sendline(cmd)

		NOVLAN = "VLAN was not created by user."
		#  XXX this has problems with 62xx switches.  Need to catch the error if a vlan doesn't exist. 
		#  Currently you can leave out the 'config-if' and it will work but will require you to wait for 
		#  the timeout when you finally create and add the node to the vlan.  Leaving out support for 62xx switches
		#  for now.
		NOVLAN62 = "ERROR"
		i=child.expect(['config-if',NOVLAN, NOVLAN62, pexpect.EOF, pexpect.TIMEOUT])
		#  Vlan must exist in order to add a host to it.  
		#  If it doesn't exist, try to create it
		if i == 1 or i == 2:
			self.log.warning("WARNING:  Vlan %sdoesn't exist, trying to create" % (vlan))
			#  Add a tag showing this was created by PRS
			newvlan = vlan + ":" + self.__getPrsLabel()
			self.createVlan(newvlan)
			self.addNodeToVlan(vlan)

		child.sendline('exit')
		child.sendline('exit')
		child.terminate()

	def removeNodeFromVlan(self, vlan):
		mesg = "Removing switchport (%s:%s) from vlan %s" % (str(self.host['hw_name']), str(self.host['hw_port']), str(vlan))
		self.log.info(mesg)
		child = self.__login()
		child.sendline('config')
		portname = self.__genPortName(self.host['hw_port'])
		cmd = "interface ethernet %s" % str(portname)
		child.sendline(cmd)
		cmd = "switchport general allowed vlan remove " + vlan
		child.sendline(cmd)
		child.sendline('exit')
		child.sendline('exit')
		child.terminate()


	#def __checkVlan(self, child, vlan):
		#NO_VLAN_EXISTS = "VLAN was not created by user."
		#i=child.expect(['config',NO_VLAN_EXISTS, pexpect.EOF, pexpect.TIMEOUT])
		#print "i is ", i
		#if i == 1:
			#sys.stderr.write("WARNING:  Vlan doesn't exist, trying to create")
			#i=child.expect(['config',NO_VLAN_EXISTS, pexpect.EOF, pexpect.TIMEOUT])
			#return "NOVLAN"
			##newvlan = vlan + ":CREATED_BY_PRS"
			##self.createVlan(newvlan)
			##self.setNativeVlan(vlan)
			
	def setPortMode (self, mode):
		child = self.__login()
		child.logfile = sys.stdout
		child.sendline('config')
		portname = self.__genPortName(self.host['hw_port'])
		cmd = "interface ethernet %s" % str(portname)
		child.sendline(cmd)
		i=child.expect(['config-if', pexpect.EOF, pexpect.TIMEOUT])
		if i > 0:
			self.log.error("setPortMode %s failed" % (cmd))

		cmd = "switchport mode %s" % mode
		child.sendline(cmd)
		i=child.expect(['config-if', pexpect.EOF, pexpect.TIMEOUT])
		child.sendline('exit')
		child.sendline('exit')
		child.terminate()

	def setNativeVlan(self, vlan):
		child = self.__login()
		child.logfile = sys.stdout
		child.sendline('config')
		portname = self.__genPortName(self.host['hw_port'])
		cmd = "interface ethernet %s" % str(portname)
		child.sendline(cmd)
		i=child.expect(['config-if', pexpect.EOF, pexpect.TIMEOUT])
		if i > 0:
			self.log.error("setNativeVlan %s failed" % (cmd))

		NOVLAN = "VLAN was not created by user."
		cmd = "switchport general pvid " + vlan
		child.sendline(cmd)
		i=child.expect(['config-if', NOVLAN, pexpect.EOF, pexpect.TIMEOUT])
		#  Vlan must exist in order to add a host to it.  
		#  If it doesn't exist, try to create it
		if i == 1:
			self.log.warning("Vlan %s doesn't exist, trying to create" % (vlan))
			#  Add a tag showing this was created by PRS
			newvlan = vlan + ":" + self.__getPrsLabel()
			self.createVlan(newvlan)
			self.setNativeVlan(vlan)
			
		child.sendline('exit')
		child.sendline('exit')
		child.terminate()

	#  Restore Native Vlan.  In Dell's case, this is vlan 1
	#  Removing this 
	#def restoreNativeVlan(self):
		#child = self.__login()
		#child.sendline('config')
		#portname = self.__genPortName(self.host['hw_port'])
		#cmd = "interface ethernet %s" % str(portname)
		#child.sendline(cmd)
		##cmd = "switchport trunk native vlan 1"
		#cmd = "switchport general pvid 1"
		#child.sendline(cmd)
		#child.sendline('exit')
		#child.sendline('exit')
		##child.terminate()
		#child.terminate()

	##  Setup the switch for node allocation
	def allocateNode(self):
		pass

	#  Remove all vlans from the interface
	def removeAllVlans(self):
		child = self.__login()
		child.logfile = sys.stdout
		child.sendline('config')
		portname = self.__genPortName(self.host['hw_port'])
		cmd = "interface ethernet %s" % str(portname)
		child.sendline(cmd)
		i=child.expect(['config-if', pexpect.EOF, pexpect.TIMEOUT])
		if i > 0:
			self.log.error("setNativeVlan %s failed" % (cmd))

		NOVLAN = "VLAN was not created by user."
		cmd = "switchport trunk allowed vlan remove all"
		child.sendline(cmd)
		i=child.expect(['config-if', NOVLAN, pexpect.EOF, pexpect.TIMEOUT])
		#  Vlan must exist in order to add a host to it.  
		#  If it doesn't exist, try to create it
		if i == 1:
			pass
			
		child.sendline('exit')
		child.sendline('exit')
		child.terminate()

	def showInterfaceConfig(self):
		child = self.__login()
		print "\n------------------------------------"
		print "SWITCH - " + self.host['hw_name'] + "/" + str(self.host['hw_port'])
		print "NODE   - " + self.host['location']
		print "------------------------------------\n"
		child.logfile = sys.stdout
		
		portname = self.__genPortName(self.host['hw_port'])

		cmd = "show interface switchport ethernet %s" % str(portname)
		child.sendline(cmd)
		i = child.expect(['#','--More--', pexpect.EOF, pexpect.TIMEOUT])
		#  send a space for more
		while i == 1:
			child.sendline(" ")
			i = child.expect(['#','--More--', pexpect.EOF, pexpect.TIMEOUT])
		child.terminate()

	def interactiveSwitchConfig(self):
		switchIp = "ssh " + self.host['hw_name']
		child = pexpect.spawn(switchIp)
		child.setecho(False)
		#child.expect('Name:')
		child.sendline(self.host['hw_userid'])
		#i=child.expect(['test','password:','Password:', pexpect.EOF, pexpect.TIMEOUT])
		#child.logfile = sys.stdout
		child.sendline(self.host['hw_password'])
		child.interact(escape_character='\x1d', input_filter=None, output_filter=None)

	def saveConfig(self, switch, query):
		self.host = query.getSwitchInfo(switch)
		child = self.__login()
		cmd = "copy running-config startup-config"
		child.sendline(cmd)
		i = child.expect(['y/n', pexpect.EOF, pexpect.TIMEOUT])
		child.sendline("y")
		child.terminate()

	def __saveConfig(self):
		cmd = "copy running-config startup-config"
		child.sendline(cmd)
		i = child.expect(['y/n', pexpect.EOF, pexpect.TIMEOUT])
		child.sendline("y")
		child.terminate()

	
	def registerToZoni(self, user, password, host):
		self.setVerbose(True)
		host = string.strip(str(host))
		#  Get hostname of the switch
		if len(host.split(".")) == 4:
			ip = host
			try:
				host = string.strip(socket.gethostbyaddr(ip)[0].split(".")[0])
			except Exception, e:
				mesg = "Host (%s) not registered in DNS, %s" % (host,str(e))
				self.log.warning(mesg)
		else:
			#  Maybe a hostname was entered...
			try:
				ip = socket.gethostbyname(host)
			except Exception, e:
				mesg = "Host (%s) not registered in DNS, %s" % (host, str(e))
				self.log.error(mesg)
				mesg = "Unable to resolve hostname"
				self.log.critical(mesg)
				exit()

		#  log into the switch
		self.host = {}
		self.host['hw_userid'] = user
		self.host['hw_name'] = host
		self.host['hw_password'] = password
		child = self.__login()

		fout = tempfile.TemporaryFile()
		child.logfile = fout

		cmd = "show system"
		child.sendline(cmd)
		val = host + "#"
		tval = host + ">"
		i = child.expect([val, tval, '\n\r\n\r', "--More--",  pexpect.EOF, pexpect.TIMEOUT])
		cmd = "show version"
		child.sendline(cmd)
		i = child.expect([val, tval, '\n\r\n\r', pexpect.EOF, pexpect.TIMEOUT])

		fout.seek(0)
		a={}
		for i in fout.readlines():
			if "System Location:" in i:
				datime = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.localtime())
				val = "Registered by Zoni on : " + datime
				a['hw_notes'] = val + "; " + string.strip(i.split(':', 1)[1])
			if "MAC" in i:
				a['hw_mac'] = normalizeMac(string.strip(i.split(":", 1)[1]))
			#  moving this capture to snmp 
			#if "SW version" in i:
				#a['hw_version_sw'] = string.strip(i.split('   ')[1].split()[0])
			if "HW version" in i:
				a['hw_version_fw'] = string.strip(i.split('   ')[1].split()[0])
				
		a['hw_type'] = "switch"
		a['hw_make'] = "dell"
		a['hw_name'] = host
		a['hw_ipaddr'] = ip
		a['hw_userid'] = user
		a['hw_password'] = password
		child.sendline('exit')
		child.sendline('exit')
		child.terminate()

		#  Try to get more info via snmp
		from pysnmp.entity.rfc3413.oneliner import cmdgen
		from pysnmp.proto import rfc1902

		user = "public"
		oid = eval("1,3,6,1,4,1,674,10895,3000,1,2,100,1,0")
		errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd( \
		cmdgen.CommunityData('my-agent', user, 0), \
		cmdgen.UdpTransportTarget((host, 161)), oid)
		a['hw_model'] = str(varBinds[0][1])

		oid = eval("1,3,6,1,4,1,674,10895,3000,1,2,100,3,0")
		errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd( \
		cmdgen.CommunityData('my-agent', user, 0), \
		cmdgen.UdpTransportTarget((host, 161)), oid)
		a['hw_make'] = str(varBinds[0][1])

		oid = eval("1,3,6,1,4,1,674,10895,3000,1,2,100,4,0")
		errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd( \
		cmdgen.CommunityData('my-agent', user, 0), \
		cmdgen.UdpTransportTarget((host, 161)), oid)
		a['hw_version_sw'] = str(varBinds[0][1])

		#  Register in dns
		if self.config['dnsEnabled']:
			try:
				mesg = "Adding %s(%s) to dns" % (host, ip)
				self.log.info(mesg)
				DhcpDns(self.config, verbose=self.verbose).addDns(host, ip)
				mesg = "Adding %s(%s) to dhcp" % (host, ip)
				self.log.info(mesg)
				DhcpDns(self.config, verbose=self.verbose).addDhcp(host, ip, a['hw_mac'])
			except:
				mesg = "Adding %s(%s) %s to dhcp/dns failed" % (host, ip, a['hw_mac'])
				self.log.error(mesg)
			
		#  Add to db
		#  Register to DB
		query = ResourceQuerySql(self.config, self.verbose)
		query.registerHardware(a)


