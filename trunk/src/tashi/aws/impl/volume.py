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

def CreateVolume():
	raise NotImplementedError

def DeleteVolume():
	raise NotImplementedError

def DescribeVolumes():
	raise NotImplementedError

def AttachVolume():
	raise NotImplementedError

def DetachVolume():
	raise NotImplementedError

def CreateSnapshot():
	raise NotImplementedError

def DeleteSnapshot():
	raise NotImplementedError

def DescribeSnapshots():
	raise NotImplementedError

functions = ['CreateVolume', 'DeleteVolume', 'DescribeVolumes', 'AttachVolume', 'DetachVolume', 'CreateSnapshot', 'DeleteSnapshot', 'DescribeSnapshots']
