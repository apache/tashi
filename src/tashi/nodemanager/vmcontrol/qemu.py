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

import cPickle
import logging
import os
import threading
import random
import select
import signal
import socket
import subprocess
import sys
import time
import shlex

#from tashi.rpycservices.rpyctypes import *
from tashi.rpycservices.rpyctypes import InstanceState, Host
from tashi.util import scrubString, boolean
from tashi import version, stringPartition
from vmcontrolinterface import VmControlInterface

def controlConsole(child, port):
	"""This exposes a TCP port that connects to a particular child's monitor -- used for debugging"""
	#print "controlConsole"
	listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	listenSocket.bind(("0.0.0.0", port))
	#print "bound"
	try:
		try:
			listenSocket.listen(5)
			ls = listenSocket.fileno()
			#input = child.monitorFd
			output = child.monitorFd
			#print "listen"
			select.select([ls], [], [])
			(s, __clientAddr) = listenSocket.accept()
			while s:
				if (output != -1):
					(rl, __wl, __el) = select.select([s, output], [], [])
				else:
					(rl, __wl, __el) = select.select([s], [], [])
				if (len(rl) > 0):
					if (rl[0] == s):
						#print "from s"
						buf = s.recv(4096)
						if (buf == ""):
							s.close()
							listenSocket.close()
							s = None
							continue
						if (output != -1):
							os.write(child.monitorFd, buf)
					elif (rl[0] == output):
						#print "from output"
						buf = os.read(output, 4096)
						#print "read complete"
						if (buf == ""):
							output = -1
						else:
							s.send(buf)
		except:
			s.close()
			listenSocket.close()
	finally:
		#print "Thread exiting"
		pass

