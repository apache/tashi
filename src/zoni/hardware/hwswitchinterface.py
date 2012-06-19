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


class HwSwitchInterface(object):
	"""  Interface description for hardware switches
          - Dell
    """
	def __init__(self, configFile, hostInst = None):
		'''  
			hostInst is all data that makes up a host
			hw_port - port number node is connected to
			hw_userid - userid node uses to configure switch
			hw_password - userid node uses to configure switch
			hw_name - switch name node is connected to
		'''
		#self.host = hostInst


	def enablePort(self):
		raise NotImplementedError

	def disablePort(self):
		raise NotImplementedError

	def removeVlan(self, vlan):
		raise NotImplementedError

	def createVlan(self, vlan):
		raise NotImplementedError

	def addNode2Vlan(self, vlan, taginfo):
		raise NotImplementedError

	def removeNodeFromVlan(self, vlan):
		raise NotImplementedError

	def addNativeVlan(self, vlan):
		raise NotImplementedError

	def restoreNativeVlan(self):
		raise NotImplementedError

	def isolateNetwork(self):
		raise NotImplementedError

	def registerToZoni(self):
		raise NotImplementedError

