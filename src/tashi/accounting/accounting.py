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
import time
import random
import logging.config

from tashi.rpycservices.rpyctypes import *
from tashi.util import getConfig, createClient, instantiateImplementation, boolean
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
					
	def start(self):
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

def main():
	(config, configFiles) = getConfig(["Accounting"])
	publisher = instantiateImplementation(config.get("Accounting", "publisher"), config)
	tashi.publisher = publisher
	cmclient = createClient(config)
	logging.config.fileConfig(configFiles)
	accounting = Accounting(config, cmclient)
	accounting.start()

if __name__ == "__main__":
	main()
