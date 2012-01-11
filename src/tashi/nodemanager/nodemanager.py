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
import signal
import sys

from tashi.util import instantiateImplementation, getConfig, debugConsole, signalHandler
import tashi
from tashi import boolean

from tashi.rpycservices import rpycservices
from rpyc.utils.server import ThreadedServer
from rpyc.utils.authenticators import TlsliteVdbAuthenticator

@signalHandler(signal.SIGTERM)
def handleSIGTERM(signalNumber, stackFrame):
	sys.exit(0)

def main():
	global config, dfs, vmm, service, server, log, notifier
	
	(config, configFiles) = getConfig(["NodeManager"])
	publisher = instantiateImplementation(config.get("NodeManager", "publisher"), config)
	tashi.publisher = publisher
	logging.config.fileConfig(configFiles)
	log = logging.getLogger(__name__)
	log.info('Using configuration file(s) %s' % configFiles)
	dfs = instantiateImplementation(config.get("NodeManager", "dfs"), config)
	vmm = instantiateImplementation(config.get("NodeManager", "vmm"), config, dfs, None)
	service = instantiateImplementation(config.get("NodeManager", "service"), config, vmm)
	vmm.nm = service

	if boolean(config.get("Security", "authAndEncrypt")):
		users = {}
		users[config.get('AllowedUsers', 'clusterManagerUser')] = config.get('AllowedUsers', 'clusterManagerPassword')
		authenticator = TlsliteVdbAuthenticator.from_dict(users)
		t = ThreadedServer(service=rpycservices.ManagerService, hostname='0.0.0.0', port=int(config.get('NodeManagerService', 'port')), auto_register=False, authenticator=authenticator)
	else:
		t = ThreadedServer(service=rpycservices.ManagerService, hostname='0.0.0.0', port=int(config.get('NodeManagerService', 'port')), auto_register=False)
	t.logger.setLevel(logging.ERROR)
	t.service.service = service
	t.service._type = 'NodeManagerService'

	debugConsole(globals())
	
	try:
		t.start()
	except KeyboardInterrupt:
		handleSIGTERM(signal.SIGTERM, None)
	except Exception, e:
		sys.stderr.write(str(e) + "\n")
		sys.exit(-1)

if __name__ == "__main__":
	main()
