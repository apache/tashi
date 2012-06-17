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


class SystemManagementInterface(object):
	"""  Interface description for hardware management controllers 
          - IPMI
          - IOL
    """
	def __init__(self, config):
		self.config = config


	def getPowerStatus(self):
		raise NotImplementedError

	def isPowered(self):
		'''  Return boolean if system is powered on or not  '''
		raise NotImplementedError
	
	def powerOn(self):
		'''  Powers on a system '''
		raise NotImplementedError

	def powerOff(self):
		'''  Powers off a system '''
		raise NotImplementedError

	def powerOffSoft(self):
		'''  Powers off a system via acpi'''
		raise NotImplementedError

	def powerCycle(self):
		'''  Powers cycles a system '''
		raise NotImplementedError

	def powerReset(self):
		'''  Resets a system '''
		raise NotImplementedError

	def activateConsole(self):
		'''  Activate Console'''
		raise NotImplementedError

	def registerToZoni(self):
		'''  register hardware to zoni'''
		raise NotImplementedError





