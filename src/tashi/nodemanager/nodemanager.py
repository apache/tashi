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

import logging.config
import signal
import sys
from thrift.transport.TSocket import TServerSocket
from thrift.server.TServer import TThreadedServer

from tashi.util import instantiateImplementation, getConfig, debugConsole, signalHandler
from tashi.services import nodemanagerservice, clustermanagerservice
from tashi import ConnectionManager

import notification

@signalHandler(signal.SIGTERM)
def handleSIGTERM(signalNumber, stackFrame):
	sys.exit(0)

def main():
	global config, dfs, vmm, service, server, log, notifier
	
	(config, configFiles) = getConfig(["NodeManager"])
	logging.config.fileConfig(configFiles)
	log = logging.getLogger(__name__)
	log.info('Using configuration file(s) %s' % configFiles)
	dfs = instantiateImplementation(config.get("NodeManager", "Dfs"), config)
	vmm = instantiateImplementation(config.get("NodeManager", "VmControl"), config, dfs, None)
	service = instantiateImplementation(config.get("NodeManager", "Service"), config, vmm)
	vmm.nm = service
	processor = nodemanagerservice.Processor(service)
	transport = TServerSocket(int(config.get('NodeManagerService', 'port')))
	server = TThreadedServer(processor, transport)
	debugConsole(globals())
	
        notifier = notification.Notifier(config)
        log.addHandler(notifier)

	try:
		server.serve()
	except KeyboardInterrupt:
		handleSIGTERM(signal.SIGTERM, None)
	except Exception, e:
		sys.stderr.write(str(e) + "\n")
		sys.exit(-1)

if __name__ == "__main__":
	main()
