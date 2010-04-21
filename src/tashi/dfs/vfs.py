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
import os
import os.path
from dfsinterface import DfsInterface

class Vfs(DfsInterface):
	def __init__(self, config):
		DfsInterface.__init__(self, config)
		self.prefix = self.config.get("Vfs", "prefix")

# why do these three need to be separate?	
	def copyTo(self, localSrc, dst):
		shutil.copy(localSrc, os.path.join(self.prefix, dst))
# just assuming this works
		return None
	
	def copyFrom(self, src, localDst):
		shutil.copy(os.path.join(self.prefix, src), localDst)
# just assuming this works
		return None

	def copy(self, src, dst):
		shutil.copy(os.path.join(self.prefix, src),
			    os.path.join(self.prefix, dst))
# just assuming this works
		return None
	
	def list(self, path):
		try:
			return os.listdir(os.path.join(self.prefix, path))
		except OSError, e:
			if (e.errno == 20):
				return [path.split('/')[-1]]
			else:
				raise
	
	def stat(self, path):
		return os.stat(os.path.join(self.prefix, path))
	
	def move(self, src, dst):
		shutil.move(os.path.join(self.prefix, src), 
			    os.path.join(self.prefix, dst))
# just assuming this works
		return None
	
	def mkdir(self, path):
		return os.mkdir(os.path.join(self.prefix, path))
	
	def unlink(self, path):
		return os.unlink(os.path.join(self.prefix, path))
	
	def rmdir(self, path):
		return os.rmdir(os.path.join(self.prefix, path))
	
	def open(self, path, perm):
		return open(os.path.join(self.prefix, path), perm)
	
	def getLocalHandle(self, path):
		return os.path.join(self.prefix, path)
