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
import os.path
import shutil
import os
from tashi.aws.wsdl.AmazonEC2_services_server import *
from tashi.aws.util import *
from tashi.rpycservices.rpyctypes import *
import tashi.aws.util

def RegisterImage(imageLocation):
	res = RegisterImageResponseMsg()
	res.requestId = genRequestId()
	userId = userNameToId(tashi.aws.util.authorizedUser)
	res.imageId = "ami-%8.8s" % (md5.md5(imageLocation).hexdigest())
	awsdata.registerImage(Image({'userId':userId,'imageId':res.imageId,'s3path':imageLocation}))
	return res

def DeregisterImage(imageId):
	res = DeregisterImageResponseMsg()
	res.requestId = genRequestId()
	res.__dict__['return'] = True
	userId = userNameToId(tashi.aws.util.authorizedUser)
	try:
		awsdata.removeImage(userId, imageId)
	except:
		res.__dict__['return'] = False
	return res

def _DescribeImages(ownersSet = {}, executableBySet = {}, imagesSet = {}):
	# _DescribeImages is meant to be used when S3 is implemented.
	res = DescribeImagesResponseMsg()
	res.requestId = genRequestId()
	res.imagesSet = res.new_imagesSet()
	res.imagesSet.item = []
	userId = userNameToId(tashi.aws.util.authorizedUser)
	for img in awsdata.getImages(userId):
		image = res.imagesSet.new_item()
		image.imageId = img.imageId
		image.imageLocation = img.s3path
		image.imageState = 'available'
		image.imageOwnerId = img.userId
		image.isPublic = img.isPublic
		image.productCodes = image.new_productCodes()
		productCodeItem = image.productCodes.new_item()
		productCodeItem.productCode = img.productCode
		image.productCodes.item = [productCodeItem]
		#image.architecture = None <string>
		#image.imageType = None <string>
		#image.kernelId = None <string>
		#image.ramdiskId = None <string>
		#image.platform = None <string>
		res.imagesSet.item.append(image)
	return res

def DescribeImages(ownersSet = {}, executableBySet = {}, imagesSet = {}):
	IMGDIR="/mnt/merkabah/tashi/images/"
	res = DescribeImagesResponseMsg()
	res.requestId = genRequestId()
	res.imagesSet = res.new_imagesSet()
	res.imagesSet.item = []
	imgList = os.listdir(IMGDIR)
	for img in imgList:
		fullImg = IMGDIR + img
		if (os.path.isdir(fullImg)):
			continue
		owner = os.stat(fullImg)[4]
		user = userIdToName(owner)
		if (owner == 0 or user == tashi.aws.util.authorizedUser):
			image = res.imagesSet.new_item()
			#image.imageId = "tmi-%8.8s" % (md5.md5(img).hexdigest())
			# This must be "ami" or else elasticfox won't display it
			image.imageId = "ami-%8.8s" % (md5.md5(img).hexdigest())
			image.imageLocation = img
			image.imageState = "available"
			image.imageOwnerId = "%12.12d" % (owner)
			image.isPublic = (owner == 0)
			#image.productCodes = None <ProductCodesSetType>
			#image.architecture = None <string>
			#image.imageType = None <string>
			#image.kernelId = None <string>
			#image.ramdiskId = None <string>
			#image.platform = None <string>
			res.imagesSet.item.append(image)
	return res

def ModifyImageAttribute(imageId, launchPermission=None, productCodes=None):
	# Account ids should probably be entered with leading 0's so that 12 character spaces are used.
	# For some reason, only the 'all' group is allowed.
	res = ModifyImageAttributeResponseMsg()
	res.requestId = genRequestId()
	userId = userNameToId(tashi.aws.util.authorizedUser)
	res.__dict__['return'] = True
	if launchPermission:
		try:
			if 'add' in launchPermission:
				if 'group' in launchPermission['add']['item']:
					targetUserId = launchPermission['add']['item']['group']
				elif 'userId' in launchPermission['add']['item']:
					targetUserId = launchPermission['add']['item']['userId']
				awsdata.addPermission(userId, targetUserId, imageId)
			if 'remove' in launchPermission:
				if 'group' in launchPermission['remove']['item']:
					targetUserId = launchPermission['remove']['item']['group']
				elif 'userId' in launchPermission['remove']['item']:
					targetUserId = launchPermission['remove']['item']['userId']
				awsdata.removePermission(userId, targetUserId, imageId)
		except:
			res.__dict__['return'] = False
	if productCodes:
		try:
			awsdata.setProductCode(userId, productCodes['item']['productCode'], imageId)
		except:
			res.__dict__['return'] = False
	return res

def ResetImageAttribute(launchPermission, imageId):
	# res.__dict__['return'] is used to specify if there is an error.
	res = ResetImageAttributeResponseMsg()
	res.requestId = genRequestId()
	userId = userNameToId(tashi.aws.util.authorizedUser)
	res.__dict__['return'] = True
	try:
		awsdata.resetImage(userId, imageId)
	except:
		res.__dict__['return'] = False
	return res

def DescribeImageAttribute(imageId, launchPermission=True, productCodes=True, kernel=True, ramdisk=True, blockDeviceMapping=True, platform=True):
	res = DescribeImageAttributeResponseMsg()
	res.requestId = genRequestId()
	res.imageId = imageId
	userId = userNameToId(tashi.aws.util.authorizedUser)
	images = awsdata.getImages(userId)
	res.launchPermission = res.new_launchPermission()
	res.launchPermission.item = []
	index = images.index(Image({'userId':userId,'imageId':imageId}))
	image = images[index]
	if not launchPermission:
		if image.isPublic:
			launchPermissionItem = res.launchPermission.new_item()
			launchPermissionItem.group = 'all'
			res.launchPermission.item.append(launchPermissionItem)
		else:
			for explicitUserId in image.explicitUserIds:
				launchPermissionItem = res.launchPermission.new_item()
				launchPermissionItem.userId = explicitUserId
				res.launchPermission.item.append(launchPermissionItem)
	elif not productCodes:
		pass
	elif not kernel:
		pass
	elif not ramdisk:
		pass
	elif not blockDeviceMapping:
		pass
	elif not platform:
		pass
	return res

functions = ['RegisterImage', 'DeregisterImage', 'DescribeImages', 'ModifyImageAttribute', 'ResetImageAttribute', 'DescribeImageAttribute']
