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

def loadConfigFile(parser):
	#parser = ConfigParser.ConfigParser()
	#parser.read(filename)
	config = {}
	#  Logging
	config['logFile'] = parser.get("logging", "LOG_FILE").split()[0]
	
	#  DB connection
	config['dbUser'] = parser.get("dbConnection", "DB_USER").split()[0]
	config['dbPassword'] = config.get("dbPassword", "")
	if not parser.get("dbConnection", "DB_PASSWORD") == "":
		config['dbPassword'] = parser.get("dbConnection", "DB_PASSWORD").strip("\",'")
	config['dbHost'] = parser.get("dbConnection", "DB_HOST").split()[0]
	config['dbPort'] = int(parser.get("dbConnection", "DB_PORT").split()[0])
	config['dbInst'] = parser.get("dbConnection", "DB_INST").split()[0]

	#  TFTP info
	config['tftpRootDir'] = parser.get("tftp", "TFTP_ROOT_DIR").split()[0]
	config['tftpImageDir'] = parser.get("tftp", "TFTP_IMAGE_DIR").split()[0]
	config['tftpBootOptionsDir'] = parser.get("tftp", "TFTP_BOOT_OPTIONS_DIR").split()[0]
	config['tftpUpdateFile'] = parser.get("tftp", "TFTP_UPDATE_FILE").split()[0]
	config['tftpBaseFile'] = parser.get("tftp", "TFTP_BASE_FILE").split()[0]
	config['tftpBaseMenuFile'] = parser.get("tftp", "TFTP_BASE_MENU_FILE").split()[0]
	
	#  SNMP
	config['snmpCommunity'] = parser.get("snmp", "SNMP_COMMUNITY").split()[0]

	#  VLAN
	config['vlan_reserved'] = parser.get("vlan", "VLAN_RESERVED")
	config['vlan_max'] = parser.get("vlan", "VLAN_MAX")

	#  HARDWARE CONTROL
	config['hardware_control'] = parser.get("hardware", "HARDWARE_CONTROL")

	#  DHCP/DNS
	config['dnsKeyFile'] = parser.get("DhcpDns", "dnsKeyfile")
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

	return loadConfigFile(config)

def logit(logfile, mesg):
	fd = open(logfile, "a+");
	mesg = str(time.time()) + " " + mesg + "\n"
	fd.write(mesg);
	fd.close;
	#if verbose:
	print mesg
	fd.close


