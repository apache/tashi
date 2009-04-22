#!/usr/bin/python

import sys
import os
from os import system

import tashi.services.layoutlocality.localityservice as localityservice

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

from tashi.util import getConfig

(config, configFiles) = getConfig(["Client"])
host = config.get('LocalityService', 'host')
port = int(config.get('LocalityService', 'port'))

socket = TSocket.TSocket(host, port)
transport = TTransport.TBufferedTransport(socket)
protocol = TBinaryProtocol.TBinaryProtocol(transport)
client = localityservice.Client(protocol)
transport.open()

while True:
       line1 = "\n"
       line2 = "\n"
       while line1 != "":
               line1 = sys.stdin.readline()
               if line1 == "":
                       sys.exit(0)
               if line1 != "\n":
                       break
       line1 = line1.strip()
       while line2 != "":
               line2 = sys.stdin.readline()
               if line2 == "":
                       sys.exit(0)
               if line2 != "\n":
                       break
       line2 = line2.strip()

       sources = line1.split(" ")
       destinations = line2.split(" ")

       mat = client.getHopCountMatrix(sources, destinations)
       for r in mat:
               for c in r:
                       print '%f\t'%c,
               print '\n',
       print '\n',
