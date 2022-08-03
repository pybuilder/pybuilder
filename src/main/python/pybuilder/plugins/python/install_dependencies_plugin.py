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

from pybuilder import pip_utils
from pybuilder.core import (task,
                            description,
                            use_plugin,
                            depends,
                            init)
from pybuilder.install_utils import install_dependencies as install_dependency
from pybuilder.utils import mkdir, as_list

__author__ = "Alexander Metzner, Arcadiy Ivanov"

use_plugin("core")


@init
def initialize_install_dependencies_plugin(project):
    project.set_property_if_unset("pip_verbose", 0)
    project.set_property_if_unset("install_env", "system")
    project.set_property_if_unset("dir_install_logs", "$dir_logs/install_dependencies")
    project.set_property_if_unset("install_dependencies_index_url", None)
    project.set_property_if_unset("install_dependencies_local_mapping", {})
    project.set_property_if_unset("install_dependencies_extra_index_url", None)
    project.set_property_if_unset("install_dependencies_trusted_host", None)
    project.set_property_if_unset("install_dependencies_constraints", "constraints_file")
    # Deprecated - has no effect
    project.set_property_if_unset("install_dependencies_upgrade", False)
    project.set_property_if_unset("install_dependencies_insecure_installation", [])


@task
@depends("prepare")
@description("Installs all (both runtime and build) dependencies specified in the build descriptor")
def install_dependencies(logger, project, reactor):
    logger.info("Installing all dependencies")
    install_dependency(logger, project, as_list(project.build_dependencies) + as_list(project.dependencies),
                       reactor.python_env_registry[project.get_property("install_env")],
                       project.expand_path("$dir_install_logs", "install_batch"),
                       project.get_property("install_dependencies_local_mapping"),
                       project.expand_path("$dir_target", "install_dependencies_constraints"))


@task
@depends("prepare")
@description("Installs all build dependencies specified in the build descriptor")
def install_build_dependencies(logger, project, reactor):
    logger.info("Installing build dependencies")
    install_dependency(logger, project, project.build_dependencies,
                       reactor.python_env_registry[project.get_property("install_env")],
                       project.expand_path("$dir_install_logs", "install_batch"),
                       project.get_property("install_dependencies_local_mapping"),
                       project.expand_path("$dir_target", "install_dependencies_constraints"))


@task
@depends("prepare")
@description("Installs all runtime dependencies specified in the build descriptor")
def install_runtime_dependencies(logger, project, reactor):
    logger.info("Installing runtime dependencies")
    install_dependency(logger, project, project.dependencies,
                       reactor.python_env_registry[project.get_property("install_env")],
                       project.expand_path("$dir_install_logs", "install_batch"),
                       project.get_property("install_dependencies_local_mapping"),
                       project.expand_path("$dir_target", "install_dependencies_constraints"))


@task
@description("Displays all dependencies the project requires")
def list_dependencies(project):
    print("\n".join(
        map(lambda d: "{0}".format(" ".join(pip_utils.as_pip_install_target(d))),
            project.build_dependencies + project.dependencies)))


@task("prepare")
def create_install_log_directory(logger, project):
    log_dir = project.expand_path("$dir_install_logs")
    logger.debug("Creating log directory %r", log_dir)
    mkdir(log_dir)

    target_dir = project.expand_path("$dir_target")
    logger.debug("Creating target directory %r", target_dir)
    mkdir(target_dir)
