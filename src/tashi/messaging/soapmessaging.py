#! /usr/bin/env python

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

from messaging import *

import cPickle
import soaplib.wsgi_soap
import cherrypy.wsgiserver
from soaplib.service import soapmethod
from soaplib.serializers.primitive import *
import SOAPpy.WSDL
import time

class MessageBrokerSoap(soaplib.wsgi_soap.SimpleWSGISoapApp, MessageBroker):
	def __init__(self, port):
		soaplib.wsgi_soap.SimpleWSGISoapApp.__init__(self)
		MessageBroker.__init__(self)
		self.port = port
		def trdfn():
			service = self
			server = cherrypy.wsgiserver.CherryPyWSGIServer(("0.0.0.0",port), service)
			server.start()
		threading.Thread(target=trdfn).start()


	@soapmethod(Array(String), Array(String), _returns=Null)
	def log(self, keys, values):
		message = {}
		if len(keys) != len(values):
			raise Exception, "Different lengths for keys and values"
		for i in range(len(keys)):
			message[keys[i]] = values[i]
		MessageBroker.log(self, message)

	@soapmethod(String, Integer, _returns=Null)
	def addSubscriber(self, host, port):
		subscriber = SubscriberSoapProxy(host, port)
		MessageBroker.addSubscriber(self, subscriber)
	
	@soapmethod(String, Integer, _returns=Null)
	def removeSubscriber(self, host, port):
		# should this method really be able to peek into subscriber.host/port 
		subscriber = None
		subscribers = self.getSubscribers()
		for subscriber in subscribers:
			if subscriber.host == host and subscriber.port == port:
				subscriber = subscriber
		if subscriber != None:
			MessageBroker.removeSubscriber(self, subscriber)
		

	@soapmethod(Array(String), Array(String), _returns=Null)
	def publish(self, keys, values):
		message = {}
		if len(keys) != len(values):
			raise Exception, "Different lengths for keys and values"
		for i in range(len(keys)):
			message[keys[i]] = values[i]
		MessageBroker.publish(self, message)



class MessageBrokerSoapProxy(object):
	def __init__(self, host, port):
		self.host = host
		self.port = port
		self.connection = SOAPpy.WSDL.Proxy("http://%s:%i/.wsdl"%(host,port))
	def log(self, message):
		keys = []
		values = []
		for k,v in message.items():
			keys.append(k)
			values.append(v)
		self.connection.log(keys=keys, values=values)
	def addSubscriber(self, subscriber):
		self.connection.addSubscriber(host=subscriber.host, port=subscriber.port)
	def publish(self, message):
		keys = []
		values = []
		for k,v in message.items():
			keys.append(k)
			values.append(v)
		self.connection.publish(keys=keys, values=values)
	def removeSubscriber(self, subscriber):
		self.connection.removeSubscriber(host=subscriber.host, port=subscriber.port)




class SubscriberSoap(soaplib.wsgi_soap.SimpleWSGISoapApp, Subscriber):
	def __init__(self, broker, port, synchronized=False):
		soaplib.wsgi_soap.SimpleWSGISoapApp.__init__(self)
		Subscriber.__init__(self, synchronized=synchronized)
		self.host = socket.gethostname()
		self.port = port
		self.broker = broker
		self.server = None
		def trdfn():
			service = self
			self.server = cherrypy.wsgiserver.CherryPyWSGIServer(("0.0.0.0",port), service)
			self.server.start()
		threading.Thread(target=trdfn).start()
#		broker.log("Subscriber started")
		broker.addSubscriber(self)
	@soapmethod(Array(String), Array(String), _returns=Integer)
	def publish(self, keys, values):
		message = {}
		if len(keys) != len(values):
			raise Exception, "Different lengths for keys and values"
		for i in range(len(keys)):
			message[keys[i]] = values[i]
		Subscriber.publish(self, message)
		return 0
	def stop(self):
		self.server.stop()

class SubscriberSoapProxy(object):
	def __init__(self, host, port):
		self.host = host
		self.port = port
		self.connection = SOAPpy.WSDL.Proxy("http://%s:%i/.wsdl"%(host,port))
	def publish(self, message):
		keys = []
		values = []
		for k,v in message.items():
			keys.append(k)
			values.append(v)
		self.connection.publish(keys=keys, values=values)


####################
# Testing Code 
####################

class CustomSubscriber(SubscriberSoap):
	def handle(self, message):
		print "Custom Subscriber: '%s'" % str(message)

class NullSubscriber(SubscriberSoap):
	def handle(self, message):
		pass


if __name__ == '__main__':
	try:
		portnum = 1717

		print "\ntesting message broker"
		broker = MessageBrokerSoap(portnum)
		proxy = MessageBrokerSoapProxy("localhost", portnum)
		portnum = portnum + 1 

		print "\ntesting log function"
		proxy.log( {"message":"Hello World!"} )
#		proxy.log("It looks like log works")

		print "\ntesting subscriber proxy"
		subscriber = SubscriberSoap(proxy, portnum)
		portnum = portnum + 1

		print "\ntesting custom subscriber"
		csub = CustomSubscriber(proxy, portnum)
		portnum = portnum + 1

		print "\ntesting publish"
		proxy.publish( {"message":"Hello World!"} )

		print "\ntesting stop"
		subscriber.stop()
		proxy.publish( {"message":"Everybody here?"} )

		print "\ntesting removeSubscriber"
		proxy.removeSubscriber(csub)
		proxy.publish( {"message":"Nobody home"} )
		proxy.addSubscriber(csub)
		proxy.publish( {"message":"You're back!"} )

		print "\ntesting filter"
		csub.setMatch( {"print":"yes"} )
		proxy.publish( {"print":"yes", "message":"this should be printed"} )
		proxy.publish( {"print":"no", "message":"this should NOT be printed"} )
		csub.setMatch()

		print "\ntesting publish performance"
		proxy.removeSubscriber(csub)
		nrmsg = 10000
		tt = time.time()
		for i in range(nrmsg):
			proxy.publish( {"message":"msg %i"%i} )
		tt = time.time() - tt
		print "Published %i messages in %f seconds, %f msg/s"%(nrmsg,
															   tt,
															   nrmsg/tt)

		print "\ntesting publish/subscribe performance"
		nsub = NullSubscriber(proxy, portnum)
		portnum = portnum + 1
		nrmsg = 10000
		tt = time.time()
		for i in range(nrmsg):
			proxy.publish( {"message":"msg %i"%i} )
		tt = time.time() - tt
		print "Published %i messages in %f seconds, %f msg/s"%(nrmsg,
															   tt,
															   nrmsg/tt)

																   

	except Exception, e:
#		raise e
		print  e
		sys.exit(0)
	sys.exit(0)
