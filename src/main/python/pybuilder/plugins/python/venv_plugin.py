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

import sys

from pybuilder.core import (before,
                            task,
                            use_plugin,
                            init)
from pybuilder.install_utils import install_dependencies
from pybuilder.utils import (as_list,
                             mkdir,
                             create_venv,
                             python_specific_dir_name,
                             venv_symlinks,
                             add_env_to_path)

__author__ = "Arcadiy Ivanov"

use_plugin("core")


@init
def initialize_venv_plugin(project):
    project.set_property_if_unset("refresh_venvs", False)
    project.set_property_if_unset("pip_verbose", 0)
    project.set_property_if_unset("dir_install_logs", "$dir_logs/install_dependencies")

    project.set_property_if_unset("install_dependencies_index_url", None)
    project.set_property_if_unset("install_dependencies_extra_index_url", None)
    project.set_property_if_unset("install_dependencies_trusted_host", None)
    project.set_property_if_unset("install_dependencies_constraints", "constraints_file")
    # Deprecated - has no effect
    project.set_property_if_unset("install_dependencies_upgrade", False)
    project.set_property_if_unset("install_dependencies_insecure_installation", [])

    project.set_property_if_unset("dir_build_venv", "$dir_target/venv/build/%s" % python_specific_dir_name)
    project.set_property_if_unset("dir_test_venv", "$dir_target/venv/test/%s" % python_specific_dir_name)
    project.set_property_if_unset("venv_names", ["build", "test"])
    project.set_property_if_unset("venv_clean", False)


@task("prepare", "Creates target VEnvs")
def create_venvs(logger, project):
    log_dir = project.expand_path("$dir_install_logs")

    logger.debug("Creating log directory '%s'", log_dir)
    mkdir(log_dir)


@before("compile_sources", only_once=True)
def install_build_venv(logger, project):
    install_venv(project, logger, "build")
    install_venv_dependencies(logger, project, "build")

    # TODO: This is a horrible hack
    add_env_to_path(project.expand_path("$dir_build_venv"), sys.path)


@before("run_integration_tests", only_once=True)
def install_test_venv(logger, project):
    install_venv(project, logger, "test")
    install_venv_dependencies(logger, project, "test")


def install_venv(project, logger, venv_name):
    venv_dir = _get_venv_dir(project, venv_name)
    clear = project.get_property("refresh_venvs")
    logger.info("Creating target '%s' VEnv in '%s'%s", venv_name, venv_dir, " (refreshing)" if clear else "")
    create_venv(venv_dir, with_pip=True, symlinks=venv_symlinks, clear=clear, offline=project.offline)


def install_venv_dependencies(logger, project, venv_name, dependencies=None):
    venv_dir = project.expand_path("$dir_%s_venv" % venv_name)
    log_file_name = project.expand_path("$dir_install_logs", "venv_%s_install_logs" % venv_name)
    constraints_file_name = project.get_property("install_dependencies_constraints")
    if not dependencies:
        if venv_name == "build":
            dependencies = as_list(project.build_dependencies) + as_list(project.dependencies)
        elif venv_name == "test":
            dependencies = as_list(project.dependencies)
        else:
            raise RuntimeError("No dependencies were specified for non-standard VEnv %s" % venv_name)

    install_dependencies(logger, project, dependencies, venv_dir, log_file_name, {}, constraints_file_name)


def _get_venv_dir(project, venv_name):
    return project.expand_path("$dir_%s_venv" % venv_name)


def _get_venv_dirs(project):
    for venv_name in project.get_property("venv_names"):
        yield venv_name, _get_venv_dir(project, venv_name)
