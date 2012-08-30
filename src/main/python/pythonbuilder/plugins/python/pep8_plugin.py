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
from pythonbuilder.core import use_plugin, task, after
from pythonbuilder.utils import assert_can_execute, read_file
from pythonbuilder.plugins.python.python_plugin_helper import execute_tool_on_source_files

use_plugin("python.core")

@after("prepare")
def check_pep8_available (logger):
    logger.debug("Checking availability of pep8")
    assert_can_execute(("pep8", ), "pep8", "plugin python.pep8")

@task
def analyze (project, logger):
    logger.info("Executing pep8 on project sources")
    _, report_file = execute_tool_on_source_files(project, "pep8", ["pep8"])
    
    reports = read_file(report_file)
    
    if len(reports) > 0:
        logger.warn("Found %d warning%s produced by pep8", 
                    len(reports), "" if len(reports) == 1 else "s")    
    
