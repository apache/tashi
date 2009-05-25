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
from tashi.services.ttypes import Errors, InstanceState, TashiException
from tashi.services.ttypes import Instance, Host
from tashi import boolean, convertExceptions, ConnectionManager, version
from tashi.util import isolatedRPC

import tashi.parallel
from tashi.parallel import synchronized, synchronizedmethod

log = logging.getLogger(__file__)

# FIXME: these should throw errors on failure
def domIdToName(domid):
	f = os.popen("xm domname %i"%domid)
	name = f.readline().strip()
	f.close()
	return name

def domNameToId(domname):
	f = os.popen("xm domid %s"%domname)
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
						diskname = self.transientDisk(a.id, i)
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
# This is an ugly function, but the muti-line string literal makes it
# a lot easier
########################################
	def createXenConfig(self, vmName, 
			    image, macAddr, memory, cores, hints):
		fn = os.path.join("/tmp", vmName)
		vmType = hints.get('vmtype', self.defaultVmType)
		print 'starting vm with type: ', vmType
		bootstr = ''
		if vmType == 'pvgrub':
			# FIXME: untested, requires Xen 3.3
			bootstr = '''
kernel = '/usr/lib/xen/boot/pv-grub-x86_64.gz'
extra = '(hd0,0)/grub/menu.lst'
'''
		elif vmType == 'pygrub':
			bootstr = '''
bootloader="/usr/bin/pygrub"
'''
		elif vmType == 'kernel':
			kernel = hints.get('kernel', None)
			ramdisk = hints.get('ramdisk', None)
			if kernel == None:
				try:
					kernel = self.config.get('XenPV', 'defaultKernel')
				except:
					raise Exception, "vmtype=kernel requires kernel= argument"
			bootstr = "kernel=\"%s\"\n"%kernel
			if ramdisk == None:
				try:
					ramdisk = self.config.get('XenPV', 'defaultRamdisk')
				except:
					ramdisk = None
			if ramdisk != None:
				bootstr = bootstr + "ramdisk = \"%s\"\n"%ramdisk
		elif vmType == 'hvm':
			# FIXME: untested, I don't have any hvm domains set up
			bootstr = '''
import os, re
arch = os.uname()[4]
if re.search('63', arch):
	arch_libdir = 'lib64'
else:
	arch_libdir = 'lib'
kernel = '/usr/lib/xen/boot/hvmlocader'
builder = 'hvm'
'''
		else:
			raise Exception, "Unknown vmType in hints: %s"%vmType
		cfgstr = """
disk=['tap:qcow:%s,xvda1,w']
vif = [ 'mac=%s' ]
memory=%i
vcpus=%i
root="/dev/xvda1"
extra='xencons=tty'
"""%(image, macAddr, memory, cores)
		f = open(fn, "w")
		f.write(bootstr+cfgstr)
		f.close()
		return fn
	def deleteXenConfig(self, vmName):
		pass
#		os.unlink(os.path.join("/tmp", vmName))
########################################

	def vmName(self, instanceId):
		return "%s-%i"%(self.vmNamePrefix, int(instanceId))
	def transientDisk(self, instanceId, disknum):
		newdisk = os.path.join(self.transientDir,
				       'tashi-%i-%i.qcow' %(instanceId, disknum))
		return newdisk
		

	@synchronizedmethod
	def instantiateVm(self, instance):
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
				newdisk = self.transientDisk(instance.id, i)
				cmd = 'qcow-create 0 %s %s' % (newdisk, imageLocal)
				print 'creating new disk with "%s"' % cmd
				os.system(cmd)
				instance.disks[i].local = newdisk


		fn = self.createXenConfig(name, 
					  instance.disks[0].local, 
					  instance.nics[0].mac, 
					  instance.memory,
					  instance.cores,
					  instance.hints)
		cmd = "xm create %s"%fn
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
		cmd = "xm save %i %s"%(vmId, tmpfile)
		r = os.system(cmd)
		if r !=0 :
			print "xm save failed!"
			raise Exception,  "replace this with a real exception!"
		r = self.dfs.copyTo(tmpfile, target)
		self.newvms.pop(vmId)
		os.unlink(tmpfile)
		return vmId
	
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
		r = os.system("xm restore %s"%(tmpfile))
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
		cmd = "xm migrate -l %i %s"%(vmId, target)
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
		r = os.system("xm pause %i"%vmId)
		if r != 0:
			print "xm pause failed for VM %i"%vmId
			raise Exception,  "xm pause failed for VM %i"%vmId
		self.newvms[vmId].state = InstanceState.Paused
		return vmId

	@synchronizedmethod
	def unpauseVm(self, vmId):
		r = os.system("xm unpause %i"%vmId)
		if r != 0:
			print "xm unpause failed for VM %i"%vmId
			raise Exception,  "xm unpause failed for VM %i"%vmId
		self.newvms[vmId].state = InstanceState.Running
		return vmId

	@synchronizedmethod
	def shutdownVm(self, vmId):
		r = os.system("xm shutdown %i"%vmId)
		if r != 0:
			print "xm shutdown failed for VM %i"%vmId
			raise Exception,  "xm shutdown failed for VM %i"%vmId
		return vmId

	@synchronizedmethod
	def destroyVm(self, vmId):
		r = os.system("xm destroy %i"%vmId)
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
		host = Host()
		host.id = service.id
		host.name = socket.gethostname()
		memp = subprocess.Popen("xm info | awk '/^total_memory/ { print $3 }' ",
					shell = True,
					stdout = subprocess.PIPE)
		mems = memp.stdout.readline()
		host.memory = int(mems)
		corep = subprocess.Popen("xm info | awk '/^nr_cpus/ { print $3 }' ",
					shell = True,
					stdout = subprocess.PIPE)
		cores = corep.stdout.readline()
		host.cores = int(cores)
		host.up = True
		host.decayed = False
		host.version = version
		return host

	def getStats(self, vmId):
		return {}
