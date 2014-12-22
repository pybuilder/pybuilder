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
    Plugin to check dependency freshness.
"""

import sys

from pybuilder.core import after, task, init, use_plugin, depends, Dependency
from pybuilder.errors import BuildFailedException, MissingPrerequisiteException
from pybuilder.plugins.python.install_dependencies_plugin import (
    install_dependency,
    create_install_log_directory)
from pybuilder.scaffolding import prompt_user

try:
    from pip.commands import ListCommand
except ImportError:
    pass  # handled in assert_pip_api_is_available


use_plugin("python.core")


@init
def initialize_outdated_dependencies_plugin(project):
    project.build_depends_on("pip")
    project.set_property("outdated_dependencies_break_build", False)


@after("prepare")
def assert_pip_api_is_available(logger):
    try:
        import pip
        logger.debug("pip API version {0}".format(pip.__version__))
    except ImportError:
        raise MissingPrerequisiteException("pip", "update_plugin")


@task("check_if_dependencies_are_uptodate",
      description="Check if dependencies are up-to-date, optionally breaks the build")
def check_if_dependencies_are_uptodate(project, logger):
    outdated_versions = [outdated_tuple for outdated_tuple in get_outdated_versions()]
    for dist, remote_raw_version in outdated_versions:
        logger.info("A newer version of {0} is available (local '{1}', latest '{2}')".format(
            dist.project_name,
            dist.version,
            remote_raw_version))

    if outdated_versions and project.get_property("outdated_dependencies_break_build"):
        wording = "dependency" if len(outdated_versions) == 1 else "dependencies"
        raise BuildFailedException("Found {0} outdated {1}".format(
                                   len(outdated_versions),
                                   wording))


@task("upgrade_outdated_dependencies",
      description="Prompts for upgrade of outdated dependencies")
@depends("prepare")
def upgrade_outdated_dependencies(project, logger):
    if not sys.stdout.isatty():
        raise BuildFailedException("There's no TTY and {0} requires user input.".format(
                                   upgrade_outdated_dependencies.__name__))

    create_install_log_directory(logger, project)
    outdated_versions = [outdated_tuple for outdated_tuple in get_outdated_versions()]
    for dist, remote_raw_version in outdated_versions:
        upgrade_message = "Replace {0} {1} with {0} {2}? (y/N)".format(
            dist.project_name,
            dist.version,
            remote_raw_version)

        choice = prompt_user(upgrade_message, "y")
        if not choice or choice.lower() == "y":
            logger.info("Upgrading %s" % dist.project_name)
            install_dependency(logger,
                               project,
                               Dependency(dist.project_name,
                                          version=remote_raw_version))


def get_outdated_versions():
    l = ListCommand()
    options, _ = l.parse_args([])
    for dist, remote_raw_version, remote_parsed_version in l.find_packages_latests_versions(options):
        if remote_parsed_version > dist.parsed_version:
            yield (dist, remote_raw_version)
