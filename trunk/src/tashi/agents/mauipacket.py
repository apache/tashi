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

import subprocess
import time
import pseudoDes

class MauiPacket:
	def __init__(self, key=0):
		self.size = 0
		self.char = '\n'
		self.chksum = '0'*16
		self.timestamp = int(time.time())
		self.auth = ''
		self.data = []
		self.msg = ''
		self.key=key
	def readPacket(self, istream):
		self.msg = ''

		size = istream.read(8)
		self.msg = self.msg+size
		self.size = int(size)

		self.char = istream.read(1)
		self.msg = self.msg + self.char

		packet = istream.read(self.size)
		self.msg = self.msg + packet

		packet = packet.split()
		
		for i in range(len(packet)):
			item = packet[i].split('=')
			if item[0] == 'CK':
				self.chksum = item[1]
			if item[0] == 'TS':
				self.timestamp = int(item[1])
			if item[0] == 'AUTH':
				self.auth = item[1]
			if item[0] == 'DT':
				self.data = packet[i:]
				self.data=self.data[0].split('=',1)[1:] + self.data[1:]

	def checksumMessage(self, message, key=None):
		if key == None:
			key = self.key
		if type(key) == type(''):
			key = int(key)
		chksum = pseudoDes.generateKey(message, key)
		chksum = '%016x' % chksum
		return chksum
	def getChecksum(self):
		cs = self.msg.partition('TS=')
		cs = cs[1]+cs[2]
		chksum = self.checksumMessage(cs)
		return chksum
	def verifyChecksum(self):
		chksum = self.getChecksum()
		if chksum != self.chksum:
			print 'verifyChecksum: "%s"\t"%s"'%(chksum, self.chksum)
			print 'verifyChecksum (types): %s\t%s' %(type(chksum), type(self.chksum))
			return False
		return True
	def set(self, data, auth=None, key=None, timestamp=None):
		if timestamp==None:
			timestamp = int(time.time())
		self.data = data
		if auth !=None:
			self.auth = auth
		if key != None:
			self.key = key
		self.timstamp=timestamp
		self.fixup()
	def fixup(self):
		datastring = "TS=%i AUTH=%s DT=%s"%(self.timestamp, self.auth, (' '.join(self.data)))
		self.chksum = self.checksumMessage(datastring)

		pktstring = 'CK=%s %s'%(self.chksum, datastring)
		self.size = len(pktstring)
	def __str__(self):
		datastring = "TS=%i AUTH=%s DT=%s"%(self.timestamp, self.auth, (' '.join(self.data)))
		self.chksum = self.checksumMessage(datastring)

		pktstring = 'CK=%s %s'%(self.chksum, datastring)
		self.msg = ''
		self.msg = self.msg + '%08i'%len(pktstring)
		self.msg = self.msg + self.char
		self.msg = self.msg + pktstring

		return self.msg
	def prettyString(self):
		s = '''Maui Packet
-----------
size:\t\t%i
checksum:\t%s
timestamp:\t%s
auth:\t\t%s
data:
%s
-----------'''
		s = s%(self.size, self.chksum, self.timestamp, self.auth, self.data)
		return s
