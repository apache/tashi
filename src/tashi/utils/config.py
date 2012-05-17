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

# Wrapper class for python configuration

class Config:
	def __init__(self, additionalNames=[], additionalFiles=[]):
		from tashi.util import getConfig
		(config, files) = getConfig(additionalNames = additionalNames, additionalFiles = additionalFiles)
		self.config = config
		self.files = files

	def getFiles(self):
		return self.files

	def get(self, section, option, default = None):
		# soft version of self.config.get. Returns configured
		# value or default value (if specified) or None.
		import ConfigParser

		value = default
		try:
			value = self.config.get(section, option)
		except ConfigParser.NoOptionError:
			pass

		return value

	def getint(self, section, option, default = None):
		# soft version of self.config.getint. Returns configured
		# value forced to int or default value (as and if specified)
		# or None.
		import ConfigParser

		value = default
		try:
			value = self.config.get(section, option)
			value = int(value)
		except ConfigParser.NoOptionError:
			pass

		return value
