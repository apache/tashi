#!/usr/bin/env python

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

import base64
import cgi
import hashlib
import hmac
import md5
import os
import re
import sys
import time
import traceback
import types
from ZSI.dispatch import _CGISendXML, _CGISendFault
from ZSI import Fault

from tashi.aws.wsdl.AmazonEC2_services_server import *
from tashi.aws.impl import address, bundle, images, instances, keys, location, monitor, other, reservation, security, volume
from tashi.aws.util import *
import tashi.aws.util
import tashi
import trans

for mod in [address, bundle, images, instances, keys, location, monitor, other, reservation, security, volume]:
	for fname in mod.__dict__.get('functions', []):
		globals()[fname] = QUERY(mod.__dict__.get(fname))

userDict = {}
def loadUserDict():
	f = open("/var/lib/tashi-ec2/access.txt")
	data = f.read()
	f.close()
	for l in data.split("\n"):
		ws = l.strip().split()
		if (len(ws) == 3):
			(accessKey, secretAccessKey, authenticatedUser) = ws
			userDict[accessKey] = (secretAccessKey, authenticatedUser)

def AsQuery():
	'''Handle the Amazon QUERY interface'''
	try:
		form = cgi.FieldStorage()
		args = {}
		signStr = ""
		for var in form:
			args[var] = form[var].value
			if (var != "Signature"):
				signStr += var + args[var]
			log("[QUERY] %s=%s\n" % (var, args[var]))
		secretKey = userDict[args['AWSAccessKeyId']][0]
		calculatedSig = base64.b64encode(hmac.new(secretKey, signStr, hashlib.sha1).digest())
		if (args['Signature'] != calculatedSig):
			_CGISendFault(Fault(Fault.Client, 'Could not authenticate'))
			return
		tashi.aws.util.authorizedUser = userDict[args['AWSAccessKeyId']][1]
		log("[AUTH] authorizedUser = %s\n" % (tashi.aws.util.authorizedUser))
		functionName = args['Action']
		res = eval("%s(args)" % (functionName))
		_CGISendXML(res)
	except Exception, e:
		_CGISendFault(Fault(Fault.Client, str(e)))

if  __name__ == "__main__" :
	log("%s\n" % (str(time.time())))
	for var in os.environ:
		log("[CGI] %s=%s\n" % (var, os.environ[var]))
	try:
		loadUserDict()
		AsQuery()
	except:
		log("%s\n" % (traceback.format_exc(sys.exc_info())))
