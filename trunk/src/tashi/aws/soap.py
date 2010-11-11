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

import md5
import os
import re
import sys
import time
import traceback
import ZSI.dispatch
from ZSI.dispatch import _Dispatch, _CGISendXML, _CGISendFault
from ZSI import ParseException, ParsedSoap, Fault
from ZSI import resolvers 
from xml.dom import minidom

from tashi.aws.wsdl.AmazonEC2_services_server import *
from tashi.aws.impl import address, bundle, images, instances, keys, location, monitor, other, reservation, security, volume
from tashi.aws.util import *
import tashi.aws.util

for mod in [address, bundle, images, instances, keys, location, monitor, other, reservation, security, volume]:
	for fname in mod.__dict__.get('functions', []):
		globals()[fname] = SOAPRPC(mod.__dict__.get(fname))

class ValidateParsedSoap(ParsedSoap):
	def __init__(self, input, *args, **kw):
		if (not self.validate(input)):
			return
		ParsedSoap.__init__(self, input, *args, **kw)
	
	def validate(self, xml):
		'''A simple blob of code that validates the xmldsig in an xml string using xmlsec1'''
		doc = minidom.parseString(xml)
		tokens = doc.getElementsByTagName("wsse:BinarySecurityToken")
		if (len(tokens) != 1):
			return -1
		token = tokens[0]
		if (len(token.childNodes) != 1):
			return -1
		childNode = token.childNodes[0]
		if (not getattr(childNode, 'wholeText', None)):
			return -1
		cert = childNode.wholeText
		CERT_DIGEST = md5.md5(cert).hexdigest()
		log("[AUTH] CERT_DIGEST=%s\n" % (CERT_DIGEST))
		output = xml
		ofile = "/tmp/%5.5d.%s.xml" % (os.getpid(), md5.md5(output).hexdigest())
		f2 = open(ofile, "w")
		f2.write(output)
		f2.close()
# XXXpipe: what are we doing here?
		(stdin, stdout) = os.popen4("xmlsec1 --verify --id-attr:Id Timestamp --id-attr:Id Body --pubkey-cert-pem /var/lib/tashi-ec2/%s.crt --print-debug %s" % (CERT_DIGEST, ofile))
		stdin.close()
		res = stdout.read()
		stdout.close()
		os.unlink(ofile)
		verified = False
		lines = res.split("\n")
		cmpRe = re.compile('==== Subject Name: (.*)')
		for line in lines:
			if (line.strip() == "OK"):
				verified = True
			res = cmpRe.match(line)
			if (res):
				varStrs = res.groups()[0].split("/")
				for var in varStrs:
					(key, sep, val) = var.partition("=")
					if (key != '' and val != ''):
						vars[key] = val
		if (not verified):
			_CGISendFault(Fault(Fault.Client, 'Could not authenticate'))
			return verified
		tashi.aws.util.authorizedUser = vars.get('CN', 'UNKNOWN')
		log("[AUTH] authorizedUser = %s\n" % (tashi.aws.util.authorizedUser))
		return verified

ZSI.dispatch.ParsedSoap = ValidateParsedSoap

if  __name__ == "__main__" :
	log("%s\n" % (str(time.time())))
	for var in os.environ:
		log("[CGI] %s=%s\n" % (var, os.environ[var]))
	try:
		ZSI.dispatch.AsCGI()
	except:
		log("%s\n" % (traceback.format_exc(sys.exc_info())))
