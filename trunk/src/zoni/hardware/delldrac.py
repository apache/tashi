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

import sys
import os 
import pexpect
import time
import logging
import tempfile

from systemmanagementinterface import SystemManagementInterface
from zoni.extra.util import timeF, log


class dellDrac(SystemManagementInterface):
	def __init__(self, config, nodeName, hostInfo):
		self.config = config
		self.hostname = hostInfo['location']
		self.host = hostInfo['drac_name']
		self.user = hostInfo['drac_userid']
		self.password = hostInfo['drac_password']
		self.port = hostInfo['drac_port']
		self.powerStatus = None
		self.verbose = False
		self.server = "Server-" + str(self.port)
		self.log = logging.getLogger(__name__)

	def setVerbose(self, verbose):
		self.verbose = verbose
	
	def __login(self):
		switchIp = "telnet " +  self.host
		child = pexpect.spawn(switchIp)

		if self.verbose:
			child.logfile = sys.stdout

		opt = child.expect(['Login:',  pexpect.EOF, pexpect.TIMEOUT])

		child.setecho(False)
		if opt == 0:
			time.sleep(.5)
			child.sendline(self.user)
			i=child.expect(["assword:", pexpect.EOF, pexpect.TIMEOUT])
			child.sendline(self.password)
			i=child.expect(['DRAC/MC:', pexpect.EOF, pexpect.TIMEOUT])
			if i == 2:
				self.log.error("Login to %s failed" % (switchIp))
				return -1
		else:
			mesg = "Error"
			self.log.error(mesg)
			return -1

		return child

	@timeF
	def __setPowerStatus(self):
		fout = tempfile.TemporaryFile()
		child = self.__login()
		child.logfile = fout
		cmd = "getmodinfo -m " + self.server
		child.sendline(cmd)
		i=child.expect(['DRAC/MC:', pexpect.EOF, pexpect.TIMEOUT])
		fout.seek(0)
		for i in fout.readlines():
			if "ON" in i and self.server in i:
				mesg = self.hostname + " Power is on\n\n"
				self.powerStatus = 1
			if "OFF" in i and self.server in i:
				mesg = self.hostname + " Power is off\n\n"
				self.powerStatus = 0
		self.log.info(mesg)

		fout.close()
		child.close()
		child.terminate()


	@timeF
	def isPowered(self):
		if self.powerStatus == None:
			self.__setPowerStatus()
		if self.powerStatus:
			return 0;
		return 1;
	
	def getPowerStatus(self):
		return self.isPowered()

	@timeF
	def powerOn(self):
		code = 0
		fout = tempfile.TemporaryFile()
		if self.powerStatus == 1:
			mesg = self.hostname + " Power On\n\n"
			return 0
			
		child = self.__login()
		child.logfile = fout
		cmd = "racadm serveraction -m " +  self.server + " powerup"
		child.sendline(cmd)
		i=child.expect(['DRAC/MC:', pexpect.EOF, pexpect.TIMEOUT])
		fout.seek(0)
		for val in fout.readlines():
			if "OK" in val:
				mesg = self.hostname + " Power On\n\n"
				self.log.info(mesg)
				code = 1 
			else:
				mesg = self.hostname + " Power On Fail\n\n"
				self.log.info(mesg)
				code = -1
		fout.close()
		child.terminate()
		return code

	@timeF
	def powerOff(self):
		code = 0
		fout = tempfile.TemporaryFile()
		child = self.__login()
		child.logfile = fout
		cmd = "racadm serveraction -m " + self.server + " powerdown"
		child.sendline(cmd)
		i=child.expect(['DRAC/MC:', pexpect.EOF, pexpect.TIMEOUT])
		fout.seek(0)
		for val in fout.readlines():
			if "OK" in val:
				mesg = self.hostname + " Power Off\n\n"
				self.log.info(mesg)
				code = 1
			else:
				mesg = self.hostname + " Power Off Fail\n\n"
				self.log.info(mesg)
				code = -1
		#i=child.expect(['DRAC/MC:', pexpect.EOF, pexpect.TIMEOUT])
		child.terminate()
		fout.close()
		return code

	@timeF
	def powerCycle(self):
		code = 0
		fout = tempfile.TemporaryFile()
		child = self.__login()
		child.logfile = fout
		cmd = "racadm serveraction -m " + self.server + " powercycle"
		child.sendline(cmd)
		i=child.expect(['DRAC/MC:', pexpect.EOF, pexpect.TIMEOUT])
		fout.seek(0)
		for val in fout.readlines():
			if "OK" in val:
				mesg = self.hostname + " Power Cycle\n\n"
				self.log.info(mesg)
				code = 1
			else:
				mesg = self.hostname + " Power Cycle Fail\n\n"
				self.log.info(mesg)
				code = -1
		child.terminate()
		fout.close()
		return code
		
	@timeF
	def powerReset(self):
		code = 0
		fout = tempfile.TemporaryFile()
		child = self.__login()
		child.logfile = fout
		cmd = "racadm serveraction -m " + self.server + " hardreset"
		child.sendline(cmd)
		i=child.expect(['DRAC/MC:', pexpect.EOF, pexpect.TIMEOUT])
		fout.seek(0)
		for val in fout.readlines():
			if "OK" in val:
				mesg = self.hostname + " Power Reset\n\n"
				self.log.info(mesg)
				code = 1
			else:
				mesg = self.hostname + " Power Reset Fail\n\n"
				self.log.info(mesg)
				code = -1
		child.terminate()
		fout.close()
		return code
		
	def activateConsole(self):
		child = self.__login()
		cmd = "connect -F " + self.server
		child.sendline(cmd)
		i=child.expect(['DRAC/MC:', pexpect.EOF, pexpect.TIMEOUT])
		child.terminate()
