<?php
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
#  $Id$
#
function DEBUG($verbose, $val) {
	if ($verbose == 1) {
		if (is_array($val)) {
			$mesg = "DEBUG: " . print_r($val,true) . "<br>\n";
		} else {
			$mesg = "DEBUG: " . $val . "<br>\n";
			
		}
		file_put_contents("/tmp/zoni_register.log", $mesg, FILE_APPEND);

	}
}

function get_netmask ($cidr) {
	$val = $cidr;
	$count = 4;
	$mask = "";
	$oct = "";
	while ($val > 0) {
		if ($val >= 8){
			$mask = $mask . "255.";
			$val -= 8;
			$count -= 1;
			
		} 
		if ($val < 8 ){
			for ($i=0;$i<8;$i++){
				if ($i < $val){
					$oct = $oct . "1";
				}else {
					$oct = $oct . "0";
				}
			}
			$lastoct = base_convert($oct, 2, 10);
			$val -= 8;
			$count -= 1;
			$mask = $mask . $lastoct;
		}
		if ($val <= 0){
			for ($i=0;$i<$count;$i++){
				$mask = $mask  . ".0";
			}
		}
	}
	return $mask;
}

function createPassword($length=8) {
	$pass = NULL;
	for($i=0; $i<$length; $i++) {
		$char = chr(rand(48,122));
		while (!preg_match("/[a-zA-Z0-9]/", $char)){
			$char = chr(rand(48,122));
		}
		$pass .= $char;
	}
	return $pass;
}



class db_connection {
	var $conn;
	var $status;
	var $mydb;
	var $table_headings;
	var $num_rows;
	var $num_fields;
	var $field_names;
	var $results_array;
	var $me;

	function db_connection ($HOST, $DBUSER, $password=NULL, $dbinst) {
		$this->conn = mysql_connect ($HOST, $DBUSER, $password);
		if (!$this->conn) {
			die("Could not connect to $HOST as $DBUSER; " . mysql_error());
		}

		$this->mydb = mysql_select_db ($dbinst, $this->conn);
		if (!$this->mydb) {
			die ("Can't use $dbinst: " . mysql_error());
		}
		if (isset($_SESSION['user_id'])) {
			$this->me =  $_SESSION['user_id'];
		}
		return $this->conn;

	}
	function close () {
		mysql_close ($this->conn);
	}


	//  will return the results of the query
	//  if index is set to 1, array key will be the field names
	function query ($query, $index=NULL) {
		#$result = mysql_query($query) or die('Query failed: ' . mysql_error());
		$result = $this->run_query($query);
		if (!(is_bool($result))) {
			$this->num_fields = $this->set_num_fields($result);
			$this->num_rows = $this->set_num_rows($result);
			$this->field_names = $this->set_field_names($result);
			$this->results_array = array();
			while ($row = mysql_fetch_array($result)) {
				$tmp = array();
				//  number index
				if ($index == 0) {
					for ($i = 0; $i < $this->get_num_fields($result); $i++) {
						array_push ($tmp, $row[$i]);
					}
					array_push($this->results_array, $tmp);
				//  print field labels as array index
				} else {
					for ($i = 0; $i < $this->get_num_fields($result); $i++) {
						$val = $this->field_names[$i];
						$tmp[$val] = $row[$i];
					}
					array_push($this->results_array, $tmp);

				}
			}
		}
		if ($this->get_num_rows($result) == 0) {
			return -1;
		} else {
			return $this->results_array;
		}
	}
	function set_num_fields ($result) {
		return mysql_num_fields($result);
	}

	function get_num_fields () {
		return $this->num_fields;
	}

	function set_num_rows ($result) {
		return mysql_num_rows($result);
	}
	function get_num_rows () {
		return $this->num_rows;
	}

	function set_field_names ($result) {
		$this->field_names = array();
		for ($i = 0; $i < $this->num_fields; $i++) {
		   $var = mysql_field_name($result, $i);
		   array_push ($this->field_names, $var);
		}
		return $this->field_names;
	}

