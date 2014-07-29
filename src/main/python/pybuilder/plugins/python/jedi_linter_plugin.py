#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
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
    Plugin for Jedi linting support.

    https://jedi.jedidjah.ch/
"""

__author__ = 'Maximilien Riehl'

import os

try:
    import jedi
except ImportError:
    jedi = None

from pybuilder.core import after, task, init, use_plugin, depends
from pybuilder.errors import BuildFailedException, MissingPrerequisiteException, InternalException
from pybuilder.utils import discover_files_matching


use_plugin("python.core")


@init
def initialize_jedi_linter_plugin(project, logger):
    project.build_depends_on("jedi")
    project.set_property_if_unset("jedi_linter_break_build", False)
    project.set_property_if_unset("jedi_linter_verbose", False)

    logger.warn("The jedi plugin is unstable since the linter API will probably change.")


@after("prepare")
def assert_jedi_is_installed(logger):
    if not jedi:
        raise MissingPrerequisiteException("'jedi'", caller="jedi_linter_plugin")
    if "_analysis" not in dir(jedi.Script):
        raise InternalException(
            "The jedi linter API changed, please file a bug at https://github.com/pybuilder/pybuilder/issues/new")


@task
@depends("prepare")
def analyze(project, logger):
    root_directory = os.getcwd()
    source_modules = discover_files_matching(project.get_property("dir_source_main_python"),
                                             "*.py")
    errors = []

    logger.info("Executing jedi linter on project sources.")

    try:
        for path in source_modules:
            for error in jedi.Script(path=path)._analysis():
                errors.append(error)
    except Exception as e:
        logger.error("Jedi crashed: {0}".format(e))
        import traceback
        logger.debug(traceback.format_exc())

    number_of_errors = len(errors)
    output = logger.info if number_of_errors == 0 else logger.warn
    output("Jedi linter found {0} errors.".format(number_of_errors))
    if project.get_property("jedi_linter_verbose") or project.get_property("verbose"):
        for error in errors:
            logger.warn(error)

    if project.get_property("jedi_linter_break_build") and number_of_errors > 0:
        raise BuildFailedException("Jedi linter found errors")

    os.chdir(root_directory)  # jedi chdirs into directories, so undo it
