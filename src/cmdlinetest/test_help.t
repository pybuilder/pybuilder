#   This file is part of PyBuilder
#
#   Copyright 2011-2020 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

Usage:

  $ pyb -h
  Usage: pyb [options] [+|^]task1 [[[+|^]task2] ...]
  
  Options:
    --version             show program's version number and exit
    -h, --help            show this help message and exit
    -t, --list-tasks      List all tasks that can be run in the current build
                          configuration
    -T, --list-plan-tasks
                          List tasks that will be run with current execution
                          plan
    --start-project       Initialize build descriptors and Python project
                          structure
    --update-project      Update build descriptors and Python project structure
  
    Project Options:
      Customizes the project to build.
  
      -D <project directory>, --project-directory=<project directory>
                          Root directory to execute in
      -O, --offline       Attempt to execute the build without network
                          connectivity (may cause build failure)
      -E <environment>, --environment=<environment>
                          Activate the given environment for this build. Can be
                          used multiple times
      -P <property>=<value>
                          Set/ override a property value
      -x <task>, --exclude=<task>
                          Exclude optional task dependencies
      -o, --exclude-all-optional
                          Exclude all optional task dependencies
      --force-exclude=<task>
                          Exclude any task dependencies (dangerous, may break
                          the build in unexpected ways)
      --reset-plugins     Reset plugins directory prior to running the build
      --no-venvs          Disables the use of Python Virtual Environments
  
    Output Options:
      Modifies the messages printed during a build.
  
      -X, --debug         Print debug messages
      -v, --verbose       Enable verbose output
      -q, --quiet         Quiet mode; print only warnings and errors
      -Q, --very-quiet    Very quiet mode; print only errors
      -c, --color         Force colored output
      -C, --no-color      Disable colored output
      -f, --log-format    Define the format of timestamp in the log (default: no
                          timestamps)