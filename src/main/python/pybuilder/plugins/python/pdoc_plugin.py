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
    Plugin for pdoc, Python Documentation generation tool

    https://pypi.python.org/pypi/pdoc
"""
import os

from pybuilder.core import task, init, depends, dependents, optional, after, use_plugin
from pybuilder.errors import BuildFailedException
from pybuilder.utils import tail_log

__author__ = "Arcadiy Ivanov"

use_plugin("core")


@init
def pdoc_init(project):
    project.plugin_depends_on("pdoc3", ">=0.8.3")

    project.set_property_if_unset("pdoc_command_args",
                                  ["--html", "--overwrite", "--external-links", "--skip-errors"])

    project.set_property_if_unset("pdoc_source", "$dir_source_main_python")
    project.set_property_if_unset("pdoc_output_dir", "$dir_target/pdocs")
    project.set_property_if_unset("pdoc_module_name", None)


@after("prepare")
def pdoc_prepare(project, logger, reactor):
    """ Asserts that pdoc is executable. """
    logger.debug("Checking if pdoc is executable.")

    reactor.pybuilder_venv.verify_can_execute(command_and_arguments=["pdoc", "--version"],
                                              prerequisite="pdoc", caller="plugin python.pdoc")

    pdoc_output_dir = project.expand_path("$pdoc_output_dir")
    if not os.path.exists(pdoc_output_dir):
        os.mkdir(pdoc_output_dir)


@task("compile_docs", "Generates HTML documentation tree with pdoc")
@depends("compile_sources", "verify")
@dependents(optional("publish"))
def pdoc_compile_docs(project, logger, reactor):
    logger.info("Generating PDoc documentation")

    if not project.get_property("pdoc_module_name"):
        raise BuildFailedException("'pdoc_module_name' must be specified")

    pdoc_command_args = project.get_property("pdoc_command_args", [])
    pdoc_output_dir = project.expand_path("$pdoc_output_dir")

    command_and_arguments = ["pdoc"] + pdoc_command_args
    if "--html" in pdoc_command_args:
        command_and_arguments += ["--html-dir", pdoc_output_dir]
    command_and_arguments += [project.get_property("pdoc_module_name")]

    source_directory = project.expand_path("$pdoc_source")
    environment = {"PYTHONPATH": source_directory,
                   "PATH": reactor.pybuilder_venv.environ["PATH"]}

    report_file = project.expand_path("$dir_reports", "pdoc.err")
    logger.debug("Executing PDoc as: %s", command_and_arguments)
    return_code = reactor.pybuilder_venv.execute_command(command_and_arguments,
                                                         outfile_name=project.expand_path("$dir_reports", "pdoc"),
                                                         error_file_name=report_file,
                                                         env=environment,
                                                         cwd=pdoc_output_dir)

    if return_code:
        error_str = "PDoc failed! See %s for full details:\n%s" % (report_file, tail_log(report_file))
        logger.error(error_str)
        raise BuildFailedException(error_str)
