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

from tashi.aws.wsdl.AmazonEC2_services_server import *
from tashi.aws.util import *
from tashi.rpycservices.rpyctypes import *

def CreateSecurityGroup(groupName, groupDescription):
	res = CreateSecurityGroupResponseMsg()
	res.requestId = genRequestId()
	res.__dict__['return'] = True
	userId = userNameToId(tashi.aws.util.authorizedUser)
	try:
		awsdata.registerGroup(Group({'userId':userId,'groupName':groupName,'groupDescription':groupDescription}))
	except Exception, e:
		res.__dict__['return'] = False
	return res

def DeleteSecurityGroup(groupName):
	res = DeleteSecurityGroupResponseMsg()
	res.requestId = genRequestId()
	userId = userNameToId(tashi.aws.util.authorizedUser)
	res.__dict__['return'] = True
	try:
		awsdata.removeGroup(userId, groupName)
	except:
		res.__dict__['return'] = False
	return res

def DescribeSecurityGroups(securityGroupSet = None):
	res = DescribeSecurityGroupsResponseMsg()
	res.requestId = genRequestId()
	res.securityGroupInfo = res.new_securityGroupInfo()
	res.securityGroupInfo.item = []
	userId = userNameToId(tashi.aws.util.authorizedUser)
	for group in awsdata.getGroups(userId):
		item = res.securityGroupInfo.new_item()
		item.ownerId = group.userId
		item.groupName = group.groupName
		item.groupDescription = group.groupDescription
		item.ipPermissions = item.new_ipPermissions()
		item.ipPermissions.item = []
		for ipPermission in group.ipPermissions:
			ipPermissionsItem = item.ipPermissions.new_item()
			ipPermissionsItem.ipProtocol = ipPermission.ipProtocol
			ipPermissionsItem.fromPort = int(ipPermission.fromPort)
			ipPermissionsItem.toPort = int(ipPermission.toPort)
			ipPermissionsItem.groups = ipPermissionsItem.new_groups()
			ipPermissionsItem.groups.item = []
			for groupPermission in ipPermission.groupPermissions:
				groupPermissionsItem = ipPermissionsItem.groups.new_item()
				groupPermissionsItem.groupName = groupPermission.groupName
				groupPermissionsItem.userId = groupPermission.targetUserId
				ipPermissionsItem.groups.item.append(groupPermissionsItem)
			ipPermissionsItem.ipRanges = ipPermissionsItem.new_ipRanges()
			ipPermissionsItem.ipRanges.item = []
			ipRangesItem = ipPermissionsItem.ipRanges.new_item()
			ipRangesItem.cidrIp = ipPermission.cidrIp
			if ipRangesItem.cidrIp != None:
				ipPermissionsItem.ipRanges.item.append(ipRangesItem)
			item.ipPermissions.item.append(ipPermissionsItem)
		res.securityGroupInfo.item.append(item)
	return res

def AuthorizeSecurityGroupIngress(userId, groupName, ipPermissions):
	res = AuthorizeSecurityGroupIngressResponseMsg()
	res.requestId = genRequestId()
	_userId = userNameToId(tashi.aws.util.authorizedUser)
	res.__dict__['return'] = True
	if userId != None and userId != _userId:
		raise TashiException({'msg':'You do not own that security group'})
	ipProtocol = ipPermissions['item']['ipProtocol']
	toPort = ipPermissions['item']['toPort']
	fromPort = ipPermissions['item']['fromPort']
	cidrIp = None
	if ipPermissions['item']['ipRanges']:
		cidrIp = ipPermissions['item']['ipRanges']['item']['cidrIp']
	groupPermissions = []
	if ipPermissions['item']['groups']:
		# Only one userId/groupName seems to get through even if you put multiple userId/groupNames on the command line.
		groupPermissions.append(GroupPermission({'targetUserId':ipPermissions['item']['groups']['item']['userId'],'groupName':ipPermissions['item']['groups']['item']['groupName']}))
	try:
		awsdata.addIpPermission(IpPermission({'userId':_userId,'groupName':groupName,'ipProtocol':ipProtocol,'toPort':toPort,'fromPort':fromPort,'cidrIp':cidrIp,'groupPermissions':groupPermissions}))
		#To Do: change permission.
		#client.changePermission()
	except:
		res.__dict__['return'] = False
	return res

def RevokeSecurityGroupIngress(userId, groupName, ipPermissions):
	res = RevokeSecurityGroupIngressResponseMsg()
	res.requestId = genRequestId()
	_userId = userNameToId(tashi.aws.util.authorizedUser)
	res.__dict__['return'] = True
	if userId != None and userId != _userId:
		raise TashiException({'msg':'You do not own that security group'})
	ipProtocol = ipPermissions['item']['ipProtocol']
	toPort = ipPermissions['item']['toPort']
	fromPort = ipPermissions['item']['fromPort']
	cidrIp = None
	if ipPermissions['item']['ipRanges']:
		cidrIp = ipPermissions['item']['ipRanges']['item']['cidrIp']
	groupPermissions = []
	if ipPermissions['item']['groups']:
		# Only one userId/groupName seems to get through even if you put multiple userId/groupNames on the command line.
		groupPermissions.append(GroupPermission({'targetUserId':ipPermissions['item']['groups']['item']['userId'],'groupName':ipPermissions['item']['groups']['item']['groupName']}))
	try:
		awsdata.removeIpPermission(IpPermission({'userId':_userId,'groupName':groupName,'ipProtocol':ipProtocol,'toPort':toPort,'fromPort':fromPort,'cidrIp':cidrIp,'groupPermissions':groupPermissions}))
		#To Do: change permission.
		#client.changePermission()
	except:
		res.__dict__['return'] = False
	return res

functions = ['CreateSecurityGroup', 'DeleteSecurityGroup', 'DescribeSecurityGroups', 'AuthorizeSecurityGroupIngress', 'RevokeSecurityGroupIngress']
