#  This file is part of Python Builder
#
#  Copyright 2012 The Python Builder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

__author__ = "Alexander Metzner"

from pythonbuilder.core import before, after, task, description, use_plugin, init
from pythonbuilder.errors import BuildFailedException
from pythonbuilder.utils import assert_can_execute, execute_command, mkdir

use_plugin("core")

@init
def initialized_install_dependencies_plugin (project):
    project.set_property_if_unset("dir_install_logs", "$dir_logs/install_dependencies")

@after("prepare")
def check_pip_available (logger):
    logger.debug("Chechking if pip is available")
    assert_can_execute("pip", "pip", "plugin python.install_dependencies")

@task
@description("Installs all (both runtime and build) dependencies specified in the build descriptor")
def install_dependencies (logger, project):
    logger.info("Installing all dependencies")
    install_build_dependencies(logger, project)
    install_runtime_dependencies(logger, project)

@task
@description("Installs all build dependencies specified in the build descriptor")
def install_build_dependencies (logger, project):
    logger.info("Installing build dependencies")
    for dependency in project.build_dependencies:
        install_dependency(logger, project, dependency)

@task
@description("Installs all runtime dependencies specified in the build descriptor")
def install_runtime_dependencies (logger, project):
    logger.info("Installing runtime dependencies")
    for dependency in project.dependencies:
        install_dependency(logger, project, dependency)

@before((install_build_dependencies, install_runtime_dependencies, install_dependencies), only_once=True)
def create_install_log_directory (logger, project):
    log_dir = project.expand("$dir_install_logs")

    logger.debug("Creating log directory '%s'", log_dir)
    mkdir(log_dir)

def install_dependency (logger, project, dependency):
    logger.info("Installing dependency '%s'%s", dependency.name, " from %s" % dependency.url if dependency.url else "")
    log_file = project.expand_path("$dir_install_logs", dependency.name)

    exit_code = execute_command("pip install %s" % as_pip_argument(dependency), log_file, shell=True)
    if exit_code != 0:
        raise BuildFailedException("Unable to install dependency '%s'. See %s for details.", dependency.name, log_file)

def as_pip_argument (dependency):
    if dependency.url:
        return dependency.url
    return "%s%s" % (dependency.name, dependency.version if dependency.version else "")
