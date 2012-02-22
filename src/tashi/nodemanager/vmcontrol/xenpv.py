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

import os
import os.path
import cPickle
import subprocess		# FIXME: should switch os.system to this
import time 
import threading
import logging
import socket

from vmcontrolinterface import VmControlInterface
from tashi.rpycservices.rpyctypes import Errors, InstanceState, TashiException
from tashi.rpycservices.rpyctypes import Instance, Host
from tashi import boolean, convertExceptions, ConnectionManager, version
from tashi.util import broken

import tashi.parallel
from tashi.parallel import synchronized, synchronizedmethod

log = logging.getLogger(__file__)

# FIXME: these should throw errors on failure
def domIdToName(domid):
# XXXpipe: get domain name from id
	f = os.popen("/usr/sbin/xm domname %i"%domid)
	name = f.readline().strip()
	f.close()
	return name

def domNameToId(domname):
# XXXpipe: get domain id from name
	f = os.popen("/usr/sbin/xm domid %s"%domname)
	name = f.readline().strip()
	f.close()
	return int(name)

def nameToId(domname, prefix='tashi'):
	prefix = prefix + '-'
	if domname[0:(len(prefix))] != prefix:
		return None
	try:
		id = int(domname[len(prefix):])
	except:
		return None
	return id


# Try to do a listVms call using info from xend
def listVms(prefix='tashi'):
	fields =['name', 'vmId', 'memory', 'cores', 'state', 'time']
	xmList = subprocess.Popen('xm list', shell=True, stdout=subprocess.PIPE)
	# skip the first line, it's just a header
	xmList.stdout.readline()
	r = {}
	for line in xmList.stdout.readlines():
		line = line.split()
		vminfo = {}
		instance = Instance()
		if len(line) != len(fields):
			# FIXME: log message
			print 'WARNING: cannot parse line'
			continue
		for i in range(len(line)):
			vminfo[fields[i]] = line[i]
		# if the name begins with our prefix, get the id,
		# otherwise skip this record
		id = nameToId(vminfo['name'], prefix)
		if id == None:
			continue

		# fill in the instance object
		instance.id = int(id)
		instance.vmId = int(vminfo['vmId'])
		instance.state = InstanceState.Running
		if(vminfo['state'][2] !='-'):
			instance.state = InstanceState.Paused
		instance.memory = int(vminfo['memory'])
		instance.cores = int(vminfo['cores'])
		instance.disks = []
		r[instance.vmId] = instance
	return r





class XenPV(VmControlInterface, threading.Thread):
	def __init__(self, config, dfs, cm):
		threading.Thread.__init__(self)
		self.config = config
		self.dfs = dfs
		self.cm = cm

		self.vmNamePrefix = self.config.get("XenPV", "vmNamePrefix")
		self.transientDir = self.config.get('XenPV', 'transientDir')
		self.defaultVmType = self.config.get('XenPV', 'defaultVmType') 
		self.disktype = self.config.get('XenPV', 'defaultDiskType')
		# XXXstroucki default disktype vhd?
		self.newvms = listVms(self.vmNamePrefix)
		self.hostId = -1
		self.sleeptime = 5
		self.setDaemon(True)
		self.start()

	# invoked every (self.sleeptime) seconds
	@synchronizedmethod
	def cron(self):
#		print 'xenpv cron woke up'
		vmlist = listVms(self.vmNamePrefix)
		# If we are supposed to be managing a VM that is not
		# in the list, tell the CM

		# FIXME: a single set operation should do this.  How
		# do you use sets in python?
		for vmId in self.newvms.keys():
			if not vmlist.has_key(vmId):
				a = self.newvms.pop(vmId)
				# If the vm had transient disks, delete them
				for i in range(len(a.disks)):
					if a.disks[i].persistent == False:
						diskname = self.transientDisk(a.id, i, self.disktype)
						try:
							os.unlink(diskname)
						except:
							print 'WARNING could not delete transient disk %s' % diskname
				self.nm.vmStateChange(a.vmId, a.state, InstanceState.Exited)
		for vmId in vmlist.keys():
			if not self.newvms.has_key(vmId):
				print 'WARNING: found vm that should be managed, but is not'
				# FIXME: log that
			

	def run(self):
		while(True):
			time.sleep(self.sleeptime)
			self.cron()
