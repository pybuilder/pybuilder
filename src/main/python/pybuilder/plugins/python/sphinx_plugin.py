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

"""Sphinx-plugin for PyBuildern to run a sphinx quickstart and generate the documentation once set up.
"""

from pybuilder.core import after
from pybuilder.core import depends
from pybuilder.core import init
from pybuilder.core import task
from pybuilder.core import use_plugin
from pybuilder.errors import BuildFailedException
from pybuilder.utils import assert_can_execute
from pybuilder.utils import execute_command
from pybuilder import scaffolding as SCAFFOLDING
from pybuilder.core import NAME_ATTRIBUTE

__author__ = 'Thomas Prebble', 'Marcel Wolf'


use_plugin("core")


DEFAULT_SPHINX_OUTPUT_DIR = SCAFFOLDING.DEFAULT_DOCS_DIRECTORY + "/_build/"

SPHINX_DOC_BUILDER = "html"


@init
def initialize_sphinx_plugin(project):

    default_project_version = project.version
    default_project_name = project.name
    default_doc_author = ", ".join([author.name for author in project.authors])

    project.build_depends_on("sphinx")
    project.set_property_if_unset(
        "sphinx_source_dir", SCAFFOLDING.DEFAULT_DOCS_DIRECTORY)
    project.set_property_if_unset(
        "sphinx_output_dir", DEFAULT_SPHINX_OUTPUT_DIR)
    project.set_property_if_unset(
        "sphinx_config_path", SCAFFOLDING.DEFAULT_DOCS_DIRECTORY)
    project.set_property_if_unset(
        "sphinx_doc_author", default_doc_author)
    project.set_property_if_unset(
        "sphinx_doc_builder", SPHINX_DOC_BUILDER)
    project.set_property_if_unset(
        "sphinx_project_name", default_project_name)
    project.set_property_if_unset(
        "sphinx_project_version", default_project_version)


@after("prepare")
def assert_sphinx_is_available(logger):
    """Asserts that the sphinx-build script is available.
    """
    logger.debug("Checking if sphinx-build is available.")

    assert_can_execute(
        ["sphinx-build", "--version"], "sphinx", "plugin python.sphinx")


@after("prepare")
def assert_sphinx_quickstart_is_available(logger):
    """Asserts that the sphinx-quickstart script is available.
    """
    logger.debug("Checking if sphinx-quickstart is available.")

    assert_can_execute(
        ["sphinx-quickstart", "--version"], "sphinx", "plugin python.sphinx")


def run_sphinx_build(build_command, task_name, logger, project):
    logger.info("Running %s" % task_name)
    log_file = project.expand_path(
        "$dir_target/reports/{0}".format(task_name))
    if project.get_property("verbose"):
        logger.info(build_command)
        exit_code = execute_command(build_command, log_file, shell=True)
        if exit_code != 0:
            raise BuildFailedException("Sphinx build command failed. See %s for details.", log_file)


@task("sphinx_generate_documentation", "Generates documentation with sphinx")
@depends("prepare")
def sphinx_generate(project, logger):
    """Runs sphinx-build against rst sources for the given project.
    """
    task_name = getattr(sphinx_generate, NAME_ATTRIBUTE)
    build_command = get_sphinx_build_command(project)
    run_sphinx_build(build_command, task_name, logger, project)


@task("sphinx_quickstart", "starts a new sphinx project")
@depends("prepare")
def sphinx_quickstart_generate(project, logger):
    """Runs sphinx-build against rst sources for the given project.
    """
    task_name = getattr(sphinx_quickstart_generate, NAME_ATTRIBUTE)
    build_command = get_sphinx_quickstart_command(project)
    run_sphinx_build(build_command, task_name, logger, project)


def get_sphinx_quickstart_command(project):
    """Builds the sphinx-quickstart command using project properties.
        sphinx-quickstart parameters:
        :param -q: Quiet mode that will skips interactive wizard to specify options.
        :param -p: Project name will be set.
        :param -a: Author names.
        :param -v: Version of project.
    """
    options = ["-q",
               "-p '%s'" % project.get_property("sphinx_project_name"),
               "-a '%s'" % project.get_property("sphinx_doc_author"),
               "-v %s" % project.get_property("sphinx_project_version"),
               "%s" % project.expand_path
               (project.get_property("sphinx_source_dir"))]
    return "sphinx-quickstart %s" % " ".join(options)


def get_sphinx_build_command(project):
    """Builds the sphinx-build command using properties.
    """
    options = ["-b %s" % project.get_property("sphinx_doc_builder"),
               project.expand_path(project.get_property("sphinx_config_path")),
               project.expand_path(project.get_property("sphinx_output_dir"))]
    return "sphinx-build %s" % " ".join(options)
