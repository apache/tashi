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

struct BlockLocation {
       list<string> hosts,           // hostnames of data nodes
       list<i32> ports,              // ports for data nodes
       list<string> names,           // hostname:port of data nodes
       i64 blocknum,
       i64 offset,
       i64 length
}

struct Pathname {
       string pathname
}

exception FileNotFoundException {
       string message
}

service layoutservice {
       list <BlockLocation> getFileBlockLocations(1:Pathname path, 2:i64 offset, 3:i64 length)
                            throws (1:FileNotFoundException ouch),
}

service localityservice {
       list <list<double>> getHopCountMatrix(1:list<string> sourceHosts, 2:list<string> destHosts),
}