########################################
# This is an ugly function, but the multi-line string literal makes it
# a lot easier
########################################
	def createXenConfig(self, vmName, 
	                    image, macAddr, netID, memory, cores, hints, id):
		bootstr = None
		rootconfig = None
		diskconfig = None
		netconfig = None
		memconfig = None
		cpuconfig = None
		extraconfig = None

		fn = os.path.join("/tmp", vmName)
		vmType = hints.get('vmtype', self.defaultVmType)
		print 'starting vm with type: ', vmType

                disk0 = 'tap:%s' % self.disktype
		diskU = 'xvda1'

		try:
			bridgeformat = self.config.get('XenPV', 'defaultBridgeFormat')
		except:
			bridgeformat = 'br%s'

		bridge = bridgeformat % netID


		if vmType == 'pvgrub':
			# FIXME: untested, requires Xen 3.3
			bootstr = '''
kernel = '/usr/lib/xen-default/boot/pv-grub-x86_64.gz'
extra = '(hd0,0)/grub/menu.lst'
'''
	
		elif vmType == 'pygrub':
			bootstr = '''
bootloader="/usr/lib/xen-default/bin/pygrub"
'''
	
		elif vmType == 'kernel':
			kernel = hints.get('kernel', None)
			ramdisk = hints.get('ramdisk', None)
			if kernel == None:
				try:
					kernel = self.config.get('XenPV', 'defaultKernel')
				except:
					raise Exception, "vmtype=kernel requires kernel= argument"
			if ramdisk == None:
				try:
					ramdisk = self.config.get('XenPV', 'defaultRamdisk')
					ramdisk = "ramdisk = \"%s\""%ramdisk
				except:
					ramdisk = ''
			bootstr = '''
kernel = "%s"
%s     # ramdisk string is full command
'''%(kernel,
     ramdisk)

		elif vmType == 'hvm':
			disk0 = 'tap:%s' % self.disktype
			diskU = 'hda1'


			bootstr = '''
import os, re
arch = os.uname()[4]
if re.search('63', arch):
	arch_libdir = 'lib64'
else:
	arch_libdir = 'lib'
kernel = '/usr/lib/xen-default/boot/hvmloader'
builder = 'hvm'

device_model='/usr/lib/xen-default/bin/qemu-dm'

sdl=0
vnc=1
vnclisten='0.0.0.0'
vncdisplay=%i
vncpasswd=''
stdvga=0
serial='pty'
usbdevice='tablet'

shadow_memory=8
'''
			rootconfig = '''
root='/dev/%s ro'
'''%(diskU)
			diskconfig = '''
disk=['%s:%s,ioemu:%s,w']
'''%(disk0, image, diskU)
			netconfig = '''
vif = [ 'type=ioemu,bridge=%s,mac=%s' ]
'''%(bridge, macAddr)

		else:
			raise Exception, "Unknown vmType in hints: %s"%vmType
		if rootconfig is None:
			rootconfig = '''
root ='/dev/%s ro'
'''%(diskU)

		if diskconfig is None:
			diskconfig = '''
disk = ['%s:%s,%s,w']
'''%(disk0, image, diskU)

		if netconfig is None:
			netconfig = '''
vif = [ 'bridge=%s,mac=%s' ]
'''%(bridge, macAddr)

		if memconfig is None:
			memconfig = '''
memory=%i
'''%(memory)

		if cpuconfig is None:
			cpuconfig = '''
vcpus=%i
'''%(cores)

		if extraconfig is None:
			extraconfig = '''
extra='xencons=tty'
'''


