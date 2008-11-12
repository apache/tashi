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

import tashi.messaging.tashimessaging

class Notifier(tashi.messaging.tashimessaging.TashiLogHandler):
    def vmExited(self, instance):
        try:
            isolatedRPC(self.cm, 'vmExited', self.hostId, vmId)
        except Exception, e:
            print "RPC failed for vmExited on CM"
            print e
            # FIXME: send this to the cm later
            # self.exitedVms[vmId] = child

        msg = {}

        msg['timestamp'] = str(time.time())
        msg['hostname'] = ''    # FIXME: fill this in
        msg['message-type'] = 'vm-event'
        msg['vm-event'] = 'vm-exited'
        
        msg['instance-id'] = str(instance.id)
        msg['host-id'] = str(instance.hostId)
        print 'Notifier publishing ', msg
        self.publish(message)
