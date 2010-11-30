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
#
#  $Id$
#

import os
import sys
import threading
import signal
import logging.config
import signal

from tashi.util import instantiateImplementation, signalHandler

from zoni.extra.util import loadConfigFile, getConfig, debugConsole
from zoni.version import *
from zoni.services.hardwareservice import HardwareService
from zoni.services.pcvciservice import pcmService
from zoni.services.rpycservices import ManagerService

from rpyc.utils.server import ThreadedServer





def startZoniManager(config):

	data = instantiateImplementation("zoni.data.resourcequerysql.ResourceQuerySql", config)
	service = instantiateImplementation("zoni.services.pcvciservice.pcmService", config, data)
	#hardware = instantiateImplementation("zoni.services.hardwareservice.HardwareService", config, data)

	t = ThreadedServer(service=ManagerService, hostname='0.0.0.0', port=12345, auto_register=False )
	t.logger.quiet = True
	t.service.service = service
	#t.service.hardware = hardware
	t.service._type = "pcmService"
	debugConsole(globals())
	t.start()

def main():
	(configs, configFiles) = getConfig()
	logging.config.fileConfig(configFiles)
	log = logging.getLogger(os.path.basename(__file__))

	mesg = "Starting Zoni Manager"
	log.info(mesg)
	startZoniManager(configs)
	





if __name__ == "__main__":
	main()
