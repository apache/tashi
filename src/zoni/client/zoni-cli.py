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

import os
import sys
import optparse


#from zoni import *
#from zoni.data.resourcequerysql import ResourceQuerySql
import zoni
from zoni.data.resourcequerysql import *

from zoni.data.usermanagementinterface import UserManagementInterface
from zoni.data.usermanagementinterface import UserManagementInterface

from zoni.bootstrap.bootstrapinterface import BootStrapInterface
from zoni.bootstrap.pxe import Pxe

from zoni.hardware.systemmanagementinterface import SystemManagementInterface
from zoni.hardware.ipmi import Ipmi
from zoni.hardware.hwswitchinterface import HwSwitchInterface
from zoni.hardware.hwswitch import HwDellSwitch
from zoni.hardware.raritanpdu import raritanDominionPx
from zoni.hardware.delldrac import dellDrac

from zoni.extra.util import * 
from zoni.version import *

#import zoni.data.usermanagement 
#from usermanagement import UserManagement

def parseTable():
	pass

def main():
	"""  Main """
	ver = version.split(" ")[0]
	rev = revision

	configFile = getConfig()
	#logit(configFile['logFile'], "Starting Zoni client")
	#logit(configFile['logFile'], "Loading config file")

	parser = optparse.OptionParser(usage="%prog [-n] [-u] [--uid] [-v]", version="%prog " + ver + " " + rev)
	parser.add_option("-n", "--nodeName", dest="nodeName", help="Specify node")
	parser.add_option("--switchPort", "--switchport", dest="switchPort", help="Specify switchport switchname:portnum")
	parser.add_option("-u", "--userName", dest="userName", help="Specify user name")
	parser.add_option("--uid", dest="uid", help="Specify user id")
	parser.add_option("-v", "--verbose", dest="verbosity", help="Be verbose", action="store_true", default=False)


	#  Hardware controller
	group = optparse.OptionGroup(parser, "Hardware control", "Options to control power on nodes")
	group.add_option("--hw", dest="hardwareType", help="Make hardware call to ipmi|drac|pdu")
	group.add_option("--powerStatus", "--powerstatus", dest="POWERSTATUS", help="Get power status on node", action="store_true", default=False)
	group.add_option("--reboot", "--reboot", dest="REBOOTNODE", help="Reboot node (Soft)", action="store_true", default=False)
	group.add_option("--powerCycle", "--powercycle", dest="POWERCYCLE", help="Power Cycle (Hard)", action="store_true", default=False)
	group.add_option("--powerOff", "--poweroff", dest="POWEROFF", help="Power off node", action="store_true", default=False)
	group.add_option("--powerOn", "--poweron", dest="POWERON", help="Power on node", action="store_true", default=False)
	group.add_option("--powerReset", "--powerreset", dest="POWERRESET", help="Power reset node", action="store_true", default=False)
	group.add_option("--console", dest="CONSOLE", help="Console mode", action="store_true", default=False)
	parser.add_option_group(group)

	#  Query Interface
	group = optparse.OptionGroup(parser, "Query Interface", "Query current systems and allocations")
	group.add_option("-R", "--showReservation", "--showreservation", dest="showReservation", help="Show current node reservations", action="store_true", default=False)
	group.add_option("-A", "--showAllocation", "--showallocation", dest="showAllocation", help="Show current node allocation", action="store_true", default=False)
	group.add_option("-s", "--showResources", dest="showResources", help="Show available resources to choose from", action="store_true", default=False)
	group.add_option("-p", "--procs", dest="numProcs", help="Set number of processors" )
	group.add_option("-c", "--clock", dest="clockSpeed", help="Processor clock" )
	group.add_option("--memory", dest="numMemory", help="Amount of memory (Bytes)" )
	group.add_option("-f", "--cpuflags", dest="cpuFlags", help="CPU flags" )
	group.add_option("--cores", dest="numCores", help="Number of Cores" )
	group.add_option("-i", "--showPxeImages", "--showpxeimages", dest="showPxeImages", help="Show available PXE images to choose from", action="store_true", default=False)
	group.add_option("-m", "--showPxeImageMap", "--showpxeimagemap", dest="showPxeImageMap", help="Show PXE images host mapping", action="store_true", default=False)
	group.add_option("--showArchive", "--showarchive", dest="showArchive", help="Show allocation archive", action="store_true", default=False)
	parser.add_option_group(group)
	#parser.add_option("-p", "--printResources", dest="printResources", help="Print available resources to choose from", action="store_true", default=False)

	#  Admin Interface
	group = optparse.OptionGroup(parser, "Admin Interface", "Administration Interface:")
	group.add_option("--admin", dest="ADMIN", help="Enter Admin mode", action="store_true", default=False)
	group.add_option("--addPxeImage", "--addpxeimage", dest="imageName", help="Add PXE image to database", action="store_true", default=False)
	group.add_option("--enableHostPort", "--enablehostport", dest="enableHostPort", help="Enable a switch port", action="store_true", default=False)
	group.add_option("--disableHostPort", "--disablehostport", dest="disableHostPort", help="Disable a switch port", action="store_true", default=False)
	group.add_option("--removeVlan", "--removevlan", dest="removeVlanId", help="Remove vlan from all switches")
	group.add_option("--createVlan", "--createvlan", dest="createVlanId", help="Create a vlan on all switches")
	group.add_option("--addNodeToVlan", "--addnodetovlan", dest="add2Vlan", help="Add node to a vlan")
	group.add_option("--removeNodeFromVlan", "--removenodefromvlan", dest="removeFromVlan", help="Remove node from a vlan")
	group.add_option("--setNativeVlan", "--setnativevlan", dest="setNative", help="Configure native vlan")
	group.add_option("--restoreNativeVlan", "--restorenativevlan", dest="restoreNative", help="Restore native vlan", action="store_true", default=False)
	group.add_option("--removeAllVlans", "--removeallvlans", dest="removeAllVlans", help="Removes all vlans from a switchport", action="store_true", default=False)
	group.add_option("--sendSwitchCommand", "--sendswitchcommand", dest="sendSwitchCommand", help="Send Raw Switch Command, VERY DANGEROUS.  config;interface switchport ethernet g14;etc")
	group.add_option("--interactiveSwitchConfig", "--interactiveswitchconfig", dest="interactiveSwitchConfig", help="Interactively configure a switch.  switchhname")
	group.add_option("--showSwitchConfig", "--showswitchconfig", dest="showSwitchConfig", help="Show switch config for node", action="store_true", default=False)
	parser.add_option_group(group)

	#  Switch
	#group = optparse.OptionGroup(parser, "Switch Interface", "Switch Interface:")
	#group.add_option("--rawswitch", dest="RAWSWITCH", help="Enter RAW Switch Admin mode", action="store_true", default=False)
	#group.add_option("--enablePort", "--enableport", dest="enablePort", help="Enable a port on the switch")
	#group.add_option("--disablePort", "--disableport", dest="disablePort", help="Disable a port on the switch")
	#group.add_option("--addVlanToTrunks", "--addvlantotrunks", dest="addVlanToTrunks", help="")
	

	#  Allocation Interface
	group = optparse.OptionGroup(parser, "Allocation Interface", "Change current systems allocations:")
	#group.add_option("-a", "--allocateResources", dest="allocateResources", help="Allocate resource", action="store_true", default=False)
	group.add_option("--addImage", "--addimage", dest="addImage", help="Add image to Zoni - amd64-image:dist:dist_ver")
	group.add_option("--delImage", "--delimage", dest="delImage", help="Delete PXE image")
	group.add_option("--assignImage", "--assignimage", dest="assignImage", help="Assign image to resource")

	group.add_option("--allocateNode", "--allocatenode", dest="allocateNode", help="Assign node to a user", action="store_true", default=False)
	group.add_option("--allocationNotes", "--allocationnotes", dest="allocationNotes", help="Description of allocation")
	group.add_option("--vlanIsolate", "--vlanisolate", dest="vlanIsolate", help="Specify vlan for network isolation")
	group.add_option("--hostName", "--hostname", dest="hostName", help="Specify hostname for node")
	group.add_option("--ipaddr", dest="ipAddr", help="Specify ip address for node")

	group.add_option("--releaseNode", "--releasenode", dest="releaseNode", help="Release current node allocation", action="store_true", default=False)
	group.add_option("--reservationDuration", "--reservationduration", dest="reservationDuration", help="Specify duration of node reservation - YYYYMMDD format")
	group.add_option("--reservationId", "--reservationid", dest="reservationId", help="Reservation ID")
	group.add_option("--reservationNotes", "--reservationnotes", dest="reservationNotes", help="Description of reservation")
	group.add_option("--addReservation", "--addreservation", dest="addReservation", help="Add a Reservation", action="store_true", default=False)
	group.add_option("--updateReservation", "--updatereservation", dest="updateReservation", help="Update Reservation", action="store_true", default=False)
	group.add_option("--delReservation", "--delreservation", dest="delReservation", help="Delete Reservation")
	#group.add_option("-a", "--allocateResources", dest="allocateResources", help="Allocate resource", action="store_true", default=False)
	group.add_option("--rgasstest", dest="rgasstest", help="Debug testing function", action="store_true", default=False)
	parser.add_option_group(group)

	(options, args) = parser.parse_args()

	cmdargs = {}

	#  setup db connection
	query = zoni.data.resourcequerysql.ResourceQuerySql(configFile, options.verbosity)

	#  Get host info
	host=None
	if options.nodeName:
		host = query.getHostInfo(options.nodeName)
		#print host
	

	#  Hardware control
	if options.hardwareType:

		if (options.hardwareType) and options.hardwareType not in configFile['hardware_control']:
			mesg = "Non support hardware type specified\n"
			mesg += "Supported types:\n"
			mesg += str(configFile['hardware_control'])
			mesg += "\n\n"
			sys.stdout.write(mesg)
			exit()

		if (options.hardwareType) and options.nodeName:
			#host = query.getHostInfo(options.nodeName)
			if options.hardwareType == "ipmi":
				hw = Ipmi(options.nodeName, host["ipmi_user"], host["ipmi_password"])

			if options.hardwareType == "pdu":
				hw = raritanDominionPx(host)

			if options.hardwareType == "drac":
				#  Check if node has drac card
				if "drac_name" in host:
					hw = dellDrac(host)
				else:
					mesg = "Host (" + options.nodeName + ") does not have a DRAC card!!\n"
					sys.stdout.write(mesg)
					exit(1)

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
			hw.getPowerStatus()


		if (options.hardwareType) and not options.nodeName:
			mesg = "\nMISSSING OPTION:  Node name required -n or --nodeName\n"
			parser.print_help();
			sys.stderr.write(mesg)
			exit()

	if (options.REBOOTNODE or options.POWERCYCLE  or options.POWEROFF or \
		options.POWERON or options.POWERSTATUS or options.CONSOLE or \
		options.POWERRESET) and not options.hardwareType:
		parser.print_help()
		usage = "\nMISSING OPTION: When specifying hardware parameters, you need the --hw option\n"
		print usage
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
		cmdargs["node_id"] = options.nodeName

	if 	(options.numCores or options.clockSpeed or options.numMemory or options.numProcs or options.cpuFlags) and not options.showResources:
			usage = "MISSING OPTION: When specifying hardware parameters, you need the -s or --showResources switch"
			print usage
			parser.print_help()	
			exit()

	#  Show current allocations 
	if (options.showAllocation):
		if options.uid:
			print "set"
			nameorid = int(options.uid)
		else: 
			nameorid = options.userName

		query.showAllocation(nameorid)
		exit()

	#  Show current reservation
	if (options.showReservation):
		if options.uid:
			print "set"
			nameorid = int(options.uid)
		else: 
			nameorid = options.userName

		query.showReservation(nameorid)
		exit()

	#  Show allocation Archive
	if (options.showArchive):
		query.showArchive()

	#  Print all Resources
	if (options.showResources):
		query.showResources(cmdargs)

	#  Show PXE images
	if (options.showPxeImages):
		query.showPxeImages()

	#  Show machine to PXE image mapping
	if (options.showPxeImageMap):
		query.showPxeImagesToSystemMap(cmdargs)
		exit()

	if (len(sys.argv) == 1):
		parser.print_help()
		exit()


	#  Get the host object
	#hostObj = getHostObject()
	#if (options.allocateResources) and options.nodeName:
		#query.getHostInfo(options.nodeName)
		
		#exit()

	#  Delete reservation
	if (options.delReservation):
		query.removeReservation(options.delReservation)
		exit()

	#  Specify usermanagement, ldap or files
	usermgt = usermanagement.ldap()


	if (options.rgasstest):
		#pdu = raritanDominionPx(host)
		#print pdu
		#bootit = pxe.Pxe(configFile, options.verbosity)
		#bootit.createPxeUpdateFile(query.getPxeImages())
		#bootit.updatePxe()
		#print "host is ", host
		#drac = dellDrac("drac-r2r1c3", 1)
		#drac.getPowerStatus()
		#drac.powerOff()
		#drac.powerOn()
		#drac.powerCycle()
		#drac.powerReset()
		#drac.getPowerStatus()
		print "host is ", host
		pdu = raritanDominionPx(host)
		print "pdu", pdu
		pdu.getPowerStatus()
		exit()

	#  Create a reservation for a user
	if (options.addReservation):
		if not (options.userName or options.uid):
			mesg = "ERROR:  AddReservation requires the following arguments...\n"
			if not (options.userName or options.uid):
				mesg += "  Username:  --userName=username or --uid 1000\n"

			mesg += "  Reservation Duration:  --reservationDuration YYYYMMDD or numdays(optional, default 15 days)\n"
			#mesg += "  ReservationId:  --reservationId IDNUM(optional, you want this if you want to add nodes to an existing reservation)\n"
			mesg += "  Notes:  --reservationNotes(optional)\n"
			sys.stderr.write(mesg)		
			exit()

		userId = options.uid
		if not options.uid:
			userId = usermgt.getUserId(options.userName)

		reservationId = query.addReservation(userId, options.reservationDuration, options.reservationNotes)


	#  Allocate node to user
	if (options.allocateNode):
		vlanNum = 999
		if (options.vlanIsolate):
			vlanNum = options.vlanIsolate
		
		if not (options.reservationId) or not options.nodeName: 
			mesg = "ERROR:  AllocateNode requires the following arguments...\n"
			if not (options.nodeName):
				mesg += "  NodeName:  --nodeName r1r1u25 \n"
			if not (options.reservationId):
				mesg += "  ReservationId:  --reservationId IDNUM(add nodes to an existing reservation)\n"

			mesg += "  Hostname:  --hostName mynode01\n"
			mesg += "  Domain:  --vlanIsolate vlan_num(default 999)\n"
			mesg += "  IP address:  --ipaddr 172.17.10.100\n"
			mesg += "  Notes:  --allocationNotes(optional)\n"
			sys.stderr.write(mesg)		
			exit()

		query.allocateNode(options.reservationId, host['node_id'], options.hostName,  vlanNum, options.ipAddr, options.allocationNotes)
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
			mesg += "  Notes:  --reservationNotes(optional)\n"
			sys.stderr.write(mesg)		
			exit()

		userId = None
		if options.uid and options.userName:
			#  Get the username from uid 
			userId = options.uid
			if not options.uid:
				userId = usermgt.getUserId(options.userName)

		print options.reservationId, userId, options.reservationDuration, options.vlanIsolate, options.reservationNotes
		query.updateReservation(options.reservationId, userId, options.reservationDuration, options.vlanIsolate, options.reservationNotes)

	#  Release node allocation
	if (options.releaseNode):
		if not options.nodeName: 
			mesg = "ERROR:  releaseNode requires the following arguments...\n"
			if not (options.nodeName):
				mesg += "  NodeName:  --nodeName r1r1u25 \n"

			sys.stderr.write(mesg)		
			exit()
		query.releaseNode(options.nodeName)
		
	#  Assign image to host
	if (options.assignImage):
		if not options.nodeName:
			usage = "Node not specified.  Please specify a node with --nodeName or -n"
			print usage
			exit()
		if query.assignImagetoHost(host, options.assignImage):
			print "ERROR"
			exit()

		#  Update PXE 
		bootit = pxe.Pxe(configFile, options.verbosity)
		bootit.createPxeUpdateFile(query.getPxeImages())
		bootit.updatePxe()
		
	
	#  Add image to database
	if (options.addImage):
		query.addImage(options.addImage)
	#  Delete PXE image 
	if (options.delImage):
		query.delImage(options.delImage)

	#  Admin Interface
	#  snmpwalk -v2c -c zoni-domain sw0-r1r1 .1.3.6.1.2.1.17.7.1.4.3.1.5    
	if (options.ADMIN):

		if not options.nodeName and not  options.createVlanId and not options.removeVlanId and not options.switchPort and not options.interactiveSwitchConfig:
			mesg = "\nERROR:  nodeName or switch not specified.  Please specify nodename with -n or --nodeName or --switchport\n"
			parser.print_help()
			sys.stderr.write(mesg)
			exit()

		#  We can specify port/switch combinations here
		if options.switchPort:
			host = query.getSwitchInfo(options.switchPort.split(":")[0])
			if len(options.switchPort.split(":")) > 1:
				host['hw_port'] = options.switchPort.split(":")[1]

			host['location'] = options.switchPort

		if options.interactiveSwitchConfig:
			host = query.getSwitchInfo(options.interactiveSwitchConfig)

		HwSwitch = HwDellSwitch
		hwswitch = HwSwitch(configFile, host)
		if options.verbosity:
			hwswitch.setVerbose(True)

		#print "create vlan", options.createVlanId
		if options.enableHostPort and options.nodeName:
			hwswitch.enableHostPort()
		if options.disableHostPort and (options.nodeName or options.switchPort):
			hwswitch.disableHostPort()
		if options.createVlanId:
			hwswitch.createVlans(options.createVlanId, query.getAllSwitches(), query)
		if options.removeVlanId:
			hwswitch.removeVlans(options.removeVlanId, query.getAllSwitches(), query)

		if options.add2Vlan and (options.nodeName or options.switchPort):
			hwswitch.addNodeToVlan(options.add2Vlan)

		if options.removeFromVlan and options.nodeName:
			hwswitch.removeNodeFromVlan(options.removeFromVlan)
		if options.setNative and (options.nodeName or options.switchPort):
			hwswitch.setNativeVlan(options.setNative)
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



if __name__ == "__main__":
	main()
