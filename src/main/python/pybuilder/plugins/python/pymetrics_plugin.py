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

import os

from pybuilder.core import use_plugin, after, task, init

use_plugin("python.core")
use_plugin("analysis")


@init
def init_pylint(project):
    project.plugin_depends_on("pymetrics")


@after("prepare")
def check_pymetrics_available(project, logger, reactor):
    logger.debug("Checking availability of pymetrics")
    reactor.pybuilder_venv.verify_can_execute(["pymetrics", "--nosql", "--nocsv"], "pymetrics",
                                              "plugin python.pymetrics")
    logger.debug("pymetrics has been found")


@task("analyze")
def execute_pymetrics(project, logger, reactor):
    logger.info("Executing pymetrics on project sources")
    source_dir = project.expand_path("$dir_source_main_python")

    files_to_scan = []
    for root, _, files in os.walk(source_dir):
        for file_name in files:
            if file_name.endswith(".py"):
                files_to_scan.append(os.path.join(root, file_name))

    csv_file = project.expand_path("$dir_reports/pymetrics.csv")

    command = ["pymetrics", "--nosql", "-c", csv_file] + files_to_scan

    report_file = project.expand_path("$dir_reports/pymetrics")

    env = project.pluginenv.copy()
    env.update({"PYTHONPATH": source_dir})
    reactor.pybuilder_venv.execute_command(command, report_file, env=env)
