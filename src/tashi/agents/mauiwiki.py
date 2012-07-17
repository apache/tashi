#! /usr/bin/env python

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

# XXXstroucki: wiki is a text based resource manager that maui can
# use. It also seems to have disappeared from the face of the web.
# This code is unmaintained.

# XXXstroucki former file mauipacket.py
#import subprocess
import time
import SocketServer
from tashi.utils import pseudoDes
from tashi.rpycservices.rpyctypes import HostState, InstanceState

class MauiPacket:
	def __init__(self, key=0):
		self.size = 0
		self.char = '\n'
		self.chksum = '0'*16
		self.timestamp = int(time.time())
		self.auth = ''
		self.data = []
		self.msg = ''
		self.key=key
	def readPacket(self, istream):
		self.msg = ''

		size = istream.read(8)
		self.msg = self.msg+size
		self.size = int(size)

		self.char = istream.read(1)
		self.msg = self.msg + self.char

		packet = istream.read(self.size)
		self.msg = self.msg + packet

		packet = packet.split()
		
		for i in range(len(packet)):
			item = packet[i].split('=')
			if item[0] == 'CK':
				self.chksum = item[1]
			if item[0] == 'TS':
				self.timestamp = int(item[1])
			if item[0] == 'AUTH':
				self.auth = item[1]
			if item[0] == 'DT':
				self.data = packet[i:]
				self.data=self.data[0].split('=',1)[1:] + self.data[1:]

	def checksumMessage(self, message, key=None):
		if key == None:
			key = self.key
		if type(key) == type(''):
			key = int(key)
		chksum = pseudoDes.generateKey(message, key)
		chksum = '%016x' % chksum
		return chksum
	def getChecksum(self):
		cs = self.msg.partition('TS=')
		cs = cs[1]+cs[2]
		chksum = self.checksumMessage(cs)
		return chksum
	def verifyChecksum(self):
		chksum = self.getChecksum()
		if chksum != self.chksum:
			print 'verifyChecksum: "%s"\t"%s"'%(chksum, self.chksum)
			print 'verifyChecksum (types): %s\t%s' %(type(chksum), type(self.chksum))
			return False
		return True
	def set(self, data, auth=None, key=None, timestamp=None):
		if timestamp==None:
			timestamp = int(time.time())
		self.data = data
		if auth !=None:
			self.auth = auth
		if key != None:
			self.key = key
		self.timestamp=timestamp
		self.fixup()
	def fixup(self):
		datastring = "TS=%i AUTH=%s DT=%s"%(self.timestamp, self.auth, (' '.join(self.data)))
		self.chksum = self.checksumMessage(datastring)

		pktstring = 'CK=%s %s'%(self.chksum, datastring)
		self.size = len(pktstring)
	def __str__(self):
		datastring = "TS=%i AUTH=%s DT=%s"%(self.timestamp, self.auth, (' '.join(self.data)))
		self.chksum = self.checksumMessage(datastring)

		pktstring = 'CK=%s %s'%(self.chksum, datastring)
		self.msg = ''
		self.msg = self.msg + '%08i'%len(pktstring)
		self.msg = self.msg + self.char
		self.msg = self.msg + pktstring

		return self.msg
	def prettyString(self):
		s = '''Maui Packet
-----------
size:\t\t%i
checksum:\t%s
timestamp:\t%s
auth:\t\t%s
data:
%s
-----------'''
		s = s%(self.size, self.chksum, self.timestamp, self.auth, self.data)
		return s

# XXXstroucki original file mauiwiki.py
import threading
import logging.config

from tashi.parallel import synchronizedmethod
from tashi.services.ttypes import *
from tashi.util import getConfig, createClient, instantiateImplementation
#from tashi.agents.mauipacket import MauiPacket
import tashi.util

def jobnameToId(jobname):
	return int(jobname.split('.')[-1])

class InstanceHooks():
	def __init__(self, config):
		self.log = logging.getLogger(__file__)
		self.hooks=[]
		items = config.items("MauiWiki")
		items.sort()
		for item in items:
			(name, value) = item
			name = name.lower()
			if (name.startswith("hook")):
				try:
					self.hooks.append(instantiateImplementation(value, config, client, transport, False))
				except:
					self.log.exception("Failed to load hook %s" % (value))
		(self.client, self.transport) = createClient(config)
	def preCreate(self, inst):
		for hook in self.hooks:
			hook.preCreate(inst)
	def postDestroy(self, inst):
		for hook in self.hooks:
			hook.postDestroy(inst)
	def idToInst(self, _id):
		instances = self.client.getInstances()
		print 'instances ', instances
		insts = [i for i in instances if str(i.id)==str(_id)]
		if len(insts) == 0:
			raise "No instance with ID %s"%_id
		if len(insts) > 1:
			raise "Multiple instances with ID %s"%_id
		inst = insts[0]
		return inst
	def destroyById(self, _id):
		inst = self.idToInst(_id)
		self.client.destroyVm(int(_id))
		self.postDestroy(inst)
	def activateById(self, _id, host):
		inst = self.idToInst(_id)
		self.preCreate(inst)
		self.client.activateVm(int(_id), host)

