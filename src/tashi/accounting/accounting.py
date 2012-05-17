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

import os
import time
import sys
import signal
import logging.config

from tashi.rpycservices import rpycservices
from rpyc.utils.server import ThreadedServer
#from rpyc.utils.authenticators import TlsliteVdbAuthenticator

#from tashi.rpycservices.rpyctypes import *
from tashi.util import createClient, instantiateImplementation, boolean, debugConsole
from tashi.utils.config import Config

import tashi

class Accounting(object):
	def __init__(self, config):
		self.config = config
		self.cm = createClient(config)
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

		#if boolean(self.config.get("Security", "authAndEncrypt")):
		if False:
			pass
		else:
			t = ThreadedServer(service=rpycservices.ManagerService, hostname='0.0.0.0', port=int(self.config.get('AccountingService', 'port')), auto_register=False)

		t.logger.setLevel(logging.ERROR)
		t.service.service = service
		t.service._type = 'AccountingService'

		debugConsole(globals())

		t.start()
		# shouldn't exit by itself
		sys.exit(0)

def main():
	config = Config(["Accounting"])
	configFiles = config.getFiles()
	publisher = instantiateImplementation(config.get("Accounting", "publisher"), config)
	tashi.publisher = publisher
	logging.config.fileConfig(configFiles)
	log = logging.getLogger(__name__)
	log.info('Using configuration file(s) %s' % configFiles)

	accounting = Accounting(config)

	# handle keyboard interrupts (http://code.activestate.com/recipes/496735-workaround-for-missed-sigint-in-multithreaded-prog/)
	child = os.fork()

	if child == 0:
		accounting.initAccountingServer()
		# shouldn't exit by itself
		sys.exit(0)

	else:
		# main
		try:
			os.waitpid(child, 0)
		except KeyboardInterrupt:
			log.info("Exiting accounting service after receiving a SIGINT signal")
			os._exit(0)
		except Exception:
			log.exception("Abnormal termination of accounting service")
			os._exit(-1)

		log.info("Exiting accounting service after service thread exited")
		os._exit(-1)

	return

if __name__ == "__main__":
	main()
