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
import time
import types

from tashi import scrubString

class GangliaPublisher(object):
	def __init__(self, config):
		self.disable = False
		self.disableAt = 0.0
		self.retry = float(config.get("GangliaPublisher", "retry"))
		self.dmax = float(config.get("GangliaPublisher", "dmax"))

	def publish(self, message):
		for (key, val) in message.iteritems():
			if (self.disable):
				if (time.time() - self.disableAt > self.retry):
					disable = False
				else:
					return
			key = scrubString(str(key))
			val = str(val)
			metricName = "tashi_%s" % (key)
			val = val.replace('"', "'")
			val = val.replace('<', '&lt;')
			val = val.replace('>', '&gt;')
			metricValue = val
			metricType = "string"
			try:
				metricValue = float(metricValue)
				metricType = "float"
				metricValue = "%3.3f" % (metricValue)
			except:
				pass
			cmd = 'gmetric -n "%s" -v "%s" -t "%s" -d "%d"' % (metricName, metricValue, metricType, self.dmax)
# XXXpipe: send a datum to ganglia
			(stdin, stdout) = os.popen4(cmd)
			stdin.close()
			res = stdout.read()
			stdout.close()
			if (res != ""):
				self.disable = True
				self.disableAt = time.time()
				print "Failed to exec gmetric, disabling: %s" % (res)
	
	def publishList(self, messages):
		for message in messages:
			self.publish(message)
