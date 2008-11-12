/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 * 
 *   http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.    
 */

#include <sys/types.h>
#include <sys/wait.h>
#include <dirent.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <assert.h>

#define SLEEP_INTERVAL 10
#define TASHI_PATH "/scratch/mryan3-d4/tashi/branches/mryan3/"
#define LOG_FILE "/var/log/nodemanager.log"

void make_invincible()
{
	int oom_adj_fd;
	int r;

	oom_adj_fd = open("/proc/self/oom_adj", O_WRONLY);
	assert(oom_adj_fd != -1);
	r = write(oom_adj_fd, "-17\n", 4);
	assert(r == 4);
	close(oom_adj_fd);

}

void make_vulnerable()
{
	int oom_adj_fd;
	int r;

	oom_adj_fd = open("/proc/self/oom_adj", O_WRONLY);
	assert(oom_adj_fd != -1);
	r = write(oom_adj_fd, "0\n", 2);
	assert(r == 2);
	close(oom_adj_fd);
}

int main(int argc, char **argv)
{
	char* env[2];
	int status;
	DIR* d;
	int pid;
	int lfd;
	int forground=0;

	if ((argc > 1) && (strncmp(argv[1], "-f", 3)==0)) {
		forground=1;
	}
	if (!forground) {
		pid = fork();
		if (pid != 0) {
			exit(0);
		}
		close(0);
		close(1);
		close(2);
	}
	make_invincible();
	env[0] = "PYTHONPATH="TASHI_PATH"/src/";
	env[1] = NULL;
	while (1) {
		pid = fork();
		if (pid == 0) {
			make_vulnerable();
			if (!forground) {
				lfd = open(LOG_FILE, O_WRONLY|O_APPEND|O_CREAT);
				if (lfd < 0) {
					lfd = open("/dev/null", O_WRONLY);
				}
				dup2(lfd, 2);
				dup2(lfd, 1);
				close(0);
			}
			chdir(TASHI_PATH);
			execle("./bin/nodemanager.py", "./bin/nodemanager.py", NULL, env);
			exit(-1);
		}
		sleep(SLEEP_INTERVAL);
		waitpid(pid, &status, 0);
	}	
}
