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

enum Errors {
	ConvertedException = 1,
	NoSuchInstanceId = 2,
	NoSuchVmId = 3,
	IncorrectVmState = 4,
	NoSuchHost = 5,
	NoSuchHostId = 6,
	InstanceIdAlreadyExists = 7,
	HostNameMismatch = 8,
	HostNotUp = 9,
	HostStateError = 10
}

enum InstanceState {
	Pending = 1,		// Job submitted
	Activating = 2,		// activateVm has been called, but instantiateVm hasn't finished yet
	Running = 3,		// Normal state
	Pausing = 4,		// Beginning pause sequence
	Paused = 5		// Paused
	Unpausing = 6,		// Beginning unpause sequence
	Suspending = 7,		// Beginning suspend sequence
	Resuming = 8,		// Beginning resume sequence
	MigratePrep = 9,	// Migrate state #1
	MigrateTrans = 10,	// Migrate state #2
	ShuttingDown = 11,	// Beginning exit sequence
	Destroying = 12,	// Beginning exit sequence
	Orphaned = 13,		// Host is missing
	Held = 14,		// Activation failed
	Exited = 15		// VM has exited
}

enum HostState {
	Normal = 1,
	Drained = 2
}

exception TashiException {
	1: Errors errno
	2: string msg
}

struct Host {
	1:i32 id,
	2:string name,
	3:bool up,
	4:bool decayed,
	5:HostState state,
	6:i32 memory,
	7:i32 cores
	// Other properties (disk?)
}

struct Network {
	1:i32 id
	2:string name
}

struct User {
	1:i32 id,
	2:string name
}

struct MachineType {
	1:i32 id,
	2:string name,
	3:i32 memory,
	4:i32 cores
}

struct DiskConfiguration {
	1:string uri,
	2:bool persistent
}

struct NetworkConfiguration {
	1:i32 network
	2:string mac
}

struct Instance {
	1:i32 id,
	2:i32 vmId,
	3:i32 hostId,
	4:Host hostObj,
	5:bool decayed,
	6:InstanceState state,
	7:i32 userId,
	8:User userObj,
	9:string name, // User specified
	10:i32 type, // User specified
	11:MachineType typeObj,
	12:list<DiskConfiguration> disks, // User specified
	13:list<NetworkConfiguration> nics // User specified
	14:map<string, string> hints // User specified
}

service clustermanagerservice {
	// Client-facing RPCs
	Instance createVm(1:Instance instance) throws (1:TashiException e)
	
	void shutdownVm(1:i32 instanceId) throws (1:TashiException e)
	void destroyVm(1:i32 instanceId) throws (1:TashiException e)
	
	void suspendVm(1:i32 instanceId, 2:string destination) throws (1:TashiException e)
	Instance resumeVm(1:Instance instance, 2:string source) throws (1:TashiException e)
	
	void migrateVm(1:i32 instanceId, 2:i32 targetHostId) throws (1:TashiException e)
	
	void pauseVm(1:i32 instanceId) throws (1:TashiException e)
	void unpauseVm(1:i32 instanceId) throws (1:TashiException e)
	
	list<MachineType> getMachineTypes() throws (1:TashiException e)
	list<Host> getHosts() throws (1:TashiException e)
	list<Network> getNetworks() throws (1:TashiException e)
	list<User> getUsers() throws (1:TashiException e)

	list<Instance> getInstances() throws (1:TashiException e)
	
	// NodeManager-facing RPCs
	i32 registerNodeManager(1:Host host, 2:list<Instance> instances) throws (1:TashiException e)
	void vmUpdate(1:i32 instanceId, 2:Instance instance, 3:InstanceState old) throws (1:TashiException e)

	// Agent-facing RPCs
	void activateVm(1:i32 instanceId, 2:Host host) throws (1:TashiException e)
}

// RPC-specific types
struct ResumeVmRes {
	1:i32 vmId,
	2:string suspendCookie
}

service nodemanagerservice {
	// ClusterManager-facing RPCs
	i32 instantiateVm(1:Instance instance) throws (1:TashiException e)
	
	void shutdownVm(1:i32 vmId) throws (1:TashiException e)
	void destroyVm(1:i32 vmId) throws (1:TashiException e)
	
	void suspendVm(1:i32 vmId, 2:string destination, 3:string suspendCookie) throws (1:TashiException e)
	ResumeVmRes resumeVm(1:Instance instance, 2:string source) throws (1:TashiException e)
	
	string prepReceiveVm(1:Instance instance, 2:Host source) throws (1:TashiException e)
	void migrateVm(1:i32 vmId, 2:Host target, 3:string transportCookie) throws (1:TashiException e)
	void receiveVm(1:Instance instance, 2:string transportCookie) throws (1:TashiException e)
	
	void pauseVm(1:i32 vmId) throws (1:TashiException e)
	void unpauseVm(1:i32 vmId) throws (1:TashiException e)

	Instance getVmInfo(1:i32 vmId) throws (1:TashiException e)
	list<i32> listVms() throws (1:TashiException e)

	// Host getHostInfo() throws (1:TashiException e)
}
