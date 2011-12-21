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

# This Makefile isn't primarily concerned with building a binary, but sets up this folder after a fresh checkout

# Setup
.SILENT:

# Explicit builds
default: bin src/utils/nmd
	@echo Done

all: bin src/utils/nmd src/tags doc/html aws
	@echo Done

doc: rmdoc doc/html
	@echo Done

clean: rmnmd rmbin rmtags rmdoc rmaws
	if [ `find . -name "*.pyc" | wc -l` -gt 0 ]; then echo Removing python byte-code...; rm `find . -name "*.pyc"`; fi
	@echo Done

version:
	sed -i "s/version = .*/version = \"`date`\"/" src/tashi/version.py

aws: src/tashi/aws/wsdl/AmazonEC2_services_types.py src/tashi/aws/wsdl/AmazonEC2_services_server.py

src/tashi/aws/wsdl/AmazonEC2_services_types.py: src/tashi/aws/wsdl/2009-04-04.ec2.wsdl
	(cd src/tashi/aws/wsdl; wsdl2py -b --file ./2009-04-04.ec2.wsdl)

src/tashi/aws/wsdl/AmazonEC2_services_server.py: src/tashi/aws/wsdl/2009-04-04.ec2.wsdl
	(cd src/tashi/aws/wsdl; wsdl2dispatch --file ./2009-04-04.ec2.wsdl)

src/tashi/aws/wsdl/2009-04-04.ec2.wsdl:
	wget -O src/tashi/aws/wsdl/2009-04-04.ec2.wsdl http://s3.amazonaws.com/ec2-downloads/2009-04-04.ec2.wsdl

rmaws:
	if test -e src/tashi/aws/wsdl/2009-04-04.ec2.wsdl; then echo Removing aws...; rm -f src/tashi/aws/wsdl/2009-04-04.ec2.wsdl; rm -f src/tashi/aws/wsdl/AmazonEC2_*.py; fi

# Implicit builds
# src/utils/nmd: src/utils/Makefile src/utils/nmd.c
#	@echo Building nmd...
#	(cd src/utils; make)
#	ln -s ../src/utils/nmd ./bin/nmd

src/utils/nmd: src/utils/nmd.py
	ln -s ../src/utils/nmd.py ./bin/nmd.py

#rmnmd:
#	if test -e src/utils/nmd; then echo Removing nmd...; (cd src/utils; make clean); rm -f bin/nmd; fi
rmnmd:
	echo Removing nmd...; rm -f bin/nmd.py

bin: bindir bin/clustermanager.py bin/nodemanager.py bin/tashi-client.py bin/primitive.py bin/zoni-cli.py bin/accounting.py
bindir:
	if test ! -d bin; then mkdir bin; fi
rmbin: rmclustermanager rmnodemanager rmtashi-client rmprimitive rmzoni-cli rmaccounting
	if test -d bin; then rmdir bin; fi
bin/getInstances: 
	if test ! -e bin/getInstances; then (echo "Generating client symlinks..."; cd bin; PYTHONPATH=../src ../src/tashi/client/client.py --makesyms); fi
rmclients:
	if test -e bin/getInstances; then (echo Removing client symlinks...; cd bin; PYTHONPATH=../src ../src/tashi/client/client.py --rmsyms; cd ..); fi
bin/accounting.py: src/tashi/accounting/accounting.py
	@echo Symlinking in Accounting server...
	(cd bin; ln -s ../src/tashi/accounting/accounting.py .)
rmaccounting:
	if test -e bin/accounting.py; then echo Removing Accounting server symlink...; rm bin/accounting.py; fi
bin/clustermanager.py: src/tashi/clustermanager/clustermanager.py
	@echo Symlinking in clustermanager...
	(cd bin; ln -s ../src/tashi/clustermanager/clustermanager.py .)
rmclustermanager:
	if test -e bin/clustermanager.py; then echo Removing clustermanager symlink...; rm bin/clustermanager.py; fi
bin/nodemanager.py: src/tashi/nodemanager/nodemanager.py
	@echo Symlinking in nodemanager...
	(cd bin; ln -s ../src/tashi/nodemanager/nodemanager.py .)
rmnodemanager:
	if test -e bin/nodemanager.py; then echo Removing nodemanager symlink...; rm bin/nodemanager.py; fi
bin/primitive.py: src/tashi/agents/primitive.py
	@echo Symlinking in primitive...
	(cd bin; ln -s ../src/tashi/agents/primitive.py .)
rmprimitive:
	if test -e bin/primitive.py; then echo Removing primitve-agent symlink...; rm bin/primitive.py; fi
bin/tashi-client.py:
	@echo Symlinking in tashi-client...
	(cd bin; ln -s ../src/tashi/client/tashi-client.py .)
rmtashi-client:
	if test -e bin/tashi-client.py; then echo Removing tashi-client symlink...; rm bin/tashi-client.py; fi
src/tags:
	@echo Generating tags...
	(cd src; ctags-exuberant -R --c++-kinds=+p --fields=+iaS --extra=+q -f ./tags .)
rmtags:
	if test -e src/tags; then echo Removing tags...; rm src/tags; fi

doc/html:
	@echo Generating HTML docs...
	epydoc --html -o doc/html --include-log --name=tashi --graph=all --exclude=tashi.messaging.messagingthrift ./src/tashi
rmdoc:
	if test -d doc/html; then echo Removing HTML docs...; rm -rf ./doc/html; fi

#  Zoni 
bin/zoni-cli.py:
	@echo Symlinking in zoni-cli...
	(cd bin; ln -s ../src/zoni/client/zoni-cli.py .)
usr/local/bin/zoni:
	@echo Creating /usr/local/bin/zoni
	(echo '#!/bin/bash\nPYTHONPATH=$(shell pwd)/src $(shell pwd)/bin/zoni-cli.py $$*' > /usr/local/bin/zoni; chmod 755 /usr/local/bin/zoni)
rmzoni-cli:
	if test -e bin/zoni-cli.py; then echo Removing zoni-cli symlink...; rm bin/zoni-cli.py; fi
	if test -e /usr/local/bin/zoni; then echo Removing zoni...; rm /usr/local/bin/zoni; fi

## for now only print warnings having to do with bad indentation. pylint doesn't make it easy to enable only 1,2 checks
disabled_warnings=$(shell pylint --list-msgs|grep :W0| awk -F: '{ORS=","; if ($$2 != "W0311" && $$2 != "W0312"){ print $$2}}')
pysrc=$(shell find . \! -path '*gen-py*' \! -path '*services*' \! -path '*messagingthrift*' \! -name '__init__.py' -name "*.py")
tidy: $(addprefix tidyfile/,$(pysrc))
	@echo Insuring .py files are nice and tidy!

tidyfile/%: %
	@echo Checking tidy for $*
	pylint --report=no --disable-msg-cat=R,C,E --disable-msg=$(disabled_warnings) --indent-string="\t" $* 2> /dev/null; 
