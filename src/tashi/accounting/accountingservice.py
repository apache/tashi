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

import logging
import threading
import time

from tashi import createClient

class AccountingService(object):
	"""RPC service for the Accounting service"""

	def __init__(self, config):
		self.log = logging.getLogger(__name__)
		self.log.setLevel(logging.INFO)

		self.config = config

		self.pollSleep = None

		# XXXstroucki new python has fallback values
		try:
			self.pollSleep = self.config.getint("AccountingService", "pollSleep")
		except:
			pass

		if self.pollSleep is None:
			self.pollSleep = 600

		self.cm = createClient(config)
		threading.Thread(target=self.__start).start()

	# remote
	def record(self, strings):
		for string in strings:
			self.log.info("Remote: %s" % (string))

	def __start(self):
		while True:
			try:
				instances = self.cm.getInstances()
				for instance in instances:
					# XXXstroucki this currently duplicates what the CM was doing.
					self.log.info('Accounting: id %s host %s vmId %s user %s cores %s memory %s' % (instance.id, instance.hostId, instance.vmId, instance.userId, instance.cores, instance.memory))
			except:
				self.log.warning("Accounting iteration failed")


			# wait to do the next iteration
			time.sleep(self.pollSleep)
