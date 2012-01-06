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

from datetime import datetime
from random import randint
from socket import gethostname
import logging
import threading
import time

from tashi.rpycservices.rpyctypes import Errors, InstanceState, HostState, TashiException
from tashi import boolean, convertExceptions, ConnectionManager, vmStates, timed, version, scrubString, createClient

class AccountingService(object):
        """RPC service for the Accounting service"""
        
        def __init__(self, config):
            self.log = logging.getLogger(__name__)
            self.log.setLevel(logging.INFO)

            self.cm = createClient(config)
            threading.Thread(target=self.__start).start()

        def record(self, strings):
            print "here"
            for string in strings:
                self.log.info("Remote: %s" % (string))

        def __start(self):
            while True:
                try:
                    instances = self.cm.getInstances()
                    for instance in instances:
                        # XXXstroucki this currently duplicates what the CM was doing.
                        # perhaps implement a diff-like log?    
                        self.log.info('Accounting: id %d host %d vmId %d user %d cores %d memory %d' % (instance.id, instance.hostId, instance.vmId, instance.userId, instance.cores, instance.memory))
                except:
                    self.log.warning("Accounting iteration failed")

                        
                # wait to do the next iteration
                # XXXstroucki make this configurable?                   
                time.sleep(60)
