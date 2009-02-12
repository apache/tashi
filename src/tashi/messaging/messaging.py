#!/usr/bin/python

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

import threading
import thread
import sys
import os
import socket
import Queue
import copy
import random
import traceback

from threadpool import ThreadPoolClass, threadpool, ThreadPool
from threadpool import threadpoolmethod, threaded, synchronized, synchronizedmethod

class RWLock(object):
    """RWLock: Simple reader/writer lock implementation
    FIXME: this implementation will starve writers!
    Methods:
        acquire() : take lock for read access
        release() : release lock from read access
        acquireWrite() : take lock for write access
        releaseWrite() : release lock from write access"""
    def __init__(self):
        self.lock = threading.Condition()
        self.readers = 0
    def acquire(self):
        self.lock.acquire()
        self.readers = self.readers + 1
        self.lock.release()
    def release(self):
        self.lock.acquire()
        self.readers = self.readers - 1
        self.lock.notify()
        self.lock.release()
    def acquireWrite(self):
        self.lock.acquire()
        while self.readers > 0:
            self.lock.wait()
    def releaseWrite(self):
        self.lock.notify()
        self.lock.release()



class MessageBroker(object):
    def __init__(self):
        self.sublock = RWLock()
        self.subscribers = []
        self.random = random.Random()
    def log(self, msg):
        print "MessageBroker: Got log: '%s'" % str(msg)
        return msg
    def addSubscriber(self, subscriber):
        self.sublock.acquireWrite()
        self.subscribers.append(subscriber)
        l = len(self.subscribers)
        self.sublock.releaseWrite()
        return l
    def publish(self, message):
        removesubs = []
        i = self.random.randint(0,100)

#         subscribers = self.getSubscribers()
#         random.shuffle(subscribers)

        self.sublock.acquire()

        sys.stdout.flush()

        for subscriber in self.subscribers:
            try:
                sys.stdout.flush()
                assert(subscriber != self)
                subscriber.publish(message)
                sys.stdout.flush()
            except Exception, e:
                print e
                removesubs.append(subscriber)

        self.sublock.release()

        if len(removesubs) > 0:
            print "detected %i failed subscribers" % len(removesubs)
            sys.stdout.flush()
            self.sublock.acquireWrite()
            for subscriber in removesubs:
                try:
                    self.subscribers.remove(subscriber)
                except:
                    pass
            self.sublock.releaseWrite()
    def getSubscribers(self):
        self.sublock.acquire()
        subs = copy.copy(self.subscribers)
        self.sublock.release()
        return subs
    def removeSubscriber(self, subscriber):
        self.sublock.acquireWrite()
        try:
            self.subscribers.remove(subscriber)
        except:
            pass
        self.sublock.releaseWrite()
    def publishList(self, messages):
        for message in messages:
            self.publish(message)

class Subscriber(object):
    def __init__(self, broker, pmatch={}, nmatch={}, synchronized=False):
        self.broker = broker
        self.lock = threading.Lock()
        self.synchronized = synchronized
        self.pmatch={}
        self.nmatch={}
        broker.addSubscriber(self)
    def publish(self, message):
        sys.stdout.flush()
        msg = message
        try:
            if self.synchronized:
                self.lock.acquire()
            msg = self.filter(msg)
            if (msg != None):
                self.handle(msg)
            if self.synchronized:
                self.lock.release()
        except Exception, x:
            if self.synchronized:
                self.lock.release()
            print '%s, %s, %s' % (type(x), x, traceback.format_exc())
    def publishList(self, messages):
        for message in messages:
            self.publish(message)
    def handle(self, message):
        print "Subscriber Default Handler: '%s'" % message
    def setMatch(self, pmatch={}, nmatch={}):
        self.lock.acquire()
        self.pmatch=pmatch
        self.nmatch=nmatch
        self.lock.release()
    def filter(self, message):
        """filter(self, message) : the filter function returns
        the message, modified to be passed to the handler.
        Returning (None) indicates that this is not a message
        we are interested in, and it will not be passed to the
        handler."""
        send = True
        for key in self.pmatch.keys():
            if (not message.has_key(key)):
                send = False
                break
            if self.pmatch[key] != None:
                if message[key] != self.pmatch[key]:
                    send = False
                    break
        if send == False:
            return None
        for key in message.keys():
            if self.nmatch.has_key(key):
                if self.nmatch[key] == None:
                    send = False
                    break
                if self.nmatch[key] == message[key]:
                    send = False
                    break
        if send == False:
            return None
        return message


    
