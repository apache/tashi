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
#
#  $Id:$
#

import os 
import sys
import string
import traceback
import optparse
import getpass

a = os.path.join("../")
sys.path.append(a)
a = os.path.join("../../")
sys.path.append(a)
a = os.path.join("../../..")
sys.path.append(a)

from zoni.version import *
from zoni.extra.util import *


def main():
	''' This file sets up the database for Zoni '''

	ver = version.split(" ")[0]
	rev = revision


	parser = optparse.OptionParser(usage="%prog -k keyname", version="%prog " + ver + " " + rev)
	parser.add_option("-k", "--keyName", "--keyname", dest="keyName", help="Key name")
	#parser.add_option("-v", "--verbose", dest="verbosity", help="Be verbose", action="store_true", default=False)
	(options, args) = parser.parse_args()

	if not options.keyName:
		parser.print_help()
		exit(1)

	(configs, configFiles) = getConfig()


	key = createKey(options.keyName)
	print "##################  DHCP  #####################"
	print "#  Put the following lines in your dhcpd.conf file\n\n"
	print "key %s {" % options.keyName
	print "    algorithm hmac-md5;"
	print "    secret %s" % key
	print "};"
	print ""
	print "omapi-key %s" % options.keyName
	print "omapi-port 7911;\n\n"

	print "##################  DNS  #####################"
	print "#  Put the following in your dns configuration files"
	print "#  E.g. /etc/bind/named.conf.local\n\n"
	print "key %s { algorithm hmac-md5; secret \"%s\"; };" % (options.keyName, key)	
	print "\n\nDon't forget to add the following to your zone configs to allow updates\n\n"
	print "allow-update { key %s; };" % options.keyName
	print "\n\n"




if __name__ == "__main__":
    main()

