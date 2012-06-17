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

# XXXstroucki: shouldn't this be tashitypes.py instead?

class Errors(object):
	ConvertedException = 1
	NoSuchInstanceId = 2
	NoSuchVmId = 3
	IncorrectVmState = 4
	NoSuchHost = 5
	NoSuchHostId = 6
	InstanceIdAlreadyExists = 7
	HostNameMismatch = 8
	HostNotUp = 9
	HostStateError = 10
	InvalidInstance = 11
	UnableToResume = 12
	UnableToSuspend = 13

class InstanceState(object):
	Pending = 1
	Activating = 2
	Running = 3
	Pausing = 4
	Paused = 5
	Unpausing = 6
	Suspending = 7
	Resuming = 8
	MigratePrep = 9
	MigrateTrans = 10
	ShuttingDown = 11
	Destroying = 12
	Orphaned = 13
	Held = 14
	Exited = 15
	Suspended = 16

class HostState(object):
	Normal = 1
	Drained = 2
	VersionMismatch = 3

class TashiException(Exception):
	def __init__(self, d=None):
		self.errno = None
		self.msg = None
		if isinstance(d, dict):
			if 'errno' in d:
				self.errno = d['errno']
			if 'msg' in d:
				self.msg = d['msg']

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

	def __ne__(self, other):
		return not (self == other)

class Host(object):
	def __init__(self, d=None):
		self.id = None
		self.name = None
		self.up = None
		self.decayed = None
		self.state = None
		self.memory = None
		self.cores = None
		self.version = None
		self.notes = None
		self.reserved = []
		if isinstance(d, dict):
			if 'id' in d:
				self.id = d['id']
			if 'name' in d:
				self.name = d['name']
			if 'up' in d:
				self.up = d['up']
			if 'decayed' in d:
				self.decayed = d['decayed']
			if 'state' in d:
				self.state = d['state']
			if 'memory' in d:
				self.memory = d['memory']
			if 'cores' in d:
				self.cores = d['cores']
			if 'version' in d:
				self.version = d['version']
			if 'notes' in d:
				self.notes = d['notes']
			if 'reserved' in d:
				self.reserved = d['reserved']

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

	def __ne__(self, other):
		return not (self == other)

class Network(object):
	def __init__(self, d=None):
		self.id = None
		self.name = None
		if isinstance(d, dict):
			if 'id' in d:
				self.id = d['id']
			if 'name' in d:
				self.name = d['name']

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

	def __ne__(self, other):
		return not (self == other)

class LocalImages(object):
	def __init__(self, d=None):
		self.id = None
		self.userId = None
		self.imageName = None
		self.imageSize = None
		self.isPublic = None
		self.explicitUserIds = None
		if isinstance(d, dict):
			if 'id' in d:
				self.id = d['id']
			if 'userId' in d:
				self.userId = d['userId']
			if 'imageName' in d:
				self.imageName = d['imageName']
			if 'imageSize' in d:
				self.imageSize = d['imageSize']
			if 'isPublic' in d:
				self.isPublic = d['isPublic']
			if 'explicitUserIds' in d:
				self.explicitUserIds = d['explicitUserIds']

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

	def __ne__(self, other):
		return not (self == other)

class User(object):
	def __init__(self, d=None):
		self.id = None
		self.name = None
		self.passwd = None
		if isinstance(d, dict):
			if 'id' in d:
				self.id = d['id']
			if 'name' in d:
				self.name = d['name']
			if 'passwd' in d:
				self.passwd = d['passwd']

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

	def __ne__(self, other):
		return not (self == other)

class DiskConfiguration(object):
	def __init__(self, d=None):
		self.uri = None
		self.persistent = None
		if isinstance(d, dict):
			if 'uri' in d:
				self.uri = d['uri']
			if 'persistent' in d:
				self.persistent = d['persistent']

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

	def __ne__(self, other):
		return not (self == other)

class NetworkConfiguration(object):
	def __init__(self, d=None):
		self.network = None
		self.mac = None
		self.ip = None
		if isinstance(d, dict):
			if 'network' in d:
				self.network = d['network']
			if 'mac' in d:
				self.mac = d['mac']
			if 'ip' in d:
				self.ip = d['ip']

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

	def __ne__(self, other):
		return not (self == other)

