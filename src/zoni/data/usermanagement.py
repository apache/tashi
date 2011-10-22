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
#
#  $Id$
#

import sys
import os 

from usermanagementinterface import UserManagementInterface
import time
def timeF(f):
	def myF(*args, **kw):
		start = time.time()
		res = f(*args, **kw)
		end = time.time()
		print "%s took %f" % (f.__name__, end-start)
		return res
	myF.__name__ = f.__name__
	return myF

class ldap(UserManagementInterface):
	#@timeF
	def __init__(self):
		self.userCache = {}
		self.userCacheForward = {}
		self.userCacheReverse= {}
		cmd = "getent passwd "
		a = os.popen(cmd)
		for user in a.readlines():
			uid = int(user.split(":")[2])
			username = user.split(":")[0]
			name = user.split(":")[4]
			self.userCacheForward[username] = self.userCacheForward.get(username, {})
			self.userCacheForward[username]['name'] = self.userCacheForward[username].get("name", name) 
			self.userCacheForward[username]['uid'] = self.userCacheForward[username].get("uid", uid) 

			self.userCacheReverse[uid] = self.userCacheReverse.get(uid, {})
			self.userCacheReverse[uid]['name'] = self.userCacheReverse.get('name', name)
			self.userCacheReverse[uid]['username']  = self.userCacheReverse.get('username', username)

	def getUserId(self, userName):
		#cmd = "getent passwd | grep " + userName	
		#a = os.popen(cmd)
		#idlist = []
		#for user in a.readlines():
			#if userName in user:
				#idlist.append(user.split(":")[2])
		
		val = self.userCacheForward.get(userName)
		if val:
			return val['uid']
		return val['username']

		#if len(set(idlist)) == 0:
			#mesg = "ERROR:  User " + userName + " does not exist\n"
			#sys.stderr.write(mesg)
			#exit()
		#elif len(set(idlist)) == 1:
			#return idlist[0]
		#else:
			#print idlist
			#mesg = "ERROR:  Multiple entries exist!  Choose one and use the --uid option"
			#sys.stderr.write(mesg)
			#exit()

	def getUserName(self, userId):

		#  Check the cache
		val = self.userCacheReverse.get(userId)
		if val:
			return val['username']
		return userId
		
		'''  the old way
		val = self.userCache.get(userId)
		if val:
			return self.userCache[userId]

		cmd = "getent passwd | grep " + str(userId)
		a = os.popen(cmd)
		idlist = []
		for user in a.readlines():
			idlist.append(user.split(":")[0])
		
		if len(idlist) > 0:
			#  Cache the info to speed things up
			self.userCache[userId] = idlist[0]

			return idlist[0]		

		return userId
		'''

	def getGroupId(self):
		pass

class files(UserManagementInterface):
	def __init__(self):
		pass


	def getUserId(self, userName=None):
		if userName == None:
			return os.getuid()
		cmd = "cat /etc/passwd "
		a = os.popen(cmd)
		for line in a.readlines():
			if userName in line :
				return line.split(":")[2]
		return 0


	def getUserName(self, userId=None):
		if userId == None:
			return os.getenv('USERNAME')
		cmd = "cat /etc/passwd "
		a = os.popen(cmd)
		for line in a.readlines():
			if str(userId) in line :
				return line.split(":")[0]

		return 0


	def getGroupId(self):
		pass
