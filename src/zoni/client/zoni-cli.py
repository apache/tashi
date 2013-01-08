#! /usr/bin/env python 

#
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

import optparse
import socket
import logging.config
import getpass
import os
import sys
import re
import string
import subprocess

#from zoni import *
#from zoni.data.resourcequerysql import ResourceQuerySql
#import zoni
#from zoni.data.resourcequerysql import *

from zoni.bootstrap.pxe import Pxe

from zoni.hardware.ipmi import Ipmi
from zoni.hardware.dellswitch import HwDellSwitch
from zoni.hardware.raritanpdu import raritanDominionPx
from zoni.hardware.delldrac import dellDrac
import zoni.hardware.systemmanagement
from zoni.data import usermanagement
from zoni.agents.dhcpdns import DhcpDns

from zoni.extra.util import validIp, validMac, getConfig
from zoni.version import version, revision

from tashi.util import instantiateImplementation
#import zoni.data.usermanagement 
#from usermanagement import UserManagement

# Extensions from MIMOS
from zoni.extensions.m_extensions import *

def parseTable():
	pass

def main():
	"""  Main """
	ver = version.split(" ")[0]
	rev = revision

	(configs, configFiles) = getConfig()
	logging.config.fileConfig(configFiles)
	#log = logging.getLogger(os.path.basename(__file__))
	#logit(configs['logFile'], "Starting Zoni client")
	#logit(configs['logFile'], "Loading config file")

	parser = optparse.OptionParser(usage="%prog [-n] [-u] [--uid] [-v]", version="%prog " + ver + " " + rev)
	parser.add_option("-n", "--nodeName", dest="nodeName", help="Specify node")
	parser.add_option("--switchPort", "--switchport", dest="switchPort", help="Specify switchport switchname:portnum")
	parser.add_option("-u", "--userName", dest="userName", help="Specify user name")
	parser.add_option("--uid", dest="uid", help="Specify user id")
	parser.add_option("-v", "--verbose", dest="verbosity", help="Be verbose", action="store_true", default=False)
	parser.add_option("--Name", "--name", dest="Name", help="Specify name of entry")
	parser.add_option("--Show", "--show", dest="show", help="Show something", default=None, action="store_true")
	parser.add_option("-d", "--domain", dest="domain", help="Work with this domain")
	parser.add_option("--notes", "--Notes",  dest="myNotes", help="Notes", default="")
	parser.add_option("--force",  dest="forcefully", help="Apply gentle pressure", default=False, action="store_true")


	#  Hardware controller
	group = optparse.OptionGroup(parser, "Hardware control", "Options for node power control")
	group.add_option("--hw", dest="hardwareType", help="Make hardware call to ipmi|drac|pdu")
	group.add_option("--powerStatus", "--powerstatus", dest="POWERSTATUS", help="Get power status on node", action="store_true", default=False)
	group.add_option("--reboot", "--reboot", dest="REBOOTNODE", help="Reboot node (Soft)", action="store_true", default=False)
	group.add_option("--powerCycle", "--powercycle", dest="POWERCYCLE", help="Power Cycle (Hard)", action="store_true", default=False)
	group.add_option("--powerOff", "--poweroff", dest="POWEROFF", help="Power off node", action="store_true", default=False)
	group.add_option("--powerOffSoft", "--poweroffsoft", dest="POWEROFFSOFT", help="Power off node (soft)", action="store_true", default=False)
	group.add_option("--powerOn", "--poweron", dest="POWERON", help="Power on node", action="store_true", default=False)
	group.add_option("--powerReset", "--powerreset", dest="POWERRESET", help="Power reset node", action="store_true", default=False)
	group.add_option("--console", dest="CONSOLE", help="Console mode", action="store_true", default=False)
	# Extensions from MIMOS - specific only for HP Blades and HP c7000 Blade Enclosures
	group.add_option("--powerOnNet", "--poweronnet", dest="POWERONENET", help="Power on Node into PXE (Currently support on HP Blades through HP c7000 Blade Enclosure)", action="store_true", default=False)
	parser.add_option_group(group)

	#  Query Interface
	group = optparse.OptionGroup(parser, "Query Interface", "Query current systems and allocations")
	group.add_option("-R", "--showReservation", "--showreservation", dest="showReservation", help="Show current node reservations", action="store_true", default=False)
	group.add_option("-A", "--showAllocation", "--showallocation", dest="showAllocation", help="Show current node allocation", action="store_true", default=False)
	group.add_option("-S", "--showResources", dest="showResources", help="Show available resources to choose from", action="store_true", default=False)
	group.add_option("--getResources", "--getresources", dest="getResources", help="Get available resources to choose from", action="store_true", default=False)
	group.add_option("-p", "--procs", dest="numProcs", help="Set number of processors" )
	group.add_option("-c", "--clock", dest="clockSpeed", help="Processor clock" )
	group.add_option("--memory", dest="numMemory", help="Amount of memory (Bytes)" )
	group.add_option("-f", "--cpuflags", dest="cpuFlags", help="CPU flags" )
	group.add_option("--cores", dest="numCores", help="Number of Cores" )
	group.add_option("-I", "--showPxeImages", "--showpxeimages", dest="showPxeImages", help="Show available PXE images to choose from", action="store_true", default=False)
	group.add_option("-M", "--showPxeImageMap", "--showpxeimagemap", dest="showPxeImageMap", help="Show PXE images host mapping", action="store_true", default=False)
	parser.add_option_group(group)
	#parser.add_option("-p", "--printResources", dest="printResources", help="Print available resources to choose from", action="store_true", default=False)

	#  Admin Interface
	group = optparse.OptionGroup(parser, "Admin Interface", "Administration Interface:")
	group.add_option("--admin", dest="ADMIN", help="Enter Admin mode", action="store_true", default=False)
	group.add_option("--setPortMode", "--setportmode", dest="setPortMode", help="Set port mode to access, trunk, or general")
	group.add_option("--enableHostPort", "--enablehostport", dest="enableHostPort", help="Enable a switch port", action="store_true", default=False)
	group.add_option("--disableHostPort", "--disablehostport", dest="disableHostPort", help="Disable a switch port", action="store_true", default=False)
	group.add_option("--destroyVlan", "--destroyvlan", dest="destroyVlanId", help="Remove vlan from all switches")
	group.add_option("--createVlan", "--createvlan", dest="createVlanId", help="Create a vlan on all switches")
	group.add_option("--addNodeToVlan", "--addnodetovlan", dest="add2Vlan", help="Add node to a vlan (:tagged)")
	group.add_option("--removeNodeFromVlan", "--removenodefromvlan", dest="removeFromVlan", help="Remove node from a vlan")
	group.add_option("--setNativeVlan", "--setnativevlan", dest="setNative", help="Configure native vlan")
	group.add_option("--restoreNativeVlan", "--restorenativevlan", dest="restoreNative", help="Restore native vlan", action="store_true", default=False)
	group.add_option("--removeAllVlans", "--removeallvlans", dest="removeAllVlans", help="Removes all vlans from a switchport", action="store_true", default=False)
	group.add_option("--sendSwitchCommand", "--sendswitchcommand", dest="sendSwitchCommand", help="Send Raw Switch Command, VERY DANGEROUS.  config;interface switchport ethernet g14;etc")
	group.add_option("--interactiveSwitchConfig", "--interactiveswitchconfig", dest="interactiveSwitchConfig", help="Interactively configure a switch.  switchhname")
	group.add_option("--showSwitchConfig", "--showswitchconfig", dest="showSwitchConfig", help="Show switch config for node", action="store_true", default=False)
	group.add_option("--register", dest="register", help="Register hardware to Zoni", action="store_true", default=False)
	group.add_option("--labelPort", dest="labelPort", help="Label switch port", action="store_true", default=False)
	group.add_option("--saveConfig", dest="saveConfig", help="SWITCHNAME - Save Switch Config")
	parser.add_option_group(group)


	#  Switch
	#group = optparse.OptionGroup(parser, "Switch Interface", "Switch Interface:")
	#group.add_option("--rawswitch", dest="RAWSWITCH", help="Enter RAW Switch Admin mode", action="store_true", default=False)
	#group.add_option("--enablePort", "--enableport", dest="enablePort", help="Enable a port on the switch")
	#group.add_option("--disablePort", "--disableport", dest="disablePort", help="Disable a port on the switch")
	#group.add_option("--addVlanToTrunks", "--addvlantotrunks", dest="addVlanToTrunks", help="")
	

	#  Domain Interface
	group = optparse.OptionGroup(parser, "Domain Interface", "Manage Zoni Domain:")
	group.add_option("-D", "--showDomains", "--showdomains", dest="showDomains", help="Show Zoni domains", action="store_true", default=False)
	group.add_option("--addDomain", "--adddomain", dest="addDomain", help="Add new domain to Zoni", action="store_true", default=False)
	group.add_option("--removeDomain", "--removedomain", dest="removeDomain", help="remove a domain from Zoni", action="store_true", default=False)
	group.add_option("-V", "--showVlans", "--showvlans", dest="showVlans", help="Show an from Zoni", action="store_true", default=False)
	#group.add_option("--addVlan", "--addvlan", dest="addVlan", help="Add new vlan to Zoni", action="store_true", default=False)
	#group.add_option("--removeVlan", "--removevlan", dest="removeVlan", help="Remove an from Zoni", action="store_true", default=False)
	group.add_option("--assignVlan", "--assignvlan", dest="assignVlan", help="Assign vlan to a domain")
	parser.add_option_group(group)

	#  Allocation Interface
	group = optparse.OptionGroup(parser, "Allocation Interface", "Change current systems allocations:")
	#group.add_option("--addReservation", "--addreservation", dest="addReservation", help="Add a Reservation", action="store_true", default=False)
	group.add_option("--addImage", "--addimage", dest="addImage", help="Add image to Zoni - amd64-image:dist:dist_ver")
	group.add_option("--delImage", "--delimage", dest="delImage", help="Delete PXE image")
	#group.add_option("--addPxeImage", "--addpxeimage", dest="imageName", help="Add PXE image to database", action="store_true", default=False)
	group.add_option("--assignImage", "--assignimage", dest="assignImage", help="Assign image to resource")
	group.add_option("--imageName", "--imagename", dest="imageName", help="Assign image to resource")

	group.add_option("--allocateNode", "--allocatenode", dest="allocateNode", help="Assign node to a user", action="store_true", default=False)
	group.add_option("--vlaninfo", "--vlanInfo", dest="vlanInfo", help="Specify vlan info for allocation")
	group.add_option("--vlanIsolate", "--vlanisolate", dest="vlanIsolate", help="Specify vlan for network isolation")
	group.add_option("--hostName", "--hostname", dest="hostName", help="Specify hostname for node")
	group.add_option("--ipaddr", dest="ipAddr", help="Specify ip address for node")

	group.add_option("--releaseNode", "--releasenode", dest="releaseNode", help="Release current node allocation", action="store_true", default=False)
	group.add_option("--reservationDuration", "--reservationduration", dest="reservationDuration", help="Specify duration of node reservation - YYYYMMDD format")
	group.add_option("-r", "--reservationId", "--reservationid", dest="reservationId", help="Reservation ID")
	group.add_option("--updateReservation", "--updatereservation", dest="updateReservation", help="Update Reservation", action="store_true", default=False)
	group.add_option("--delReservation", "--delreservation", dest="delReservation", help="Delete Reservation")
	group.add_option("--rgasstest", dest="rgasstest", help="Debug testing function", action="store_true", default=False)
	parser.add_option_group(group)

	group = optparse.OptionGroup(parser, "Reservation Interface", "Change current systems reservations:")
	group.add_option("--createReservation", "--createreservation", dest="createReservation", help="Create a new Reservation", action="store_true", default=False)
	parser.add_option_group(group)

	#  Zoni Helpers
	group = optparse.OptionGroup(parser, "Zoni Helpers", "Helper functions:")
	group.add_option("--addDns", dest="addDns", help="Add a DNS entry", action="store_true", default=False)
	group.add_option("--removeDns", dest="removeDns", help="Remove a DNS entry", action="store_true", default=False)
	group.add_option("--addCname", dest="addCname", help="Add a DNS Cname entry", action="store_true", default=False)
	group.add_option("--removeCname", dest="removeCname", help="Remove a DNS Cname entry", action="store_true", default=False)
	group.add_option("--addDhcp", dest="addDhcp", help="Add a DHCP entry", action="store_true", default=False)
	group.add_option("--removeDhcp", dest="removeDhcp", help="Remove a DHCP entry", action="store_true", default=False)
	parser.add_option_group(group)

	# Extensions from MIMOS
	group = optparse.OptionGroup(parser, "Zoni MIMOS Extensions", "Special Functions created by MIMOS Lab:")
	group.add_option("--addRole", "--addrole", dest="addRole", help="Create a disk based installation default file for a node based on its role or function, e.g. one|oned|cc|clc|walrus|sc|nc|preseed|kickstart", default=None, action="store")
	group.add_option("--removeRole", "--removerole", dest="removeRole", help="Remove the default file of a node", action="store_true", default=False)
	group.add_option("--showRoleMap", dest="showRoleMap", help="Show Role to Host Mapping", action="store_true", default=False)
	group.add_option("--showKernel", dest="showKernelInfo", help="Show Kernel Info", action="store_true", default=False)
	group.add_option("--showInitrd", dest="showInitrdInfo", help="Show Initrd Info", action="store_true", default=False)
	group.add_option("--registerKernelInitrd", dest="registerKernelInitrd", help="Register Kernel and Initrd - vmlinuz:vmlinuz-ver:vmlinuz-arch:initrd:initrd-arch:imagename")
	group.add_option("--getKernelInitrdID", dest="getKernelInitrdID", help="Get corresponding Kernel and Initrd Info - vmlinuz:initrd:arch")
	group.add_option("--getConfig", dest="getConfig", help="Get a value from ZoniDefault.cfg - e.g. tftpRootDir, initrdRoot, kernelRoot, fsImagesBaseDir, etc.", default=None, action="store")
	parser.add_option_group(group)

	(options, args) = parser.parse_args()

	
	cmdargs = {}

	#  setup db connection
	#print "starting tread"
	#threading.Thread(daemon=True, target=self.dbKeepAlive()).start()
	#print "after tread"

	data = instantiateImplementation("zoni.data.resourcequerysql.ResourceQuerySql", configs, options.verbosity)
	reservation = instantiateImplementation("zoni.data.reservation.reservationMysql", configs, data, options.verbosity)
	#query = zoni.data.resourcequerysql.ResourceQuerySql(configs, options.verbosity)
	# Extensions from MIMOS
	mimos = instantiateImplementation("zoni.extensions.m_extensions.mimos",configs)

	#  Get host info
	host=None
	if options.nodeName:
		host = data.getHostInfo(options.nodeName)
		#print host
	

	#  Hardware control
	if options.hardwareType and options.nodeName:
		host = data.getHostInfo(options.nodeName)
		if options.hardwareType == "ipmi":
		#hardware = zoni.hardware.systemmanagement.SystemManagement(configs,data)
			hw = Ipmi(configs, options.nodeName, host)
