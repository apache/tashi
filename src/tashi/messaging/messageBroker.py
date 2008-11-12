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

import ConfigParser
import getopt

import os
import sys
import time

import thriftmessaging

options = []
long_options = ['port=']

# FIXME: should initialize from config file
params = {"port":1717}

try:
    optlist, args = getopt.getopt(sys.argv[1:], options, long_options)
except getopt.GetoptError, err:
    print str(err)
    sys.exit(2)

for opt in optlist:
    if opt[0] == "--port":
        try:
            params["port"] = int(opt[1])
        except:
            print "--port expects an integer, got %s" % opt[1]
            sys.exit(0)

print "Starting message broker on port %i" % params["port"]
broker = thriftmessaging.MessageBrokerThrift(params["port"], daemon=False)

