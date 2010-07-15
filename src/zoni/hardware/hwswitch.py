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
import thread


from zoni.hardware.hwswitchinterface import HwSwitchInterface
from zoni.data.resourcequerysql import ResourceQuerySql
from zoni.extra.util import logit


'''  Using pexpect to control switches because couldn't get snmp to work 
'''

class HwDellSwitch(HwSwitchInterface):
	def __init__(self, config, host=None):
		self.host = host
		self.verbose = False
		self.logFile = config['logFile']


 	def setVerbose(self, verbose):
		self.verbose = verbose

	def __login(self):
		
		switchIp = "ssh " +  self.host['hw_userid'] + "@" + self.host['hw_name']
		child = pexpect.spawn(switchIp)
		opt = child.expect(['Name:', 'password:', pexpect.EOF, pexpect.TIMEOUT])
		print "opt is ", opt
		#XXX  Doesn't seem to do what I want:(
		child.setecho(False)
		if opt == 0:
			child.sendline(self.host['hw_userid'])
		#i=child.expect(['test','password:','Password:', pexpect.EOF, pexpect.TIMEOUT])

		#  Be Verbose and print everything
		if self.verbose:
			child.logfile = sys.stdout

		child.sendline(self.host['hw_password'])
		i=child.expect(['console','sw', 'Name:', pexpect.EOF, pexpect.TIMEOUT])
		if i == 2:
			mesg = "ERROR:  Login failed\n"
			logit(self.logFile, mesg)

			sys.stderr.write()
			exit(1)
		#  on the 6448 dell, need to send enable
		if opt == 1:
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
		mesg = "Adding Vlan to trunks on switch"
		logit(self.logFile, mesg)
		child = self.__login()
		child.sendline('config')
		cmd = "interface range port-channel all"
		child.sendline(cmd)
		child.expect(["config-if", pexpect.EOF])
		cmd = "switchport trunk allowed vlan add " + vlan
		child.sendline(cmd)
		child.sendline('exit')

	def createVlansThread(self, vlan, switch,host):
		mesg = "Creating vlan " + str(vlan) + " on switch " + str(switch)
		print "host is ", host
		logit(self.logFile, mesg)
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
			mesg = "Creating vlan " + str(vlan) + " on switch " + str(switch)
			logit(self.logFile, mesg)
			self.host = query.getSwitchInfo(switch)
			self.createVlan(vlan)
			self.addVlanToTrunk(vlan);
		
	def removeVlans(self, vlan, switchlist, query):
		for switch in switchlist:
			mesg = "Deleting vlan " + str(vlan) + " on switch " + str(switch)
			logit(self.logFile, mesg)
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
			mesg = "ERROR:  Vlan out of range.  Must be < 4095"
			logit(self.logFile, mesg)
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
				i=child.expect(['console','sw', 'Name:', pexpect.EOF, pexpect.TIMEOUT], timeout=2)
				i=child.expect(['console','sw', 'Name:', pexpect.EOF, pexpect.TIMEOUT], timeout=2)
				
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
		print "Adding Node to vlan ", vlan
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
			sys.stderr.write("WARNING:  Vlan doesn't exist, trying to create\n")
			#  Add a tag showing this was created by PRS
			newvlan = vlan + ":" + self.__getPrsLabel()
			self.createVlan(newvlan)
			self.addNodeToVlan(vlan)

		child.sendline('exit')
		child.sendline('exit')
		child.terminate()
		sys.stdout.write("Success\n")

	def removeNodeFromVlan(self, vlan):
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
			sys.stderr.write("ERROR: setNativeVlan ", cmd, " failed\n")

		NOVLAN = "VLAN was not created by user."
		cmd = "switchport trunk native vlan " + vlan
		child.sendline(cmd)
		i=child.expect(['config-if', NOVLAN, pexpect.EOF, pexpect.TIMEOUT])
		#  Vlan must exist in order to add a host to it.  
		#  If it doesn't exist, try to create it
		if i == 1:
			sys.stderr.write("WARNING:  Vlan doesn't exist, trying to create")
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
			sys.stderr.write("ERROR: setNativeVlan ", cmd, " failed\n")

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
		i = child.expect(['sw(.*)', pexpect.EOF, pexpect.TIMEOUT])
		i = child.expect(['sw(.*)', pexpect.EOF, pexpect.TIMEOUT])
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


