#!/usr/bin/python

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

from socket import gethostname
import os
import socket
import sys
import threading
import signal
import time
import random
import logging.config

from tashi.rpycservices import rpycservices
from rpyc.utils.server import ThreadedServer
from rpyc.utils.authenticators import TlsliteVdbAuthenticator

from tashi.rpycservices.rpyctypes import *
from tashi.util import getConfig, createClient, instantiateImplementation, boolean, debugConsole, signalHandler
import tashi

class Accounting(object):
	def __init__(self, config, cmclient):
		self.config = config
		self.cm = cmclient
		self.hooks = []
		self.log = logging.getLogger(__file__)

		items = self.config.items("Accounting")
		items.sort()
		for item in items:
			(name, value) = item
			name = name.lower()
			if (name.startswith("hook")):
				try:
					self.hooks.append(instantiateImplementation(value, config, cmclient, False))
				except:
					self.log.exception("Failed to load hook %s" % (value))
					
	def initAccountingServer(self):
		service = instantiateImplementation(self.config.get("Accounting", "service"), self.config)

		if boolean(self.config.get("Security", "authAndEncrypt")):
			users = {}
			userDatabase = data.getUsers()
			for user in userDatabase.values():
				if user.passwd != None:
					users[user.name] = user.passwd
			users[self.config.get('AllowedUsers', 'clusterManagerUser')] = self.config.get('AllowedUsers', 'clusterManagerPassword')
			users[self.config.get('AllowedUsers', 'nodeManagerUser')] = self.config.get('AllowedUsers', 'nodeManagerPassword')
			users[self.config.get('AllowedUsers', 'agentUser')] = self.config.get('AllowedUsers', 'agentPassword')
			authenticator = TlsliteVdbAuthenticator.from_dict(users)
			t = ThreadedServer(service=rpycservices.ManagerService, hostname='0.0.0.0', port=int(self.config.get('AccountingService', 'port')), auto_register=False, authenticator=authenticator)
		else:
			t = ThreadedServer(service=rpycservices.ManagerService, hostname='0.0.0.0', port=int(self.config.get('AccountingService', 'port')), auto_register=False)
			print "ah"

		t.logger.setLevel(logging.ERROR)
		t.service.service = service
		t.service._type = 'AccountingService'

		debugConsole(globals())

		try:
			t.start()
		except KeyboardInterrupt:
			handleSIGTERM(signal.SIGTERM, None)

	@signalHandler(signal.SIGTERM)
	def handleSIGTERM(signalNumber, stackFrame):
		global log
		
		log.info('Exiting cluster manager after receiving a SIGINT signal')
		sys.exit(0)

def main():
	(config, configFiles) = getConfig(["Accounting"])
	publisher = instantiateImplementation(config.get("Accounting", "publisher"), config)
	tashi.publisher = publisher
	cmclient = createClient(config)
	logging.config.fileConfig(configFiles)
	accounting = Accounting(config, cmclient)

	accounting.initAccountingServer()

if __name__ == "__main__":
	main()