def cmplists(a, b):
	for i in range(len(a)):
		if a[i] < b[i]:
			return -1
		if a[i] > b[i]:
			return 1
	return 0

class TashiConnection(threading.Thread):
	def __init__(self, config, client, transport):
		(self.client, self.transport) = createClient(config)

		self.hosts={}
		self.instances={}
		self.users={}

		self.config = config
		self.ihooks = InstanceHooks(config)
		self.log = logging.getLogger(__file__)
		self.refreshTime = float(self.config.get('MauiWiki', 'refreshTime'))
		self.defaultJobTime = str(self.config.get('MauiWiki', 'defaultJobTime'))
		threading.Thread.__init__(self)
		self.daemon = True
	def run(self):
		while True:
			print 'TashiConnection:run updating hosts ...'
			self.updateHosts()
			print 'TashiConnection:run updating instances ...'
			self.updateInstances()
			print 'TashiConnection:run updating users ...'
			self.updateUsers()
			time.sleep(self.refreshTime)
	def wikiHostState(self, host):
		'''Returns a string representing the host state in a form compatable
		with the maui-wiki protocol.  This code simply chooses between
		"Down" and "Unknown":

		- Busy: Node is running some jobs and will not accept additional jobs
		- Down: Resource Manager problems have been detected.  Node is
		incapable of running jobs.
		- Draining: Node is responding but will not accept new jobs
		- Idle: Node is ready to run jobs but currently is not running any.
		Running: Node is running some jobs and will accept additional jobs
		- Unknown: Node is capable of running jobs but the scheduler
		will need to determine if the node state is actually Idle,
		Running, or Busy.'''
		if host.up == False or host.state == HostState.VersionMismatch:
			return "Down"
		if host.state == HostState.Drained:
			return "Draining"
		return "Unknown"

	def wikiInstanceState(self, instance):
		'''Returns a string representing the instance stat in a form compatable
		with the maui-wiki protocol.

		Completed: Job has completed
		Hold: Job is in the queue but is not allowed to run
		Idle: Job is ready to run
		Removed: Job has been canceled or otherwise terminated externally
		Running: Job is currently executing
		Suspended: job has started but execution has temporarily been suspended'''
		tashiToWiki = {InstanceState.Pending:'Idle',
		               InstanceState.Held:'Hold',
		               InstanceState.Exited:'Removed'}
		if tashiToWiki.has_key(instance.state):
			return tashiToWiki[instance.state]
		else:
			return 'Running'

	# Host handling
	def compareHosts(self, host1, host2):
		def ii(host):
			try:
				state = tashi.util.hostStates[host.state]
			except:
				state = 'Unknown'
			return [host.id, host.name, host.up, state, host.memory, host.cores]
		return cmplists(ii(host1), ii(host2))
#	 @synchronizedmethod
	def updateHost(self, host):
		self.hosts[host.id] = host
		self.hosts[host.id].updateTime = time.time()
#	 @synchronizedmethod
	def addHost(self, host):
		self.hosts[host.id] = host
		self.hosts[host.id].updateTime = time.time()
#	 @synchronizedmethod
	def removeHost(self, host):
		self.hosts.pop(host.id)