#
		if options.hardwareType == "pdu":
			hw = raritanDominionPx(configs, options.nodeName, host)
#
		if options.hardwareType == "drac":
			##  Check if node has drac card
			if "drac_name" in host:
				hw= dellDrac(configs, options.nodeName, host)
			else:
				mesg = "Host (%s) does not have a DRAC card!!\n" % options.nodeName
				sys.stdout.write(mesg)
				exit(1)

		## Extensions from MIMOS - For Dell Blades - calling Dell Blades via the Blade Enclosure, some DRAC commands are slightly different from the ones in blade enclosure when compared to those in the actual blade, this allow a bit more flexiblity and standard calls to the blades
		if options.hardwareType == "dracblade":
			hw = dellBlade(configs, options.nodeName, host)

		## Extensions from MIMOS - For HP Blades - calling HP Blades via the HP c7000 Blade Enclosure instead of direct to the blade server itself, this allow a bit more flexiblity and standard calls to the blades
		if options.hardwareType == "hpilo":
			hw = hpILO(configs, options.nodeName, host)

		if (options.REBOOTNODE or options.POWERCYCLE  or options.POWEROFF or options.POWEROFFSOFT or \
			options.POWERON or options.POWERSTATUS or options.CONSOLE or \
			options.POWERONNET or options.POWERRESET) and options.nodeName: # Extensions from MIMOS - added POWERONNET

			if options.verbosity:
				hw.setVerbose(True)

			if options.REBOOTNODE:
				hw.powerReset()
				exit()
			if options.POWERCYCLE: 
				hw.powerCycle()
				exit()
			if options.POWEROFF:
				hw.powerOff()
				exit()
			if options.POWEROFFSOFT:
				hw.powerOffSoft()
				exit()
			if options.POWERON:
				hw.powerOn()
				exit()
			if options.POWERRESET:
				hw.powerReset()
				exit()
			if options.POWERSTATUS:
				hw.getPowerStatus()
				exit()
			if options.CONSOLE:
				hw.activateConsole()
				exit()
			## Extensions from MIMOS - For HP Blade via c7000 Blade Enclosure
			if options.POWERONNET:
				hw.powerOnNet()
				exit()
			hw.getPowerStatus()
			exit()
	else:
		hw = zoni.hardware.systemmanagement.SystemManagement(configs,data)

	if (options.REBOOTNODE or options.POWERCYCLE  or options.POWEROFF or options.POWEROFFSOFT or \
		options.POWERON or options.POWERSTATUS or options.CONSOLE or \
		options.POWERRESET) and options.nodeName:

		if options.verbosity:
			hw.setVerbose(True)

		if options.REBOOTNODE:
			hw.powerReset(options.nodeName)
			exit()
		if options.POWERCYCLE: 
			hw.powerCycle(options.nodeName)
			exit()
		if options.POWEROFFSOFT:
			hw.powerOffSoft(options.nodeName)
			exit()
		if options.POWEROFF:
			hw.powerOff(options.nodeName)
			exit()
		if options.POWERON:
			hw.powerOn(options.nodeName)
			exit()
		if options.POWERRESET:
			hw.powerReset(options.nodeName)
			exit()
		if options.POWERSTATUS:
			hw.getPowerStatus(options.nodeName)
			exit()
		if options.CONSOLE:
			hw.activateConsole(options.nodeName)
			exit()
		hw.getPowerStatus(options.nodeName)



	if (options.REBOOTNODE or options.POWERCYCLE  or options.POWEROFF or \
		options.POWERON or options.POWERSTATUS or options.CONSOLE or \
		options.POWERRESET) and not options.nodeName:
		parser.print_help()
		mesg = "\nMISSSING OPTION:  Node name required -n or --nodeName\n"
		print mesg
		exit()

	#  Query Interface
	if (options.numProcs):
		cmdargs["num_procs"] = options.numProcs
	if (options.numMemory):
		cmdargs["mem_total"] = options.numMemory
	if (options.clockSpeed):
		cmdargs["clock_speed"] = options.clockSpeed
	if (options.numCores):
		cmdargs["num_cores"] = options.numCores
	if (options.cpuFlags):
		cmdargs["cpu_flags"] = options.cpuFlags
	if (options.nodeName):
		cmdargs["sys_id"] = options.nodeName

	if (options.numCores or options.clockSpeed or options.numMemory or options.numProcs or options.cpuFlags) and not options.showResources:
		usage = "MISSING OPTION: When specifying hardware parameters, you need the -s or --showResources switch"
		print usage
		parser.print_help()	
		exit()

	if options.getResources:
		print "ALL resources"
		print data.getAvailableResources()
		key = "3Lf7Qy1oJZue1q/e3ZQbfg=="
		print "Tashi Resources"
		print data.getMyResources(key)

	#  Show current allocations 
	if (options.showAllocation) or (options.show and re.match(".lloca.*", args[0])):
		if options.uid:
			nameorid = int(options.uid)
		else: 
			nameorid = options.userName

		data.showAllocation(nameorid)
		exit()

	#  Show current reservation
	if options.showReservation or (options.show and re.match(".eserv.*", args[0])):
		if options.uid:
			nameorid = int(options.uid)
		else: 
			nameorid = options.userName

		data.showReservation(nameorid)

	#  Print all Resources
	if options.showResources or (options.show and re.match(".esour.*", args[0])):
		data.showResources(cmdargs)

	#  Show PXE images
	#if (options.show and re.match(".esour.*", args[0])):
	if options.showPxeImages or (options.show and re.match("pxei.*", args[0])):
		data.showPxeImages()

	#  Show machine to PXE image mapping
	if options.showPxeImageMap or (options.show and re.match("pxem.*", args[0])):
		data.showPxeImagesToSystemMap(cmdargs)

	if (len(sys.argv) == 1):
		parser.print_help()
		exit()


	#  Delete reservation
	if (options.delReservation):
		data.removeReservation(options.delReservation)
		exit()

	#  Specify usermanagement, ldap or files
	if configs['userManagement'] == "ldap":
		usermgt = usermanagement.ldap()
	elif configs['userManagement'] == "files":
		usermgt = usermanagement.files()
	else:
		print "User management problem"
		exit()


	if (options.rgasstest):
		#data.getHardwareCapabilities(options.nodeName)
		#pdu = raritanDominionPx(host)
		#print pdu
		#bootit = pxe.Pxe(configs, options.verbosity)
		#bootit.createPxeUpdateFile(data.getPxeImages())
		#bootit.updatePxe()
		#print "host is ", host
		#drac = dellDrac("drac-r2r1c3", 1)
		drac = dellDrac(configs, options.nodeName, host)
		#drac.getPowerStatus()
		#drac.powerOff()
		#drac.powerOn()
		#drac.powerCycle()
		drac.setVerbose(options.verbosity)
		drac.powerReset()
		#drac.getPowerStatus()
		#print "host is ", host
		#pdu = raritanDominionPx(configs, options.nodeName, host)
		#print "pdu", pdu
		#pdu.getPowerStatus()
		#exit()

	#  Create a reservation for a user
	if (options.createReservation):
		if not (options.userName or options.uid):
			mesg = "ERROR:  CreateReservation requires the following arguments...\n"
			if not (options.userName or options.uid):
				mesg += "  Username:  --userName=username or --uid 1000\n"

			mesg += "  Reservation Duration:  --reservationDuration YYYYMMDD or numdays(optional, default 15 days)\n"
			mesg += "  Notes:  --notes(optional)\n"
			sys.stderr.write(mesg)		
			exit()

		userId = options.uid
		if not userId:
			userId = usermgt.getUserId(options.userName)

		if userId:
			__reservationId = reservation.createReservation(userId, options.reservationDuration, options.myNotes + " " + str(string.join(args[0:len(args)])))

		else:
			print "user doesn't exist"
			exit()

	#  Allocate node to user
	if (options.allocateNode):
		if options.reservationId and options.domain and options.vlanInfo and options.nodeName and options.imageName:
			host = data.getHostInfo(options.nodeName)
			#  optparse does not pass multiple args that are quoted anymore?  
			#  Used to work with python 2.5.2.  Doesn't work with python 2.6.5.  
			data.allocateNode(options.reservationId, options.domain, host['sys_id'], options.vlanInfo, options.imageName, options.hostName, options.myNotes + " " + str(string.join(args[0:len(args)])))
		else:
			mesg = "USAGE: %s --allocateNode --nodeName nodeName --domain domainname --reservationId ID --vlanInfo vlanNums:info, --imageName imagename [--notes]\n" % (sys.argv[0])
			mesg += "Options\n"
			mesg += "  --domain testdomain\n"
			mesg += "  --reservationId 10\n"
			mesg += "  --vlanInfo 999:native,1000:tagged,1001:tagged\n"
			mesg += "  --imageName imageName (see available images with 'zoni -I')\n"
			mesg += "  --hostName mynode01 (optional)\n"
			mesg += "  --notes \"your notes here \"(optional)\n"
			sys.stdout.write(mesg)
			exit()
		
		if not (options.reservationId) or not options.nodeName: 
			mesg = "ERROR:  AllocateNode requires the following arguments...\n"
			if not (options.nodeName):
				mesg += "  NodeName:  --nodeName r1r1u25 \n"
			if not (options.reservationId):
				mesg += "  ReservationId:  --reservationId IDNUM(add nodes to an existing reservation)\n"

			mesg += "  Hostname:  --hostName mynode01\n"
			mesg += "  Domain:  --vlanIsolate vlan_num(default 999)\n"
			mesg += "  IP address:  --ipaddr 172.17.10.100\n"
			mesg += "  Notes:  --notes(optional)\n"
			sys.stderr.write(mesg)		
			exit()

		#  Reconfigure switchports
		memberMap = data.getDomainMembership(host['sys_id'])
		HwSwitch = HwDellSwitch
		hwswitch = HwSwitch(configs, host)
		for vlan, tag in memberMap.iteritems():
			hwswitch.addNodeToVlan(vlan, tag)
		#  Register node in DNS
		if options.hostName:
			#  Add cname
			cmd = "zoni --addCname %s %s" % (options.hostName, host['location'])
			subprocess.Popen(string.split(cmd))
			
		

	
		#data.allocateNode(options.reservationId, options.domain, host['sys_id'], options.vlanInfo, options.imageName, options.hostName, options.myNotes + " " + str(string.join(args[0:len(args)])))
		#data.allocateNode(options.reservationId, host['sys_id'], options.hostName,  vlanNum, options.ipAddr, options.myNotes)
		exit()

	#  Update allocation
	if (options.updateReservation):
		if not options.reservationId:
			mesg = "ERROR:  UpdateReservation requires the following arguments...\n"
			if not (options.reservationId):
				mesg += "  Reservation ID:  --reservationId RES\n"
			mesg += "  NodeName:  --nodeName r1r1u25 (optional)\n"
			mesg += "  Username:  --userName=username or --uid 1000 (optional)\n"
			mesg += "  Reservation Duration:  --reservationDuration YYYYMMDD or numdays (optional, default 15 days)\n"
			mesg += "  Vlan:  --vlanIsolate vlan_num(optional)\n"
			mesg += "  Notes:  --notes(optional)\n"
			sys.stderr.write(mesg)		
			exit()

		userId = None
		if options.uid or options.userName:
			#  Get the username from uid 
			userId = options.uid
			if not options.uid:
				userId = usermgt.getUserId(options.userName)

		data.updateReservation(options.reservationId, userId, options.reservationDuration, options.vlanIsolate, options.myNotes)

	#  Release node allocation
	if (options.releaseNode):
		if not options.nodeName: 
			mesg = "ERROR:  releaseNode requires the following arguments...\n"
			if not (options.nodeName):
				mesg += "  NodeName:  --nodeName r1r1u25 \n"

			sys.stderr.write(mesg)		
			exit()
		data.releaseNode(options.nodeName)
		
	#  Assign image to host
	if (options.assignImage):
		if not options.nodeName:
			usage = "Node not specified.  Please specify a node with --nodeName or -n"
			print usage
			exit()
		#  need to fix this later
		#if data.assignImagetoHost(host, options.assignImage):
			#print "ERROR"
			#exit()

		#  Update PXE 
		bootit = Pxe(configs, data, options.verbosity)
		bootit.setBootImage(host['mac_addr'], options.assignImage)
		#bootit.createPxeUpdateFile(data.getPxeImages())
		#bootit.updatePxe()
		
	
	#  Add image to database
	if (options.addImage):
		data.addImage(options.addImage)
	#  Delete PXE image 
	if (options.delImage):
		data.delImage(options.delImage)

	#  Domain interface
	if (options.showDomains):
		data.showDomains()
	if (options.addDomain):
		if len(args) > 2 and options.vlanInfo:
			data.addDomain(args[0], string.join(args[1:len(args)]), options.vlanInfo)
		else:
			mesg = "USAGE: %s --addDomain domainname \"domain desc\" --vlanInfo vlan:type,vlan:type\n" % (sys.argv[0])
			mesg += "Options\n\n  --vlanInfo 999:native,1000:untagged,1001:tagged\n"
			sys.stdout.write(mesg)
			exit()
	if (options.removeDomain):
		if len(args) > 0:
			data.removeDomain(args[0])
		else:
			mesg = "USAGE: %s --removeDomain domainname \n" % (sys.argv[0])
			sys.stdout.write(mesg)
			exit()

	if (options.showVlans):
		data.showVlans()
	#if (options.addVlan):
		#print len(args)
		#if len(args) > 0:
			#data.addVlan(args[0], string.join(args[1:len(args)]))
		#else:
			#mesg = "USAGE: %s --addVlan vlanNumber [VlanDesc]\n" % (sys.argv[0])
			#sys.stdout.write(mesg)
			#exit()
	#if (options.removeVlan):
		#if len(args) > 0:
			#data.removeVlan(args[0])
		#else:
			#mesg = "USAGE: %s --removeVlan VlanNumber\n" % (sys.argv[0])
			#sys.stdout.write(mesg)
			#exit()

	if (options.assignVlan):
		print len(args)
		if len(args) > 0:
			data.assignVlan(options.assignVlan, args[0], options.forcefully)
		else:
			mesg = "USAGE: %s --assignVlan vlannum DomainName\n" % (sys.argv[0])
			sys.stdout.write(mesg)
			exit()
		
	#  Admin Interface
	#  snmpwalk -v2c -c zoni-domain sw0-r1r1 .1.3.6.1.2.1.17.7.1.4.3.1.5    
	if (options.ADMIN):
			

		if not options.nodeName and not  options.createVlanId and not options.destroyVlanId and not options.switchPort and not options.interactiveSwitchConfig and not options.saveConfig:
			mesg = "\nERROR:  nodeName or switch not specified.  Please specify nodename with -n or --nodeName or --switchport\n"
			parser.print_help()
			sys.stderr.write(mesg)
			exit()

		#  We can specify port/switch combinations here
		if options.switchPort:
			host = data.getSwitchInfo(options.switchPort.split(":")[0])
			if len(options.switchPort.split(":")) > 1:
				host['hw_port'] = options.switchPort.split(":")[1]

			host['location'] = options.switchPort

		if options.interactiveSwitchConfig:
			host = data.getSwitchInfo(options.interactiveSwitchConfig)

		HwSwitch = HwDellSwitch
		hwswitch = HwSwitch(configs, host)
		if options.verbosity:
			hwswitch.setVerbose(True)

		if options.setPortMode:
			hwswitch.setPortMode(options.setPortMode)

		if options.saveConfig:
			hwswitch.saveConfig(options.saveConfig, data)
		if options.labelPort:
			mydesc = None
			if len(args) > 0:
				mydesc = " ".join(["%s" % i for i in args])
			hwswitch.labelPort(mydesc)
			
		if options.enableHostPort and (options.nodeName or options.switchPort):
			hwswitch.enableHostPort()
		if options.disableHostPort and (options.nodeName or options.switchPort):
			hwswitch.disableHostPort()
		#  Create a new vlan on all switches and add to db
		if options.createVlanId:
			print options.createVlanId
			hwswitch.createVlans(options.createVlanId, data.getAllSwitches(), data)
			data.addVlan(options.createVlanId, string.join(args[1:len(args)]))
		#  Remove vlan on all switches and remove from db
		if options.destroyVlanId:
			hwswitch.removeVlans(options.destroyVlanId, data.getAllSwitches(), data)
			data.removeVlan(options.destroyVlanId)

		if options.add2Vlan and (options.nodeName or options.switchPort):
			tag="untagged"
			vlan = options.add2Vlan
			if ":" in options.add2Vlan:
				print options.add2Vlan
				vlan = options.add2Vlan.split(":")[0]
				tag = options.add2Vlan.split(":")[1]

			hwswitch.addNodeToVlan(vlan, tag)
			data.addNodeToVlan(host['location'], vlan, tag)
			exit()

		if options.removeFromVlan and (options.nodeName or options.switchPort): 
			hwswitch.removeNodeFromVlan(options.removeFromVlan)
			data.removeNodeFromVlan(options.nodeName, options.removeFromVlan)
		if options.setNative and (options.nodeName or options.switchPort):
			hwswitch.setNativeVlan(options.setNative)
			data.addNodeToVlan(host['location'], options.setNative, "native")
		if options.restoreNative and options.nodeName:
			hwswitch.restoreNativeVlan()
		if options.removeAllVlans and (options.nodeName or options.switchPort):
			hwswitch.removeAllVlans()

		if options.sendSwitchCommand and (options.nodeName or options.switchPort):
			hwswitch.sendSwitchCommand(options.sendSwitchCommand)
		if options.interactiveSwitchConfig:
			hwswitch.interactiveSwitchConfig()
		if options.showSwitchConfig and (options.nodeName or options.switchPort):
			hwswitch.showInterfaceConfig()
		
	#  Register hardware
	if options.register: 

		supported_hardware = ['dellswitch', 'raritan']
		if len(args) < 3:
			mesg = "ERROR:  Expecting username and ip address of hardware to be registered\n"
			mesg += os.path.basename(sys.argv[0]) + " --register HARDWARE username ipaddr\n"
			mesg += "Supported hardware " + str(supported_hardware) + "\n"
			sys.stderr.write(mesg)
		else:
			if string.lower(args[0]) == "dellswitch":
				HwSwitch = HwDellSwitch
				hw = HwSwitch(configs)
			elif string.lower(args[0]) == "raritan":
				hw = raritanDominionPx(configs)
			else:
				mesg = "Undefined hardware type\nSupported Hardware" + str(supported_hardware) + "\n"
				sys.stderr.write(mesg)
				exit()
				
			if options.verbosity:
				hw.setVerbose(True)

			print args
			password = getpass.getpass()
			data = hw.registerToZoni(args[1], password, args[2])

			#  Register to DB
			#data.registerHardware(data)
			
	#  Zoni Helper
	if options.addDns or options.removeDns or options.addDhcp or options.removeDhcp or options.addCname or options.removeCname:
		if options.addDns:
			thisone = "--addDns"
		if options.removeDns:
			thisone = "--removeDns"
		if options.removeDhcp:
			thisone = "--removeDhcp"
		if options.addDhcp:
			thisone = "--addDhcp"
		if options.addCname:
			thisone = "--addCname"
		if options.removeCname:
			thisone = "--removeCname"

		if options.addDns:
			if len(args) < 2:
				mesg = "ERROR:  Incorrect number of arguments\n"
				mesg += "Example:  " + os.path.basename(sys.argv[0]) + " " + thisone + " hostname IP_Address\n"
				print mesg
				exit()
			
			hostName = args[0]
			ip = args[1]
			if validIp(ip):
				mesg = "Adding DNS entry: %s (%s) " % (hostName, ip)
				sys.stdout.write(mesg)
				dhcpdns = DhcpDns(configs, verbose=options.verbosity)
				dhcpdns.addDns(hostName, ip)
				try:
					socket.gethostbyname(hostName)
					sys.stdout.write("[Success]\n")
				except Exception:
					sys.stdout.write("[Fail]\n")
			else:
				mesg = "ERROR:  Malformed IP Address\n"
				mesg += "Use the dotted quad notation, e.g. 10.0.0.10\n"
				print mesg
				exit()

		if options.removeDns or options.removeDhcp or options.removeCname:
			if len(args) < 1:
				mesg = "ERROR:  Incorrect number of arguments\n"
				mesg += "Example:  " + os.path.basename(sys.argv[0]) + " " + thisone + " hostname\n"
				sys.stdout.write(mesg)
				exit()
			hostName = args[0]
			dhcpdns = DhcpDns(configs, verbose=options.verbosity)
			if options.removeDns:	
				mesg = "Removing DNS entry: %s " % (hostName)
				sys.stdout.write(mesg)
				dhcpdns.removeDns(hostName)
				try:
					socket.gethostbyname(hostName)
					sys.stdout.write("[Fail]\n")
				except Exception:
					sys.stdout.write("[Success]\n")
			if options.removeDhcp:	
				dhcpdns.removeDhcp(hostName)
			if options.removeCname:	
				mesg = "Removing DNS CNAME entry: %s  " % (hostName)
				sys.stdout.write(mesg)
				dhcpdns.removeCname(hostName)
				if dhcpdns.error:
					mesg = "[FAIL]  " + str(dhcpdns.error) + "\n"
					sys.stdout.write(mesg)
				else:
					mesg = "[SUCCESS]" + "\n"
					sys.stdout.write(mesg)
					

		if options.addDhcp:
			if len(args) < 3:
				mesg = "ERROR:  Incorrect number of arguments\n"
				mesg += "Example:  " + os.path.basename(sys.argv[0]) + " " + thisone + " hostname IP_Address Mac_Address\n"
				print mesg
				exit()
			
			hostName = args[0]
			ip = args[1]
			mac = args[2]
			if validIp(ip) and validMac(mac):
				dhcpdns = DhcpDns(configs, verbose=options.verbosity)
				dhcpdns.addDhcp(hostName, ip, mac)
				if dhcpdns.error:
					mesg = "ERROR:  Add DHCP Error " + dhcpdns.error + "\n"
			else:
				if not validIp(ip):
					mesg = "ERROR:  Malformed IP Address\n"
					mesg += "Use the dotted quad notation, e.g. 10.0.0.10\n"
					print mesg
					exit()
				if not validMac(mac):
					mesg = "ERROR:  Malformed MAC Address\n"
					mesg += "Example 10:20:30:40:50:60\n"
					print mesg
					exit()
		
		if options.addCname:
			if len(args) < 2:
				mesg = "ERROR:  Incorrect number of arguments\n"
				mesg += "Example: %s %s cname existing_name" % (os.path.basename(sys.argv[0]), thisone) 
				print mesg
				exit()
			hostName = args[1]
			cname = args[0]
			mesg = "Adding DNS CNAME entry: %s -> %s  " % (cname, hostName)
			sys.stdout.write(mesg)
			dhcpdns = DhcpDns(configs, verbose=options.verbosity)
			dhcpdns.addCname(cname, hostName)
			if dhcpdns.error: 
				mesg = "[FAIL]  \n %s\n" % str(dhcpdns.error)
				sys.stdout.write(mesg) 
			else: 
				mesg = "[SUCCESS]\n"
				sys.stdout.write(mesg) 

	## Extensions from MIMOS - functions are defined in m_extensions.py
	if ( options.addRole and options.nodeName ) or ( options.removeRole and options.nodeName ):
		if options.addRole:
			mimos.assignRoletoHost(host,options.addRole)
			mimos.addRoletoNode(configs,host,options.nodeName,options.addRole)
		if options.removeRole:
			mimos.unassignRolefromHost(host)
			mimos.removeRolefromNode(configs,host,options.nodeName)
	if ( options.addRole and not options.nodeName ) or ( options.removeRole and not options.nodeName ):
		mesg = "Roles: Missing Parameter(s)!"
		log.error(mesg)
	if options.showRoleMap:
		mimos.showRoletoHost(configs)
	if options.showKernelInfo:
		mimos.showKernelInfo()
	if options.showInitrdInfo:
		mimos.showInitrdInfo()
	if options.registerKernelInitrd:
		mimos.registerKernelInitrd(configs,options.registerKernelInitrd)
	if options.getKernelInitrdID:
		mimos.getKernelInitrdID(options.getKernelInitrdID)
	if options.getConfig:
		mimos.getConfig(configs,options.getConfig)

if __name__ == "__main__":
	main()
