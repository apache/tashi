#! /usr/bin/python

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

import logging.config
import sys
import os

from tashi.util import instantiateImplementation, debugConsole
import tashi
from tashi import boolean

from tashi.rpycservices import rpycservices
from tashi.utils.config import Config

from rpyc.utils.server import ThreadedServer
from rpyc.utils.authenticators import TlsliteVdbAuthenticator

def main():
	global config, log
	
	config = Config(["NodeManager"])
	configFiles = config.getFiles()

	logging.config.fileConfig(configFiles)
	log = logging.getLogger(__name__)
	log.info('Using configuration file(s) %s' % configFiles)

	# handle keyboard interrupts (http://code.activestate.com/recipes/496735-workaround-for-missed-sigint-in-multithreaded-prog/)
	child = os.fork()
	
	if child == 0:
		startNodeManager()
		# shouldn't exit by itself
		sys.exit(0)

	else:
		# main
		try:
			os.waitpid(child, 0)
		except KeyboardInterrupt:
			log.info("Exiting node manager after receiving a SIGINT signal")
			os._exit(0)
		except Exception:
			log.exception("Abnormal termination of node manager")
			os._exit(-1)

		log.info("Exiting node manager after service thread exited")
		os._exit(-1)

	return

def startNodeManager():
	global config, dfs, vmm, service, server, log, notifier
	publisher = instantiateImplementation(config.get("NodeManager", "publisher"), config)
	tashi.publisher = publisher
	dfs = instantiateImplementation(config.get("NodeManager", "dfs"), config)
	vmm = instantiateImplementation(config.get("NodeManager", "vmm"), config, dfs, None)
	service = instantiateImplementation(config.get("NodeManager", "service"), config, vmm)
	vmm.nm = service

	if boolean(config.get("Security", "authAndEncrypt")):
		users = {}
		users[config.get('AllowedUsers', 'clusterManagerUser')] = config.get('AllowedUsers', 'clusterManagerPassword')
		authenticator = TlsliteVdbAuthenticator.from_dict(users)

		# XXXstroucki: ThreadedServer is liable to have exceptions
		# occur within if an endpoint is lost.
		t = ThreadedServer(service=rpycservices.ManagerService, hostname='0.0.0.0', port=int(config.get('NodeManagerService', 'port')), auto_register=False, authenticator=authenticator)
	else:
		t = ThreadedServer(service=rpycservices.ManagerService, hostname='0.0.0.0', port=int(config.get('NodeManagerService', 'port')), auto_register=False)
	t.logger.setLevel(logging.ERROR)
	t.service.service = service
	t.service._type = 'NodeManagerService'

	debugConsole(globals())

	t.start()
	# shouldn't exit by itself
	sys.exit(0)


if __name__ == "__main__":
	main()
