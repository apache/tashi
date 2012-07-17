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
#  $Id:$ 
#

import os 
import string
import logging

from reservationmanagementinterface import ReservationManagementInterface

class reservationMysql(ReservationManagementInterface):
	def __init__(self, config, data, verbose=None):
		self.config = config
		self.data = data
		self.verbose = verbose
		self.log = logging.getLogger(__name__)



	def createReservation (self, userId, reservationDuration=None, reservationNotes=None, vlan=None):
		if not reservationDuration:
			resDuration = str(15)
		else:
			resDuration = str(reservationDuration)

		if len(resDuration) == 8:
			expireDate = resDuration
		elif len(resDuration) < 4:
			numdays = resDuration
			cmd = "date +%Y%m%d --date=\"" + numdays + " day\""
			p = os.popen(cmd)
			expireDate = string.strip(p.read())
		else:
			mesg = "ERROR: Invalid reservation duration\n"
			self.log.info(mesg)
			return
		#  Create the reservation
		print userId, expireDate,reservationNotes
		query = "insert into reservationinfo (user_id, reservation_expiration, notes) values ('%s', '%s', '%s')" % (str(userId), str(expireDate), str(reservationNotes))
		mesg = "Creating new reservation : %s" % query
		self.log.info(mesg)
		self.data.insertDb(query)
		#  Get the res_id
		query = "select max(reservation_id) from reservationinfo"
		res_id = self.data.selectDb(query).fetchone()[0]
		mesg = "  Reservation created - ID : %s" % str(res_id)
		self.log.info(mesg)

		return res_id



	

	def createDomain (self, domain):
		raise NotImplementedError

	def destroyDomain (self, domain):
		raise NotImplementedError

	def addNode2Domain(self, userId):
		raise NotImplementedError

	def addVlan2Domain(self, userId):
		raise NotImplementedError


	def updateReservation (self, userId):
		raise NotImplementedError

	def delReservation (self, userId):
		raise NotImplementedError
	
	def defineReservation(self):
		raise NotImplementedError

	def showReservation(self):
		raise NotImplementedError

