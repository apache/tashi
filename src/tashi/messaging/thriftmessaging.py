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

import sys
import time
import socket
import traceback
import threading

sys.path.append('./gen-py')
import tashi.messaging.messagingthrift
import tashi.messaging.messagingthrift.MessageBrokerThrift
import tashi.messaging.messagingthrift.SubscriberThrift
from tashi.messaging.messagingthrift.ttypes import *

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

from tashi import ConnectionManager

from tashi.messaging.messaging import *
from tashi.messaging.threadpool import ThreadPoolClass, threadpool, ThreadPool, threadpoolmethod, threaded

class MessageBrokerThrift(MessageBroker):
    def __init__(self, port, daemon=True):
        MessageBroker.__init__(self)
        self.processor = tashi.messaging.messagingthrift.MessageBrokerThrift.Processor(self)
        self.transport = TSocket.TServerSocket(port)
        self.tfactory = TTransport.TBufferedTransportFactory()
        self.pfactory = TBinaryProtocol.TBinaryProtocolFactory()
        self.proxy = ConnectionManager(tashi.messaging.messagingthrift.SubscriberThrift.Client, 0)
        self.ready = threading.Event()
#         self.server = TServer.TSimpleServer(self.processor,
#                                             self.transport,
#                                             self.tfactory,
#                                             self.pfactory)
#         self.server = TServer.TThreadPoolServer(self.processor,
#                                                 self.transport,
#                                                 self.tfactory,
#                                                 self.pfactory)
        self.server = TServer.TThreadedServer(self.processor,
                                                self.transport,
                                                self.tfactory,
                                                self.pfactory)
        self.publishCalls = 0

        def ssvrthrd():
            try:
                # FIXME: Race condition, the ready event should be set after
                # starting the server.  However, server.serve()
                # doesn't return under normal circumstances.  This
                # seems to work in practice, even though it's clearly
                # wrong.
                self.ready.set()
                self.server.serve()
            except Exception, e:
                print e
                sys.stdout.flush()
                pass
        svt = threading.Thread(target=ssvrthrd)
        svt.setDaemon(daemon)
        svt.start()
        self.ready.wait()
    def log(self, message):
        MessageBroker.log(self, message)
    @synchronizedmethod
    def addSubscriber(self, host, port):
        subscribers = self.getSubscribers()
        for sub in subscribers:
            if sub.host == host and sub.port == port:
                return
        subscriber = SubscriberThriftProxy(host, port, self.proxy)
        MessageBroker.addSubscriber(self, subscriber)
    def removeSubscriber(self, host, port):
        subscriber = None
        subscribers = self.getSubscribers()
        for sub in subscribers:
            if sub.host == host and sub.port == port:
                subscriber = sub
        if subscriber != None:
            MessageBroker.removeSubscriber(self, subscriber)
    @synchronizedmethod
    def publish(self, message):
        self.publishCalls  = self.publishCalls + 1
        sys.stdout.flush()
        MessageBroker.publish(self, message)

class MessageBrokerThriftProxy:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.proxy = ConnectionManager(tashi.messaging.messagingthrift.MessageBrokerThrift.Client,port)
    @synchronizedmethod
    def log(self, message):
        self.proxy[self.host, self.port].log(message)
    @synchronizedmethod
    def publish(self, message):
        self.proxy[self.host, self.port].publish(message)
    @synchronizedmethod
    def publishList(self, messages):
        self.proxy[self.host, self.port].publishList(messages)
    @synchronizedmethod
    def addSubscriber(self, subscriber):
        self.proxy[self.host, self.port].addSubscriber(host=subscriber.host, port=subscriber.port)
    @synchronizedmethod
    def removeSubscriber(self, subscriber):
        self.proxy[self.host, self.port].removeSubscriber(host=subscriber.host, port=subscriber.port)