#	 @synchronizedmethod
	def updateHosts(self):
		if (not self.transport.isOpen):
			self.transport.open()
		hosts = self.client.getHosts()
		for host in hosts:
			if not self.hosts.has_key(host.id):
				self.addHost(host)
			elif self.compareHosts(self.hosts[host.id], host) != 0:
				self.updateHost(host)
		hhosts = {}
		for host in hosts:
			hhosts[host.id] = host
		for host in self.hosts.values():
			if not hhosts.has_key(host.id):
				self.removeHost(host)
	# Instance handling
	def compareInstances(self, instance1, instance2):
		def ii(inst):
			return [inst.id,
			        inst.vmId,
			        inst.hostId,
			        tashi.util.vmStates[inst.state],
			        inst.userId,
			        inst.name,
			        inst.cores,
			        inst.memory,
			        len(inst.disks), # FIXME: this isn't a good way to compare
			        len(inst.nics),   # FIXME: this isn't a good way to compare
			        len(inst.hints)]
		return cmplists(ii(instance1), ii(instance2))
		return 0
	@synchronizedmethod
	def updateInstance(self, instance):
		qt = self.instances[instance.id].queueTime
		self.instances[instance.id] = instance
		self.instances[instance.id].updateTime = time.time()
		self.instances[instance.id].queueTime = qt
	@synchronizedmethod
	def addInstance(self, instance):
		self.instances[instance.id] = instance
		self.instances[instance.id].updateTime = time.time()
		self.instances[instance.id].queueTime = time.time()
	@synchronizedmethod
	def removeInstance(self, instance):
		self.instances[instance.id].state = InstanceState.Exited
		self.ihooks.postDestroy(instance)
	@synchronizedmethod
	def updateInstances(self):
		if (not self.transport.isOpen):
			self.transport.open()
		instances = self.client.getInstances()
		for instance in instances:
			print 'found instance', instance.id
			if not self.instances.has_key(instance.id):
				print "it's a new instance"
				self.addInstance(instance)
			elif self.compareInstances(self.instances[instance.id], instance) != 0:
				self.updateInstance(instance)
		iinsts = {}
		for instance in instances:
			iinsts[instance.id] = instance
		for instance in self.instances.values():
			if instance.state == InstanceState.Exited:
				continue
			if not iinsts.has_key(instance.id):
				print 'removing instance ', instance.id
				self.removeInstance(instance)
	# User handling
	def compareUsers(self, user1, user2):
		if user1.id < user2.id:
			return -1
		elif user1.id > user2.id:
			return 1
		if user1.name < user2.name:
			return -1
		if user1.name > user2.name:
			return 1
		return 0
	@synchronizedmethod
	def updateUser(self, user):
		self.users[user.id] = user
		self.users[user.id].updatetime = time.time()
	@synchronizedmethod
	def addUser(self, user):
		self.users[user.id] = user
		self.users[user.id].updatetime = time.time()
	@synchronizedmethod
	def removeUser(self, user):
		self.users.pop(user.id)
	@synchronizedmethod
	def updateUsers(self):
		if (not self.transport.isOpen):
			self.transport.open()
		users = self.client.getUsers()
		for user in users:
			if not self.users.has_key(user.id):
				self.addUser(user)
			elif self.compareUsers(self.users[user.id], user) != 0:
				self.updateUser(user)
		uusers = {}
		for user in users:
			uusers[user.id] = user
		for user in self.users.values():
			if not uusers.has_key(user.id):
				self.removeUser(user)
	# Get data structures for maui
	# Format is {id:{field:value}}
	@synchronizedmethod
	def getNodes(self, updatetime=0, nodelist=['ALL']):
		if len(nodelist) == 0:
			return {}
		if nodelist[0]=='ALL':
			nodes = [n for n in self.hosts.values() if n.updateTime >= updatetime]
		else:
			nodes = [n for n in self.hosts.values()
					 if n.updateTime >= updatetime and n.name in nodelist]
		nl = {}
		for node in nodes:
			nl[node.name] = {'STATE':self.wikiHostState(node),
			                 'UPDATETIME':str(int(node.updateTime)),
			                 'CPROC':str(node.cores),
			                 'CMEMORY':str(node.memory)}
		return nl
	@synchronizedmethod
	def getJobs(self, updatetime=0, joblist=['ALL']):
		if len(joblist) == 0:
			return {}
		if joblist[0] == 'ALL':
			jobs = [j for j in self.instances.values() if j.updateTime >= updatetime]
		else:
			jobs = [j for j in self.instances.values()
					if j.updateTime >= updatetime and j.id in joblist]
		jl = {}
		for job in jobs:
			_id = "%s.%i"%(job.name, job.id)
			jl[_id] = {'STATE':self.wikiInstanceState(job),
			          'UNAME':self.users[job.userId].name,
			          'GNAME':self.users[job.userId].name,
			          'UPDATETIME':int(job.updateTime),
			          'QUEUETIME':job.queueTime,
			          'TASKS':'1',
			          'DPROCS':str(job.cores),
			          'DMEM':str(job.memory),
			          'RMEM':str(job.memory),
			          'WCLIMIT':str(self.defaultJobTime)}
			if job.hostId != None:
				jl[_id]['TASKLIST'] = self.hosts[job.hostId].name
		return jl
	@synchronizedmethod
	def activateById(self, _id, host):
		if not self.instances.has_key(_id):
			raise "no such instance"
		self.ihooks.activateById(_id, host)
		self.instances[_id].state=InstanceState.Activating

