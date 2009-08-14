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
from tashi.aws.wsdl.AmazonEC2_services_server import *
from tashi.aws.util import *

def RegisterImage():
	raise NotImplementedError

def DeregisterImage():
	raise NotImplementedError

def DescribeImages(ownersSet={}, executableBySet={}, imagesSet={}):
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

def ModifyImageAttribute():
	raise NotImplementedError

def ResetImageAttribute():
	raise NotImplementedError

def DescribeImageAttribute():
	raise NotImplementedError

functions = ['RegisterImage', 'DeregisterImage', 'DescribeImages', 'ModifyImageAttribute', 'ResetImageAttribute', 'DescribeImageAttribute']
