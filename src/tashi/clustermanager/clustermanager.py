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

import os
import sys
import threading
import signal
import logging.config
from getopt import getopt, GetoptError
from ConfigParser import ConfigParser
from thrift.transport.TSocket import TServerSocket
from thrift.server.TServer import TThreadedServer

from tashi.messaging.thriftmessaging import MessageBrokerThrift
from tashi.messaging.tashimessaging import TashiLogHandler
from tashi.services import clustermanagerservice
from tashi.util import signalHandler, boolean, instantiateImplementation, getConfig, debugConsole

def startClusterManager(config):
    global service, data
    
    # start the event broker
    broker = MessageBrokerThrift(int(config.get('MessageBroker', 'port')))
    broker.ready.wait()
    messageHandler = TashiLogHandler(config)
    log.addHandler(messageHandler)

    data = instantiateImplementation(config.get("ClusterManager", "data"), config)
    service = instantiateImplementation(config.get("ClusterManager", "service"), config, data)
    processor = clustermanagerservice.Processor(service)
    transport = TServerSocket(int(config.get('ClusterManagerService', 'port')))
    server = TThreadedServer(processor, transport)
    
    debugConsole(globals())
    
    try:
        server.serve()
    except KeyboardInterrupt:
        handleSIGTERM(signal.SIGTERM, None)

@signalHandler(signal.SIGTERM)
def handleSIGTERM(signalNumber, stackFrame):
    log.info('Exiting cluster manager after receiving a SIGINT signal')
    sys.exit(0)
    
def main():
    global log
    
    # setup configuration and logging
    (config, configFiles) = getConfig(["ClusterManager"])
    logging.config.fileConfig(configFiles)
    log = logging.getLogger(__file__)
    log.info('Using configuration file(s) %s' % configFiles)
    
    # bind the database
    log.info('Starting cluster manager')
    startClusterManager(config)

if __name__ == "__main__":
    main()