	function get_field_names () {
		return $this->field_names;
	}

	function get_results () {
		return $this->results_array;
	}


	function system_exists ($mac) {
		$query = "select * from sysinfo where mac_addr = '$mac'";
		$result = mysql_query ($query)
			or die ('Check dup query failed: ' . mysql_error());
		$val = $this->set_num_rows ($result);
		if ($val > 0) {
			return 1;
		} else {
			return 0;
		}
	}

	function get_ip_addr($mac) {
		$query = "select ip_addr from sysinfo where mac_addr = '$mac'";
		$val = $this->query($query, 1);
		return $val[0]['ip_addr'];
	}
	function get_location ($sys_id) {

		#  location is not defined in here so get it from db
		$query = "select location from sysinfo where sys_id = '$sys_id'";
		$results = $this->query($query, 1);
		$location = $results[0]['location'];
		return $location;

	}
	function get_sys_id($mac) {
		$query = "select sys_id from sysinfo where mac_addr = '$mac'";
		$val = $this->query($query, 1);
		return $val[0]['sys_id'];
	}

	function check_dup ($table, $colname, $value, $colname2=NULL, $value2=NULL) {
		$cond = "where $colname = '$value'";
		if ($colname2 != NULL && $value2 != NULL) {
			$cond .= " and $colname2 = '$value2'";
		}
		$query = "select * from $table $cond";
		$result = mysql_query($query)
					or die('Check dup query failed: ' . mysql_error());
		$val = $this->set_num_rows ($result);
		return $val;

	}
	function add_system ($G, $u) {
		$val = $this->check_dup ("users", "username", $u['username']);
		if ($val < 1) {
			$user_info = $this->create_new_user($u);
			$msg = "SUCCESS<br> $user_info";
		} else {
			$msg = "A username by this name ";
			$msg .= "({$u['username']}) already exists<br>";
		}
		return $msg;
	}

	/**
	 * This function returns all info about a system 
	 *
	 * @param $G Global var
	 * @return Returns an array of the contents indexed by mac address.
	 */

	function get_system_summary () {
		$query = "select s.mac_addr, s.location, ";
		$query .= "s.num_procs, s.num_cores, s.mem_total, s.clock_speed, ";
		$query .= "s.sys_vendor, s.sys_model, s.proc_vendor, s.proc_model, ";
		#$query .= "s.proc_cache, s.dell_tag, s.cpu_flags, s.bios_rev ";
		$query .= "s.proc_cache, s.dell_tag, s.bios_rev ";
		// $query .= "d.disk_size ";
		#$query .= "from sysinfo s, diskinfo d ";
		$query .= "from sysinfo s";
		//$query .= "where s.mac_addr = d.mac_addr";
		$results = $this->query($query, 1);

		return $results;
	}

	/**
	 * This function returns all images
	 *
	 * @return Returns an array of the contents 
	 */
	function get_images () {
		$image_array = array();
		$query = "select image_name from imageinfo";
		$val = $this->query($query, 1);
		for ($i = 0; $i < count($val); $i++) {
			foreach ($val[$i] as $key => $image) {
				array_push($image_array, $image);
			}
		}
		return $image_array;
	}

	function get_something ($fieldname, $table, $crit_field, $crit) {
		$query = "select $fieldname from $table ";
		$query .= "where $crit_field = '$crit'";
		$val = $this->query($query, 1);
		return $val[0]["$fieldname"];

	}
 
	function get_mac_addr_from_hostname ($node) {
		$query = "select mac_addr from sysinfo ";
		$query .= "where location = '$node' ";
		$val = $this->query($query, 1);
		return $val[0]['mac_addr'];

	}
	function get_hostname_from_mac_addr($mac_addr) {
		$query = "select location from hostinfo ";
		$query .= "where mac_addr = '$mac_addr' ";
		$val = $this->query($query, 1);
		if ($this->num_rows == 1) {
			return $val[0]['location'];
		} else {
			$query = "select location from ";
			$query .= "where mac_addr = '$mac_addr' ";
			$val = $this->query($query, 1);
			return $val[0]['location'];
		}


	}

