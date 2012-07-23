#  This file is part of Python Builder
#   
#  Copyright 2011 The Python Builder Team
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

import os

from pythonbuilder.utils import discover_modules, discover_files, execute_command, as_list

def execute_tool_on_source_files (project, name, command_and_arguments):
    source_dir = project.expand_path("$dir_source_main_python")
    files = discover_files(source_dir, ".py")
    command = as_list(command_and_arguments) + [f for f in files]

    report_file = project.expand_path("$dir_reports/%s" % name)

    return execute_command(command, report_file), report_file

def execute_tool_on_modules (project, name, command_and_arguments, extend_pythonpath=True):
    source_dir = project.expand_path("$dir_source_main_python")
    modules = discover_modules(source_dir)
    command = as_list(command_and_arguments) + modules

    report_file = project.expand_path("$dir_reports/%s" % name)

    env = os.environ
    if extend_pythonpath:
        env["PYTHONPATH"] = source_dir
    return execute_command(command, report_file, env=env), report_file
