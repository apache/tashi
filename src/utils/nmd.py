#!/usr/bin/python
"""
/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 * 
 *   http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.    
 */
"""

import os
import sys
import getopt
import subprocess
import time

SLEEP_INTERVAL=10
TASHI_PATH="/usr/local/tashi/"
LOG_FILE="/var/log/nodemanager.log"

"""
/* This function changes (on Linux!) its oom scoring, to make it
 * unattractive to kill
 */
"""
def make_invincible():
   # dependent on linux
   try:
      oom_adj_fd = os.open("/proc/self/oom_adj", os.O_WRONLY)
   except IOError:
      pass
   else:
      os.write(oom_adj_fd, "-17\n")
      os.close(oom_adj_fd)

"""
/* This function resets (on Linux!) its oom scoring to default
 */
"""
def make_vulnerable():
   # dependent on linux
   try:
      oom_adj_fd = os.open("/proc/self/oom_adj", os.O_WRONLY)
   except IOError:
      pass
   else:
      os.write(oom_adj_fd, "0\n")
      os.close(oom_adj_fd)

def main(argv=None):
   if argv is None:
      argv = sys.argv
   try:
      opts, args = getopt.getopt(argv[1:], "f", ["foreground"])
   except getopt.GetoptError, err:
      # print help information and exit:
      print str(err) # will print something like "option -a not recognized"
      # usage()
      return 2
   foreground = False
   for o, a in opts:
      if o in ("-f", "--foreground"):
         foreground = True
      else:
         assert False, "unhandled option"
   if foreground == False:
      pid = os.fork();
      if pid != 0:
         os._exit(0)
      os.close(0)
      os.close(1)
      os.close(2)

   # adjust oom preference
   make_invincible()

   # configure environment of children
   env = {"PYTHONPATH":TASHI_PATH+"/src"}
   while True:
      pid = os.fork();
      if pid == 0:
         # child
         # nodemanagers are vulnerable, not the supervisor
         make_vulnerable()
         if foreground == False:
            try:
               lfd = os.open(LOG_FILE, os.O_APPEND|os.O_CREAT|os.O_WRONLY)
            except IOError:
               lfd = os.open("/dev/null", os.O_WRONLY)
            # make this fd stdout and stderr
            os.dup2(lfd, 1)
            os.dup2(lfd, 2)
            # close stdin
            os.close(0)
         os.chdir(TASHI_PATH)
         os.execle("./bin/nodemanager.py", "./bin/nodemanager.py", env)
         os._exit(-1)
      # sleep before checking child status
      time.sleep(SLEEP_INTERVAL)
      os.waitpid(pid, 0)
   return 0

if __name__ == "__main__":
   sys.exit(main())