class Qemu(VmControlInterface):
	"""This class implements the VmControlInterface for Qemu/KVM"""
	
	def __init__(self, config, dfs, nm):
		VmControlInterface.__init__(self, config, dfs, nm)
		self.QEMU_BIN = self.config.get("Qemu", "qemuBin", default = "/usr/bin/kvm")
		self.INFO_DIR = self.config.get("Qemu", "infoDir", default = "/var/tmp/VmControlQemu/")
		self.POLL_DELAY = float(self.config.get("Qemu", "pollDelay", default = 1))
		self.migrationRetries = int(self.config.get("Qemu", "migrationRetries", default = 10))
		self.monitorTimeout = float(self.config.get("Qemu", "monitorTimeout", default = 60))
		self.migrateTimeout = float(self.config.get("Qemu", "migrateTimeout", default = 300))
		self.useMigrateArgument = boolean(self.config.get("Qemu", "useMigrateArgument", default = False))
		self.statsInterval = float(self.config.get("Qemu", "statsInterval", default = 0))
		reservedMem = self.config.get("Qemu", "reservedMem", default = 512)
		reservedMem = int(reservedMem)

		self.reservedMem = reservedMem

		self.log = logging.getLogger(__file__)
		self.ifPrefix = "tashi"
		self.controlledVMs = {}
		self.usedPorts = []
		self.usedPortsLock = threading.Lock()
		self.vncPorts = []
		self.vncPortLock = threading.Lock()
		self.consolePort = 10000
		self.consolePortLock = threading.Lock()
		maxParallelMigrations = self.config.get("Qemu", "maxParallelMigrations")
		maxParallelMigrations = int(maxParallelMigrations)
		if maxParallelMigrations < 1:
			maxParallelMigrations = 1

		self.migrationSemaphore = threading.Semaphore(maxParallelMigrations)
		self.stats = {}

		self.suspendHandler = self.config.get("Qemu", "suspendHandler", default = "gzip")
		self.resumeHandler = self.config.get("Qemu", "resumeHandler", default = "zcat")

		self.scratchVg = self.config.get("Qemu", "scratchVg")

		self.scratchDir = self.config.get("Qemu", "scratchDir", default = "/tmp")

		try:
			os.mkdir(self.INFO_DIR)
		except:
			pass

		self.__scanInfoDir()

		threading.Thread(target=self.__pollVMsLoop).start()
		if (self.statsInterval > 0):
			threading.Thread(target=self.statsThread).start()
	
	class anonClass:
		def __init__(self, **attrs):
			self.__dict__.update(attrs)

	def __dereferenceLink(self, spec):
		newspec = os.path.realpath(spec)
		return newspec


	def __getHostPids(self):
		"""Utility function to get a list of system PIDs that match the QEMU_BIN specified (/proc/nnn/exe)"""
		pids = []
		real_bin = self.__dereferenceLink(self.QEMU_BIN)

		for f in os.listdir("/proc"):
			try:
				binary = os.readlink("/proc/%s/exe" % (f))
				if (binary.find(real_bin) != -1):
					pids.append(int(f))
			except Exception:
				pass
		return pids

	# extern
	def getInstances(self):
		"""Will return a dict of instances by vmId to the caller"""
		return dict((x, self.controlledVMs[x].instance) for x in self.controlledVMs.keys())

	def __matchHostPids(self):
		"""This is run in a separate polling thread and it must do things that are thread safe"""

		vmIds = self.controlledVMs.keys()
		pids = self.__getHostPids()

		for vmId in vmIds:
			child = self.controlledVMs[vmId]

			# check to see if the child was just started.
			# Only try to check on it if startup was more
			# than 5 seconds in the past
			if "startTime" in child.__dict__:
				if child.startTime + 5 < time.time():
					del child.startTime
				else:
					self.log.info("Not processing vmId %d because it is newly started" % (vmId))
					continue

			instance = child.instance
			name = instance.name

			if vmId not in pids:
				# VM is no longer running, but is still
				# considered controlled

				# remove info file
				os.unlink(self.INFO_DIR + "/%d"%(vmId))

				# XXXstroucki python should handle
				# locking here (?)
				del self.controlledVMs[vmId]

				# remove any stats (appropriate?)
				try:
					del self.stats[vmId]
				except:
					pass

				if (child.vncPort >= 0):
					self.vncPortLock.acquire()
					self.vncPorts.remove(child.vncPort)
					self.vncPortLock.release()

				self.log.info("Removing vmId %d because it is no longer running" % (vmId))

				# if the VM was started from this process,
				# wait on it
				if (child.OSchild):
					try:
						(_pid, status) = os.waitpid(vmId, 0)
						self.log.info("vmId %s exited with status %s" % (vmId, status))
					except:
						self.log.exception("waitpid failed for vmId %s" % (vmId))
				# recover the child's stderr and monitor
				# output if possible
				if (child.errorBit):
					if (child.OSchild):
						f = open("/tmp/%d.err" % (vmId), "w")
						f.write(child.stderr.read())
						f.close()

					f = open("/tmp/%d.pty" % (vmId), "w")
					for i in child.monitorHistory:
						f.write(i)
					f.close()

				# remove scratch storage
				try:
					if self.scratchVg is not None:
						scratchName = "lv%s" % name
						self.log.info("Removing any scratch for %s" % (name))
						cmd = "/sbin/lvremove --quiet -f %s/%s" % (self.scratchVg, scratchName)
						__result = subprocess.Popen(cmd.split(), executable=cmd.split()[0], stdout=subprocess.PIPE, stderr=open(os.devnull, "w"), close_fds=True).wait()
				except:
					self.log.warning("Problem cleaning scratch volumes")
					pass

				# let the NM know
				try:
					# XXXstroucki: we don't want to treat
					# the source VM of a migration exiting
					# as an actual
					# exit, but the NM should probably know.
					self.nm.vmStateChange(vmId, None, InstanceState.Exited)
				except Exception:
					self.log.exception("vmStateChange failed for VM %s" % (name))
			else:
				# VM is still running
				try:
					
					if (child.migratingOut):
						self.nm.vmStateChange(vmId, None, InstanceState.MigrateTrans)
					elif (instance.state == InstanceState.Orphaned) or \
						(instance.state == InstanceState.Activating):
						self.nm.vmStateChange(vmId, None, InstanceState.Running)
				except:
					self.log.exception("vmStateChange failed for VM %s" % (name))
						

	# called once on startup
	def __scanInfoDir(self):
		"""This is not thread-safe and must only be used during class initialization"""
		controlledVMs = {}
		controlledVMs.update(map(lambda x: (int(x), self.anonClass(OSchild=False, errorBit=False, migratingOut=False)), os.listdir(self.INFO_DIR + "/")))
		if (len(controlledVMs) == 0):
			self.log.info("No VM information found in %s" % (self.INFO_DIR))
		for vmId in controlledVMs:
			try:
				child = self.__loadChildInfo(vmId)
				self.vncPortLock.acquire()
				if (child.vncPort >= 0):
					self.vncPorts.append(child.vncPort)
				self.vncPortLock.release()
				child.monitorFd = os.open(child.ptyFile, os.O_RDWR | os.O_NOCTTY)
				child.monitor = os.fdopen(child.monitorFd)

				#XXXstroucki ensure instance has vmId
				child.instance.vmId = vmId
				
				self.controlledVMs[vmId] = child
			except Exception:
				self.log.exception("Failed to load VM info for %d", vmId)
			else:
				self.log.info("Loaded VM info for %d", vmId)
	# service thread
	def __pollVMsLoop(self):
		"""Infinite loop that checks for dead VMs"""

		# As of 2011-12-30, nm is None when this is called, and
		# is set later by the NM. Things further down require
		# access to the NM, so wait until it is set.
		# Moved into __pollVMsLoop since putting it in this thread
		# will allow the init to complete and nm to be actually
		# set.

		while self.nm is None:
			self.log.info("Waiting for NM initialization")
			time.sleep(2)

		while True:
			try:
				time.sleep(self.POLL_DELAY)
				self.__matchHostPids()
			except:
				self.log.exception("Exception in poolVMsLoop")
	
	def __waitForExit(self, vmId):
		"""This waits until an element is removed from the dictionary -- the polling thread must detect an exit"""
		while vmId in self.controlledVMs:
			time.sleep(self.POLL_DELAY)
	
	def __getChildFromPid(self, pid):
		"""Do a simple dictionary lookup, but raise a unique exception if the key doesn't exist"""
		child = self.controlledVMs.get(pid, None)
		if (not child):
			raise Exception, "Uncontrolled vmId %d" % (pid)
		return child
	
	def __consumeAvailable(self, child):
		"""Consume characters one-by-one until they stop coming"""
		monitorFd = child.monitorFd
		buf = ""
		try:
			(rlist, __wlist, __xlist) = select.select([monitorFd], [], [], 0.0)
			while (len(rlist) > 0):
				c = os.read(monitorFd, 1)
				if (c == ""):
					self.log.error("Early termination on monitor for vmId %d" % (child.pid))
					child.errorBit = True
					raise EOFError
				buf = buf + c
				(rlist, __wlist, __xlist) = select.select([monitorFd], [], [], 0.0)
		finally:
			child.monitorHistory.append(buf)
		return buf
	
	def __consumeUntil(self, child, needle, timeout = -1):
		"""Consume characters one-by-one until something specific comes up"""
		if (timeout == -1):
			timeout = self.monitorTimeout
		monitorFd = child.monitorFd
		buf = " " * len(needle)
		try:
			while (buf[-(len(needle)):] != needle):
				#print "[BUF]: %s" % (buf)
				#print "[NEE]: %s" % (needle)
				(rlist, __wlist, __xlist) = select.select([monitorFd], [], [], timeout)
				if (len(rlist) == 0):
					self.log.error("Timeout getting results from monitor on FD %s for vmId %d" % (monitorFd, child.pid))
					child.errorBit = True
					raise EOFError
				c = os.read(monitorFd, 1)
				if (c == ""):
					self.log.error("Early termination on monitor FD %s for vmId %d" % (monitorFd, child.pid))
					child.errorBit = True
					raise EOFError
				buf = buf + c
		finally:
			child.monitorHistory.append(buf[len(needle):])
		return buf[len(needle):]
		
	def __enterCommand(self, child, command, expectPrompt = True, timeout = -1):
		"""Enter a command on the qemu monitor"""
		res = self.__consumeAvailable(child)
		os.write(child.monitorFd, command + "\n")
		if (expectPrompt):
			# XXXstroucki: receiving a vm can take a long time
			self.__consumeUntil(child, command, timeout=timeout)
			res = self.__consumeUntil(child, "(qemu) ", timeout=timeout)
		return res

	def __loadChildInfo(self, vmId):
		child = self.anonClass(pid=vmId)
		info = open(self.INFO_DIR + "/%d"%(child.pid), "r")
		(instance, pid, ptyFile) = cPickle.load(info)
		info.close()
		if (pid != child.pid):
			raise Exception, "PID mismatch"
		child.instance = instance
		child.pid = pid
		child.ptyFile = ptyFile
		if ('monitorHistory' not in child.__dict__):
			child.monitorHistory = []
		if ('OSchild' not in child.__dict__):
			child.OSchild = False
		if ('errorBit' not in child.__dict__):
			child.errorBit = False
		if ('migratingOut' not in child.__dict__):
			child.migratingOut = False
		if ('vncPort' not in child.__dict__):
			child.vncPort = -1
		return child
	
	def __saveChildInfo(self, child):
		# XXXstroucki: if the disk INFO_DIR is on is full,
		# we may not be able to store our data. This can lead
		# to VMs remaining running that the NM doesn't know about
		# Can we do anything, or should be a task external to Tashi?
		info = open(self.INFO_DIR + "/%d"%(child.pid), "w")
		cPickle.dump((child.instance, child.pid, child.ptyFile), info)
		info.close()
	
	# extern
	def getHostInfo(self, service):
		host = Host()
		host.id = service.id
		host.name = socket.gethostname()

		# Linux specific
		memoryStr = open("/proc/meminfo","r").readline().strip().split()
		if (memoryStr[2] == "kB"):
			# XXXstroucki should have parameter for reserved mem
			host.memory = (int(memoryStr[1])/1024) - self.reservedMem
		else:
			self.log.warning('Unable to determine amount of physical memory - reporting 0')
			host.memory = 0
		host.cores = os.sysconf("SC_NPROCESSORS_ONLN")
		host.up = True
		host.decayed = False
		host.version = version
		return host

	def __stripSpace(self, s):
		return "".join(s.split())

	def __startVm(self, instance, source):
		"""Universal function to start a VM -- used by instantiateVM, resumeVM, and prepReceiveVM"""

		#  Capture __startVm Hints
		#  CPU hints
		cpuModel = instance.hints.get("cpumodel")

		cpuString = ""
		if cpuModel:
			# clean off whitespace
			cpuModel = self.__stripSpace(cpuModel)
			cpuString = "-cpu " + cpuModel 

		#  Clock hints
		clockString = instance.hints.get("clock", "dynticks")
		# clean off whitespace
		clockString = self.__stripSpace(clockString)

		#  Disk hints
		# XXXstroucki: insert commentary on jcipar's performance
		# measurements
		# virtio is recommended, but linux will name devices
		# vdX instead of sdX. This adds a trap for someone who
		# converts a physical machine or other virtualization
		# layer's image to run under Tashi.
		diskInterface = instance.hints.get("diskInterface", "ide")
		# clean off whitespace
		diskInterface = self.__stripSpace(diskInterface)

		diskString = ""

		for index in range(0, len(instance.disks)):
			disk = instance.disks[index]
			uri = scrubString(disk.uri)
			imageLocal = self.dfs.getLocalHandle("images/" + uri)
			imageLocal = self.__dereferenceLink(imageLocal)
			thisDiskList = [ "file=%s" % imageLocal ]
			thisDiskList.append("if=%s" % diskInterface)
			thisDiskList.append("index=%d" % index)

			if (index == 0 and diskInterface == "virtio"):
				thisDiskList.append("boot=on")

			if (disk.persistent):
				snapshot = "off"
				migrate = "off"
			else:
				snapshot = "on"
				migrate = "on"

			thisDiskList.append("cache=off")

			thisDiskList.append("snapshot=%s" % snapshot)

			if (self.useMigrateArgument):
				thisDiskList.append("migrate=%s" % migrate)

			diskString = diskString + "-drive " + ",".join(thisDiskList) + " "

		# scratch disk
		scratchSize = instance.hints.get("scratchSpace", "0")
		scratchSize = int(scratchSize)
		scratchName = None

		try:
			if scratchSize > 0:
				if self.scratchVg is None:
					raise Exception, "No scratch volume group defined"
				# create scratch disk
				# XXXstroucki: needs to be cleaned somewhere
				# XXXstroucki: clean user provided instance name
				scratchName = "lv%s" % instance.name
				# XXXstroucki hold lock
				# XXXstroucki check for capacity
				cmd = "/sbin/lvcreate --quiet -n%s -L %dG %s" % (scratchName, scratchSize, self.scratchVg)
				# XXXstroucki check result
				__result = subprocess.Popen(cmd.split(), executable=cmd.split()[0], stdout=subprocess.PIPE).wait()
				index += 1

				thisDiskList = [ "file=/dev/%s/%s" % (self.scratchVg, scratchName) ]
				thisDiskList.append("if=%s" % diskInterface)
				thisDiskList.append("index=%d" % index)
				thisDiskList.append("cache=off")
				
				# XXXstroucki force scratch disk to be
				# persistent
				if (True or disk.persistent):
					snapshot = "off"
					migrate = "off"
				else:
					snapshot = "on"
					migrate = "on"

				thisDiskList.append("snapshot=%s" % snapshot)

				if (self.useMigrateArgument):
					thisDiskList.append("migrate=%s" % migrate)

				diskString = "%s-drive %s " % (diskString, ",".join(thisDiskList))

		except:
			self.log.exception('caught exception in scratch disk formation')
			raise
	
		#  Nic hints
		nicModel = instance.hints.get("nicModel", "virtio")
		# clean off whitespace
		nicModel = self.__stripSpace(nicModel)

		nicString = ""
		nicNetworks = {}
		for i in range(0, len(instance.nics)):
			# Don't allow more than one interface per vlan
			nic = instance.nics[i]
			if nicNetworks.has_key(nic.network):
				continue
			nicNetworks[nic.network] = True

			nicString = nicString + "-net nic,macaddr=%s,model=%s,vlan=%d -net tap,ifname=%s%d.%d,vlan=%d,script=/etc/qemu-ifup.%d " % (nic.mac, nicModel, nic.network, self.ifPrefix, instance.id, i, nic.network, nic.network)

		#  ACPI
		if (boolean(instance.hints.get("noAcpi", False))):
			noAcpiString = "-no-acpi"
		else:
			noAcpiString = ""

		#  Construct the qemu command
		strCmd = "%s %s %s -clock %s %s %s -m %d -smp %d -serial null -vnc none -monitor pty" % (self.QEMU_BIN, noAcpiString, cpuString, clockString, diskString, nicString, instance.memory, instance.cores)
		if (source):
			strCmd = '%s -incoming "%s"' % (strCmd, source)
		# XXXstroucki perhaps we're doing it backwards
		cmd = shlex.split(strCmd)

		self.log.info("Executing command: %s" % (strCmd))
		(pipe_r, pipe_w) = os.pipe()
		pid = os.fork()
		if (pid == 0):
			# child process
			pid = os.getpid()
			os.setpgid(pid, pid)
			os.close(pipe_r)
			os.dup2(pipe_w, sys.stderr.fileno())
			for i in [sys.stdin.fileno(), sys.stdout.fileno()]:
				try:
					os.close(i)
				except:
					pass
			for i in xrange(3, os.sysconf("SC_OPEN_MAX")):
				try:
					os.close(i)
				except:
					pass

			# XXXstroucki unfortunately no kvm option yet
			# to direct COW differences elsewhere, so change
			# this process' TMPDIR, which kvm will honour
			os.environ['TMPDIR'] = self.scratchDir
			os.execl(self.QEMU_BIN, *cmd)
			sys.exit(-1)

		# parent process
		os.close(pipe_w)
		child = self.anonClass(pid=pid, instance=instance, stderr=os.fdopen(pipe_r, 'r'), migratingOut = False, monitorHistory=[], errorBit = True, OSchild = True)
		child.ptyFile = None
		child.vncPort = -1
		child.instance.vmId = child.pid

		# Add a token to this new child object so that
		# we don't mistakenly clean up when matchHostPids
		# runs and the child process hasn't exec'ed yet.
		child.startTime = time.time()

		self.__saveChildInfo(child)
		self.log.info("Adding vmId %d" % (child.pid))
		self.controlledVMs[child.pid] = child
		return (child.pid, cmd)

	def __getPtyInfo(self, child, issueContinue):
		ptyFile = None
		while not ptyFile:
			line = child.stderr.readline()
			if (line == ""):
				try:
					os.waitpid(child.pid, 0)
				except:
					self.log.exception("waitpid failed")
				raise Exception, "Failed to start VM -- ptyFile not found"
			redirLine = "char device redirected to "
			if (line.find(redirLine) != -1):
				ptyFile=line[len(redirLine):].strip()
				break
		child.ptyFile = ptyFile
		child.monitorFd = os.open(child.ptyFile, os.O_RDWR | os.O_NOCTTY)
		child.monitor = os.fdopen(child.monitorFd)
		self.__saveChildInfo(child)
		if (issueContinue):
			# XXXstroucki: receiving a vm can take a long time
			self.__enterCommand(child, "c", timeout=None)
	
	def __stopVm(self, vmId, target, stopFirst):
		"""Universal function to stop a VM -- used by suspendVM, migrateVM """
		child = self.__getChildFromPid(vmId)
		if (stopFirst):
			self.__enterCommand(child, "stop")
		if (target):
			retry = self.migrationRetries
			while (retry > 0):
				# migrate in foreground respecting cow backed
				# images
				# XXXstroucki if we're doing this in the fg
				# then it may still be ongoing when the timeout
				# happens, and no way of interrupting it
				# trying to restart the migration by running
				# the command again (when qemu is ready to
				# listen again) is probably not helpful
				# XXXstroucki: failures observed:
				# "migration failed"
				# "Block format 'qcow' used by device '' does not support feature 'live migration'
				success = False
				# see if migration can be speeded up
				res = self.__enterCommand(child, "migrate_set_speed 1g", timeout=self.migrateTimeout)
				res = self.__enterCommand(child, "migrate -i %s" % (target), timeout=self.migrateTimeout)
				retry = retry - 1
				if (res.find("Block migration completed") != -1):
					success = True
					retry = 0
					break
				else:
					self.log.error("Migration (transiently) failed: %s\n", res)
			if (retry == 0) and (success is False):
				self.log.error("Migration failed: %s\n", res)
				child.errorBit = True
				raise RuntimeError
		# XXXstroucki what if migration is still ongoing, and
		# qemu is not listening?
		self.__enterCommand(child, "quit", expectPrompt=False)
		return vmId

	# extern	
	def instantiateVm(self, instance):
		# XXXstroucki: check capacity before instantiating

		try:
			(vmId, cmd) = self.__startVm(instance, None)
			child = self.__getChildFromPid(vmId)
			self.__getPtyInfo(child, False)
			child.cmd = cmd
			self.nm.createInstance(child.instance)
			self.nm.vmStateChange(vmId, None, InstanceState.Running)
			# XXXstroucki Should make sure Running state is saved
			# otherwise on restart it will appear as Activating
			# until we update the state in __matchHostPids
			child.instance.state = InstanceState.Running
			self.__saveChildInfo(child)
			return vmId
		except:
			self.log.exception("instantiateVm failed")
			raise
	
	# extern
	def suspendVm(self, vmId, target):
		# XXX: Use fifo to improve performance
		# XXXstroucki: we could create a fifo on the local fs,
		# then start a thread to copy it to dfs. But if we're
		# reading from dfs directly on resume, why not write
		# directly here?

		#tmpTarget = "/%s/tashi_qemu_suspend_%d_%d" % (self.scratchDir, os.getpid(), vmId)
		fn = self.dfs.getLocalHandle("%s" % target)
		vmId = self.__stopVm(vmId, "\"exec:%s > %s\"" % (self.suspendHandler, fn), True)
		#self.dfs.copyTo(tmpTarget, target)
		#os.unlink(tmpTarget)
		return vmId
	
	# extern
	def resumeVmHelper(self, instance, source):
		vmId = instance.vmId
		child = self.__getChildFromPid(vmId)
		try:
			self.__getPtyInfo(child, True)
		except EOFError:
			self.log.error("Failed to get pty info -- VM likely died")
			child.errorBit = True
			raise
		status = "paused"
		while ("running" not in status):
			try:
				status = self.__enterCommand(child, "info status")
			except EOFError:
				pass
			time.sleep(60)

		self.nm.vmStateChange(vmId, None, InstanceState.Running)
		child.instance.state = InstanceState.Running
		self.__saveChildInfo(child)
	
	# extern
	def resumeVm(self, instance, source):
		fn = self.dfs.getLocalHandle("%s" % (source))
		(vmId, cmd) = self.__startVm(instance, "exec:%s < %s" % (self.resumeHandler, fn))
		child = self.__getChildFromPid(vmId)
		child.cmd = cmd
		return vmId

	def __checkPortListening(self, port):
		# XXXpipe: find whether something is listening yet on the port
		p = subprocess.Popen("netstat -ln | grep 0.0.0.0:%d | wc -l" % (port), shell = True, stdin = subprocess.PIPE, stdout = subprocess.PIPE, close_fds = True)
		(stdin, stdout) = (p.stdin, p.stdout)
		stdin.close()
		r = stdout.read()
		lc = int(r.strip())
		if (lc < 1):
			return False
		else:
			return True

	# extern
	def prepReceiveVm(self, instance, source):
		self.usedPortsLock.acquire()
		while True:
			port = random.randint(19000, 20000)
			if port not in self.usedPorts:
				break

		self.usedPorts.append(port)
		self.usedPortsLock.release()
		(vmId, cmd) = self.__startVm(instance, "tcp:0.0.0.0:%d" % (port))
		transportCookie = cPickle.dumps((port, vmId, socket.gethostname()))
		child = self.__getChildFromPid(vmId)
		child.cmd = cmd
		child.transportCookie = transportCookie
		self.__saveChildInfo(child)
		# XXX: Cleanly wait until the port is listening
		while self.__checkPortListening(port) is not True:
			time.sleep(1)

		return transportCookie
	
	# extern
	def migrateVm(self, vmId, target, transportCookie):
		self.migrationSemaphore.acquire()
		try:
			(port, _vmId, _hostname) = cPickle.loads(transportCookie)
			child = self.__getChildFromPid(vmId)
			child.migratingOut = True
			# tell the VM to live-migrate out
			res = self.__stopVm(vmId, "tcp:%s:%d" % (target, port), False)
			# XXX: Some sort of feedback would be nice
			# XXX: Should we block?
			# XXXstroucki: isn't this what __waitForExit does?
			self.__waitForExit(vmId)
		finally:
			self.migrationSemaphore.release()
		return res
	
	# extern
	def receiveVm(self, transportCookie):
		(port, vmId, _hostname) = cPickle.loads(transportCookie)
		try:
			child = self.__getChildFromPid(vmId)
		except:
			# XXXstroucki: Does hostname contain the peer hostname?
			self.log.error("Failed to get child info; transportCookie = %s; hostname = %s" %
					(str(cPickle.loads(transportCookie)), _hostname))
			raise
		try:
			self.__getPtyInfo(child, True)
		except EOFError:
			self.log.error("Failed to get pty info -- VM likely died")
			child.errorBit = True
			raise
		self.usedPortsLock.acquire()
		self.usedPorts = filter(lambda _port: _port != port, self.usedPorts)
		self.usedPortsLock.release()
		return vmId
	
	# extern
	def pauseVm(self, vmId):
		child = self.__getChildFromPid(vmId)
		self.__enterCommand(child, "stop")
		# XXXstroucki we have no Stopped state, so consider
		# the VM still Running?
	
	# extern
	def unpauseVm(self, vmId):
		child = self.__getChildFromPid(vmId)
		self.__enterCommand(child, "c")
		# XXXstroucki as above, should this be a state change
		# or not?
	
	# extern
	def shutdownVm(self, vmId):
		"""'system_powerdown' doesn't seem to actually shutdown the VM on some versions of KVM with some versions of Linux"""
		# If clean shutdown is desired, should try on VM first,
		# shutdownVm second and if that doesn't work use
		# destroyVm
		child = self.__getChildFromPid(vmId)
		self.__enterCommand(child, "system_powerdown")
	
	# extern
	def destroyVm(self, vmId):
		child = self.__getChildFromPid(vmId)
		child.migratingOut = False
		# XXX: the child could have exited between these two points, but I don't know how to fix that since it might not be our child process
		os.kill(child.pid, signal.SIGKILL)
	
	def __specificStartVnc(self, vmId):
		child = self.__getChildFromPid(vmId)
		hostname = socket.gethostname()
		if (child.vncPort == -1):
			self.vncPortLock.acquire()
			port = 0
			while (port in self.vncPorts):
				port += 1

			self.vncPorts.append(port)
			self.vncPortLock.release()
			self.__enterCommand(child, "change vnc :%d" % (port))
			child.vncPort = port
			self.__saveChildInfo(child)
		port = child.vncPort
		return "VNC running on %s:%d" % (hostname, port + 5900)

	def __specificStopVnc(self, vmId):
		child = self.__getChildFromPid(vmId)
		self.__enterCommand(child, "change vnc none")
		if (child.vncPort != -1):
			self.vncPortLock.acquire()
			self.vncPorts.remove(child.vncPort)
			self.vncPortLock.release()
			child.vncPort = -1
			self.__saveChildInfo(child)
		return "VNC halted"

	def __specificChangeCdRom(self, vmId, iso):
		child = self.__getChildFromPid(vmId)
		imageLocal = self.dfs.getLocalHandle("images/" + iso)
		self.__enterCommand(child, "change ide1-cd0 %s" % (imageLocal))
		return "Changed ide1-cd0 to %s" % (iso)

	def __specificStartConsole(self, vmId):
		child = self.__getChildFromPid(vmId)
		hostname = socket.gethostname()
		self.consolePortLock.acquire()
		# XXXstroucki why not use the existing ports scheme?
		consolePort = self.consolePort
		self.consolePort += 1
		self.consolePortLock.release()
		threading.Thread(target=controlConsole, args=(child,consolePort)).start()
		return "Control console listening on %s:%d" % (hostname, consolePort)

	def __specificReset(self, vmId):
		child = self.__getChildFromPid(vmId)
		self.__enterCommand(child, "system_reset")
		return "Sent reset signal to instance"

	# extern
	def vmmSpecificCall(self, vmId, arg):
		arg = arg.lower()
		changeCdText = "changecdrom:"

		if (arg == "startvnc"):
			return self.__specificStartVnc(vmId)

		elif (arg == "stopvnc"):
			return self.__specificStopVnc(vmId)

		elif (arg.startswith(changeCdText)):
			iso = scrubString(arg[len(changeCdText):])
			return self.__specificChangeCdRom(vmId, iso)

		elif (arg == "startconsole"):
			return self.__specificStartConsole(vmId)

		elif (arg == "reset"):
			return self.__specificReset(vmId)

		elif (arg == "list"):
			commands = [
				"startVnc",
				"stopVnc",
				"changeCdrom:<image.iso>",
				"startConsole",
				"reset",
				]
			return "\n".join(commands)
				
		else:
			return "Unknown command %s" % (arg)
	
	# extern
	def listVms(self):
		return self.controlledVMs.keys()

	def __processVmStats(self, vmId):
		try:
			f = open("/proc/%d/stat" % (vmId))
			procData = f.read()
			f.close()
		except:
			self.log.warning("Unable to get data for instance %d" % vmId)
			return

		ws = procData.strip().split()
		userTicks = float(ws[13])
		sysTicks = float(ws[14])
		myTicks = userTicks + sysTicks
		vsize = (int(ws[22]))/1024.0/1024.0
		rss = (int(ws[23])*4096)/1024.0/1024.0
		cpuSeconds = myTicks/self.ticksPerSecond
		# XXXstroucki be more exact here?
		last = time.time() - self.statsInterval
		lastCpuSeconds = self.cpuStats.get(vmId, cpuSeconds)
		if lastCpuSeconds is None:
			lastCpuSeconds = cpuSeconds
		cpuLoad = (cpuSeconds - lastCpuSeconds)/(time.time() - last)
		self.cpuStats[vmId] = cpuSeconds
		try:
			child = self.controlledVMs[vmId]
		except:
			self.log.warning("Unable to obtain information on instance %d" % vmId)
			return

		(recvMBs, sendMBs, recvBytes, sendBytes) = (0.0, 0.0, 0.0, 0.0)
		for i in range(0, len(child.instance.nics)):
			netDev = "%s%d.%d" % (self.ifPrefix, child.instance.id, i)
			(tmpRecvMBs, tmpSendMBs, tmpRecvBytes, tmpSendBytes) = self.netStats.get(netDev, (0.0, 0.0, 0.0, 0.0))
			(recvMBs, sendMBs, recvBytes, sendBytes) = (recvMBs + tmpRecvMBs, sendMBs + tmpSendMBs, recvBytes + tmpRecvBytes, sendBytes + tmpSendBytes)
		self.stats[vmId] = self.stats.get(vmId, {})
		child = self.controlledVMs.get(vmId, None)
		if (child):

			try:
				res = self.__enterCommand(child, "info blockstats")
			except EOFError:
				# The VM is likely exiting
				return

			for l in res.split("\n"):
				(device, __sep, data) = stringPartition(l, ": ")
				if (data != ""):
					for field in data.split(" "):
						(label, __sep, val) = stringPartition(field, "=")
						if (val != ""):
							self.stats[vmId]['%s_%s_per_s' % (device, label)] = (float(val) - float(self.stats[vmId].get('%s_%s' % (device, label), 0)))/self.statsInterval
							self.stats[vmId]['%s_%s' % (device, label)] = int(val)
		self.stats[vmId]['cpuLoad'] = cpuLoad
		self.stats[vmId]['rss'] = rss
		self.stats[vmId]['vsize'] = vsize
		self.stats[vmId]['recvMBs'] = sendMBs
		self.stats[vmId]['sendMBs'] = recvMBs

	# thread
	def statsThread(self):
		self.ticksPerSecond = float(os.sysconf('SC_CLK_TCK'))
		self.netStats = {}
		self.cpuStats = {}
		# XXXstroucki be more exact here?
		last = time.time() - self.statsInterval
		while True:
			now = time.time()
			try:
				f = open("/proc/net/dev")
				netData = f.readlines()
				f.close()
				for l in netData:
					if (l.find(self.ifPrefix) != -1):
						(dev, __sep, ld) = stringPartition(l, ":")
						dev = dev.strip()
						ws = ld.split()
						recvBytes = float(ws[0])
						sendBytes = float(ws[8])
						(recvMBs, sendMBs, lastRecvBytes, lastSendBytes) = self.netStats.get(dev, (0.0, 0.0, recvBytes, sendBytes))
						if (recvBytes < lastRecvBytes):
							# We seem to have overflowed
							# XXXstroucki How likely is this to happen?

							if (lastRecvBytes > 2**32):
								lastRecvBytes = lastRecvBytes - 2**64
							else:
								lastRecvBytes = lastRecvBytes - 2**32
						if (sendBytes < lastSendBytes):
							if (lastSendBytes > 2**32):
								lastSendBytes = lastSendBytes - 2**64
							else:
								lastSendBytes = lastSendBytes - 2**32
						recvMBs = (recvBytes-lastRecvBytes)/(now-last)/1024.0/1024.0
						sendMBs = (sendBytes-lastSendBytes)/(now-last)/1024.0/1024.0
						self.netStats[dev] = (recvMBs, sendMBs, recvBytes, sendBytes)


				for vmId in self.controlledVMs:
					self.__processVmStats(vmId)

			except:
				self.log.exception("statsThread threw an exception")
			last = now
			time.sleep(self.statsInterval)

	# extern	
	def getStats(self, vmId):
		return self.stats.get(vmId, {})
