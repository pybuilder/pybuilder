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

from __future__ import print_function

__author__ = "Alexander Metzner"

import sys

from pybuilder.core import (before,
                            after,
                            task,
                            description,
                            use_plugin,
                            init,
                            RequirementsFile)
from pybuilder.errors import BuildFailedException
from pybuilder.utils import assert_can_execute, execute_command, mkdir
from pybuilder.plugins.python.setuptools_plugin_helper import build_dependency_version_string
from pybuilder.terminal import print_file_content
use_plugin("core")


@init
def initialize_install_dependencies_plugin(project):
    project.set_property_if_unset("dir_install_logs", "$dir_logs/install_dependencies")
    project.set_property_if_unset("install_dependencies_index_url", None)
    project.set_property_if_unset("install_dependencies_extra_index_url", None)
    project.set_property_if_unset("install_dependencies_upgrade", False)


@after("prepare")
def check_pip_available(logger):
    logger.debug("Checking if pip is available")
    assert_can_execute("pip", "pip", "plugin python.install_dependencies")


@task
@description("Installs all (both runtime and build) dependencies specified in the build descriptor")
def install_dependencies(logger, project):
    logger.info("Installing all dependencies")
    install_build_dependencies(logger, project)
    install_runtime_dependencies(logger, project)


@task
@description("Installs all build dependencies specified in the build descriptor")
def install_build_dependencies(logger, project):
    logger.info("Installing build dependencies")
    for dependency in project.build_dependencies:
        install_dependency(logger, project, dependency)


@task
@description("Installs all runtime dependencies specified in the build descriptor")
def install_runtime_dependencies(logger, project):
    logger.info("Installing runtime dependencies")
    for dependency in project.dependencies:
        install_dependency(logger, project, dependency)


@task
@description("Displays all dependencies the project requires")
def list_dependencies(project):
    print("\n".join(map(lambda d: "{0}".format(as_pip_argument(d)), project.build_dependencies + project.dependencies)))


@before((install_build_dependencies, install_runtime_dependencies, install_dependencies), only_once=True)
def create_install_log_directory(logger, project):
    log_dir = project.expand("$dir_install_logs")

    logger.debug("Creating log directory '%s'", log_dir)
    mkdir(log_dir)


def install_dependency(logger, project, dependency):
    url = getattr(dependency, "url", None)
    logger.info("Installing dependency '%s'%s", dependency.name,
                " from %s" % url if url else "")
    log_file = project.expand_path("$dir_install_logs", dependency.name)

    if sys.platform.startswith("win"):
        # we can't use quotes on windows
        pip_dependency = as_pip_argument(dependency)
    else:
        # on linux we need quotes because version pinning (>=) would be an IO redirect
        pip_dependency = "'{0}'".format(as_pip_argument(dependency))
    pip_command_line = "pip install {0}{1}".format(build_pip_install_options(project, pip_dependency), pip_dependency)
    exit_code = execute_command(pip_command_line, log_file, shell=True)
    if exit_code != 0:
        if project.get_property("verbose"):
            print_file_content(log_file)
            raise BuildFailedException("Unable to install dependency '%s'.", dependency.name)
        else:
            raise BuildFailedException("Unable to install dependency '%s'. See %s for details.",
                                       getattr(dependency, "name", dependency),
                                       log_file)


def build_pip_install_options(project, dependency):
    options = []
    if project.get_property("install_dependencies_index_url"):
        options.append("--index-url " + project.get_property("install_dependencies_index_url"))
        if project.get_property("install_dependencies_extra_index_url"):
            options.append("--extra-index-url " + project.get_property("install_dependencies_extra_index_url"))

    if project.get_property("install_dependencies_upgrade"):
        options.append("--upgrade")

    if _pip_disallows_insecure_packages_by_default():
        for insecure_dependency in project.get_property("install_dependencies_insecure_installation", []):
            arguments_for_insecure_installation = ["--allow-unverified", insecure_dependency,
                                                   "--allow-external", insecure_dependency]
            options.extend(arguments_for_insecure_installation)

    result = " ".join(options)
    if result:
        result += " "
    return result


def as_pip_argument(dependency):
    if isinstance(dependency, RequirementsFile):
        return "-r{0}".format(dependency.name)
    if dependency.url:
        return dependency.url
    return "{0}{1}".format(dependency.name, build_dependency_version_string(dependency))


def _pip_disallows_insecure_packages_by_default():
    import pip
    # (2014-01-01) BACKWARD INCOMPATIBLE pip no longer will scrape insecure external urls by default
    # nor will it install externally hosted files by default
    # Also pip v1.1 for example has no __version__
    return hasattr(pip, "__version__") and pip.__version__ >= '1.5'
