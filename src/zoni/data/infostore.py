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


class InfoStore (object):
	"""  Interface description for query system resources
    """
	def __init__(self, config):
		self.config = config

	#def updateDatabase(self, query):
		#raise NotImplementedError

	def addDomain(self):
		raise NotImplementedError

	def removeDomain(self):
		raise NotImplementedError

	def showDomains(self):
		raise NotImplementedError

	def addVlan(self):
		raise NotImplementedError

	def removeVlan(self):
		raise NotImplementedError

	def showVlans(self):
		raise NotImplementedError

	def assignVlan(self):
		raise NotImplementedError

	def printAll(self):
		raise NotImplementedError

	def showResources(self, cmdargs):
		raise NotImplementedError
	
	def printResources(self):
		raise NotImplementedError

	def showAllocation(self):
		raise NotImplementedError

	def showPxeImages(self):
		raise NotImplementedError

	def showPxeImagesToSystemMap(self):
		raise NotImplementedError

	def getHwAccessMethod(self):
		'''  Get hardware access method and return a list 
		'''
		raise NotImplementedError
	
	def addPxeImage(self):
		raise NotImplementedError

	def removePxeImage(self):
		raise NotImplementedError

	def assignPxeImage(self):
		raise NotImplementedError

