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
import time
import Queue
import logging

_log = logging.getLogger('tashi.parallel')

def threaded(func):
    def fn(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return fn


class ThreadPool(Queue.Queue):
    def __init__(self, size=8, maxsize=0):
        Queue.Queue.__init__(self, maxsize)
        for i in range(size):
            thread = threading.Thread(target=self._worker)
            thread.setDaemon(True)
            thread.start()
    def _worker(self):
        while True:
            try:
                func, args, kwargs = self.get()
                func(*args, **kwargs)
            except Exception, e:
                _log.error(e)
                # FIXME: do something smarter here, backtrace, log,
                # allow user-defined error handling...
                
    def submit(self, func, *args, **kwargs):
        self.put((func, args, kwargs))
    def submitlist(self, func, args, kwargs):
        self.put((func, args, kwargs))

class ThreadPoolClass:
    def __init__(self, size=8, maxsize=0):
        self._threadpool_pool = ThreadPool(size=size, maxsize=maxsize)


def threadpool(pool):
    def dec(func):
        def fn(*args, **kwargs):
            pool.submit(func, *args, **kwargs)
        return fn
    return dec

def threadpoolmethod(meth):
    def fn(*args, **kwargs):
        try:
            pool = args[0]._threadpool_pool
        except AttributeError:
            pool = args[0].__dict__.setdefault('_threadpool_pool', ThreadPool())
        # FIXME: how do we check parent class?
#        assert args[0].__class__ == ThreadPoolClass, "Thread pool method must be in a ThreadPoolClass"
        pool.submit(meth, *args, **kwargs)
    return fn

def synchronized(lock=None):
    if lock==None:
        lock = threading.RLock()
    def dec(func):
        def fn(*args, **kwargs):
            lock.acquire()
            ex = None
            try:
                r = func(*args, **kwargs)
            except Exception, e:
                ex = e
            lock.release()
            if ex != None:
                raise e
            return r
        return fn
    return dec
            
def synchronizedmethod(func):
    def fn(*args, **kwargs):
        try:
            lock = args[0]._synchronized_lock
        except AttributeError:
            lock = args[0].__dict__.setdefault('_synchronized_lock', threading.RLock())
        lock.acquire()
        ex = None
        try:
            res = func(*args, **kwargs)
        except Exception, e:
            ex = e
        lock.release()
        if ex != None:
            raise e
        return res
    return fn
        

##############################
# Test Code
##############################
import unittest
import sys
import time

class TestThreadPool(unittest.TestCase):
    def setUp(self):
        self.errmargin = 0.5

    def testUnthreaded(self):
        queue = Queue.Queue()
        def slowfunc(sleep=1):
            time.sleep(sleep)
            queue.put(None)
        tt = time.time()
        for i in range(4):
            slowfunc()
        for i in range(4):
            queue.get()
        tt = time.time() - tt
        self.assertAlmostEqual(tt, 4, 1) 

    def testThreaded(self):
        queue = Queue.Queue()
        @threaded
        def slowthreadfunc(sleep=1):
            time.sleep(sleep)
            queue.put(None)
        tt = time.time()
        for i in range(8):
            slowthreadfunc()
        for i in range(8):
            queue.get()
        tt = time.time() - tt
        self.assertAlmostEqual(tt, 1, 1) 

    def testThreadPool(self):
        pool = ThreadPool(size=4)
        queue = Queue.Queue()
        @threadpool(pool)
        def slowpoolfunc(sleep=1):
            time.sleep(sleep)
            queue.put(None)
        tt = time.time()
        for i in range(8):
            slowpoolfunc()
        for i in range(8):
            queue.get()
        tt = time.time() - tt
        self.assertAlmostEqual(tt, 2, 1) 

    def testUnthreadedMethod(self):
        queue = Queue.Queue()
        class slowclass:
            def __init__(self, sleep=1):
                self.sleep=sleep
            def beslow(self):
                time.sleep(self.sleep)
                queue.put(None)
        sc = slowclass()
        tt = time.time()
        for i in range(4):
            sc.beslow()
        for i in range(4):
            queue.get()
        tt = time.time() - tt
        self.assertAlmostEqual(tt, 4, 1)
    
    def testThreadedMethod(self):
        queue = Queue.Queue()
        class slowclass:
            def __init__(self, sleep=1):
                self.sleep=sleep
            @threaded
            def beslow(self):
                time.sleep(self.sleep)
                queue.put(None)
        sc = slowclass()
        tt = time.time()
        for i in range(4):
            sc.beslow()
        for i in range(4):
            queue.get()
        tt = time.time() - tt
        self.assertAlmostEqual(tt, 1, 1)
    
    def testThreadPoolMethod(self):
        queue = Queue.Queue()
        class slowclass:
            def __init__(self, sleep=1):
                self.sleep=sleep
            @threadpoolmethod
            def beslow(self):
                time.sleep(self.sleep)
                queue.put(None)
        sc = slowclass()
        tt = time.time()
        for i in range(16):
            sc.beslow()
        for i in range(16):
            queue.get()
        tt = time.time() - tt
        self.assertAlmostEqual(tt, 2, 1)
    
    def testSynchronized(self):
        queue = Queue.Queue()
        @synchronized()
        def addtoqueue():
            time.sleep(1)
            queue.put(None)
        @threaded
        def slowthreadfunc():
            addtoqueue()
        tt = time.time()
        for i in range(4):
            slowthreadfunc()
        for i in range(4):
            queue.get()
        tt = time.time() - tt
        self.assertAlmostEqual(tt, 4, 1) 

    def testSynchronizedMethod(self):
        queue = Queue.Queue()
        class addtoqueue:
            @synchronizedmethod
            def addtoqueue1(self):
                time.sleep(1)
                queue.put(None)
            @synchronizedmethod
            def addtoqueue2(self):
                time.sleep(1)
                queue.put(None)
        atc = addtoqueue()
        @threaded
        def slowthreadfunc1():
            atc.addtoqueue1()
        @threaded
        def slowthreadfunc2():
            atc.addtoqueue2()
        tt = time.time()
        for i in range(4):
            slowthreadfunc1()
            slowthreadfunc2()
        for i in range(8):
            queue.get()
        tt = time.time() - tt
        self.assertAlmostEqual(tt, 8, 1) 

    def testUnsynchronizedMethod(self):
        queue = Queue.Queue()
        class addtoqueue:
            def addtoqueue1(self):
                time.sleep(1)
                queue.put(None)
            def addtoqueue2(self):
                time.sleep(1)
                queue.put(None)
        atc = addtoqueue()
        @threaded
        def slowthreadfunc1():
            atc.addtoqueue1()
        @threaded
        def slowthreadfunc2():
            atc.addtoqueue2()
        tt = time.time()
        for i in range(4):
            slowthreadfunc1()
            slowthreadfunc2()
        for i in range(8):
            queue.get()
        tt = time.time() - tt
        self.assertAlmostEqual(tt, 1, 1) 



if __name__=='__main__':
    import sys

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s:\t %(message)s",
                        stream=sys.stdout)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestThreadPool)
    unittest.TextTestRunner(verbosity=2).run(suite)
