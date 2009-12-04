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

import md5
import os
import random
import time
from tashi.aws.wsdl.AmazonEC2_services_server import *
from tashi.rpycservices.rpyctypes import *
from tashi.aws.util import *
import tashi.aws.util
import tashi

def getImages():
	IMGDIR="/mnt/merkabah/tashi/images/"
	imgList = os.listdir(IMGDIR)
	images = {}
	for img in imgList:
		fullImg = IMGDIR + img
		if (os.path.isdir(fullImg)):
			continue
		imageId = "ami-%8.8s" % (md5.md5(img).hexdigest())
		images[imageId] = img
	return images

def makeTashiInstanceEC2Instance(inst):
	res = RunInstancesResponseMsg()
	res = res.new_instancesSet()
	instanceItem = res.new_item()
	instanceItem.instanceId = "i-%8.8d" % (inst.id)
	instanceItem.imageId = "ami-%8.8s" % (md5.md5(inst.disks[0].uri).hexdigest())
	instanceItem.instanceState = instanceItem.new_instanceState()
	instanceItem.instanceState.code = inst.state
	instanceItem.instanceState.name = "%10.10s" % (tashi.vmStates[inst.state])
	instanceItem.privateDnsName = inst.name
	instanceItem.dnsName = str(inst.nics[0].ip)
	#instanceItem.reason = 'None'
	instanceItem.keyName = "%12.12d" % (inst.userId)
	instanceItem.amiLaunchIndex = str(inst.id)
	#instanceItem.productCodes = instanceItem.new_productCodes()
	#productItem = instanceItem.productCodes.new_item()
	#productItem.productCode = '774F4FF8'
	#instanceItem.productCodes.item = [productItem]
	sizeList = sizes.items()
	sizeList.sort(cmp=lambda x, y: cmp(cmp(x[1][0], y[1][0]) + cmp(x[1][1], y[1][1]), 0))
	sizeList.reverse()
	mySize = 'undef'
	for size in sizeList:
		if (inst.memory <= size[1][0] and inst.cores <= size[1][1]):
			mySize = size[0]
	instanceItem.instanceType = mySize
	instanceItem.launchTime = time.time()
	instanceItem.placement = instanceItem.new_placement()
	instanceItem.placement.availabilityZone = 'tashi'
	#instanceItem.kernelId = 'aki-ba3adfd3'
	#instanceItem.ramdiskId = 'ari-badbad00'
	#instanceItem.platform = 'Linux'
	instanceItem.monitoring = instanceItem.new_monitoring()
	instanceItem.monitoring.state = 'OFF'
	return instanceItem

def RunInstances(imageId, minCount, maxCount, instanceType='m1.small', groupSet=None, keyName=None, additionalInfo="", userData={'data':None}, addressingType="", placement={'availabilityZone':None}, kernelId="", ramdiskId="", blockDeviceMapping={'virtualName':None,'deviceName':None}, monitoring={'enabled':False}):
	inst = Instance()
	inst.userId = userNameToId(tashi.aws.util.authorizedUser)
	res = RunInstancesResponseMsg()
	res.requestId = genRequestId()
	if (additionalInfo == ""):
		inst.name = tashi.aws.util.authorizedUser + res.requestId
	else:
		inst.name = additionalInfo
	(inst.memory, inst.cores) = sizes.get(instanceType, (0, 0))
	dc = DiskConfiguration()
	images = getImages()
	if (imageId in images):
		dc.uri = images[imageId]
	else:
		dc.uri = imageId
	dc.persistent = False
	inst.disks = [dc]
	nc = NetworkConfiguration()
	nc.network = 999
	nc.mac = '52:54:00:%2.2x:%2.2x:%2.2x' % (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
	inst.nics = [nc]
	inst.hints = {}
	oldInst = inst
	inst = client.createVm(oldInst)
	res.reservationId = 'r-12345678'
	res.ownerId = 'UYY3TLBUXIEON5NQVUUX6OMPWBZIQNFM'
	res.groupSet = res.new_groupSet()
	item = res.groupSet.new_item()
	item.groupId = '1234'
	res.groupSet.item = [item]
	res.instancesSet = res.new_instancesSet()
	instanceItem = makeTashiInstanceEC2Instance(inst)
	res.instancesSet.item = [instanceItem]
	return res

def GetConsoleOutput():
	raise NotImplementedError

def TerminateInstances(instancesSet={'item':{}}):
	res = TerminateInstancesResponseMsg()
	res.requestId = genRequestId()
	res.instancesSet = res.new_instancesSet()
	items = []
	if (instancesSet):
		for instanceId in instancesSet['item'].values():
			thisInstanceId = int(filter(lambda x: x in "0123456789", instanceId))
			item = res.instancesSet.new_item()
			item.instanceId = str(instanceId)
			item.shutdownState = item.new_shutdownState()
			item.shutdownState.code = InstanceState.Exited
			item.shutdownState.name = tashi.vmStates[InstanceState.Exited]
			item.previousState = item.new_previousState()
			item.previousState.code = InstanceState.Running
			item.previousState.name = tashi.vmStates[InstanceState.Running]
			client.destroyVm(int(thisInstanceId))
			items.append(item)
	res.instancesSet.item = items
	return res

def RebootInstances():
	raise NotImplementedError

def DescribeInstances(instancesSet={}):
	instances = client.getInstances()
	res = DescribeInstancesResponseMsg()
	res.requestId = genRequestId()
	res.reservationSet = res.new_reservationSet()
	item = res.reservationSet.new_item()
	item.reservationId = 'r-12345678'
	item.ownerId = 'UYY3TLBUXIEON5NQVUUX6OMPWBZIQNFM'
	item.groupSet = item.new_groupSet()
	groupItem = item.groupSet.new_item()
	groupItem.groupId = 'default'
	item.groupSet.item = [groupItem]
	item.instancesSet = item.new_instancesSet()
	item.instancesSet.item = []
	instances.sort(cmp=lambda x, y: cmp(x.id, y.id))
	for inst in instances:
		userName = userIdToName(inst.userId)
		if (userName == tashi.aws.util.authorizedUser):
			instanceItem = makeTashiInstanceEC2Instance(inst)
			item.instancesSet.item.append(instanceItem)
	# For some reason, if item.instancesSet is empty,
	# "Server: Processing Failure is printed out on the command line.
	item.requesterId = '1234'
	res.reservationSet.item = [item]
	return res

functions = ['RunInstances', 'GetConsoleOutput', 'TerminateInstances', 'RebootInstances', 'DescribeInstances']
