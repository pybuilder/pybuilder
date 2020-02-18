#   -*- coding: utf-8 -*-
#
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

from pybuilder.core import use_plugin, task, after, init
from pybuilder.plugins.python.python_plugin_helper import execute_tool_on_source_files
from pybuilder.utils import read_file

use_plugin("python.core")


@init
def init_pep8_properties(project):
    project.plugin_depends_on("pep8")


@after("prepare")
def check_pep8_available(project, logger, reactor):
    logger.debug("Checking availability of pep8")
    reactor.python_env_registry["pybuilder"].verify_can_execute(["pep8"], "pep8", "plugin python.pep8")


@task
def analyze(project, logger):
    logger.info("Executing pep8 on project sources")
    _, report_file = execute_tool_on_source_files(project, "pep8", ["pep8"])

    reports = read_file(report_file)

    if len(reports) > 0:
        logger.warn("Found %d warning%s produced by pep8",
                    len(reports), "" if len(reports) == 1 else "s")
