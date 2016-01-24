#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2015 PyBuilder Team
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

from pybuilder.core import use_plugin, after, init, task
from pybuilder.utils import assert_can_execute
from pybuilder.plugins.python.python_plugin_helper import execute_tool_on_modules

use_plugin("python.core")
use_plugin("analysis")

DEFAULT_PYLINT_OPTIONS = ["--max-line-length=100", "--no-docstring-rgx=.*"]


@init
def init_pylint(project):
    project.plugin_depends_on("pylint")
    project.set_property_if_unset("pylint_options", DEFAULT_PYLINT_OPTIONS)


@after("prepare")
def check_pylint_availability(logger):
    logger.debug("Checking availability of pychecker")
    assert_can_execute(("pylint", ), "pylint", "plugin python.pylint")
    logger.debug("pylint has been found")


@task("analyze")
def execute_pylint(project, logger):
    logger.info("Executing pylint on project sources")

    command_and_arguments = ["pylint"] + project.get_property("pylint_options")
    execute_tool_on_modules(project, "pylint", command_and_arguments, True)
