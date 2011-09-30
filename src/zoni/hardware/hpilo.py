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

from systemmanagementinterface import SystemManagementInterface


#class systemmagement():
	#def __init__(self, proto):
		#self.proto = proto

#XXX  Need to add more error checking!

def log(f):
	def myF(*args, **kw):
		print "calling %s%s" % (f.__name__, str(args))
		res = f(*args, **kw)
		print "returning from %s -> %s" % (f.__name__, str(res))
		return res
	myF.__name__ = f.__name__
	return myF

import time

def timeF(f):
	def myF(*args, **kw):
		start = time.time()
		res = f(*args, **kw)
		end = time.time()
		print "%s took %f" % (f.__name__, end-start)
		return res
	myF.__name__ = f.__name__
	return myF


class hpILo(SystemManagementInterface):
	def __init__(self, host):
		self.hostname = host['location']
		self.host = host['ilo_name']
		self.user = host['ilo_userid']
		self.password = host['ilo_password']
		self.port = host['ilo_port']
		self.powerStatus = None
		self.verbose = 0
		#self.server = "Server-" + str(self.port)

	def setVerbose(self, verbose):
		self.verbose = verbose
	
	def __login(self):
		switchIp = "ssh " +  self.host
		child = pexpect.spawn(switchIp)

		if self.verbose:
			child.logfile = sys.stdout

		opt = child.expect(['password:',  pexpect.EOF, pexpect.TIMEOUT])


		#XXX  Doesn't seem to do what I want:(
		child.setecho(False)
		if opt == 0:
			child.sendline(self.password)
			time.sleep(.5)
			i=child.expect(['>', 'please try again.', pexpect.EOF, pexpect.TIMEOUT])
		else:
			mesg = "Error"
			sys.stderr.write(mesg)
			exit(1)

		if i == 1:
			mesg = "Error:  Incorrect password\n"
			sys.stderr.write(mesg)
			exit(1)

		if i == 0:
			if self.verbose:
				print "login success"

		return child


	@timeF
	@log
	def getPowerStatus(self):
		child = self.__login()
		cmd = "show server status " + str(self.port)
		child.sendline(cmd)
		val = child.readline()
		while "Power" not in val:
			val = child.readline()

		if "On" in val:
			mesg = self.hostname + " Power is on\n\n"
			self.powerStatus = 1
		if "Off" in val:
			mesg = self.hostname + " Power is off\n\n"
			self.powerStatus = 0

		sys.stdout.write(mesg)

		child.close()
		child.terminate()

	@timeF
	def isPowered(self):
		if self.powerStatus == None:
			self.getPowerStatus()
		if self.powerStatus:
			return 1;
		if not self.powerStatus:
			return 0;
	

	@timeF
	def powerOn(self):
		if self.powerStatus == 1:
			mesg = self.hostname + " Power On\n\n"
			exit(1)
			
		child = self.__login()
		cmd = "poweron server " +  str(self.port)
		child.sendline(cmd)
		val = child.readline()
		while  "Powering" not in val and "powered" not in val:
			val = child.readline()

		if "Powering" in val or "already" in val:
			#  if already in val:  you can say it is already in on or off state
			mesg = self.hostname + " Power On\n\n"
		else:
			mesg = self.hostname + " Power On Fail\n\n"
		sys.stdout.write(mesg)
		child.sendline("quit")
		child.terminate()

	@timeF
	def powerOff(self):
		child = self.__login()
		cmd = "poweroff server " + str(self.port)
		child.sendline(cmd)
		val = child.readline()
		while  "graceful" not in val and "already"  not in val:
			val = child.readline()

		if "graceful" in val or "already" in val:
			mesg = self.hostname + " Power Off - Graceful\n\n"
		else:
			mesg = self.hostname + " Power Off Fail\n\n"

		sys.stdout.write(mesg)
		child.sendline("quit")
		child.terminate()

	@timeF
	def powerCycle(self):
		self.powerReset()
		self.powerOn()
		
	@timeF
	def powerReset(self):
		child = self.__login()
		cmd = "poweroff server " + str(self.port) + " FORCE"
		child.sendline(cmd)
		#val = child.readline()
		#val = child.readline()
		#if "powering down" in val:
		mesg = self.hostname + " Power Reset\n\n"
		#else:
			#mesg = self.hostname + " Power Reset Fail\n\n"
		sys.stdout.write(mesg)
		child.sendline("quit")
		child.terminate()
		
	def activateConsole(self):
		pass