class SubscriberThrift(Subscriber, threading.Thread):
    def __init__(self, broker, port, synchronized=False):
        self.host = socket.gethostname()
        self.port = port
        self.processor = tashi.messaging.messagingthrift.SubscriberThrift.Processor(self)
        self.transport = TSocket.TServerSocket(port)
        self.tfactory = TTransport.TBufferedTransportFactory()
        self.pfactory = TBinaryProtocol.TBinaryProtocolFactory()
        self.server = TServer.TThreadedServer(self.processor,
                                              self.transport,
                                              self.tfactory,
                                              self.pfactory)
        def ssvrthrd():
            try:
                self.server.serve()
            except Exception, e:
                pass


        self.thread = threading.Thread(target=ssvrthrd)
        self.thread.setDaemon(True)
        self.thread.start()

        # We have to call this AFTER initializing our server, so that
        # the broker can contact us
        # Wrap this in a try/catch because the broker may not be online yet
        try:
            Subscriber.__init__(self, broker,  synchronized=synchronized)        
        except:
            pass
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.start()

    def stop(self):
#         # FIXME: this is broken, there is no clear way to stop a
#         # Thrift server
        self.broker.removeSubscriber(self)
        self.transport.close()
    def run(self):
        while(True):
            # renew subscription every 5 min
            try:
                self.broker.addSubscriber(self)
            except:
                pass
            time.sleep(5*60)

class SubscriberThriftProxy:
    def __init__(self, host, port, proxy, aggregate = 100):
        self.host = host
        self.port = port
        self.proxy = proxy
        # for some reason, thrift clients are not thread-safe, lock during send
        self.lock = threading.Lock()
        self.pending = []
        self.aggregateSize = aggregate
    def publish(self, message):
        self.lock.acquire()
        sys.stdout.flush()
        if message.has_key('aggregate') and message['aggregate'] == 'True':
            self.pending.append(message)
            if len(self.pending) >= self.aggregateSize:
                try:
                    self.proxy[self.host, self.port].publishList(self.pending)
                except Exception, e:
                    print e
                    self.lock.release()
                    raise e
                self.pending = []
        else:
            try:
                self.proxy[self.host, self.port].publish(message)
            except Exception, e:
                sys.stdout.flush()
                print e
                self.lock.release()
                raise e
        self.lock.release()

class PublisherThrift(Publisher):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.broker = MessageBrokerThriftProxy(host, port)
        Publisher.__init__(self, self.broker)
        
####################
# Testing Code 
####################

class TestSubscriberThrift(SubscriberThrift):
    def __init__(self, *args, **kwargs):
        self.queue = Queue.Queue()
        SubscriberThrift.__init__(self, *args, **kwargs)
    def handle(self, message):
        self.queue.put(message)

portnum = 1718
class TestThriftMessaging(unittest.TestCase):
    def setUp(self):
        global portnum
        self.broker = MessageBrokerThrift(portnum)
        self.brokerPort = portnum
        portnum = portnum + 1 
        self.proxy = MessageBrokerThriftProxy('localhost', self.brokerPort)
        self.publisher = PublisherThrift('localhost', self.brokerPort)
        self.subscriber = TestSubscriberThrift(self.proxy, portnum)
        portnum = portnum + 1
    def tearDown(self):
        pass
    def testSetUp(self):
        pass
    def testPublish(self):
        self.publisher.publish( {'message':'hello world'} )
        self.subscriber.queue.get(True, timeout=5)
        self.assertEqual(self.subscriber.queue.qsize(), 0)
    def testPublishList(self):
        nrmsgs = 10
        msgs = []
        for i in range(nrmsgs):
            msgs.append( {'msgnum':str(i)} )
        self.publisher.publishList( msgs )
        for i in range(nrmsgs):
            self.subscriber.queue.get(True, timeout=5)
        self.assertEqual(self.subscriber.queue.qsize(), 0)
    def testAggregate(self):
        nrmsgs = self.publisher.aggregateSize
        for i in range(nrmsgs):
            self.assertEqual(self.subscriber.queue.qsize(), 0)
            self.publisher.aggregate( {'msgnum':str(i)} )
        for i in range(nrmsgs):
            self.subscriber.queue.get(True, timeout=5)
        self.assertEqual(self.subscriber.queue.qsize(), 0)
    def testAggregateKeyword(self):
        nrmsgs = self.publisher.aggregateSize
        for i in range(nrmsgs):
            self.assertEqual(self.subscriber.queue.qsize(), 0)
            self.publisher.publish( {'msgnum':str(i), 'aggregate':'True'} )
        for i in range(nrmsgs):
            self.subscriber.queue.get(True, timeout=5)
        self.assertEqual(self.subscriber.queue.qsize(), 0)


if __name__=='__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestThriftMessaging)
    unittest.TextTestRunner(verbosity=2).run(suite)


