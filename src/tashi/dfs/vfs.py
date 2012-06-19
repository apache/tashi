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

# implementation of dfs interface functions

import shutil
import os.path
from dfsinterface import DfsInterface

class Vfs(DfsInterface):
	def __init__(self, config):
		DfsInterface.__init__(self, config)
		self.prefix = self.config.get("Vfs", "prefix")

	def __dfsToReal(self, dfspath):
		realpath = os.path.join(self.prefix, dfspath)
		return realpath

	def copyTo(self, localSrc, dst):
		realdest = self.__dfsToReal(dst)
		shutil.copy(localSrc, realdest)
		# just assuming this works
		return None
	
	def copyFrom(self, src, localDst):
		realsrc = self.__dfsToReal(src)
		shutil.copy(realsrc, localDst)
		# just assuming this works
		return None

	def copy(self, src, dst):
		realsrc = self.__dfsToReal(src)
		realdst = self.__dfsToReal(dst)
		shutil.copy(realsrc, realdst)
		# just assuming this works
		return None
	
	def list(self, path):
		try:
			realpath = self.__dfsToReal(path)
			return os.listdir(realpath)
		except OSError, e:
			# XXXstroucki error 20 = ENOTDIR
			if (e.errno == 20):
				return [path.split('/')[-1]]
			else:
				raise
	
	def stat(self, path):
		realpath = self.__dfsToReal(path)
		return os.stat(realpath)
	
	def move(self, src, dst):
		realsrc = self.__dfsToReal(src)
		realdst = self.__dfsToReal(dst)
		shutil.move(realsrc, realdst)
		# just assuming this works
		return None
	
	def mkdir(self, path):
		realpath = self.__dfsToReal(path)
		return os.mkdir(realpath)
	
	def unlink(self, path):
		realpath = self.__dfsToReal(path)
		return os.unlink(realpath)
	
	def rmdir(self, path):
		realpath = self.__dfsToReal(path)
		return os.rmdir(realpath)
	
	def open(self, path, perm):
		realpath = self.__dfsToReal(path)
		return open(realpath, perm)
	
	def getLocalHandle(self, path):
		realpath = self.__dfsToReal(path)
		return realpath
