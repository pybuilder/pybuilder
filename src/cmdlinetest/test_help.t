#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

Usage:

  $ pyb -h
  Usage: pyb [options] task1 [[task2] ...]
  
  Options:
    --version             show program's version number and exit
    -h, --help            show this help message and exit
    -t, --list-tasks      List tasks
    --start-project       Initialize a build descriptor and python project
                          structure.
    -v, --verbose         Enable verbose output
  
    Project Options:
      Customizes the project to build.
  
      -D <project directory>, --project-directory=<project directory>
                          Root directory to execute in
      -E <environment>, --environment=<environment>
                          Activate the given environment for this build. Can be
                          used multiple times
      -P <property>=<value>
                          Set/ override a property value
  
    Output Options:
      Modifies the messages printed during a build.
  
      -X, --debug         Print debug messages
      -q, --quiet         Quiet mode; print only warnings and errors
      -Q, --very-quiet    Very quiet mode; print only errors
      -C, --no-color      Disable colored output
