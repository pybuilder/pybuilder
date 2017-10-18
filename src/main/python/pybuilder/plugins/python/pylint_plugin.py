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
from pybuilder.errors import BuildFailedException
from pybuilder.plugins.python.python_plugin_helper import execute_tool_on_modules
from pybuilder.utils import assert_can_execute

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
    pylint_output_file_path = execute_tool_on_modules(project, "pylint", command_and_arguments, True)[1]

    with open(pylint_output_file_path, 'r') as f:
        file_content = f.read().splitlines()

    module_name = ''
    pylint_score = 0
    pylint_change = 0
    errors = 0
    errors_info = ''
    warnings = 0
    warnings_info = ''
    show_info_messages = project.get_property('pylint_show_info_messages')
    show_warning_messages = project.get_property('pylint_show_warning_messages')
    for line in file_content:
        if line.startswith('************* Module'):
            module_name = line.split(' ')[2]

        if line.startswith('E:') or line.startswith('F:'):
            logger.error('Pylint: Module %s: ' % module_name + line)
            errors += 1

        if show_warning_messages and line.startswith('W:'):
            logger.warn('Pylint: Module %s: ' % module_name + line)
            warnings += 1

        if show_info_messages and (line.startswith('C:') or line.startswith('R:')):
            logger.info('Pylint: Module %s: ' % module_name + line)

        if line.startswith('Your code has been rated at '):
            pylint_score = float(line.split(' ')[6].split('/')[0])
            pylint_change = float(line.split(' ')[10][:-1])

    if errors > 0:
        errors_info = ' / Errors: {}'.format(errors)

    if warnings > 0:
        warnings_info = ' / Warnings {}'.format(warnings)

    logger.info(
        'Pylint ratio: {} / Pylint change: {}'.format(pylint_score, pylint_change) + errors_info + warnings_info
    )

    if errors > 0 and project.get_property('pylint_break_build_on_errors'):
        raise BuildFailedException(
            "Pylint: Building failed due to {} errors or fatal errors".format(errors)
        )

    pylint_expected_score = project.get_property('pylint_score_threshold')
    pylint_expected_score_change = project.get_property('pylint_score_change_threshold')
    if pylint_expected_score and pylint_score < pylint_expected_score:
        raise BuildFailedException(
                    "Pylint: Building failed due to Pylint score({}) less then expected({})".
                    format(pylint_score, pylint_expected_score)
                )
    if pylint_expected_score_change and pylint_change < pylint_expected_score_change:
        raise BuildFailedException(
            "Pylint: Building failed due to Pylint score decrease({}) higher then allowed({})".
            format(pylint_change, pylint_expected_score_change)
        )
