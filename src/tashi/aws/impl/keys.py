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
import os
import re

def CreateKeyPair(keyName):
	res = CreateKeyPairResponseMsg()
	res.requestId = genRequestId()
	res.keyName = keyName
	privkeyfile = awsdir + 'id_rsa.tmp'
	pubkeyfile = awsdir + 'id_rsa.tmp.pub'
	fingerprintfile = awsdir + 'fingerprint.tmp'
	try:
		os.remove(privkeyfile)
	except:
		pass
	os.system('ssh-keygen -t rsa -b 2048 -f ' + privkeyfile + ' -P "" > ' + fingerprintfile)
	infile = open(privkeyfile, 'r')
	privkey = infile.read()
	infile.close()
	infile = open(pubkeyfile, 'r')
	pubkey = infile.read()
	infile.close()
	infile = open(fingerprintfile, 'r')
	fingerprint = infile.read()
	infile.close()
	fingerprint = re.findall('The key fingerprint is:\s+(\S+)\s+', fingerprint)[0]
	res.keyFingerprint = fingerprint
	res.keyMaterial = privkey
	os.remove(privkeyfile)
	os.remove(pubkeyfile)
	os.remove(fingerprintfile)
	userId = userNameToId(tashi.aws.util.authorizedUser)
	awsdata.registerKey(Key({'userId':userId,'keyName':keyName,'fingerprint':fingerprint,'pubkey':pubkey,'privkey':privkey}))
	return res

def DescribeKeyPairs(keySet={}):
	res = DescribeKeyPairsResponseMsg()
	res.requestId = genRequestId()
	res.keySet = res.new_keySet()
	res.keySet.item = []
	userId = userNameToId(tashi.aws.util.authorizedUser)
	for key in awsdata.getKeys(userId):
		item = res.keySet.new_item()
		item.keyName = key.keyName
		item.keyFingerprint = key.fingerprint
		res.keySet.item.append(item)
	return res

def DeleteKeyPair(keyName):
	res = DeleteKeyPairResponseMsg()
	res.requestId = genRequestId()
	res.__dict__['return'] = True
	userId = userNameToId(tashi.aws.util.authorizedUser)
	try:
		awsdata.removeKey(userId, keyName)
	except:
		res.__dict__['return'] = False
	return res

functions = ['CreateKeyPair', 'DescribeKeyPairs', 'DeleteKeyPair']
