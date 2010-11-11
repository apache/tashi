#! /usr/bin/env python

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

values = {1:(0xcba4e531, 0x12be4590),
          2:(0x537158eb, 0xab54ce58),
          3:(0x145cdc3c, 0x6954c7a6),
          4:(0x0d3fdeb2, 0x15a2ca46)}

def crc(short, char):
	short = short & 0xffff
	char = char & 0xff
	value = short ^ (char << 8)
	for i in range(0, 8):
		if value & 0x8000:
			value = (value << 1) ^ 4129
		else:
			value = value << 1
	return value & 0xffff

def pseudoDes(in1, in2):
	for i in range(1, 5):
		in1 = in1 & 0xffffffff
		in2 = in2 & 0xffffffff
		(value1, value2) = values[i]

		out1 = in2
		tmp2 = in2 ^ value1
		tmp1 = ((tmp2 & 0xffff)*(tmp2 & 0xffff)) + ((~((tmp2 >> 16)*(tmp2 >> 16))) & 0xffffffff)
		tmp1 = tmp1 & 0xffffffff
		out2 = in1 ^ ((((tmp1 >> 16) | ((tmp1 & 0xffff) << 16)) ^ value2) + ((tmp2 & 0xffff) * (tmp2 >> 16)))

		in1, in2 = out1, out2
	out1 = 0xffffffff & out1
	out2 = 0xffffffff & out2
	return out1, out2

def generateKey(msg, key):
	crcValue = 0
	for char in msg:
		crcValue = crc(crcValue, ord(char))
	left, right = pseudoDes(crcValue, key)
	return (left << 32) | right

if __name__ == '__main__':
	msg = 'I am not a crook'
	key = 35005211
	print 'Actual = %x, Expected = %x' % (generateKey(msg, key), 0x52268fb4322709f3)
	msg = 'Hello World!'
	key = 521595368
	print 'Actual = %x, Expected = %x' % (generateKey(msg, key), 0xa3b5866eb29a78b6)
	msg = 'pseudo des'
	key = 294702567
	print 'Actual = %x, Expected = %x' % (generateKey(msg, key), 0xa35e82ad71b4549d)
	msg = 'copyright infringement'
	key = 1726956429
	print 'Actual = %x, Expected = %x' % (generateKey(msg, key), 0x0dbf6879e721f7b9)
	msg = 'whiteboard cowboy'
	key = 336465782
	print 'Actual = %x, Expected = %x' % (generateKey(msg, key), 0x92d36b3848a5f3a2)
