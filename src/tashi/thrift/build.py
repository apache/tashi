#!/usr/bin/python

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

import shutil
import os
from os import path
import re

if __name__ == '__main__':
	if (path.exists('gen-py')):
		print 'Removing \'gen-py\' directory...'
		shutil.rmtree('gen-py')
		
	if (path.exists('../services')):
		print 'Removing \'../services\' directory...'
		shutil.rmtree('../services')
	
	if (path.exists('../messaging/messagingthrift')):
		print 'Removing \'../messaging/messagingthrift\' directory...'
		shutil.rmtree('../messaging/messagingthrift')
	
	print 'Generating Python code for \'services.thrift\'...'
	os.system('thrift --gen py:new_style services.thrift')
	
	print 'Copying generated code to \'tashi.services\' package...'
	shutil.copytree('gen-py/services', '../services')
	
        print 'Generatign Python code for \'messagingthrift\'...'
        os.system('rm -rf gen-py')
        os.system('thrift --gen py messagingthrift.thrift')
        
        print 'Copying generated code to \'tashi.messaging.messagingthrift\' package...'
        shutil.copytree(os.path.join('gen-py', 'messagingthrift'),
                        os.path.join('..', 'messaging', 'messagingthrift'))
