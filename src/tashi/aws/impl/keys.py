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

def CreateKeyPair():
	raise NotImplementedError

def DescribeKeyPairs():
	res = DescribeKeyPairsResponseMsg()
	res.requestId = genRequestId()
	res.keySet = res.new_keySet()
	item = res.keySet.new_item()
	item.keyName = "fake"
	item.keyFingerprint = "missing"
	res.keySet.item = [item]
	return res

def DeleteKeyPair():
	raise NotImplementedError

functions = ['CreateKeyPair', 'DescribeKeyPairs', 'DeleteKeyPair']
