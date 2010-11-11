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

def AllocateAddress():
	res = AllocateAddressResponseMsg()
	res.requestId = genRequestId()
	# To Do, reserve an available ip address.
	# client.getAddress()
	res.publicIp = '0.0.0.0'
	userId = userNameToId(tashi.aws.util.authorizedUser)
	awsdata.registerAddress(Address({'userId':userId,'publicIp':res.publicIp}))
	return res

def ReleaseAddress(publicIp):
	res = ReleaseAddressResponseMsg()
	res.requestId = genRequestId()
	# To Do, release a reserved ip address.
	# client.releaseAddress()
	userId = userNameToId(tashi.aws.util.authorizedUser)
	res.__dict__['return'] = True
	try:
		awsdata.removeAddress(userId, publicIp)
	except:
		res.__dict__['return'] = False
	return res

def DescribeAddresses(publicIpsSet={}):
	res = DescribeAddressesResponseMsg()
	res.requestId = genRequestId()
	userId = userNameToId(tashi.aws.util.authorizedUser)
	res.addressesSet = res.new_addressesSet()
	res.addressesSet.item = []
	for address in awsdata.getAddresses(userId):
		addressItem = res.addressesSet.new_item()
		addressItem.publicIp = address.publicIp
		addressItem.instanceId = address.instanceId
		res.addressesSet.item.append(addressItem)
	return res

def AssociateAddress(instanceId, publicIp):
	res = AssociateAddressResponseMsg()
	res.requestId = genRequestId()
	res.__dict__['return'] = True
	userId = userNameToId(tashi.aws.util.authorizedUser)
	try:
		awsdata.associateAddress(userId, instanceId, publicIp)
		# To Do, associate an Address
		#client.associateAddress()
	except:
		res.__dict__['return'] = False
	return res

def DisassociateAddress(publicIp):
	res = DisassociateAddressResponseMsg()
	res.requestId = genRequestId()
	res.__dict__['return'] = True
	userId = userNameToId(tashi.aws.util.authorizedUser)
	try:
		awsdata.dissociateAddress(userId, publicIp)
		# To Do, associate an Address
		#client.dissociateAddress()
	except:
		res.__dict__['return'] = False
	return res

functions = ['AllocateAddress', 'ReleaseAddress', 'DescribeAddresses', 'AssociateAddress', 'DisassociateAddress']
