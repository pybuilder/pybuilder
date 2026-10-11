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

"""
    Plugin for mypy static type checker (http://mypy-lang.org).
    Runs mypy on project sources during the analyze phase.

    https://mypy-lang.org
"""

from pybuilder.core import use_plugin, after, init, task
from pybuilder.errors import BuildFailedException
from pybuilder.pluginhelper.external_command import ExternalCommandBuilder

use_plugin("python.core")
use_plugin("analysis")

# Default mypy options suppressing import errors for untyped third-party
# packages and showing error codes for easier suppression inline.
DEFAULT_MYPY_OPTIONS = ["--ignore-missing-imports", "--show-error-codes"]


@init
def initialize_mypy_plugin(project):
    """Initialise the mypy plugin and set default property values."""
    project.plugin_depends_on("mypy", ">=1.0")
    project.set_property_if_unset("mypy_options", DEFAULT_MYPY_OPTIONS)
    project.set_property_if_unset("mypy_break_build", False)
    project.set_property_if_unset("mypy_include_test_sources", False)
    project.set_property_if_unset("mypy_include_scripts", False)
    project.set_property_if_unset("mypy_exclude_patterns", None)


@after("prepare")
def assert_mypy_is_executable(project, logger, reactor):
    """Verify that mypy is installed and can be invoked before the analyze task runs."""
    logger.debug("Checking availability of MyPy")
    reactor.pybuilder_venv.verify_can_execute(["mypy", "--version"], "mypy", "plugin python.mypy")


@task("analyze")
def execute_mypy(project, logger, reactor):
    """Run mypy on production (and optionally test/script) sources and handle results."""
    logger.info("Executing mypy on project sources")

    command = ExternalCommandBuilder("mypy", project, reactor)

    for opt in project.get_property("mypy_options"):
        command.use_argument(opt)

    exclude_patterns = project.get_property("mypy_exclude_patterns")
    if exclude_patterns:
        command.use_argument("--exclude={0}".format(exclude_patterns))

    include_test_sources = project.get_property("mypy_include_test_sources")
    include_scripts = project.get_property("mypy_include_scripts")

    result = command.run_on_production_source_files(logger,
                                                    include_test_sources=include_test_sources,
                                                    include_scripts=include_scripts,
                                                    include_dirs_only=True)

    break_build = project.get_property("mypy_break_build")

    # mypy exit code 2 indicates a fatal error (invalid args, internal crash, etc.)
    # This always breaks the build regardless of mypy_break_build.
    if result.exit_code == 2:
        logger.error("mypy failed with exit code %s (fatal error)", result.exit_code)
        raise BuildFailedException("mypy failed with exit code %s" % result.exit_code)

    # mypy note: lines also contain ".py:" but are not errors.
    # Filtering on ": error:" ensures only actual type errors are counted.
    errors = [line.rstrip()
              for line in result.report_lines
              if ": error:" in line]
    error_count = len(errors)

    if error_count:
        for error in errors:
            logger.warn("mypy: %s", error)

        message = "mypy found {} type error(s).".format(error_count)
        if break_build:
            logger.error(message)
            raise BuildFailedException(message)
        else:
            logger.warn(message)
