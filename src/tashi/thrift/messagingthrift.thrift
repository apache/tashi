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

typedef map<string, string> strstrmap

service SubscriberThrift{
  # the async keyword seems to slow things down in the simple
  # tests.  However, with non-trivial subscribers it will be 
  # necessary to use async here.
  async void publish(strstrmap message)
  async void publishList(list<strstrmap> messages)
}

service MessageBrokerThrift{
  void log(strstrmap message),
  void addSubscriber(string host, i16 port)
  void removeSubscriber(string host, i16 port)
  async void publish(strstrmap message)
  async void publishList(list<strstrmap> messages)

}

