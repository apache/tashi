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

# module to provide a thread timeout monitor
# by Alexey Tumanov and Michael Stroucken

import threading

class TimeoutException(Exception):
	def __init__(self, string):
		Exception.__init__(self,'Timeout: %s' % string)

class TimeoutThread:
	def __init__(self, function, args = (), kwargs = {}):
		self.cv	   = threading.Condition()
		self.function = function
		self.args = args
		self.kwargs = kwargs
		self.finished = False
		self.rval	 = None

	def wait(self, timeout=None):
		self.cv.acquire()
		if not self.finished:
			if timeout:
				self.cv.wait(timeout)
			else:
				self.cv.wait()
		finished = self.finished
		rval	 = self.rval
		self.cv.release()

		#
		# Raise an exception if a timeout occurred.
		#
		if finished:
			return rval
		else: # NOTE: timeout must be set for this to be true.
			raise TimeoutException("function %s timed out after %f seconds" % (str(self.function), timeout))

	def run(self):
		try:
			rval = self.function(*self.args, **self.kwargs)
		except Exception, e:
			rval = e

		self.cv.acquire()
		self.finished = True
		self.rval	 = rval
		self.cv.notify()
		self.cv.release()