class Instance(object):
	def __init__(self, d=None):
		self.id = None
		self.vmId = None
		self.hostId = None
		self.decayed = None
		self.state = None
		self.userId = None
		self.name = None
		self.cores = None
		self.memory = None
		self.disks = None
		#Quick fix so self.nics is not None
		self.nics = []
		self.hints = None
		self.groupName = None
		if isinstance(d, dict):
			if 'id' in d:
				self.id = d['id']
			if 'vmId' in d:
				self.vmId = d['vmId']
			if 'hostId' in d:
				self.hostId = d['hostId']
			if 'decayed' in d:
				self.decayed = d['decayed']
			if 'state' in d:
				self.state = d['state']
			if 'userId' in d:
				self.userId = d['userId']
			if 'name' in d:
				self.name = d['name']
			if 'cores' in d:
				self.cores = d['cores']
			if 'memory' in d:
				self.memory = d['memory']
			if 'disks' in d:
				self.disks = d['disks']
			if 'nics' in d:
				self.nics = d['nics']
			if 'hints' in d:
				self.hints = d['hints']
			if 'groupName' in d:
				self.groupName = d['groupName']

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

	def __ne__(self, other):
		return not (self == other)

class Key(object):
	def __init__(self, d=None):
		self.userId = None
		self.keyName = None
		self.fingerprint = None
		self.pubkey = None
		self.privkey = None
		if isinstance(d, dict):
			if 'userId' in d:
				self.userId = d['userId']
			if 'keyName' in d:
				self.keyName = d['keyName']
			if 'fingerprint' in d:
				self.fingerprint = d['fingerprint']
			if 'pubkey' in d:
				self.pubkey = d['pubkey']
			if 'privkey' in d:
				self.privkey = d['privkey']

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.userId == other.userId and self.keyName == other.keyName

	def __ne__(self, other):
		return not (self == other)

class Group(object):
	def __init__(self, d=None):
		self.userId = None
		self.groupName = None
		self.groupDescription = None
		self.ipPermissions = []
		if isinstance(d, dict):
			if 'userId' in d:
				self.userId = d['userId']
			if 'groupName' in d:
				self.groupName = d['groupName']
			if 'groupDescription' in d:
				self.groupDescription = d['groupDescription']
			if 'ipPermissions' in d:
				self.ipPermissions = d['ipPermissions']

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.userId == other.userId and self.groupName == other.groupName

	def __ne__(self, other):
		return not (self == other)

class GroupPermission(object):
	def __init__(self, d=None):
		self.targetUserId = None
		self.groupName = None
		if isinstance(d, dict):
			if 'targetUserId' in d:
				self.targetUserId = d['targetUserId']
			if 'groupName' in d:
				self.groupName = d['groupName']

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

	def __ne__(self, other):
		return not (self == other)

class IpPermission(object):
	def __init__(self, d=None):
		self.userId = None
		self.groupName = None
		self.ipProtocol = None
		self.fromPort = None
		self.toPort = None
		self.cidrIp = None
		self.groupPermissions = []
		if isinstance(d, dict):
			if 'userId' in d:
				self.userId = d['userId']
			if 'groupName' in d:
				self.groupName = d['groupName']
			if 'ipProtocol' in d:
				self.ipProtocol = d['ipProtocol']
			if 'fromPort' in d:
				self.fromPort = d['fromPort']
			if 'toPort' in d:
				self.toPort = d['toPort']
			if 'cidrIp' in d:
				self.cidrIp = d['cidrIp']
			if 'groupPermissions' in d:
				self.groupPermissions = d['groupPermissions']

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.groupName == other.groupName and self.userId == other.userId and self.ipProtocol == other.ipProtocol and self.fromPort == other.fromPort and self.toPort == other.toPort and self.cidrIp == other.cidrIp

	def __ne__(self, other):
		return not (self == other)

class Image(object):
	def __init__(self, d=None):
		self.userId = None
		self.imageId = None
		self.isPublic = False
		self.explicitUserIds = []
		self.s3path = None
		self.productCode = ''
		if isinstance(d, dict):
			if 'userId' in d:
				self.userId = d['userId']
			if 'imageId' in d:
				self.imageId = d['imageId']
			if 'isPublic' in d:
				self.isPublic = d['isPublic']
			if 'explicitUserIds' in d:
				self.explicitUserIds = d['explicitUserIds']
			if 's3path' in d:
				self.s3path = d['s3path']
			if 'productCode' in d:
				self.productCode = d['productCode']

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.imageId == other.imageId and self.userId == other.userId

	def __ne__(self, other):
		return not (self == other)

class Address(object):
	def __init__(self, d=None):
		self.userId = None
		self.publicIp = None
		self.instanceId = None
		if 'userId' in d:
			self.userId = d['userId']
		if 'publicIp' in d:
			self.publicIp = d['publicIp']
		if 'instanceId' in d:
			self.instanceId = d['instanceId']

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.userId == other.userId and self.publicIp == other.publicIp

	def __ne__(self, other):
		return not (self == other)
