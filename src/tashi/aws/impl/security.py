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

def CreateSecurityGroup():
	raise NotImplementedError

def DeleteSecurityGroup():
	raise NotImplementedError

def DescribeSecurityGroups():
	res = DescribeSecurityGroupsResponseMsg()
	res.requestId = genRequestId()
	res.securityGroupInfo = res.new_securityGroupInfo()
	res.securityGroupInfo.item = []
	return res

def AuthorizeSecurityGroupIngress():
	raise NotImplementedError

def RevokeSecurityGroupIngress():
	raise NotImplementedError

functions = ['CreateSecurityGroup', 'DeleteSecurityGroup', 'DescribeSecurityGroups', 'AuthorizeSecurityGroupIngress', 'RevokeSecurityGroupIngress']
