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

import unittest
import logging
import sys
import signal
import os.path
import copy
import time
import random
from ConfigParser import ConfigParser

from tashi.services.ttypes import *
from thrift.transport.TSocket import TSocket
from thrift.protocol.TBinaryProtocol import TBinaryProtocol
from thrift.transport.TTransport import TBufferedTransport

from tashi.services import clustermanagerservice
from tashi.messaging.threadpool import synchronized
from tashi.messaging.tashimessaging import TestTashiSubscriber

from tashi.util import getConfig

import tashi.client.client

class ClientConnection(object):
	'''Creates an rpc proxy'''
	def __init__(self, host, port):
		self.host = host
		self.port = port
		self.transport = TBufferedTransport(TSocket(host, int(port)))
		self.protocol = TBinaryProtocol(self.transport)
		self.client = clustermanagerservice.Client(self.protocol)
		self.client._transport = self.transport
		self.client._transport.open()
	def __del__(self):
		self.client._transport.close()

def incrementor(init=0):
	while 1:
		yield init
		init = init + 1

# FIXME: don't duplicate code from clustermanager
# def getConfig(args):
#	 config = ConfigParser()
#	 configFiles = [
#		'/usr/share/tashi/ClusterManagerDefaults.cfg',
#		'/etc/tashi/ClusterManager.cfg',
#		os.path.expanduser('~/.tashi/ClusterManager.cfg')
#		] + ([args[0]] if len(args) > 0 else [])

#	 configFiles = config.read(configFiles)
#	 if len(configFiles) == 0:
#		 print >>sys.stderr, 'Unable to find the configuration file\n'
#		 sys.exit(3)

#	 return config


class TestClient(unittest.TestCase):
	@synchronized()
	def getPortNum(self):
		return self.portnum.next()

	"""macro test cases for single-host tests

	Assumes cwd is 'src/tashi/client/'
	"""
	def setUp(self):
		"""Create a CM and single NM on local host"""
		logging.info('setting up test')
		
		(self.config, self.configfiles) = getConfig([])

		self.port = 1717		# FIXME: take this (and other things) from config file
		self.portnum = incrementor(self.port)

		self.cwd = os.getcwd()
		self.srcd = os.path.dirname(os.path.dirname(self.cwd))
		
		self.environ = copy.copy(os.environ)
		self.environ['PYTHONPATH'] = self.srcd
		logging.info('base path = %s' % self.srcd)

		self.nm = os.spawnlpe(os.P_NOWAIT, 'python', 'python', 
							  os.path.join(self.srcd, 'tashi', 'nodemanager', 'nodemanager.py'),
							  self.environ)
		self.cm = os.spawnlpe(os.P_WAIT, 'python', 'python',
							 os.path.join(self.srcd,  'tashi', 'clustermanager', 'clustermanager.py'),
							 '--drop', '--create',
							 os.path.expanduser('~/.tashi/ClusterManager.cfg'),
							 self.environ)
		self.cm = os.spawnlpe(os.P_NOWAIT, 'python', 'python',
							 os.path.join(self.srcd,  'tashi', 'clustermanager', 'clustermanager.py'),
							 os.path.expanduser('~/.tashi/ClusterManager.cfg'),
							 self.environ)
		# since we are spawning with P_NOWAIT, we need to sleep to ensure that the CM is listening
		time.sleep(1)
		try:
			self.connection = ClientConnection('localhost', self.config.get('ClusterManagerService', 'port'))
		except Exception, e:
			logging.warning('client connection failed')
			ex = None
			try:
				logging.warning("setUp killing node manager " + str(self.nm))
				os.kill(self.nm, signal.SIGKILL)
			except Exception, e:
				ex = e
				logging.warning('could not kill node manager: '+ str(e))
			try:
				logging.warning('setUp killing cluster manager ' + str(self.cm))
				os.kill(self.cm, signal.SIGKILL)
			except Exception, e:
				ex = e
				logging.warning('could not kill cluster manager: ' + str(e))
			if e != None:
				raise e

		logging.info('node manager PID: %i' % self.nm)
	def tearDown(self):
		'''Kill the CM and NM that were created by setUP'''
		logging.info('tearing down test')
		ex = None
		try:
			logging.debug("killing cluster manager " + str(self.cm))
			os.kill(self.cm, signal.SIGKILL)
		except Exception, e:
			ex = e
			logging.error('Could not kill cluster manager: ' + str(e))
			
		try:
			logging.debug("killing node manager " + str(self.nm))
			os.kill(self.nm, signal.SIGKILL)
		except Exception, e:
			ex = e
			logging.error('Could not kill node manager: ' + str(e))
		if ex != None:
			raise ex
	def testSetup(self):
		'''empty test to ensure that setUp code works'''
		logging.info('setting up')
	def testHostManagement(self):
		'''test adding/removing/listing hosts

		Right now this just adds a single host: localhost.  Eventually
		it should 1) take a list of hosts from a test configuration
		file, 2) ensure that all were added, 3) remove a random
		subset, 4) ensure that they were correctly removed, 5) remove
		all, 6) ensure that they were correctly removed.'''

		# get empty host list
		hosts = self.connection.client.getHosts()
		self.assertEqual(hosts, [], 'starting host list not empty: ' + str(hosts) )

		# add a host
		host = Host()
		host.hostname = 'localhost'
		host.enabled=True
		self.connection.client.addHost(host)
		hosts = self.connection.client.getHosts()
		self.assertEqual(len(hosts), 1, 'wrong number of hosts %i, should be %i' % (len(hosts), 1) )
		self.assertEqual(hosts[0].hostname, 'localhost', 'wrong hostname: ' + str(hosts[0].hostname) )

		# remove first host
		hid = hosts[0].id
		self.connection.client.removeHost(hid)
		hosts = self.connection.client.getHosts()
		self.assertEqual(hosts, [], 'host list not empty after remove: ' + str(hosts) )

	def testMessaging(self):
		'''test messaging system started by CM

		tests messages published directly, through events in the CM,
		and the log system'''
		# FIXME: add tests for generating events as a side-effect of
		# rpc commands, as well as logging in the CM
		portnum = self.getPortNum()
		self.sub = TestTashiSubscriber(self.config, portnum)
		self.assertEqual(self.sub.messageQueue.qsize(), 0)
		self.pub = tashi.messaging.thriftmessaging.PublisherThrift(self.config.get('MessageBroker', 'host'),
																   int(self.config.get('MessageBroker', 'port')))
		self.pub.publish({'message-type':'text', 'message':'Hello World!'})
		time.sleep(0.5)
		print '*** QSIZE', self.sub.messageQueue.qsize()
		self.assertEqual(self.sub.messageQueue.qsize(), 1)

		self.log = logging.getLogger(__name__)
		messageHandler = tashi.messaging.tashimessaging.TashiLogHandler(self.config)
		self.log.addHandler(messageHandler)
		# FIXME: why can't we log messages with severity below 'warning'?
		self.log.warning('test log message')
		time.sleep(0.5)
		self.assertEqual(self.sub.messageQueue.qsize(), 2)

		# This should generate at least one log message
