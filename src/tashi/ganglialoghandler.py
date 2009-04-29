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
import os.path
import sys
import time

import tashi

logging.tashi = tashi

class GangliaLogHandler(logging.Handler):
	def __init__(self, dmax, retry):
		logging.Handler.__init__(self)
		self.dmax = dmax
		self.retry = retry
		self.name = os.path.basename(sys.argv[0])
		self.msgIndex = 0
		self.disable = False
		self.disableAt = 0.0
	
	def emit(self, record):
		now = time.time()
		if (self.disable):
			if (now - self.disableAt > self.retry):
				disable = False
			else:
				return
		try:
			msg = self.format(record)
			metricName = "tashi_log_%s_%d_%d" % (self.name, self.msgIndex, int(now*1000))
			metricValue = msg.replace('"', "'")
			metricType = "string"
			(stdin, stdout) = os.popen4('gmetric -n "%s" -v "%s" -t "%s" -d "%d"' % (metricName, metricValue, metricType, self.dmax))
			stdin.close()
			res = stdout.read()
			if (res != ""):
				print "Failed to exec gmetric, disabling: %s" % (res)
				self.disable = True
				self.disableAt = now
			stdout.close()
			self.msgIndex = self.msgIndex + 1
		except Exception, e:
			print e
