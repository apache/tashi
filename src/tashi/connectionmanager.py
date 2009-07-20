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

import rpyc
from tashi.rpycservices import rpycservices
from tashi.rpycservices.rpyctypes import *

class ConnectionManager(object):
	def __init__(self, username, password, port, timeout=10000.0):
		self.username = username
		self.password = password
		self.timeout = timeout
		self.port = port
	
	def __getitem__(self, hostname):
		port = self.port
		if len(hostname) == 2:
			port = hostname[1]
			hostname = hostname[0]

		return rpycservices.client(hostname, port, username=self.username, password=self.password)