#		 hosts = self.connection.client.getHosts()
#		 time.sleep(0.5)
#		 if (self.sub.messageQueue.qsize() <= 2):
#			 self.fail()

	def testUserManagement(self):
		'''test adding/removing/listing users

		same as testHostManagement, but with users'''
		usernames = ['sleepy', 'sneezy', 'dopey', 'doc',
					 'grumpy', 'bashful', 'happy']
		# add all users
		for un in usernames:
			user = User()
			user.username = un
			self.connection.client.addUser(user)
		# ensure that all were added
		users = self.connection.client.getUsers()
		self.assertEqual(len(usernames), len(users))
		for user in users:
			usernames.remove(user.username)
		self.assertEqual(0, len(usernames))
		# remove a random subset
		rm = random.sample(users, 4)
		for user in rm:
			self.connection.client.removeUser(user.id)
			users.remove(user)
		newUsers = self.connection.client.getUsers()
		# This ensures that the remaining ones are what we expect:
		for user in newUsers:
			# if there is a user remaining that we asked to be removed,
			# this will throw an exception
			users.remove(user)
		# if a user was removed that we did not intend, this will
		# throw an exception
		self.assertEqual(0, len(users))

#	 def testInstanceConfigurationManagement(self):
#		 '''test adding/removing/listing instance configurations

#		 same as testHostManagement, but with instance configurations'''
#		 self.fail('test not implemented')
	def testHardDiskConfigurationManagement(self):
		'''test adding/removing/listing hard disk configurations

		same as testHostManagement, but with hard disk configurations'''

		user = User(d={'username':'sleepy'})
		self.connection.client.addUser(user)
		users = self.connection.client.getUsers()

		per = PersistentImage()
		per.userId = users[0].id
		per.name = 'sleepy-PersistentImage'
		self.connection.client.addPersistentImage(per)
		pers = self.connection.client.getPersistentImages()

		inst = InstanceConfiguration()
		inst.name = 'sleepy-inst'
		inst.memory = 512
		inst.cores = 1
		self.connection.client.addInstanceConfiguration(inst)
		insts = self.connection.client.getInstanceConfigurations()

		hdc = HardDiskConfiguration()
		hdc.index = 0
		hdc.persistentImageId = pers[0].id
		hdc.persistent = False
		hdc.instanceConfigurationId = insts[0].id

#	 def testCreateDestroyShutdown(self):
#		 '''test creating/destroying/shutting down VMs

#		 not implemented'''
#		 self.fail('test not implemented')
#	 def testSuspendResume(self):
#		 '''test suspending/resuming VMs

#		 not implemented'''
#		 self.fail('test not implemented')
#	 def testMigrate(self):
#		 '''test migration

#		 not implemented'''
#		 self.fail('test not implemented')
#	 def testPauseUnpause(self):
#		 '''test pausing/unpausing VMs

#		 not implemented'''
#		 self.fail('test not implemented')


##############################
# Test Code
##############################
if __name__ == '__main__':
	logging.basicConfig(level=logging.NOTSET,
						format="%(asctime)s %(levelname)s:\t %(message)s",
						stream=sys.stdout)

	suite = unittest.TestLoader().loadTestsFromTestCase(TestClient)
	unittest.TextTestRunner(verbosity=2).run(suite)

