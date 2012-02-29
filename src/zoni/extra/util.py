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
import string
import ConfigParser
import time
import shutil
import re
import threading
import subprocess
import logging

def loadConfigFile(parser):
	#parser = ConfigParser.ConfigParser()
	#parser.read(filename)
	config = {}
	#  Install dir
	config['installBaseDir'] = parser.get("home", "INSTALL_BASE_DIR").split()[0]

	#  Logging
	config['logFile'] = parser.get("logging", "LOG_FILE").split()[0]
	
	#  Management
	config['userManagement'] = parser.get("management", "USER_MANAGEMENT").split()[0]
	#config['infoStore'] = parser.get("management", "INFO_STORE").split()[0]
	config['pickleFile'] = parser.get("management", "PICKLE_FILE").split()[0]
	
	#  DB connection
	config['dbUser'] = parser.get("dbConnection", "DB_USER").split()[0]
	config['dbPassword'] = config.get("dbPassword", "")
	if not parser.get("dbConnection", "DB_PASSWORD") == "":
		config['dbPassword'] = parser.get("dbConnection", "DB_PASSWORD").strip("\",'")
	config['dbHost'] = parser.get("dbConnection", "DB_HOST").split()[0]
	config['dbPort'] = int(parser.get("dbConnection", "DB_PORT").split()[0])
	config['dbInst'] = parser.get("dbConnection", "DB_INST").split()[0]

	#  PXE info
	config['tftpRootDir'] = parser.get("pxe", "TFTP_ROOT_DIR").split()[0]
	config['tftpImageDir'] = parser.get("pxe", "TFTP_IMAGE_DIR").split()[0]
	config['tftpBootOptionsDir'] = parser.get("pxe", "TFTP_BOOT_OPTIONS_DIR").split()[0]
	config['tftpUpdateFile'] = parser.get("pxe", "TFTP_UPDATE_FILE").split()[0]
	config['tftpBaseFile'] = parser.get("pxe", "TFTP_BASE_FILE").split()[0]
	config['tftpBaseMenuFile'] = parser.get("pxe", "TFTP_BASE_MENU_FILE").split()[0]
	config['pxeServerIP'] = parser.get("pxe", "PXE_SERVER_IP").split()[0]
	config['initrdRoot'] = parser.get("pxe", "INITRD_ROOT").split()[0]
	config['kernelRoot'] = parser.get("pxe", "KERNEL_ROOT").split()[0]

	#  Image store
	config['imageServerIP'] = parser.get("imageStore", "IMAGE_SERVER_IP").split()[0]
	config['fsImagesBaseDir'] = parser.get("imageStore", "FS_IMAGES_BASE_DIR").split()[0]

	#  WWW
	config['wwwDocumentRoot'] = parser.get("www", "WWW_DOCUMENT_ROOT").split()[0]
	config['registrationBaseDir'] = parser.get("www", "REGISTRATION_BASE_DIR").split()[0]
	
	#  SNMP
	config['snmpCommunity'] = parser.get("snmp", "SNMP_COMMUNITY").split()[0]

	#  VLAN
	#config['vlan_reserved'] = parser.get("vlan", "VLAN_RESERVED")
	config['vlanMax'] = int(parser.get("vlan", "VLAN_MAX"))

	#  Domain
	config['zoniHomeDomain'] = parser.get("domain", "ZONI_HOME_DOMAIN").split()[0]
	config['zoniHomeNetwork'] = parser.get("domain", "ZONI_HOME_NETWORK").split()[0]
	config['zoniIpmiNetwork'] = parser.get("domain", "ZONI_IPMI_NETWORK").split()[0]
	#config['vlan_max'] = parser.get("vlan", "VLAN_MAX")

	#  HARDWARE CONTROL
	config['hardwareControl'] = eval(parser.get("hardware", "HARDWARE_CONTROL"))

	#  DHCP/DNS
	config['dnsEnabled'] = parser.get("DhcpDns", "dnsEnabled")
	config['reverseDns'] = parser.get("DhcpDns", "reverseDns")
	#config['dnsKeyFile'] = parser.get("DhcpDns", "dnsKeyfile")
	config['dnsKeyName'] = parser.get("DhcpDns", "dnsKeyName")
	config['dnsSecretKey'] = parser.get("DhcpDns", "dnsSecretKey")
	config['dnsServer'] = parser.get("DhcpDns", "dnsServer")
	config['dnsDomain'] = parser.get("DhcpDns", "dnsDomain")
	config['dnsExpire'] = parser.get("DhcpDns", "dnsExpire")
	config['dhcpServer'] = parser.get("DhcpDns", "dhcpServer")
	config['dhcpKeyName'] = parser.get("DhcpDns", "dhcpKeyName")
	config['dhcpSecretKey'] = parser.get("DhcpDns", "dhcpSecretKey")

	#self.ap_model['radius'] = int(parser.get("wireless_range", "radius").split()[0])
	return config

