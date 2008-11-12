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

from thriftmessaging import *
import logging
import Queue
from ConfigParser import ConfigParser
import time
import socket
import signal

class TashiLogHandler(logging.Handler, PublisherThrift):
    def __init__(self, config, *args, **kwargs):
        self.messages = Queue.Queue()
        self.config = config
        logging.Handler.__init__(self, *args, **kwargs)
        PublisherThrift.__init__(self, 
                                 config.get('MessageBroker', 'host'),
                                 int(config.get('MessageBroker', 'port')))
    def emit(self, record):
        # 'args', 'created', 'exc_info', 'exc_text', 'filename',
        # 'funcName', 'getMessage', 'levelname', 'levelno', 'lineno',
        # 'module', 'msecs', 'msg', 'name', 'pathname', 'process',
        # 'relativeCreated', 'thread', 'threadName']
        msg = {}
        # args
        # created
        # exc_info
        # exc_text
        msg['log-filename'] = str(record.filename)
        msg['log-funcname'] = str(record.funcName)
        msg['log-levelname'] = str(record.levelname)
        msg['log-level'] = str(record.levelno)
        msg['log-lineno'] = str(record.lineno)
        msg['log-module'] = str(record.module)
        msg['log-msecs'] = str(record.msecs)
        msg['log-message'] = str(record.msg)
        msg['log-name'] = str(record.name)
        msg['log-pathname'] = str(record.pathname)
        msg['log-process'] = str(record.process)
        # relativeCreated
        msg['log-thread'] = str(record.thread)
        msg['log-threadname'] = str(record.threadName)

        # standard message fields
        msg['timestamp'] = str(time.time())
        msg['hostname'] = socket.gethostname()
        msg['message-type'] = 'log'

        self.messages.put(msg)
        self.publish(msg)

class TashiSubscriber(SubscriberThrift):
    def __init__(self, config, port, **kwargs):
        sys.stdout.flush()
        brokerPort = int(config.get('MessageBroker', 'port'))
        self.broker = MessageBrokerThriftProxy(config.get('MessageBroker', 'host'), brokerPort)
        SubscriberThrift.__init__(self, self.broker, port, **kwargs)

        

##############################
# Test Code
##############################
import unittest
import sys

class TestTashiSubscriber(TashiSubscriber):
    def __init__(self, *args, **kwargs):
        self.messageQueue = Queue.Queue()
        TashiSubscriber.__init__(self, *args, **kwargs)
    def handle(self, message):
        self.messageQueue.put(message)


def incrementor(start = 0):
    while True:
        a = start
        start = start + 1
        yield a
increment = incrementor()

class TestTashiMessaging(unittest.TestCase):
    def setUp(self):
        self.configFiles = [ '../../../etc/TestConfig.cfg']
        self.config = ConfigParser()
        self.configFiles = self.config.read(self.configFiles)
        self.port = int(self.config.get('MessageBroker', 'port'))

        try:
            self.brokerPid = os.spawnlpe(os.P_NOWAIT, 'python', 'python', 
                                         './messageBroker.py', 
                                         '--port', str(self.port),
                                         os.environ)
            self.port = self.port + 1
            # FIXME: what's the best way to wait for the broker to be ready?
            time.sleep(1)
        except Exception, e:
            sys.exit(0)
        self.initialized = True
        self.log = logging.getLogger('TestTashiMessaging')
        self.handler = TashiLogHandler(self.config)
        self.log.addHandler(self.handler)
        self.sub = TestTashiSubscriber(self.config, int(self.port) + increment.next())
    def tearDown(self):
        os.kill(self.brokerPid, signal.SIGKILL)
        # FIXME: wait for the port to be ready again
        time.sleep(2)
        self.log.removeHandler(self.handler)
#         self.sub.broker.removeSubscriber(self.sub)
        pass
    def testLog(self):
        self.log.log(50, "Hello World!")
        self.handler.messages.get(timeout=5)
        self.sub.messageQueue.get(timeout=5)
        self.assertEqual(self.handler.messages.qsize(), 0)
        self.assertEqual(self.sub.messageQueue.qsize(), 0)
    def testPublish(self):
        sys.stdout.flush()
        self.port = self.port + 1
        self.handler.publish({'message':'hello world'})
        self.sub.messageQueue.get(timeout=5)
        self.assertEqual(self.sub.messageQueue.qsize(), 0)
        

if __name__=='__main__':


#     logging.basicConfig(level=logging.INFO,
#                         format="%(asctime)s %(levelname)s:\t %(message)s",
#                         stream=sys.stdout)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestTashiMessaging)
    unittest.TextTestRunner(verbosity=2).run(suite)
