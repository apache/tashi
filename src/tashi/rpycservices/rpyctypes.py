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

	def __str__(self): 
		return str(self.__dict__)

	def __repr__(self): 
		return repr(self.__dict__)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

	def __ne__(self, other):
		return not (self == other)

