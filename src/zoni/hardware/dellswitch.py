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


from zoni.hardware.hwswitchinterface import HwSwitchInterface
from zoni.data.resourcequerysql import ResourceQuerySql


'''  Using pexpect to control switches because couldn't get snmp to work 
'''

class HwDellSwitch(HwSwitchInterface):
	def __init__(self, config, host=None):
		self.config = config
		self.host = host
		self.verbose = False
		self.log = logging.getLogger(os.path.basename(__file__))


 	def setVerbose(self, verbose):
		self.verbose = verbose

	def __login(self):
		
		switchIp = "ssh " +  self.host['hw_userid'] + "@" + self.host['hw_name']
		child = pexpect.spawn(switchIp)

		#  Be Verbose and print everything
		if self.verbose:
			child.logfile = sys.stdout

		opt = child.expect(['Name:', 'assword:', 'Are you sure.*', pexpect.EOF, pexpect.TIMEOUT])
		#XXX  Doesn't seem to do what I want:(
		child.setecho(False)

		#  Send a yes to register authenticity of host for ssh
		if opt == 2:
			child.sendline("yes")
			opt = child.expect(['Name:', 'assword:', 'Are you sure.*', pexpect.EOF, pexpect.TIMEOUT])
			
		if opt == 0:
			child.sendline(self.host['hw_userid'])
			i = child.expect(['assword:', 'Connection',  pexpect.EOF, pexpect.TIMEOUT])
			child.sendline(self.host['hw_password'])
			i=child.expect(['console','#', 'Name:', pexpect.EOF, pexpect.TIMEOUT])
			if i == 2:
				mesg = "ERROR:  Login to %s failed\n" % (self.host['hw_name'])
				self.log.error(mesg)
				exit(1)

		if opt == 1:
			#  the 6448 doesn't prompt for username
			child.sendline(self.host['hw_password'])
			i=child.expect(['console','>', 'Name:', pexpect.EOF, pexpect.TIMEOUT])
			#  on the 6448 dell, need to send enable, just send to all
			child.sendline('enable')
			i=child.expect(['#', pexpect.EOF, pexpect.TIMEOUT])


		return child

	def __getPrsLabel(self):
		dadate = datetime.datetime.now().strftime("%Y%m%d-%H%M-%S")
		return "PRS_" + dadate

	
	def enableHostPort(self):
		child = self.__login()
		child.sendline('config')
		cmd = "interface ethernet g" + str(self.host['hw_port'])
		child.sendline(cmd)
		cmd = "no shutdown" 
		child.sendline(cmd)
		child.sendline('exit')
		child.terminate()
		
	def disableHostPort(self):
		child = self.__login()
		child.sendline('config')
		cmd = "interface ethernet g" + str(self.host['hw_port'])
		child.sendline(cmd)
		cmd = "shutdown"
		child.sendline(cmd)
		child.sendline('exit')
		child.terminate()

	def removeVlan(self, num):
		#  Check for important vlans
		
		cmd = "no vlan " + num
		child = self.__login()
		child.sendline('config')
		child.sendline('vlan database')
		child.sendline(cmd)
		child.sendline('exit')
		child.terminate()
	
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
		print "host is ", host
		self.log(mesg)
		print "create"
		self.createVlan(vlan)
		print "cend"
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
		#print "before", child.before
		#print "after", child.after

	def addNodeToVlan(self, vlan):
		mesg = "Adding Node to vlan %s" % (str(vlan))
		self.log.info(mesg)
		
		child = self.__login()
		child.sendline('config')
		cmd = "interface ethernet g" + str(self.host['hw_port'])
		child.sendline(cmd)
		child.expect(["config-if", pexpect.EOF])
		cmd = "switchport trunk allowed vlan add " + vlan
		child.sendline(cmd)
		child.sendline('exit')

		NOVLAN = "VLAN was not created by user."
		i=child.expect(['config-if',NOVLAN, pexpect.EOF, pexpect.TIMEOUT])
		#  Vlan must exist in order to add a host to it.  
		#  If it doesn't exist, try to create it
		if i == 1:
			self.log.warning("WARNING:  Vlan %sdoesn't exist, trying to create" % (vlan))
			#  Add a tag showing this was created by PRS
			newvlan = vlan + ":" + self.__getPrsLabel()
			self.createVlan(newvlan)
			self.addNodeToVlan(vlan)

		child.sendline('exit')
		child.sendline('exit')
		child.terminate()

	def removeNodeFromVlan(self, vlan):
		mesg = "Removing Node from vlan %s" % (str(vlan))
		self.log.info(mesg)
		child = self.__login()
		child.sendline('config')
		cmd = "interface ethernet g" + str(self.host['hw_port'])
		child.sendline(cmd)
		cmd = "switchport trunk allowed vlan remove " + vlan
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
			

	def setNativeVlan(self, vlan):
		child = self.__login()
		child.logfile = sys.stdout
		child.sendline('config')
		cmd = "interface ethernet g" + str(self.host['hw_port'])
		child.sendline(cmd)
		i=child.expect(['config-if', pexpect.EOF, pexpect.TIMEOUT])
		if i > 0:
			self.log.error("setNativeVlan %s failed" % (cmd))

		NOVLAN = "VLAN was not created by user."
		cmd = "switchport trunk native vlan " + vlan
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
	def restoreNativeVlan(self):
		child = self.__login()
		child.sendline('config')
		cmd = "interface ethernet g" + str(self.host['hw_port'])
		child.sendline(cmd)
		cmd = "switchport trunk native vlan 1"
		child.sendline(cmd)
		child.sendline('exit')
		child.sendline('exit')
		#child.terminate()
		child.terminate()

	#  Setup the switch for node allocation
	def allocateNode(self):
		pass

	#  Remove all vlans from the interface
	def removeAllVlans(self):
		child = self.__login()
		child.logfile = sys.stdout
		child.sendline('config')
		cmd = "interface ethernet g" + str(self.host['hw_port'])
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
		cmd = "show interface switchport ethernet g" + str(self.host['hw_port'])
		child.sendline(cmd)
		i = child.expect(['#', pexpect.EOF, pexpect.TIMEOUT])
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
	
	def registerToZoni(self, user, password, host):
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

		switchIp = "ssh " + user + "@" + ip
		child = pexpect.spawn(switchIp)
		opt = child.expect(['Name:', 'assword:', 'Are you sure.*', pexpect.EOF, pexpect.TIMEOUT])
		#XXX  Doesn't seem to do what I want:(
		child.setecho(False)

		#  Send a yes to register authenticity of host for ssh
		if opt == 2:
			child.sendline("yes")
			opt = child.expect(['Name:', 'assword:', 'Are you sure.*', pexpect.EOF, pexpect.TIMEOUT])
			
		if opt == 0:
			child.sendline(user)
			i = child.expect(['assword:', 'Connection',  pexpect.EOF, pexpect.TIMEOUT])
			child.sendline(password)
			i=child.expect(['console',host, 'Name:', pexpect.EOF, pexpect.TIMEOUT])
			if i == 2:
				mesg = "Login to switch %s failed" % (host)
				self.log.error(mesg)
				exit(1)

		if opt == 1:
			child.sendline(password)
			i=child.expect(['console',host, 'Name:', pexpect.EOF, pexpect.TIMEOUT])
			#  on the 6448 dell, need to send enable, just send to all
			child.sendline('enable')
			i=child.expect(['#', pexpect.EOF, pexpect.TIMEOUT])

		fout = tempfile.TemporaryFile()
		child.logfile = fout

		cmd = "show system"
		child.sendline(cmd)
		val = host + "#"
		i = child.expect([val, '\n\r\n\r', pexpect.EOF, pexpect.TIMEOUT])
		cmd = "show version"
		child.sendline(cmd)
		i = child.expect([val, '\n\r\n\r', pexpect.EOF, pexpect.TIMEOUT])

		fout.seek(0)
		a={}
		for i in fout.readlines():
			if "System Location:" in i:
				datime = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.localtime())
				val = "Registered by Zoni on : " + datime
				a['hw_notes'] = val + "; " + string.strip(i.split(':', 1)[1])
			if "System MAC" in i:
				a['hw_mac'] = string.strip(i.split(':', 1)[1])
			if "SW version" in i:
				a['hw_version_sw'] = string.strip(i.split('   ')[1].split()[0])
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

		return a


