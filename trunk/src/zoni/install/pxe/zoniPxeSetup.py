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
#  $Id$
#

import os 
import sys
import string
import traceback
import optparse
import shutil
import urllib
import tarfile

#a = os.path.join("zoni", "install", "pxe")
#a = os.path.join("zoni", "install")
#sys.path.append(os.getcwd().split(a)[0])
a = os.path.join("../")
sys.path.append(a)
a = os.path.join("../../")
sys.path.append(a)
a = os.path.join("../../..")
sys.path.append(a)

from zoni.extra.util import *
from zoni.version import *
from zoni.bootstrap.pxe import Pxe


def main():
	''' This file sets up PXE for Zoni '''

	ver = version.split(" ")[0]
	rev = revision

	parser = optparse.OptionParser(usage="%prog ", version="%prog " + ver + " " + rev)
	(options, args) = parser.parse_args()

	(configs, configFile) = getConfig()

	ZoniPxeSetup(configs)
	ZoniGetSyslinux(configs)

@checkSuper
def ZoniPxeSetup(config):
	tftpRootDir = config['tftpRootDir']
	tftpImageDir = config['tftpImageDir']
	tftpBootOptionsDir = config['tftpBootOptionsDir']
	tftpUpdateFile =  config['tftpUpdateFile'] 
	tftpBaseFile = config['tftpBaseFile'] 
	tftpBaseMenuFile = config['tftpBaseMenuFile'] 
	installBaseDir = config['installBaseDir']
	

	#  Create the directory structure
	print "Creating PXE Directory Structure..."
	createDir(tftpRootDir)
	bootScreenDir = os.path.join(tftpRootDir, "boot-screens")
	createDir(bootScreenDir)
	dirName = os.path.join(tftpRootDir, "builds")
	createDir(dirName)
	createDir(tftpImageDir)
	createDir(tftpBootOptionsDir)

	#  Find the base files to copy
	
	pxeDir = os.path.join(installBaseDir, "src", "zoni", "install", "pxe")
	#dirName = os.path.join(pxeDir, "base-menu")
	#shutil.copy2(dirName, tftpBaseMenuFile)
	print "open dir name ", tftpBaseMenuFile
	open(tftpBaseMenuFile, 'w').write(zoniCreateBaseMenu(config))
	
	dirName = os.path.join(pxeDir, "base.zoni")
	shutil.copy2(dirName, tftpBaseFile)
	#  Copy over zoni pxe image 
	dirName = os.path.join(pxeDir, "zoni_pxe.jpg")
	shutil.copy2(dirName, os.path.join(bootScreenDir, "zoni_pxe.jpg"))

	#  Create the PXE config files, seeding the register images
	pxe = Pxe(config)
	pxe.createPxeUpdateFile(["zoni-register-64", "zoni-register-64-interactive"])
	pxe.updatePxe()

	try:
		#  Create the default image to be the registration image
		os.chdir(tftpImageDir)
		dirName = os.path.join(os.path.basename(tftpBootOptionsDir), "zoni-register-64")
		os.symlink(dirName, "default")
		print "   Symlinking default in " + dirName 
	except (OSError, Exception), e:
		if e.errno == 17:
			print "    " + e.args[1] + ": " + dirName
		else:
			print "    " + e.args[1] + ": " + dirName

	print "Finished"

@checkSuper
def ZoniGetSyslinux(config, ver=None):
	tftpRootDir = config['tftpRootDir']
	tmpdir = os.path.join("/tmp")

	print "Installing necessary files for PXE"
	

	#  Download syslinux and get latest version
	syslinuxVersion = 0
	if not ver:
		#  Get latest
		print "    Determining latest version of syslinux...",
		data = urllib.urlopen("http://www.kernel.org/pub/linux/utils/boot/syslinux/")
		for line in data.readlines():
			if "syslinux" in line and "tar.bz2" in line and not "sign" in line:
				a = float(line.split("syslinux-")[1].split(".tar.bz2")[0])
				if a > syslinuxVersion:
					syslinuxVersion = a
		ver = str(syslinuxVersion)
		print ver

	syslinuxFile = "syslinux-" + ver
	#  Check if the file already exists
	tmpfile = os.path.join(tmpdir, "syslinux-" + ver + ".tar.bz2")
	if not os.path.exists(tmpfile):
		print "Downloading syslinux from kernel.org"
		url = "http://www.kernel.org/pub/linux/utils/boot/syslinux/syslinux-" + ver + ".tar.bz2" 
		print "    Downloading: " + url
		tmpfile = os.path.join(tmpdir, "syslinux-" + ver + ".tar.bz2")
		urllib.urlretrieve(url, tmpfile)
	else:
		print "    Found syslinux: " + tmpfile

	print "    Opening syslinux tar.bz2"
	myTar = tarfile.TarFile.open(tmpfile)
	tmpfile = os.path.join(tmpdir, syslinuxFile)
	print "    Extracting pxelinux.0 from tarball"
	memberName = os.path.join(syslinuxFile, "core", "pxelinux.0")
	myTar.extract(memberName, tmpdir)
	tmpfile = os.path.join(tmpdir, syslinuxFile, "core", "pxelinux.0")
	shutil.copy2(tmpfile, tftpRootDir)
	print "    Extracting vesamenu.c32 from tarball"
	memberName = os.path.join(syslinuxFile, "com32", "menu", "vesamenu.c32")
	myTar.extract(memberName, tmpdir)
	tmpfile = os.path.join(tmpdir, syslinuxFile, "com32", "menu", "vesamenu.c32")
	shutil.copy2(tmpfile, tftpRootDir)
	print "Finished"

def zoniCreateBaseMenu(config):

	a = ""
	a += "DISPLAY boot-screens/boot.txt\n\n"
	a += "LABEL zoni-register-64\n"
	a += "        kernel builds/amd64/zoni-reg/linux\n"
	a += "        append initrd=builds/amd64/zoni-reg/initrd.gz pxeserver=" + config['pxeServerIP'] +  " imageserver=" + config['imageServerIP'] + " defaultimage=amd64-tashi_nm registerfile=register_node mode=register console=tty1 rw --\n"
	a += "\n"
	a += "LABEL zoni-register-64-interactive\n"
	a += "        kernel builds/amd64/zoni-reg/linux\n"
	a += "        append initrd=builds/amd64/zoni-reg/initrd_zoni_interactive.gz pxeserver=" + config['pxeServerIP'] +  " imageserver=" + config['imageServerIP'] + " defaultimage=amd64-tashi_nm registerfile=register_node mode=register console=tty1 rw --\n"
	a += "\n"
	a += "LABEL localdisk\n"
	a += "    LOCALBOOT 0\n"
	a += "LABEL rescue\n"
	a += "        kernel ubuntu-installer/hardy/i386/linux\n"
	a += "        append vga=normal initrd=ubuntu-installer/hardy/i386/initrd.gz  rescue/enable=true --\n"
	a += "\n"
	a += "PROMPT 1\n"
	a += "TIMEOUT 100\n"
	return a


		

if __name__ in "__main__":
	main()
