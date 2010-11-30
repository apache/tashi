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
    include("include/zoni_www_registration.conf");
	include("include/zoni_functions.php");
	$PYTHONPATH=$G['ZONI_BASE_DIR'] . "/src"

    $G = init_globals();
    $verbose = (isset($_GET['verbose'])) ? $_GET['verbose']: 0;

    DEBUG($verbose, "<pre>");
    DEBUG($verbose, $G);


    $action = (isset($_GET['action'])) ? $_GET['action']: NULL;
	DEBUG($verbose, "Action is $action");

    //  Action = reg
    $mac_addr = (isset($_GET['mac'])) ? $_GET['mac']: NULL;
	DEBUG($verbose, "mac_addr - $mac_addr<br>\n");
    //  This format of the mac is required for pxe
    $mod_mac = (isset($_GET['mod_mac'])) ? $_GET['mod_mac']: NULL;
	DEBUG($verbose, "mod_mac - $mod_mac<br>\n");
    $tmp_sys_model = (isset($_GET['sys_model'])) ? $_GET['sys_model']: NULL;
	#  Remove spaces
	$sys_model = preg_replace("/ /", "_", $tmp_sys_model);
	DEBUG($verbose, "sys_model- $sys_model ");
    $bios_rev = (isset($_GET['bios_rev'])) ? $_GET['bios_rev']: NULL;
	DEBUG($verbose, "bios_rev - $bios_rev");
    $system_serial_number = (isset($_GET['system_serial_number'])) ? $_GET['system_serial_number']: NULL;
	DEBUG($verbose, "system_serial_number - $system_serial_number");
    $chassis_serial_number = (isset($_GET['chassis_serial_number'])) ? $_GET['chassis_serial_number']: NULL;
	DEBUG($verbose, "chassis_serial_number - $chassis_serial_number");
    $system_uuid = (isset($_GET['system_uuid'])) ? $_GET['system_uuid']: NULL;
	DEBUG($verbose, "system_uuid - $system_uuid");
    $sys_vendor = (isset($_GET['sys_vendor'])) ? $_GET['sys_vendor']: NULL;
	DEBUG($verbose, "sys_vendor - $sys_vendor");
    $num_disks = (isset($_GET['num_disks'])) ? $_GET['num_disks']: NULL;
	DEBUG($verbose, "num_disks - $num_disks");

    //  action = Query 
    $proc_vendor = (isset($_GET['proc_vendor'])) ? $_GET['proc_vendor']: NULL;
	DEBUG($verbose, "proc_vendor - $proc_vendor");
    $proc_model = (isset($_GET['proc_model'])) ? $_GET['proc_model']: NULL;
	DEBUG($verbose, "proc_model - $proc_model");
    $clock_speed = (isset($_GET['clock_speed'])) ? $_GET['clock_speed']: NULL;
	DEBUG($verbose, "clock_speed - $clock_speed");
    $proc_cache = (isset($_GET['proc_cache'])) ? $_GET['proc_cache']: NULL;
	DEBUG($verbose, "proc_cache - $proc_cache");
    $cpu_flags = (isset($_GET['cpu_flags'])) ? $_GET['cpu_flags']: NULL;
	DEBUG($verbose, "cpu_flags - $cpu_flags");
    $num_procs = (isset($_GET['num_procs'])) ? $_GET['num_procs']: NULL;
    $num_procs = ($num_procs == 0 || $num_procs == "") ? 1 :$num_procs;
	DEBUG($verbose, "num_procs - $num_procs");
    $num_cores = (isset($_GET['num_cores'])) ? $_GET['num_cores']: NULL;
    $num_cores = ($num_cores == "" || $num_cores == 0) ? 1 :$num_cores ;
	DEBUG($verbose, "num_cores - $num_cores");
    $mem_total = (isset($_GET['mem_total'])) ? $_GET['mem_total']: NULL;
	DEBUG($verbose, "mem_total - $mem_total");
    $disk_info = (isset($_GET['disk_info'])) ? $_GET['disk_info']: NULL;
	DEBUG($verbose, "disk_info - $disk_info");

    //  action=finalize
    $ip_addr = (isset($_GET['ip_addr'])) ? $_GET['ip_addr']: NULL;
    DEBUG($verbose, "ip_addr - $ip_addr");
    $location = (isset($_GET['location'])) ? $_GET['location']: NULL;
    DEBUG($verbose, "location - $location");
    $hostname = (isset($_GET['hostname'])) ? $_GET['hostname']: NULL;
    DEBUG($verbose, "hostname - $hostname");
    $image = (isset($_GET['image'])) ? $_GET['image']: NULL;
    DEBUG($verbose, "image - $image");

    //  action=bootopt
    $image_name = (isset($_GET['image_name'])) ? $_GET['image_name']: NULL;
    DEBUG($verbose, "image_name - $image_name");
    $machine_type = (isset($_GET['machine_type'])) ? $_GET['machine_type']: NULL;
    DEBUG($verbose, "machine_type - $machine_type");

	//  IPMI
    $ipmi_addr = (isset($_GET['ipmi_addr'])) ? $_GET['ipmi_addr']: NULL;
    $ipmi_mac = (isset($_GET['ipmi_mac'])) ? $_GET['ipmi_mac']: NULL;
    $ipmi_ver = (isset($_GET['ipmi_ver'])) ? $_GET['ipmi_ver']: NULL;
    $ipmi_rev = (isset($_GET['ipmi_rev'])) ? $_GET['ipmi_rev']: NULL;
    $ipmi_password = (isset($_GET['ipmi_password'])) ? $_GET['ipmi_password']: NULL;

	//  Allocation
    $next_image = (isset($_GET['next_image'])) ? $_GET['next_image']: NULL;

	//  hardware
    $hwport = (isset($_GET['hwport'])) ? $_GET['hwport']: NULL;
    $hwdev = (isset($_GET['hwdev'])) ? $_GET['hwdev']: NULL;
	DEBUG($verbose, "hardware $hwdev $hwport");	

	//  Disk info
	$disk_split = explode(" ", $disk_info);
   
  
    
    //  action=update-hostinfo
    //  getting ip_addr and hostname which are already grabbed



    //  DEBUG : Write out request uri
    $requesturi = $_SERVER['REQUEST_URI'];
    file_put_contents("/tmp/requesturi.txt", $requesturi);

    //  Get a db handle
    $myconn = new db_connection($G['DB_HOST'], 
                                $G['DB_USER'], 
                                $G['DB_PASS'],
								$G['DB_INST']);

    //  Add the link 
    //  Reg is set in the reg initrd image
    //  This will run the first time a system is booted
    if ($action == "register_system") {

        //  If the system is not in the db, add it
        if (!($myconn->system_exists($mac_addr))) {
            $query = "insert into sysinfo ";
            $query .= "(mac_addr, num_procs, num_cores, mem_total, ";
            $query .= "clock_speed, sys_vendor, sys_model, proc_vendor, ";
            $query .= "proc_model, proc_cache, bios_rev, system_serial_number, ";
            $query .= "chassis_serial_number, system_uuid, init_checkin, ";
            $query .= "cpu_flags)";
            $query .= " values ('$mac_addr', '$num_procs', '$num_cores', ";
            $query .= " '$mem_total', '$clock_speed', '$sys_vendor', ";
            $query .= " '$sys_model', '$proc_vendor', '$proc_model', ";
            $query .= " '$proc_cache', '$bios_rev', '$system_serial_number', ";
            $query .= " '$chassis_serial_number', '$system_uuid', NOW(), ";
            $query .= "'$cpu_flags') ";
            DEBUG(1, "query is $query<br>\n");
            $result = mysql_query($query)
                or die('Add system query failed: ' . mysql_error());
        } else {
		#  Update it
            $query = "update sysinfo set ";
            #$query .= "mac_addr = '$mac_addr', ";
			$query .= "num_procs = '$num_procs', ";
			$query .= "num_cores = '$num_cores', ";
			$query .= "mem_total = '$mem_total', ";
            $query .= "clock_speed = '$clock_speed', ";
			$query .= "sys_vendor = '$sys_vendor', ";
			$query .= "sys_model = '$sys_model', ";
			$query .= "proc_vendor = '$proc_vendor', ";
            $query .= "proc_model = '$proc_model', ";
			$query .= "proc_cache = '$proc_cache', ";
			$query .= "bios_rev = '$bios_rev', ";
			$query .= "chassis_serial_number = '$chassis_serial_number', ";
			$query .= "system_uuid = '$system_uuid', ";
            $query .= "cpu_flags = '$cpu_flags' ";
            $query .= " where system_serial_number = '$system_serial_number'";
            DEBUG($verbose, "<br>query is $query <br>\n");
			file_put_contents("/tmp/updatequery.txt", $query);
            $result = mysql_query($query)
                or die('Update system query failed: ' . mysql_error());
		}

		#  Update disk info
		$sys_id = $myconn->get_sys_id($mac_addr);
        if ($myconn->check_dup("diskmap", "sys_id", $sys_id)) {
			DEBUG($verbose, "deleting from diskmap");
            $query = "delete from diskmap ";
            $query .= "where sys_id = '$sys_id'";
			DEBUG($verbose, "query is $query<br>\n");
			$result = mysql_query($query)
				or die('Delete from diskmap failed: ' . mysql_error());
		}

		#  Iterate through the disks and add to db
		for ($i = 0; $i < count($disk_split); $i++) {

			$tmpval = explode(":", $disk_split[$i]);
			DEBUG($verbose, $tmpval);
			$disk_name = $tmpval[0];
			$disk_size = $tmpval[1];

			$query = "insert into diskmap";
			$query .= "(sys_id, disk_name, disk_size) ";
			$query .= "values ('$sys_id', '$disk_name', '$disk_size') ";
			DEBUG($verbose, "query is $query<br>\n");
			$result = mysql_query($query)
				or die('Insert into diskmap failed: ' . mysql_error());
		}

  
	}

	#  add the ip address
	if ($action == "addip") {
		$query = "update sysinfo set ip_addr = '$ip_addr' where mac_addr = '$mac_addr'";
		DEBUG($verbose, "addip query is $query <br>\n");
		#file_put_contents("/tmp/updatequery.txt", $query);
		$result = $myconn->run_query($query);
	}
	#  add the location
	if ($action == "addlocation") {
		$query = "update sysinfo set location = '$location' where mac_addr = '$mac_addr'";
		#DEBUG($verbose, "addip query is $query <br>\n");
		print "query is $query";
		#file_put_contents("/tmp/updatequery.txt", $query);
		$result = $myconn->run_query($query);
	}

	#  Update an image only
	if ($action == "assign_image") {
        $query = "select image_id ";
        $query .= "from imageinfo  ";
        $query .= "where image_name = '$image_name'";
		DEBUG($verbose, "query is $query<br>\n");
        $results = $myconn->query($query);
        DEBUG($verbose, $results);
        $num_rows = $myconn->get_num_rows();
		DEBUG($verbose, "num rows is $num_rows<br>\n");

        if ($num_rows == 1) {
			$image_id = $results[0][0];

            if ($myconn->check_dup("imagemap", "mac_addr", $mac_addr)) {
                $query = "delete from imagemap ";
                $query .= "where mac_addr = '$mac_addr' ";
                $result = $myconn->run_query($query);
            }
		}else {
			$query = "insert into imagemap ";
			$query .= "(mac_addr, image_id) ";
			$query .= "values ('$mac_addr', '$image_id')";
			DEBUG($verbose, "inserting $query<br>\n");
			$result = $myconn->run_query($query);
		}

		$sys_id = $myconn->get_sys_id($mac_addr);
		$location = $myconn->get_location($sys_id);

		DEBUG($verbose, "creating link in pxe");
		print shell_exec("cd {$G['ZONI_BASE_DIR']}; sudo ./bin/zoni-cli.py --assignimage $image_name --nodeName $location");
		DEBUG($verbose, "finished linking in pxe");
	}

	#  Add initial IPMI entry 
	
    if (($action == "add_ipmi") || ($action == "reset_ipmi")) {
		$ipmi_name =$location . "-ipmi";
		$ipmi_pass = createPassword();
		$sys_id = $myconn->get_sys_id($mac_addr);
		print "mac is $mac_addr\n";
		
		print "sysid is $sys_id\n";
		#$dbipaddr = $myconn->get_ip_addr($mac_addr);

		$var = preg_split("/\//", $G['ZONI_IPMI_NETWORK']);		
		DEBUG($verbose, $var);
		$network = $var[1];
		$ipmi_netmask = get_netmask($network);
		$ipminet = preg_split("/\./", $var[0]);		
		DEBUG($verbose, "network is $network, ipmi_netmask is $ipmi_netmask");

		$hostip = preg_split("/\./", $ip_addr);		
		DEBUG(1, "ipaddr is $ip_addr");

		#  Doing the class B for now...
		$mymod = pow(2, (32-$network))/ 256;
		$oct = ($hostip[2] % $mymod) + $ipminet[2] ;
		$ipmi_addr = $hostip[0] . "." . $hostip[1] . "." . $oct . "." . $hostip[3];
		DEBUG($verbose, "ipmi_addr is $ipmi_addr");
		
		if (!($myconn->check_dup("hardwareinfo", "hw_mac", $ipmi_mac))) {
			$ipmi_notes = "Registered by Zoni on : " . date("r", time()) ;
			$query = "insert into hardwareinfo ";
			$query .= "(hw_type, hw_mac, hw_name, hw_ipaddr, hw_userid, hw_password, hw_version_sw, hw_version_fw, hw_notes) ";
			$query .= "values ('ipmi', '$ipmi_mac', '$ipmi_name', '$ipmi_addr', 'root', '$ipmi_pass', $ipmi_rev, $ipmi_ver, '$ipmi_notes')";
			$result = $myconn->run_query($query);
			DEBUG($verbose, $query, $result);

			$hw_id = $myconn->get_something("hw_id", "hardwareinfo", "hw_mac", $ipmi_mac);
			$query = "insert into portmap "; 
			$query .= "(hw_id, sys_id) ";
			$query .= "values ('$hw_id', '$sys_id') "; 
			$result = $myconn->run_query($query);
			DEBUG($verbose, $query, $result);
		} else {
			#  Entry exists, reset password, and update versions
			$query = "update hardwareinfo set ";
			$query .= "hw_password = '$ipmi_pass', ";
			$query .= "hw_ipaddr = '$ipmi_addr',  ";
			$query .= "hw_version_sw = '$ipmi_ver',  ";
			$query .= "hw_version_fw = '$ipmi_rev'  ";
			$query .= "where hw_mac = '$ipmi_mac'";
			$result = $myconn->run_query($query);
			DEBUG($verbose, "UPDATING THE HARDWEARE INFO");
			DEBUG($verbose, $query, $result);
			
		}
		
		#  Add gateway later...
		$ipmi_gateway = "0.0.0.0";

		print "\n\nIPMI_ADDR $ipmi_addr\n";
		print "IPMI_PASSWORD $ipmi_pass\n";
		print "IPMI_DOMAIN {$G['ZONI_HOME_DOMAIN']}\n";
		print "IPMI_NETMASK $ipmi_netmask\n";
		print "IPMI_GATEWAY $ipmi_gateway\n";

		print "IPMI name is $ipmi_name  address is $ipmi_addr\n";
		print shell_exec("PYTHONPATH=$PYTHONPATH  zoni --addDns $ipmi_name $ipmi_addr");
		print shell_exec("PYTHONPATH=$PYTHONPATH zoni --addDhcp $ipmi_name $ipmi_addr $mac_addr");
        #print shell_exec("cd /var/www/cluster-admin/scripts-prs/; sudo ./remove_dns ${location}-ipmi");
        #print shell_exec("cd /var/www/cluster-admin/scripts-prs/; sudo ./remove_rdns ${location}-ipmi $ipmi_addr");
        #print shell_exec("cd /var/www/cluster-admin/scripts-prs/; sudo ./add_dns ${location}-ipmi $ipmi_addr");
        #print shell_exec("cd /var/www/cluster-admin/scripts-prs/; sudo ./add_rdns ${location}-ipmi $ipmi_addr");
		DEBUG($verbose, "finished add_reset_ipmi");
	}

	#  Add switch info to db	
	if ($action == "addhardwareinfo") {
		#  XXX Switch/PDU must already exist before node registration!  
		print "adding hardware info $hwdev\n\n";
		$hw_id  = $myconn->get_something("hw_id","hardwareinfo", "hw_name", $hwdev);
		$sys_id  = $myconn->get_something("sys_id","sysinfo", "mac_addr", $mac_addr);
		DEBUG($verbose, "result is $hw_id ");
		DEBUG($verbose, "mac is $mac_addr node id is $sys_id");

		#  If the hardware doesn't exist, skip
		if ($hw_id == "") {
			DEBUG($verbose, "Hardware doesn't exist!! $hwdev");
		 	exit();
		}
		$query = "select * from portmap where ";
		$query .= "hw_id = '$hw_id' and ";
		$query .= "sys_id = '$sys_id'";
        $results = $myconn->query($query);
        $num_rows = $myconn->get_num_rows();
		#  If there is an entry, delete and reset
		if ($num_rows > 0) {
			DEBUG($verbose, "Entry Exists, deleting... ");
			$query = "delete from portmap where ";
			$query .= "hw_id = '$hw_id' and ";
		 	$query .= "sys_id = '$sys_id'";
			$results = $myconn->query($query);
		}
		DEBUG($verbose, "Adding Entry ... ");
        $query = "insert into portmap "; 
        $query .= "(hw_id, sys_id, port_num) ";
        $query .= "values ('$hw_id', '$sys_id', '$hwport') "; 
		DEBUG($verbose, "Query is $query");
		$results = $myconn->query($query);

	}

	#  update dns and dhcp
	if ($action == "updatednsdhcp") {
		DEBUG($verbose, "Updating DNS/DHCP");
		if (!isset($location) || $location == ""){
			DEBUG($verbose, "location not set");
			#  location is not defined in here so get it from db
			$sys_id = $myconn->get_sys_id($mac_addr);
			$location = $myconn->get_location($sys_id);
		}
		DEBUG($verbose, "location is $location");
		DEBUG($verbose, "doing the dns and dhcp updates");
		#print shell_exec("cd {$G['ZONI_BASE_DIR']}; sudo ./bin/zoni-cli.py --addDns $location $ip_addr");
		#print shell_exec("cd {$G['ZONI_BASE_DIR']}; sudo ./bin/zoni-cli.py --addDhcp $location $ip_addr $mac_addr");
		print shell_exec("PYTHONPATH=$PYTHONPATH zoni --addDns $location $ip_addr");
		print shell_exec("PYTHONPATH=$PYTHONPATH zoni --addDhcp $location $ip_addr $mac_addr");
	}

	#  set next boot image after allocation setup
	if ($action == "next_image") {
        $query = "select image_id ";
        $query .= "from imageinfo  ";
        $query .= "where image_name = '$next_image'";
		print "query is $query<br>";
        $results = $myconn->query($query);
        print_r($results);
        $num_rows = $myconn->get_num_rows();
		print "num rows is $num_rows";

        if ($num_rows == 1) {
            $image_id = $results[0][0];

            if ($myconn->check_dup("imagemap", "mac_addr", $mac_addr)) {
                $query = "delete from imagemap ";
                $query .= "where mac_addr = '$mac_addr' ";
                $result = mysql_query($query)
                    or die('Deleting imagemap query failed: ' . mysql_error());
            }
            $query = "insert into imagemap ";
            $query .= "(mac_addr, image_id) ";
            $query .= "values ('$mac_addr', '$image_id')";
            print "inserting $query<br>\n";
            $result = mysql_query($query)
                or die('insert into imagemap failed: ' . mysql_error());

			echo "creating link in pxe";
			#  Try to use prs to do this...
			print shell_exec("cd /home/rgass/projects/prs/; sudo ./zoni-client.py --assignimage $next_image --nodeName $location");
			#print shell_exec("cd /var/www/cluster/scripts/; sudo ./add_pxe_from_db $location");
			DEBUG($verbose, "finished linking in pxe");
        }
	}

	#  close the connection to the db
    $myconn->close();

?>
