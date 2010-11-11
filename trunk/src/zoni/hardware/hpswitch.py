# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#http://www.apache.org/licenses/LICENSE-2.0
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
# What HP switches is this for? The configuration syntax does not
# not appear like it would work for Procurves. - stroucki 20100224

import os
import sys
import pexpect
import datetime
import thread
import time
import threading
import logging


from hwswitchinterface import HwSwitchInterface
from resourcequerysql import ResourceQuerySql


class HwHPSwitch(HwSwitchInterface):
	def __init__(self, config, host=None):
		self.config = config
		self.host = host
		self.verbose = False
		self.log = logging.getLogger(os.path.basename(__file__))

	def setVerbose(self, verbose):
		self.verbose = verbose

	def __login(self):
		switchIp = "telnet " +  self.host['hw_name']
		child = pexpect.spawn(switchIp)
		opt = child.expect(['Name:', 'password:', pexpect.EOF, pexpect.TIMEOUT])
		child.setecho(False)
		if opt == 0:
			child.sendline(self.host['hw_userid'])

		#  Be Verbose and print everything
		if self.verbose:
			child.logfile = sys.stdout

		child.sendline(self.host['hw_password'])
		i=child.expect(['Main#', pexpect.EOF, pexpect.TIMEOUT])
		if i == 2:
			mesg = "Login to %s failed\n" % (self.host['hw_name'])
			self.log.error(mesg)
			exit(1)
		return child

	def __getPrsLabel(self):
		dadate = datetime.datetime.now().strftime("%Y%m%d-%H%M-%S")
		return "ZONI_" + dadate

	def __saveConfig(self, child):
		#child.logfile = sys.stdout
		cmd = "save"
		child.sendline(cmd)
		opt = child.expect(["Confirm(.*)", "No save(.*)", pexpect.EOF, pexpect.TIMEOUT])
		if opt == 0:
				print "saving to flash"
				child.sendline("y\n")
		if opt == 1:
				print "no save needed"
		child.sendline('exit')
		child.terminate()

	def enableHostPort(self):
		child = self.__login()
		cmd = "/cfg/port " + str(self.host['hw_port']) + " /ena/apply "
		child.sendline(cmd)
		#  testing this thread... Looks like this works ...
		threading.Thread(target=self.__saveConfig(child)).start()

	def disableHostPort(self):
		child = self.__login()
		cmd = "/cfg/port " + str(self.host['hw_port']) + " /dis/apply "
		child.sendline(cmd)
		threading.Thread(target=self.__saveConfig(child)).start()

	def removeVlan(self, num):
		print "removing vlan"
		#  Check for important vlans
		child = self.__login()

		cmd = "/cfg / l2 / vlan " + num + " / del / apply"
		child.sendline(cmd)
		opt = child.expect(["Confirm(.*)", pexpect.EOF, pexpect.TIMEOUT])
		if opt == 0:
			child.sendline("y\n")
		threading.Thread(target=self.__saveConfig(child)).start()


	def addVlanToTrunk(self, vlan):
		print "NOT IMPLEMENTED"
		print "No trunks to test @ MIMOS"

	def createVlansThread(self, vlan, switch,host):
		mesg = "Creating vlan %s on switch %s" % (str(vlan), str(switch))
		self.log.info(mesg)
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
			mesg = "Deleting vlan %s on switch %s" % (str(vlan), str(switch))
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

		if num > 4095 or num < 0:
			mesg = "Vlan out of range.  Must be < %s" % (self.config['vlan_max'])
			self.log.error(mesg)
			exit(1)

		child = self.__login()
		cmd = "/cfg / l2 / vlan " + str(num) + " / ena/ apply"
		child.sendline(cmd)
		cmd = "name " + str(vlanname) +  " / apply"
		child.sendline(cmd)
		threading.Thread(target=self.__saveConfig(child)).start()


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
		child = self.__login()
		cmd = "/cfg/l2/vlan " + str(vlan) + " /add " + str(self.host['hw_port']) + " /apply "
		child.sendline(cmd)
		opt = child.expect(['(.*)#','(.*)needs to be enabled', pexpect.EOF, pexpect.TIMEOUT], timeout=2)
		if opt == 1:
			print "VLAN Created, Enabling..." + str(vlan)
			cmd = "/cfg/l2/vlan " + str(vlan) + " /ena/apply "
			child.sendline(cmd)

		threading.Thread(target=self.__saveConfig(child)).start()


	def removeNodeFromVlan(self, vlan):
		child = self.__login()
		cmd = "/cfg/l2/vlan " + str(vlan) + " /rem " + str(self.host['hw_port']) + "/apply"
		child.sendline(cmd)
		threading.Thread(target=self.__saveConfig(child)).start()

	def setNativeVlan(self, vlan):
		child = self.__login()
		#child.logfile = sys.stdout
		cmd = "/cfg/port " + str(self.host['hw_port']) + "/pvid " + str(vlan) + "/apply"
		child.sendline(cmd)
		threading.Thread(target=self.__saveConfig(child)).start()

		#  HP switches allow more free control.  Example, if you set a port to a native vlan
		#  that doesn't exist, HP switches will happily create for you.
		#  However, if you delete a vlan that exists on many ports, it will still happily delete
		#  the vlan, forcing all the other ports to default to some other native vlan.  Need
		#  to make sure we check before blasting vlans.

	#  Restore Native Vlan.
	def restoreNativeVlan(self):
		child = self.__login()
		cmd = "/cfg/port " + str(self.host['hw_port']) + "/pvid 1/apply"
		child.sendline(cmd)
		threading.Thread(target=self.__saveConfig(child)).start()

	#  Setup the switch for node allocation
	def allocateNode(self):
		pass

	#  Remove all vlans from the interface
	def removeAllVlans(self):
		child = self.__login()
		cmd = "/cfg/port " + str(self.host['hw_port']) + "/tag d/apply"
		#child.logfile = sys.stdout
		child.sendline(cmd)

	def showInterfaceConfig(self):
		print "\n---------------" + self.host['hw_make'] + "---------------------"
		print "SWITCH - " + self.host['hw_name'] + "/" + str(self.host['hw_port'])
		print "NODE- " + self.host['location']
		print "------------------------------------\n"
		#  using run and parsing output.  Still have issues an "rt" after the command.  Fix later
		#val = pexpect.run("telnet sw0-r4r1e1", withexitstatus=False, timeout=2, events=({'(?i)password:': "admin\r\n", "Main#": "info\r\n", "Info(.*)" : "port\r\n"})) #, "Info(.*)" : "exit\n"}))
		#  Just print everything for now, fix when back in the US
		#print val


		child = self.__login()
		cmd = "/info/port " + str(self.host['hw_port'])
		child.sendline(cmd)
		child.logfile = sys.stdout
		opt = child.expect(['Info(.*)', pexpect.EOF, pexpect.TIMEOUT])

	#  this needs to be removed or rewritten
	def interactiveSwitchConfig(self):
		switchIp = "telnet " + self.host['hw_name']
		child = pexpect.spawn(switchIp)
		child.setecho(False)
		#child.expect('Name:')
		#child.sendline(self.host['hw_userid'])
		#i=child.expect(['test','password:','Password:', pexpect.EOF, pexpect.TIMEOUT])
		#child.logfile = sys.stdout
		child.sendline(self.host['hw_password'])
		child.interact(escape_character='\x1d', input_filter=None, output_filter=None)


