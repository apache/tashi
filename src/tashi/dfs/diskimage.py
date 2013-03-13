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

import logging
import subprocess

from tashi.dfs.diskimageinterface import DiskImageInterface

class QemuImage(DiskImageInterface):
    '''  This class implements the image creation for qemu/kvm '''

    def __init__(self, config):
        DiskImageInterface.__init__(self, config)
        self.log = logging.getLogger(__name__)
        self.prefix = self.config.get("Vfs", "prefix")
        

    def cloneImage(self, srcImage, dstImage):
        self.log.info("Cloning image %s -> %s" % (srcImage, dstImage))
        cmd = "/usr/bin/qemu-img create -b %s -f qcow2 %s" % (srcImage, dstImage)
        p = subprocess.Popen(cmd.split(), executable=cmd.split()[0], stdout=subprocess.PIPE) 
        self.log.info("Finished cloning image %s" % (p.stdout.readlines()))

    def rebaseImage(self, srcImage, dstImage):
        self.log.info("Rebasing image %s -> %s" % (srcImage, dstImage))
        cmd = "/usr/bin/qemu-img convert %s -O qcow2 %s" % (srcImage, dstImage)
        p = subprocess.Popen(cmd.split(), executable=cmd.split()[0], stdout=subprocess.PIPE) 
        self.log.info("Finished rebasing image %s" % (p.stdout.readlines()))

    def getImageInfo(self, srcImage):
        cmd = "/usr/bin/qemu-img info %s" % srcImage
        subprocess.Popen(cmd.split(), executable=cmd.split()[0], stdout=subprocess.PIPE) 