	function get_image_id_from_image_name ($name) {
		$query = "select image_id from imageinfo ";
		$query .= "where image_name = '$name'";
		$val = $this->query($query, 1);
		return $val[0]['image_id'];
	}



	/**
	 * This function returns image from mac_addr
	 *
	 * @return Returns an array of the contents 
	 */
	function get_current_image($mac_addr) {
		#$mac_addr = $this->get_mac_addr_from_hostname ($node);
		$query = "select image_name from ";
		$query .= "imageinfo i, imagemap j ";
		$query .= "where i.image_id = j.image_id ";
		$query .= "and j.mac_addr = '$mac_addr'";
		$val = $this->query($query, 1);
		return $val[0]['image_name'];
	}


	/**
	 * This function returns all projects
	 *
	 * @return Returns an array of the contents 
	 */
	function get_projects () {
		$my_array = array();
		$query = "select project_id, project_name, description from projectinfo";
		$val = $this->query($query, 1);
		if ($this->get_num_rows() == 0) {
			return 0;
		}
#		for ($i = 0; $i < count($val); $i++) {
#			foreach ($val[$i] as $key => $value) {
#				array_push($my_array, $value);
#			}
#		}
		return $val;
	}

	/**
	 * This function adds a projects
	 *
	 * @return Returns string message
	 * @param  $project_name  
	 * @param  $description  desc of project
	 */
	function add_project ($project_name, $description) {
		$val = $this->check_dup ("projectinfo", "project_name", $project_name);
		if ($val < 1) {
			$query = "insert into projectinfo ";
			$query .= "(project_name, description) ";
			$query .= "values ('$project_name', '$description')";
			$result = mysql_query($query)
				or die('insert into projectinfo query failed: ' . mysql_error());

			return "Entry added to database";
		} else {
			return "Project $project_name exists";
		}
	}

	/*
	 * This function deletes a projects
	 *
	 */
	function del_project($id) {
		$query = "delete from projectinfo ";
		$query .= "where project_id = '$id' ";
		$result = mysql_query($query)
			or die('Deleting projectinfo query failed: ' . mysql_error());
	}

	/*
	 * This function gets all users
	 *
	 * @return Returns array of users
	 */
	function get_users() {
		$my_array = array();
		$query = "select * from userinfo";
		$val = $this->query($query, 1);
		if ($this->get_num_rows() == 0) {
			return 0;
		}
		return $val;
	}

	/*
	 * This function adds a user
	 *
	 * @return Returns string message
	 */
	function add_user($surname, $fname, $user_name, $position, $affil, $notes) {
		$val = $this->check_dup ("userinfo", "user_name", $user_name);
		if ($val < 1) {
			$query = "insert into userinfo ";
			$query .= "(surname, fname, user_name, position, "; 
			$query .= "affiliation, notes ) ";
			$query .= "values ('$surname', '$fname', '$user_name', ";
			$query .= "'$position', '$affil', '$notes')";
			$result = mysql_query($query)
				or die('insert into userinfo query failed: ' . mysql_error());

			return "Entry added to database";
		} else {
			return "User $fname $surname exists";
		}
	}

	/*
	 * This function deletes a user
	 *
	 * @return 
	 */
	function del_user($user_id) {
		$query = "delete from userinfo ";
		$query .= "where user_id = '$user_id' ";
		$result = mysql_query($query)
			or die('Deleting userinfo query failed: ' . mysql_error());
	}

	/**
	 * This runs a generic query
	 *
	 * @ return 0 on success
	 */
	function run_query($query) {
		$result = mysql_query($query)
			or die('Query failed: ' . mysql_error() . "\n$query");
		return $result;
	}

}


?>
