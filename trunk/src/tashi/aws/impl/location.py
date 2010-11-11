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

import socket
from tashi.aws.wsdl.AmazonEC2_services_server import *
from tashi.aws.util import *

def DescribeAvailabilityZones(availabilityZoneSet={}):
	res = DescribeAvailabilityZonesResponseMsg()
	res.requestId = genRequestId()
	res.availabilityZoneInfo = res.new_availabilityZoneInfo()
	item = res.availabilityZoneInfo.new_item()
	item.zoneName = 'tashi'
	item.zoneState = 'available'
	item.regionName = 'here'
	res.availabilityZoneInfo.item = [item]
	return res

def DescribeRegions(regionSet={}):
	res = DescribeRegionsResponseMsg()
	res.requestId = genRequestId()
	res.regionInfo = res.new_regionInfo()
	item = res.regionInfo.new_item()
	item.regionName = "here"
	item.regionEndpoint = socket.getfqdn()
	res.regionInfo.item = [item]
	return res

functions = ['DescribeAvailabilityZones', 'DescribeRegions']
