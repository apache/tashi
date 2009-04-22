#! /usr/bin/env python

from socket import gethostname
import os
import threading
import time
import socket

from tashi.services.ttypes import *

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

from tashi.services import clustermanagerservice
from tashi.util import getConfig, createClient
from tashi.parallel import *

import tashi.services.layoutlocality.localityservice as localityservice

from numpy import *
from scipy import *

cnames = {}
def cannonicalName(hn):
       try:
               if cnames.has_key(hn):
                       return cnames[hn]
               r = socket.gethostbyname_ex(hn)[0]
               cnames[hn] = r
               return r
       except:
               return hn

def genMul(A, B, add, mult):
       '''generalized matrix multiplication'''
       C = zeros((shape(A)[0], shape(B)[1]))
       for i in range(shape(C)[0]):
               for j in range(shape(C)[1]):
                       C[i,j] = add(mult(A[i,:], B[:,j]))
       return C

def addHost(graph, hostVals, host):
       if not graph.has_key(host):
               graph[host] = []
       if not hostVals.has_key(host):
               hostVals[host] = len(hostVals)

def graphConnect(graph, h1, h2):
       if not h1 in graph[h2]:
               graph[h2].append(h1)
       if not h2 in graph[h1]:
               graph[h1].append(h2)

def graphFromFile(fn = 'serverLayout', graph = {}, hostVals = {}):
       f = open(fn)
       for line in f.readlines():
               line = line.split()
               if len(line) < 1:
                       continue
               server = cannonicalName(line[0].strip())

               addHost(graph, hostVals, server)
               for peer in line[1:]:
                       peer = cannonicalName(peer.strip())
                       addHost(graph, hostVals, peer)
                       graphConnect(graph, server, peer)
       return graph, hostVals

def graphFromTashi(client, transport, graph={}, hostVals={}):
       print 'getting graph'
       if not transport.isOpen():
               transport.open()
       hosts = client.getHosts()
       instances = client.getInstances()
       for instance in instances:
               host = [cannonicalName(h.name) for h in hosts if h.id == instance.hostId]
               if len(host) <1 :
                       print 'cant find vm host'
                       continue
               host = host[0]
               print 'host is ', host
               addHost(graph, hostVals, host)
               print 'added host'
               vmhost = cannonicalName(instance.name)
               addHost(graph, hostVals, vmhost)
               print 'added vm'
               graphConnect(graph, host, vmhost)
               print 'connected'
       print 'returning from graphFromTashi'
       return graph, hostVals



def graphToArray(graph, hostVals):
       a = zeros((len(hostVals), len(hostVals)))
       for host in graph.keys():
               if not hostVals.has_key(host):
                       continue
               a[hostVals[host], hostVals[host]] = 1
               for peer in graph[host]:
                       if not hostVals.has_key(peer):
                               continue
                       a[hostVals[host], hostVals[peer]] = 1
       a[a==0] = inf
       for i in range(shape(a)[0]):
               a[i,i]=0
       return a

def shortestPaths(graphArray):
       a = graphArray
       for i in range(math.ceil(math.log(shape(a)[0],2))):
               a = genMul(a,a,min,plus)
       return a

def plus(A, B):
       return A + B


def getHopCountMatrix(sourceHosts, destHosts, array, hostVals):
       a = zeros((len(sourceHosts), len(destHosts)))
       a[a==0] = inf
       for i in range(len(sourceHosts)):
               sh = cannonicalName(sourceHosts[i])
               shv = None
               if hostVals.has_key(sh):
                       shv = hostVals[sh]
               else:
                       print 'host not found', sh
                       continue
               for j in range(len(destHosts)):
                       dh = cannonicalName(destHosts[j])
                       dhv = None
                       if hostVals.has_key(dh):
                               dhv = hostVals[dh]
                       else:
                               print 'dest not found', dh
                               continue
                       print sh, dh, i,j, shv, dhv, array[shv, dhv]
                       a[i,j] = array[shv, dhv]
       return a


class LocalityService:
       def __init__(self):
               (config, configFiles) = getConfig(["Agent"])
               self.port = int(config.get('LocalityService', 'port'))
               print 'Locality service on port %i' % self.port
               self.processor = localityservice.Processor(self)
               self.transport = TSocket.TServerSocket(self.port)
               self.tfactory = TTransport.TBufferedTransportFactory()
               self.pfactory = TBinaryProtocol.TBinaryProtocolFactory()
               self.server = TServer.TThreadedServer(self.processor,
                                                     self.transport,
                                                     self.tfactory,
                                                     self.pfactory)

               self.hostVals =[]
               self.array = array([[]])
               self.rtime = 0


               self.fileName = os.path.expanduser(config.get("LocalityService", "staticLayout"))
               (self.client, self.transport) = createClient(config)

               self.server.serve()

       @synchronizedmethod
       def refresh(self):
               if time.time() - self.rtime < 10:
                       return
               g, self.hostVals = graphFromFile(self.fileName)
               try:
                       g, self.hostVals = graphFromTashi(self.client, self.transport, g, self.hostVals)
               except e:
                       print e
                       print 'could not get instance list from cluster manager'
               print 'graph to array'
               a = graphToArray(g, self.hostVals)
               print 'calling shortest paths ', a.shape
               self.array = shortestPaths(a)
               print 'computed shortest paths'
               print self.array
               print self.hostVals
       @synchronizedmethod
       def getHopCountMatrix(self, sourceHosts, destHosts):
               self.refresh()
               print 'getting hop count matrix for', sourceHosts, destHosts
               hcm =  getHopCountMatrix(sourceHosts, destHosts, self.array, self.hostVals)
               print hcm
               return hcm


def main():
       ls = LocalityService()

if __name__ == "__main__":
       main()