def getConfig(additionalNames=[], additionalFiles=[]):
	"""Creates many permutations of a list of locations to look for config 
	   files and then loads them"""
	config = ConfigParser.ConfigParser()
	baseLocations = ['./etc/', '/usr/share/zoni/', '/etc/zoni/', os.path.expanduser('~/.zoni/')]
	names = ['Zoni'] + additionalNames
	names = reduce(lambda x, y: x + [y+"Defaults", y], names, [])
	allLocations = reduce(lambda x, y: x + reduce(lambda z, a: z + [y + a + ".cfg"], names, []), baseLocations, []) + additionalFiles
	configFiles = config.read(allLocations)
	if (len(configFiles) == 0):
		raise Exception("No config file could be found: %s" % (str(allLocations)))

	return (loadConfigFile(config), configFiles)

def logit(logfile, mesg):
	fd = open(logfile, "a+");
	mesg = str(time.time()) + " " + mesg + "\n"
	fd.write(mesg);
	fd.close;
	#if verbose:
	print mesg
	fd.close




def checkSuper(f):
	def myF(*args, **kw):
		res = f(*args, **kw)
		if os.getuid() != 0:
			print "Please use sudo!"
			exit()
		return res
	myF.__name__ = f.__name__
	
	return myF


def timeF(f):
	def myF(*args, **kw):
		start = time.time()
		res = f(*args, **kw)
		end = time.time()
		print "%s took %f" % (f.__name__, end-start)
		return res
	myF.__name__ = f.__name__
	return myF

def log(f):
	def myF(*args, **kw):
		print "calling %s%s" % (f.__name__, str(args))
		res = f(*args, **kw)
		print "returning from %s -> %s" % (f.__name__, str(res))
		return res
	myF.__name__ = f.__name__
	return myF

def createDir(dirName, checkexists=None):
	if checkexists and os.path.exists(dirName):
		Bak = os.path.join(dirName + ".bak." + str(int(time.time())))
		shutil.move(dirName, Bak)

	try:
		os.mkdir(dirName, 0755)
		print "	Creating directory " + dirName
	except (OSError, Exception), e:
		print "	" + e.args[1] + ": " + dirName
		return 0

	return 1



def validIp(ip):
	if len(ip.split(".")) != 4:
		return 0
	for i in ip.split("."):
		try: 
			if not 0 <= int(i) <= 255:
				return 0
		except ValueError, e:
			print "ERROR:  " + str(e)
			return 0
	return 1

def normalizeMac(mac):
	rawmac = re.sub('[.:-]', '', mac)
	return  string.lower(":".join(["%s%s" % (rawmac[i], rawmac[i+1]) for i in range(0,12,2)]))

def validMac(mac):
	reg = '([a-fA-F0-9]{2}[:|\\-]?){6}'
	val = re.compile(reg).search(mac)
	if val:
		return 1
	return 0

def createKey(name):
	tmpdir = "/tmp"
	def cleanIt(tmpdir, name):
		check = "K%s" % name
		for i in os.listdir(tmpdir):
			if check in i:
				keyName = os.path.join(tmpdir, i)
				os.unlink(keyName)

	cleanIt(tmpdir, name)
	cmd = "dnssec-keygen -a HMAC-MD5 -r /dev/urandom -b 128 -K %s -n USER %s" % (tmpdir, name)
	c = subprocess.Popen(args=cmd.split(), stdout=subprocess.PIPE)
	keyName = os.path.join(tmpdir, string.strip(c.stdout.readline()) + ".key")
	f = open(keyName, "r")
	val = string.strip(string.split(f.readline(), " " , 6)[6])
	f.close()
	return val
	

def __getShellFn():
	if sys.version_info < (2, 6, 1):
		from IPython.Shell import IPShellEmbed
		return IPShellEmbed()
	else:
		import IPython
		return IPython.embed()

def debugConsole(globalDict):
	"""A debugging console that optionally uses pysh"""
	def realDebugConsole(globalDict):
		try :
			import atexit
			shellfn = __getShellFn()
			def resetConsole():
# XXXpipe: make input window sane
				(stdin, stdout) = os.popen2("reset")
				stdout.read()
			dbgshell = shellfn()
			atexit.register(resetConsole)
			dbgshell(local_ns=globalDict, global_ns=globalDict)
		except Exception:
			CONSOLE_TEXT=">>> "
			input = " "
			while (input != ""):
				sys.stdout.write(CONSOLE_TEXT)
				input = sys.stdin.readline()
				try:
					exec(input) in globalDict
				except Exception, e:
					sys.stdout.write(str(e) + "\n")
	if (os.getenv("DEBUG", "0") == "1"):
		threading.Thread(target=lambda: realDebugConsole(globalDict)).start()

