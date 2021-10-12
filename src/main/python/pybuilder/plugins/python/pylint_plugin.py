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

from pybuilder.core import use_plugin, after, init, task
from pybuilder.errors import BuildFailedException
from pybuilder.pluginhelper.external_command import ExternalCommandBuilder

use_plugin("python.core")
use_plugin("analysis")

DEFAULT_PYLINT_OPTIONS = ["--max-line-length=100", "--no-docstring-rgx=.*"]


@init
def init_pylint(project):
    project.plugin_depends_on("pylint")
    project.set_property_if_unset("pylint_options", DEFAULT_PYLINT_OPTIONS)
    project.set_property_if_unset("pylint_break_build", False)
    project.set_property_if_unset("pylint_include_test_sources", False)
    project.set_property_if_unset("pylint_include_scripts", False)


@after("prepare")
def check_pylint_availability(project, logger, reactor):
    logger.debug("Checking availability of PyLint")
    reactor.pybuilder_venv.verify_can_execute(["pylint"], "pylint", "plugin python.pylint")


@task("analyze")
def execute_pylint(project, logger, reactor):
    logger.info("Executing pylint on project sources")

    verbose = project.get_property("verbose")
    project.set_property_if_unset("pylint_verbose_output", verbose)

    command = ExternalCommandBuilder("pylint", project, reactor)

    for opt in project.get_property("pylint_options"):
        command.use_argument(opt)

    include_test_sources = project.get_property("pylint_include_test_sources")
    include_scripts = project.get_property("pylint_include_scripts")

    result = command.run_on_production_source_files(logger,
                                                    include_test_sources=include_test_sources,
                                                    include_scripts=include_scripts)

    break_build = project.get_property("pylint_break_build")
    if result.exit_code == 32 and break_build:
        raise BuildFailedException("PyLint failed with exit code %s", result.exit_code)

    warnings = [line.rstrip()
                for line in result.report_lines
                if line.find(".py:") >= 0]
    warning_count = len(warnings)

    if warning_count:
        for warning in warnings:
            logger.warn("pylint: %s", warning)

        message = "PyLint found {} warning(s).".format(warning_count)
        if break_build:
            logger.error(message)
            raise BuildFailedException(message)
        else:
            logger.warn(message)
