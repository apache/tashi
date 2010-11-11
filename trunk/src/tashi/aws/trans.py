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

import types

def transArgsHelper(functionName, args):
	if (type(args) == types.StringType):
		return args
	for key in ['Action', 'AWSAccessKeyId', 'SignatureVersion', 'Timestamp', 'Version', 'Signature']:
		if key in args:
			del args[key]
	for key in args.keys():
		firstChar = key[0]
		if (firstChar.lower() != firstChar):
			args[firstChar.lower() + key[1:]] = args[key]
			del args[key]
	for key in args.keys():
		if (key.find(".") != -1):
			(base, sep, sub) = key.partition(".")
			args[base] = args.get(base, {})
			args[base][sub] = args[key]
			del args[key]
	for key in args.keys():
		args[key] = transArgsHelper(functionName, args[key])
	return args

def transArgs(functionName, args):
	args = transArgsHelper(functionName, args)
	if (functionName == 'TerminateInstances'):
		args['instancesSet'] = {'item':args['instanceId']}
		del args['instanceId']
	return args

def transNode(node):
	try:
		for i in range(0, len(node.childNodes)):
			node.childNodes[i] = transNode(node.childNodes[i])
		node.nodeName = node.nodeName.replace("ns1:", "")
	except:
		pass
	return node

def transResult(functionName, doc):
	try:
		newRoot = transNode(doc.getElementsByTagName("ns1:" + functionName + "Response")[0])
		newRoot.setAttribute('xmlns', 'http://ec2.amazonaws.com/doc/2009-03-01/')
		newRoot.removeAttribute('xsi:type')
		response = newRoot.cloneNode(True)
		responseStr = '<?xml version="1.0"?>\n' + str(response.toxml())
		return responseStr
	except Exception, e:
		_CGISendFault(Fault(Fault.Client, str(e)))
		return 0
