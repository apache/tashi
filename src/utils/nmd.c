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
#define TASHI_PATH "/usr/local/tashi/"
#define LOG_FILE "/var/log/nodemanager.log"

/* This function changes (on Linux!) its oom scoring, to make it
 * unattractive to kill
 */

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

/* This function resets (on Linux!) its oom scoring to default
 */
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
	int foreground=0;

/* If first argument is "-f", run in foreground */
	if ((argc > 1) && (strncmp(argv[1], "-f", 3)==0)) {
		foreground=1;
	}
/* If not running in foreground, fork off and exit the parent.
 * The child closes its default file descriptors.
 */
	if (!foreground) {
		pid = fork();
		if (pid != 0) {
			exit(0);
		}
		close(0);
		close(1);
		close(2);
	}
/* Adjust OOM preference */
	make_invincible();
/* Configure environment of children */
	env[0] = "PYTHONPATH="TASHI_PATH"/src/";
	env[1] = NULL;
	while (1) {
		pid = fork();
		if (pid == 0) {
			/* child */
			/* nodemanagers are vulnerable. Not the supervisor. */
			make_vulnerable();
			if (!foreground) {
				/* If not running fg, open log file */
				lfd = open(LOG_FILE, O_WRONLY|O_APPEND|O_CREAT);
				if (lfd < 0) {
					/* If this failed, open something? */
					lfd = open("/dev/null", O_WRONLY);
				}
				/* Make this fd stdout and stderr */
				dup2(lfd, 2);
				dup2(lfd, 1);
				/* close stdin */
				close(0);
			}
			chdir(TASHI_PATH);
			/* start node manager with python environment */
			execle("./bin/nodemanager.py", "./bin/nodemanager.py", NULL, env);
			exit(-1);
		}
		/* sleep before checking for child's status */
		sleep(SLEEP_INTERVAL);
		/* catch child exiting and go through loop again */
		waitpid(pid, &status, 0);
	}	 /* while (1) */
}
