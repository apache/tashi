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
import ConfigParser
import time
import shutil
import re

def loadConfigFile(parser):
	#parser = ConfigParser.ConfigParser()
	#parser.read(filename)
	config = {}
	#  Install dir
	config['installBaseDir'] = parser.get("home", "INSTALL_BASE_DIR")

	#  Logging
	#config['logFile'] = parser.get("logging", "LOG_FILE")
	config['logFile'] = parser.get("logging", "LOG_FILE")
	
	#  DB connection
	config['dbUser'] = parser.get("dbConnection", "DB_USER")
	config['dbPassword'] = config.get("dbPassword", "")
	if not parser.get("dbConnection", "DB_PASSWORD") == "":
		config['dbPassword'] = parser.get("dbConnection", "DB_PASSWORD").strip("\",'")
	config['dbHost'] = parser.get("dbConnection", "DB_HOST")
	config['dbPort'] = int(parser.get("dbConnection", "DB_PORT"))
	config['dbInst'] = parser.get("dbConnection", "DB_INST")

	#  PXE info
	config['tftpRootDir'] = parser.get("pxe", "TFTP_ROOT_DIR")
	config['tftpImageDir'] = parser.get("pxe", "TFTP_IMAGE_DIR")
	config['tftpBootOptionsDir'] = parser.get("pxe", "TFTP_BOOT_OPTIONS_DIR")
	config['tftpUpdateFile'] = parser.get("pxe", "TFTP_UPDATE_FILE")
	config['tftpBaseFile'] = parser.get("pxe", "TFTP_BASE_FILE")
	config['tftpBaseMenuFile'] = parser.get("pxe", "TFTP_BASE_MENU_FILE")
	config['pxeServerIP'] = parser.get("pxe", "PXE_SERVER_IP")
	config['initrdRoot'] = parser.get("pxe", "INITRD_ROOT")

	#  Image store
	config['imageServerIP'] = parser.get("imageStore", "IMAGE_SERVER_IP")
	config['fsImagesBaseDir'] = parser.get("imageStore", "FS_IMAGES_BASE_DIR")

	#  WWW
	config['wwwDocumentRoot'] = parser.get("www", "WWW_DOCUMENT_ROOT")
	config['registrationBaseDir'] = parser.get("www", "REGISTRATION_BASE_DIR")
	
	#  SNMP
	config['snmpCommunity'] = parser.get("snmp", "SNMP_COMMUNITY")

	#  VLAN
	#config['vlan_reserved'] = parser.get("vlan", "VLAN_RESERVED")
	config['vlan_max'] = parser.get("vlan", "VLAN_MAX")

	#  Domain
	config['zoniHomeDomain'] = parser.get("domain", "ZONI_HOME_DOMAIN")
	config['zoniHomeNetwork'] = parser.get("domain", "ZONI_HOME_NETWORK")
	config['zoniIpmiNetwork'] = parser.get("domain", "ZONI_IPMI_NETWORK")
	#config['vlan_max'] = parser.get("vlan", "VLAN_MAX")

	#  HARDWARE CONTROL
	config['hardware_control'] = parser.get("hardware", "HARDWARE_CONTROL")

	#  DHCP/DNS
	#config['dnsKeyFile'] = parser.get("DhcpDns", "dnsKeyfile")
	config['dnsKeyName'] = parser.get("DhcpDns", "dnsKeyName")
	config['dnsSecretKey'] = parser.get("DhcpDns", "dnsSecretKey")
	config['dnsServer'] = parser.get("DhcpDns", "dnsServer")
	config['dnsDomain'] = parser.get("DhcpDns", "dnsDomain")
	config['dnsExpire'] = parser.get("DhcpDns", "dnsExpire")
	config['dhcpServer'] = parser.get("DhcpDns", "dhcpServer")
	config['dhcpKeyName'] = parser.get("DhcpDns", "dhcpKeyName")
	config['dhcpSecretKey'] = parser.get("DhcpDns", "dhcpSecretKey")

	#self.ap_model['radius'] = int(parser.get("wireless_range", "radius"))
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


def createDir(dirName, checkexists=None):
	if checkexists and os.path.exists(dirName):
		Bak = os.path.join(dirName + ".bak." + str(int(time.time())))
		shutil.move(dirName, Bak)

	try:
		os.mkdir(dirName, 0755)
		print "	Creating directory " + dirName
	except (OSError, Exception), e:
		if e.errno == 17:
			print "	" + e.args[1] + ": " + dirName
		else:
			print "	" + e.args[1] + ": " + dirName


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

def validMac(mac):
	reg = '([a-fA-F0-9]{2}[:|\\-]?){6}'
	val = re.compile(reg).search(mac)
	if val:
		return 1
	return 0



