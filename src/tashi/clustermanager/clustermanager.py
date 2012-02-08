#!/usr/bin/env python

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

import sys
import signal
import logging.config

from tashi.util import signalHandler, boolean, instantiateImplementation, getConfig, debugConsole
import tashi

from tashi.rpycservices import rpycservices
from rpyc.utils.server import ThreadedServer

log = None

def startClusterManager(config):
	global service, data
	
	dfs = instantiateImplementation(config.get("ClusterManager", "dfs"), config)
	data = instantiateImplementation(config.get("ClusterManager", "data"), config)
	service = instantiateImplementation(config.get("ClusterManager", "service"), config, data, dfs)

	if boolean(config.get("Security", "authAndEncrypt")):
		users = {}
		userDatabase = data.getUsers()
		for user in userDatabase.values():
			if user.passwd != None:
				users[user.name] = user.passwd
		users[config.get('AllowedUsers', 'nodeManagerUser')] = config.get('AllowedUsers', 'nodeManagerPassword')
		users[config.get('AllowedUsers', 'agentUser')] = config.get('AllowedUsers', 'agentPassword')
		authenticator = rpycservices.UsernamePasswordAuthenticator(config, users)
		t = ThreadedServer(service=rpycservices.ManagerService, hostname='0.0.0.0', port=int(config.get('ClusterManagerService', 'port')), auto_register=False, authenticator=authenticator)
	else:
		t = ThreadedServer(service=rpycservices.ManagerService, hostname='0.0.0.0', port=int(config.get('ClusterManagerService', 'port')), auto_register=False)
	t.logger.setLevel(logging.ERROR)
	t.service.service = service
	t.service._type = 'ClusterManagerService'

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
	global log
	
	# setup configuration and logging
	(config, configFiles) = getConfig(["ClusterManager"])
	publisher = instantiateImplementation(config.get("ClusterManager", "publisher"), config)
	tashi.publisher = publisher
	logging.config.fileConfig(configFiles)
	log = logging.getLogger(__file__)
	log.info('Using configuration file(s) %s' % configFiles)
	
	# bind the database
	log.info('Starting cluster manager')
	startClusterManager(config)

if __name__ == "__main__":
	main()