class MauiListener(SocketServer.StreamRequestHandler):
	def setup(self):
		global config
		self.log = logging.getLogger(__file__)
		SocketServer.StreamRequestHandler.setup(self)
		self.ihooks = InstanceHooks(config)
		(self.client, self.transport) = createClient(config)
		self.tashiconnection=tashiconnection
		self.auth = config.get('MauiWiki', 'authuser')
		self.key = config.get('MauiWiki', 'authkey')

	def handle(self):
		p = MauiPacket(key=self.key)
		self.istream = self.ostream = self.rfile
		p.readPacket(self.istream)
		self.processPacket(p)

	def processGetNodes(self, p):
		arg = p.data[1]
		arg = arg.split('=')
		arg = arg[1].split(':')
		updatetime = int(arg[0])
		nodelist = arg[1:]
		print 'got GETNODES packet "%s" "%s"'%(updatetime, nodelist)
		r = MauiPacket()
		nodes = tashiconnection.getNodes(updatetime, nodelist)
		numNodes = len(nodes)
		dat = 'ARG=%i#'%numNodes
		first = True
		for node, attributes in nodes.iteritems():
			if first:
				dat = dat + '%s:'%node
				first = False
			else:
				dat = dat + '#%s:'%node
			attrs = ['%s=%s'%(a,v) for a,v in attributes.iteritems()]
			dat = dat + ';'.join(attrs)+';'
		r.set(['SC=0', dat], auth=self.auth, key=self.key)
		return r

	def processGetJobs(self, p):
		arg = p.data[1]
		arg = arg.split('=')
		arg = arg[1].split(':')
		updatetime = int(arg[0])
		joblist = arg[1:]
		print 'got GETJOBS packet "%s" "%s"'%(updatetime, joblist)
		r = MauiPacket();
		jobs = tashiconnection.getJobs(updatetime, joblist)
		numJobs = len(jobs)
		dat = 'ARG=%i#'%numJobs
		first = True
		for job, attributes in jobs.iteritems():
			if first:
				dat = dat +'%s:'%job
				first = False
			else:
				dat = dat +'#%s:'%job
			# FIXME: support limits
			attributes['WCLIMIT']=str(10000)
			attrs = ['%s=%s'%(a,v) for a,v in attributes.iteritems()]
			dat = dat + ';'.join(attrs) + ';'
		r.set(['SC=0', dat], auth=self.auth, key=self.key)
		return r

	def processStartJob(self, p):
		job = p.data[1]
		job = job.split('=')[1].strip()
		job = job.split('.')[-1]
		tasklist = p.data[2].split('=')[1].split(':')
		print 'STARTJOB ', job, tasklist
		try:
			hosts = self.client.getHosts()
			print 'hosts ', hosts
			host = [h for h in hosts if h.name == tasklist[0]][0]
			self.tashiconnection.activateById(jobnameToId(job), host)
			print '\tactivated VM!'
			r = MauiPacket()
			r.set(['SC=0','RESPONSE=VM %s started on host %s'%(job, tasklist[0])])
			return r
		except Exception, e:
			# FIXME: make this a real failure response
			print 'Oh noes! ', e
			r = MauiPacket()
			r.set(['SC=-1', 'RESPONSE=%s'%str(e)])
			return r

	def processCancelJob(self, p):
		job = p.data[1]
		job = job.split('=')[1].strip()
		print 'CANCELJOB ', job
		try:
			self.client.destroyVm(jobnameToId(job))
			print '\tdestroyed VM!'
			r = MauiPacket()
			r.set(['SC=0', 'RESPONSE=VM %s destroyed'%job])
			return r
		except Exception, e:
			# FIXME: make this a real failure response
			print 'Oh noes! ', e
			r = MauiPacket()
			r.set(['SC=-1', 'RESPONSE=%s'%str(e)])
			return r

	def processPacket(self,p):
		dat = p.data
		if not p.verifyChecksum():
			print p
			print 'bad checksum'
			return
		r = None
		if dat[0] == 'CMD=GETNODES':
			r = self.processGetNodes(p)
		elif dat[0] == 'CMD=GETJOBS':
			r = self.processGetJobs(p)
		elif dat[0] == 'CMD=STARTJOB':
			r = self.processStartJob(p)
		elif dat[0] == 'CMD=CANCELJOB':
			r = self.processCancelJob(p)
		else:
			print 'got unknown packet'
			print p.prettyString()
			r = MauiPacket()
			r.set(['SC=-810', 'RESPONSE=command not supported'])
		print r.prettyString()
		self.ostream.write(str(r))
		self.ostream.flush()
		self.ostream.close()
		self.ostream.close()
		self.istream.close()

if __name__ == '__main__':
	(config, configFiles) = getConfig(["Agent"])
	publisher = instantiateImplementation(config.get("Agent", "publisher"), config)
	tashi.publisher = publisher
	(client, transport) = createClient(config)
	logging.config.fileConfig(configFiles)
	tashiconnection = TashiConnection(config, client, transport)
	tashiconnection.start()

	HOST, PORT = '', 1717
	server = SocketServer.TCPServer((HOST,PORT), MauiListener)
	server.serve_forever()
