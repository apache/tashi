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

import sys
import traceback
import types
import uuid
from xml.dom import minidom
from ZSI import SoapWriter
import tashi
import trans

sizes = {'m1.small': (int(1.7*1024), 1),
         'm1.large': (int(7.5*1024), 4),
         'm1.xlarge': (int(15*1024), 8),
         'c1.medium': (int(1.7*1024), 5),
         'c1.xlarge': (int(7*1024), 20),
        }

def log(s):
	sys.stderr.write(s)

def fixObject(obj):
	if (type(obj) in [types.StringType, types.BooleanType, types.IntType, types.FloatType, types.NoneType, types.UnicodeType]):
		return obj
	try:
		if (getattr(obj, "__dict__", None)):
			for k in obj.__dict__.keys():
				if (not k.startswith("_")):
					setattr(obj, "_%s" % (k), fixObject(getattr(obj, k)))
		else:
			obj = map(lambda x: fixObject(x), obj)
	except:
		log("%s\n" % (traceback.format_exc(sys.exc_info())))
		log("%s\n" % (type(obj)))
	return obj

def SOAPRPC(oldFunc):
	def newFunc(kw):
		try:
			log("%s(%s)\n" % (str(oldFunc.__name__), str(kw)))
			if kw:
				res = oldFunc(**kw)
			else:
				res = oldFunc()
			res = fixObject(res)
			log("%s(%s) -> %s\n" % (str(oldFunc.__name__), str(kw), str(res)))
			return res
		except:
			log("%s\n" % (traceback.format_exc(sys.exc_info())))
			raise
	return newFunc

def QUERY(oldFunc):
	def newFunc(kw):
		try:
			log("%s(%s)\n" % (str(oldFunc.__name__), str(kw)))
			kw = trans.transArgs(oldFunc.__name__, kw)
			res = oldFunc(**kw)
			res = fixObject(res)
			log("%s(%s) -> %s\n" % (str(oldFunc.__name__), str(kw), str(res)))
			sw = SoapWriter()
			sw.serialize(res, res.typecode)
			res = trans.transResult(oldFunc.__name__, minidom.parseString(str(sw)))
			return res
		except:
			log("%s\n" % (traceback.format_exc(sys.exc_info())))
			raise
	return newFunc

class Lazy(object):
	def __init__(self, objString):
		self._objString = objString
	
	def __getattr__(self, name):
		obj = eval(self._objString, locals(), globals())
		return getattr(obj, name)

client = Lazy("tashi.createClient(tashi.getConfig()[0])")

users = {}
def userIdToName(id):
	if (users == {}):
		_users = client.getUsers()
		for user in _users:
			users[user.id] = user.name
			users[user.name] = id
	if (id in users):
		return users[id]
	else:
		return "UNKNOWN"

def userNameToId(name):
	if (users == {}):
		_users = client.getUsers()
		for user in _users:
			users[user.id] = user.name
			users[user.name] = user.id
	if (name in users):
		return users[name]
	else:
		return -1
	
vars = {}

def genRequestId():
	return str(uuid.uuid1())

authorizedUser = "UNKNOWN"