class Publisher(object):
    '''Superclass for pub/sub publishers

    FIXME: use finer-grained locking'''
    def __init__(self, broker, aggregate=100):
        self.pending = []
        self.pendingLock = threading.Lock()
        self.aggregateSize = aggregate
        self.broker = broker
    @synchronizedmethod
    def publish(self, message):
        if message.has_key('aggregate') and message['aggregate'] == 'True':
            self.aggregate(message)
            return
        else:
            self.broker.publish(message)
    @synchronizedmethod
    def publishList(self, messages):
        self.broker.publishList(messages)
    @synchronizedmethod
    def aggregate(self, message):
        # we can make this lock-less by using a queue for pending
        # messages
        self.pendingLock.acquire()
        self.pending.append(message)
        if len(self.pending) >= self.aggregateSize:
            self.broker.publishList(self.pending)
            self.pending = []
        self.pendingLock.release()
    @synchronizedmethod
    def setBroker(self, broker):
        self.broker = broker

##############################
# Testing Code
##############################
import time
import unittest
import sys
import logging

        
class TestSubscriber(Subscriber):
    def __init__(self, *args, **kwargs):
        self.queue = Queue.Queue()
        Subscriber.__init__(self, *args, **kwargs)
    def handle(self, message):
        self.queue.put(message)

class TestMessaging(unittest.TestCase):
    def setUp(self):
        self.broker = MessageBroker()
        self.publisher = Publisher(self.broker)
        self.subscriber = TestSubscriber(self.broker)
    def testPublish(self):
        self.publisher.publish( {'message':'hello world'} )
        self.assertEqual(self.subscriber.queue.qsize(), 1)
    def testPublishList(self):
        nrmsgs = 10
        msgs = []
        for i in range(nrmsgs):
            msgs.append( {'msgnum':str(i)} )
        self.publisher.publishList( msgs )
        self.assertEqual(self.subscriber.queue.qsize(), nrmsgs)
    def testAggregate(self):
        nrmsgs = self.publisher.aggregateSize
        for i in range(nrmsgs):
            self.assertEqual(self.subscriber.queue.qsize(), 0)
            self.publisher.aggregate( {'msgnum':str(i)} )
        self.assertEqual(self.subscriber.queue.qsize(), nrmsgs)
    def testAggregateKeyword(self):
        nrmsgs = self.publisher.aggregateSize
        for i in range(nrmsgs):
            self.assertEqual(self.subscriber.queue.qsize(), 0)
            self.publisher.publish( {'msgnum':str(i), 'aggregate':'True'} )
        self.assertEqual(self.subscriber.queue.qsize(), nrmsgs)

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s:\t %(message)s",
                        stream=sys.stdout)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestMessaging)
    unittest.TextTestRunner(verbosity=2).run(suite) 

    sys.exit(0)


##############################
# Old/Unused testing code
##############################



    print 'testing removeSubscriber'
    broker.removeSubscriber(subscriber)
    publisher.publish( {'message':"you shouldn't see this"} )

    nsub = NullSubscriber(broker)
    print 'timing publish'
    nrmsg = 100000
    tt = time.time()
    for i in range(nrmsg):
#        publisher.publish( {"message":"hello world!"} )
        publisher.publish( {} )
    tt = time.time() - tt
    print "Published %i messages in %f seconds, %f msg/s"%(nrmsg,
                                                           tt,
                                                           nrmsg/tt)
    broker.removeSubscriber(nsub)

    class SlowSubscriber(Subscriber):
        def handle(self, message):
            print 'called slow subscriber with message', message
            time.sleep(1)
            print 'returning from slow subscriber with message', message
    class ThreadedSubscriber(Subscriber):
        @threaded
        def handle(self, message):
            print 'called threaded subscriber with message', message
            time.sleep(1)
            print 'returning from threaded subscriber with message', message
    class ThreadPoolSubscriber(Subscriber, ThreadPoolClass):
        @threadpoolmethod
        def handle(self, message):
            print 'called threadpool subscriber with message', message
            time.sleep(1)
            print 'returning from threadpool subscriber with message', message



    tsub = ThreadedSubscriber(broker)
    for i in range(8):
        publisher.publish( {"msg":str(i)} )
    broker.removeSubscriber(tsub)
    time.sleep(3)

    tpsub = ThreadPoolSubscriber(broker)
    for i in range(8):
        publisher.publish( {"msg":str(i)} )
    broker.removeSubscriber(tpsub)
    time.sleep(3)

    ssub = SlowSubscriber(broker)
    for i in range(4):
        publisher.publish( {"msg":str(i)} )
    broker.removeSubscriber(ssub)