#build the configuration file
#(bootloader, (kernel, extra), (kernel, ramdisk)), disk, vif, memory, vcpus, root, extra
		f = open(fn, "w")
		f.write(bootstr)
		f.write(diskconfig)
		f.write(netconfig)
		f.write(memconfig)
		f.write(cpuconfig)
# is root necessary? Only when using kernel directly
		f.write(rootconfig)
		f.write(extraconfig)
		f.close()
		return fn
	def deleteXenConfig(self, vmName):
		pass
#		os.unlink(os.path.join("/tmp", vmName))
########################################

	def vmName(self, instanceId):
		return "%s-%i"%(self.vmNamePrefix, int(instanceId))

	def transientDisk(self, instanceId, disknum, disktype):

		newdisk = os.path.join(self.transientDir,
				       'tashi-%i-%i.%s' %(instanceId, disknum, disktype))
		return newdisk
		

	@synchronizedmethod
	def instantiateVm(self, instance):

                try:
                   disktype = self.config.get('XenPV', 'defaultDiskType')
                except:
                   disktype = 'vhd'

		# FIXME: this is NOT the right way to get out hostId
		self.hostId = instance.hostId

		if (len(instance.disks) != 1):
			raise NotImplementedError
		if (len(instance.nics) != 1):
			raise NotImplementedError

		name = self.vmName(instance.id)

		for i in range(len(instance.disks)):
			imageLocal = self.dfs.getLocalHandle(instance.disks[i].uri)
			instance.disks[i].local = imageLocal
			if instance.disks[i].persistent == False:
				newdisk = self.transientDisk(instance.id, i, disktype)

				if disktype == 'qcow':
					cmd = '/usr/lib/xen-default/bin/qcow-create 0 %s %s' % (newdisk, imageLocal)
				elif disktype == 'vhd':
					cmd = '/usr/lib/xen-default/bin/vhd-util snapshot -n %s -p %s' % (newdisk, imageLocal)
				else:
					raise Exception, "Unknown disktype in configuration: %s"%disktype

				print 'creating new disk with "%s"' % cmd
				os.system(cmd)
				instance.disks[i].local = newdisk


		fn = self.createXenConfig(name, 
					  instance.disks[0].local, 
					  instance.nics[0].mac, 
					  instance.nics[0].network,
					  instance.memory,
					  instance.cores,
					  instance.hints,
					  instance.id)
		cmd = "/usr/sbin/xm create %s"%fn
		r = os.system(cmd)
