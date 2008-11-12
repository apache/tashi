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
all: src/tashi/services bin src/utils/nmd
	@echo Done

mryan3: src/tashi/services bin src/utils/nmd src/tags doc/html
	@echo Done

doc: rmdoc doc/html
	@echo Done

clean: rmnmd rmbin rmtags rmservices rmdoc
	if [ `find . -name "*.pyc" | wc -l` -gt 0 ]; then echo Removing python byte-code...; rm `find . -name "*.pyc"`; fi
	@echo Done

# Implicit builds
src/utils/nmd: src/utils/Makefile src/utils/nmd.c
	@echo Building nmd...
	(cd src/utils; make)
	ln -s src/utils/nmd/nmd ./bin/nmd

rmnmd:
	if test -e src/utils/nmd; then echo Removing nmd...; (cd src/utils; make clean); rm -f bin/nmd; fi

src/tashi/services: src/tashi/thrift/services.thrift
	@echo Building tashi.services...
	(cd src/tashi/thrift; ./build.py)

rmservices:
	if test -d src/tashi/services; then echo Removing tashi.services...; rm -rf src/tashi/services; fi
	if test -d src/tashi/thrift/gen-py; then echo Removing tashi.thrift.gen-py...; rm -rf src/tashi/thrift/gen-py; fi
	if test -d src/tashi/messaging/messagingthrift; then echo Removing tashi.messaging.messagingthrift; rm -rf src/tashi/messaging/messagingthrift; fi

bin: bindir bin/getInstances bin/clustermanager.py bin/nodemanager.py
bindir:
	if test ! -d bin; then mkdir bin; fi
rmbin: rmclustermanager rmnodemanager rmclients
	if test -d bin; then rmdir bin; fi
bin/getInstances: src/tashi/services
	if test ! -e bin/getInstances; then (echo "Generating client symlinks..."; cd bin; PYTHONPATH=../src ../src/tashi/client/client.py --makesyms); fi
rmclients:
	if test -e bin/getInstances; then (echo Removing client symlinks...; make src/tashi/services; cd bin; PYTHONPATH=../src ../src/tashi/client/client.py --rmsyms; cd ..); fi
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

src/tags:
	@echo Generating tags...
	(cd src; ctags-exuberant -R --c++-kinds=+p --fields=+iaS --extra=+q -f ./tags .)
rmtags:
	if test -e src/tags; then echo Removing tags...; rm src/tags; fi

doc/html:
	@echo Generating HTML docs...
	epydoc --html -o doc/html --include-log --name=tashi --graph=all --exclude=tashi.services --exclude=tashi.messaging.messagingthrift ./src/tashi
rmdoc:
	if test -d doc/html; then echo Removing HTML docs...; rm -rf ./doc/html; fi
