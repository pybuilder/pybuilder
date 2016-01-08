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

import os
import re

from pybuilder.pip_utils import PIP_EXEC_STANZA
from pybuilder.core import (before,
                            task,
                            description,
                            use_plugin,
                            init)
from pybuilder.errors import BuildFailedException
from pybuilder.pip_utils import (build_pip_install_options,
                                 as_pip_install_target,
                                 )
from pybuilder.terminal import print_file_content
from pybuilder.utils import execute_command, mkdir

__author__ = "Alexander Metzner, Arcadiy Ivanov"

use_plugin("core")


@init
def initialize_install_dependencies_plugin(project):
    project.set_property_if_unset("dir_install_logs", "$dir_logs/install_dependencies")
    project.set_property_if_unset("install_dependencies_index_url", None)
    project.set_property_if_unset("install_dependencies_local_mapping", {})
    project.set_property_if_unset("install_dependencies_extra_index_url", None)
    project.set_property_if_unset("install_dependencies_upgrade", False)
    project.set_property_if_unset("install_dependencies_insecure_installation", [])


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
    print("\n".join(
        map(lambda d: "{0}".format(" ".join(as_pip_install_target(d))),
            project.build_dependencies + project.dependencies)))


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
    log_file = re.sub(r'<|>|=', '_', log_file)

    target_dir = None
    try:
        target_dir = project.get_property("install_dependencies_local_mapping")[dependency.name]
    except KeyError:
        pass

    pip_command_line = list()
    pip_command_line.extend(PIP_EXEC_STANZA)
    pip_command_line.append("install")
    pip_command_line.extend(build_pip_install_options(project.get_property("install_dependencies_index_url"),
                                                      project.get_property("install_dependencies_extra_index_url"),
                                                      project.get_property("install_dependencies_upgrade"),
                                                      project.get_property(
                                                          "install_dependencies_insecure_installation"),
                                                      True if url else False,
                                                      target_dir,
                                                      project.get_property("verbose")
                                                      ))
    pip_command_line.extend(as_pip_install_target(dependency))
    logger.debug("Invoking pip: %s", pip_command_line)
    exit_code = execute_command(pip_command_line, log_file, env=os.environ, shell=False)

    if exit_code != 0:
        if project.get_property("verbose"):
            print_file_content(log_file)
            raise BuildFailedException("Unable to install dependency '%s'.", dependency.name)
        else:
            raise BuildFailedException("Unable to install dependency '%s'. See %s for details.",
                                       getattr(dependency, "name", dependency),
                                       log_file)