#		self.deleteXenConfig(name)
		if r != 0:
			print 'WARNING: "%s" returned %i' % ( cmd, r)
			raise Exception, 'WARNING: "%s" returned %i' % ( cmd, r)
			# FIXME: log/handle error
		vmId = domNameToId(name)
		self.newvms[vmId] = instance
		instance.vmId = vmId
		instance.state = InstanceState.Running
		return vmId
		
	
	# for susp/res we want the xen save/restore commands, not
	# suspend/resume.  save/restore allow you to specify the state
	# file, suspend/resume do not.
	@broken
	@synchronizedmethod
	def suspendVm(self, vmId, target, suspendCookie=None):
		# FIXME: don't use hardcoded /tmp for temporary data.
		# Get tmp location from config
		infofile = target + ".info"
		target = target + ".dat"
		tmpfile = os.path.join("/tmp", target)

		# FIXME: these files shouldn't go in the root of the
		# dfs
		instance = self.newvms[vmId]
		instance.suspendCookie = suspendCookie
		infof = self.dfs.open(infofile, "w")
		name = domIdToName(vmId)
		cPickle.dump(instance, infof)
		infof.close()
		

		# FIXME: handle errors
		cmd = "/usr/sbin/xm save %i %s"%(vmId, tmpfile)
		r = os.system(cmd)
		if r !=0 :
			print "xm save failed!"
			raise Exception,  "replace this with a real exception!"
		r = self.dfs.copyTo(tmpfile, target)
		self.newvms.pop(vmId)
		os.unlink(tmpfile)
		return vmId
	
	@broken
	@synchronizedmethod
	def resumeVm(self, source):
		infofile = source + ".info"
		source = source + ".dat"
		tmpfile = os.path.join("/tmp", source)
		# FIXME: errors
		infof = self.dfs.open(infofile, "r")
		instance = cPickle.load(infof)
		infof.close
		self.dfs.unlink(infofile)

		self.dfs.copyFrom(source, tmpfile)
		r = os.system("/usr/sbin/xm restore %s"%(tmpfile))
		os.unlink(tmpfile)
		
		# FIXME: if the vmName function changes, suspended vms will become invalid
		vmId = domNameToId(self.vmName(instance.id))
		instance.vmId = vmId
		self.newvms[vmId] = instance
		return vmId, instance.suspendCookie
		
	@synchronizedmethod
	def prepReceiveVm(self, instance, source):
		return cPickle.dumps(instance)
	@synchronizedmethod
	def migrateVm(self, vmId, target, transportCookie):
		cmd = "/usr/sbin/xm migrate -l %i %s"%(vmId, target)
		r = os.system(cmd)
		if r != 0:
			# FIXME: throw exception
			print "migrate failed for VM %i"%vmId
			raise Exception,  "migrate failed for VM %i"%vmId
		self.newvms.pop(vmId)
		return vmId
	@synchronizedmethod
	def receiveVm(self, transportCookie):
		instance = cPickle.loads(transportCookie)
		vmId = domNameToId(self.vmName(instance.id))
		print 'received VM, vmId=%i\n'%vmId
		self.newvms[vmId] = instance
		return vmId

	
	@synchronizedmethod
	def pauseVm(self, vmId):
		r = os.system("/usr/sbin/xm pause %i"%vmId)
		if r != 0:
			print "xm pause failed for VM %i"%vmId
			raise Exception,  "xm pause failed for VM %i"%vmId
		self.newvms[vmId].state = InstanceState.Paused
		return vmId

	@synchronizedmethod
	def unpauseVm(self, vmId):
		r = os.system("/usr/sbin/xm unpause %i"%vmId)
		if r != 0:
			print "xm unpause failed for VM %i"%vmId
			raise Exception,  "xm unpause failed for VM %i"%vmId
		self.newvms[vmId].state = InstanceState.Running
		return vmId

	@synchronizedmethod
	def shutdownVm(self, vmId):
		r = os.system("/usr/sbin/xm shutdown %i"%vmId)
		if r != 0:
			print "xm shutdown failed for VM %i"%vmId
			raise Exception,  "xm shutdown failed for VM %i"%vmId
		return vmId

	@synchronizedmethod
	def destroyVm(self, vmId):
		r = os.system("/usr/sbin/xm destroy %i"%vmId)
		if r != 0:
			print "xm destroy failed for VM %i"%vmId
			raise Exception,  "xm destroy failed for VM %i"%vmId
		return vmId

	
	@synchronizedmethod
	def getVmInfo(self, vmId):
		return self.newvms[vmId]

	@synchronizedmethod
	def listVms(self):
		# On init, this should get a list from listVMs
		return self.newvms.keys()


	@synchronizedmethod
	def getHostInfo(self, service):
# collect information from the physical host:
# total memory in host
# number of CPU cores in host

		host = Host()
		host.id = service.id
		host.name = socket.gethostname()
		infopipe = subprocess.Popen("/usr/sbin/xm info",
					shell = True,
					stdout = subprocess.PIPE)

		for line in infopipe.stdout.readlines():

			if line.startswith("total_memory"):
				host.memory = int((line.split(':'))[1])
			if line.startswith("nr_cpus"):
				host.cores = int((line.split(':'))[1])

		host.up = True
		host.decayed = False
		host.version = version
		return host

	def getStats(self, vmId):
		return {}
