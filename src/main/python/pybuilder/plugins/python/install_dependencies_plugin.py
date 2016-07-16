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

import collections
import imp
import os
import sys

from pybuilder.core import (before,
                            task,
                            description,
                            use_plugin,
                            init,
                            Dependency,
                            RequirementsFile)
from pybuilder.errors import BuildFailedException
from pybuilder.pip_utils import (PIP_EXEC_STANZA,
                                 build_pip_install_options,
                                 as_pip_install_target,
                                 get_package_version,
                                 should_update_package,
                                 version_satisfies_spec)
from pybuilder.terminal import print_file_content
from pybuilder.utils import execute_command, mkdir, as_list, safe_log_file_name

__author__ = "Alexander Metzner, Arcadiy Ivanov"

use_plugin("core")


@init
def initialize_install_dependencies_plugin(project):
    project.set_property_if_unset("dir_install_logs", "$dir_logs/install_dependencies")
    project.set_property_if_unset("install_dependencies_index_url", None)
    project.set_property_if_unset("install_dependencies_local_mapping", {})
    project.set_property_if_unset("install_dependencies_extra_index_url", None)
    project.set_property_if_unset("install_dependencies_trusted_host", None)
    # Deprecated - has no effect
    project.set_property_if_unset("install_dependencies_upgrade", False)
    project.set_property_if_unset("install_dependencies_insecure_installation", [])


@task
@description("Installs all (both runtime and build) dependencies specified in the build descriptor")
def install_dependencies(logger, project):
    logger.info("Installing all dependencies")
    install_dependency(logger, project, as_list(project.build_dependencies) + as_list(project.dependencies))


@task
@description("Installs all build dependencies specified in the build descriptor")
def install_build_dependencies(logger, project):
    logger.info("Installing build dependencies")
    install_dependency(logger, project, project.build_dependencies)


@task
@description("Installs all runtime dependencies specified in the build descriptor")
def install_runtime_dependencies(logger, project):
    logger.info("Installing runtime dependencies")
    install_dependency(logger, project, project.dependencies)


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


def install_dependency(logger, project, dependencies):
    dependencies_to_install, orig_installed_pkgs = _filter_dependencies(logger, project, dependencies)
    batch_dependencies = []
    standalone_dependencies = []
    local_mapping = project.get_property("install_dependencies_local_mapping")
    for dependency in dependencies_to_install:
        url = getattr(dependency, "url", None)

        if dependency.name in local_mapping or url:
            install_type = "standalone"
            logger.debug("Dependency '%s' has to be installed standalone" % dependency)
            standalone_dependencies.append(dependency)
        else:
            install_type = "batch"
            logger.debug("Dependency '%s' will be included in batch install" % dependency)
            batch_dependencies.append(dependency)

        logger.info("Processing %s dependency '%s%s'%s", install_type, dependency.name,
                    dependency.version if dependency.version else "",
                    " from %s" % url if url else "")

    for standalone_dependency in standalone_dependencies:
        url = getattr(standalone_dependency, "url", None)
        log_file = project.expand_path("$dir_install_logs", safe_log_file_name(dependency.name))
        _do_install_dependency(logger, project, standalone_dependency,
                               True,
                               url,
                               local_mapping.get(dependency.name),
                               log_file)

    if len(batch_dependencies):
        log_file = project.expand_path("$dir_install_logs", "install_batch")
        _do_install_dependency(logger, project, batch_dependencies, True, False, None, log_file)

    __reload_pip_if_updated(logger, dependencies_to_install)


def _filter_dependencies(logger, project, dependencies):
    dependencies = as_list(dependencies)
    installed_packages = get_package_version(dependencies)
    dependencies_to_install = []

    for dependency in dependencies:
        logger.debug("Inspecting dependency '%s'" % dependency)
        if isinstance(dependency, RequirementsFile):
            # Always add requirement file-based dependencies
            logger.debug("Dependency '%s' is a requirement file and will be included" % dependency)
            dependencies_to_install.append(dependency)
            continue
        elif isinstance(dependency, Dependency):
            if dependency.url:
                # Always add dependency that is url-based
                logger.debug("Dependency '%s' is URL-based and will be included" % dependency)
                dependencies_to_install.append(dependency)
                continue
            if should_update_package(dependency.version) and not getattr(dependency, "version_not_a_spec", False):
                # Always add dependency that has a version specifier indicating desire to always update
                logger.debug("Dependency '%s' has a non-exact version specifier and will be included" % dependency)
                dependencies_to_install.append(dependency)
                continue

        dependency_name = dependency.name.lower()
        if dependency_name not in installed_packages:
            # If dependency not installed at all then install it
            logger.debug("Dependency '%s' is not installed and will be included" % dependency)
            dependencies_to_install.append(dependency)
            continue

        if dependency.version and not version_satisfies_spec(dependency.version, installed_packages[dependency_name]):
            # If version is specified and version constraint is not satisfied
            logger.debug("Dependency '%s' is not satisfied by installed dependency version '%s' and will be included" %
                         (dependency, installed_packages[dependency_name]))
            dependencies_to_install.append(dependency)
            continue

        logger.debug("Dependency '%s' is already up-to-date and will be skipped" % dependency)

    return dependencies_to_install, installed_packages


def _do_install_dependency(logger, project, dependency, upgrade, force_reinstall, target_dir, log_file):
    batch = isinstance(dependency, collections.Iterable)

    pip_command_line = list()
    pip_command_line.extend(PIP_EXEC_STANZA)
    pip_command_line.append("install")
    pip_command_line.extend(build_pip_install_options(project.get_property("install_dependencies_index_url"),
                                                      project.get_property("install_dependencies_extra_index_url"),
                                                      upgrade,
                                                      project.get_property(
                                                          "install_dependencies_insecure_installation"),
                                                      force_reinstall,
                                                      target_dir,
                                                      project.get_property("verbose"),
                                                      project.get_property("install_dependencies_trusted_host")
                                                      ))
    pip_command_line.extend(as_pip_install_target(dependency))
    logger.debug("Invoking pip: %s", pip_command_line)
    exit_code = execute_command(pip_command_line, log_file, env=os.environ, shell=False)

    if exit_code != 0:
        if batch:
            dependency_name = " batch dependencies."
        else:
            dependency_name = " dependency '%s'." % dependency.name

        if project.get_property("verbose"):
            print_file_content(log_file)
            raise BuildFailedException("Unable to install%s" % dependency_name)
        else:
            raise BuildFailedException("Unable to install%s See %s for details.",
                                       dependency_name,
                                       log_file)


def __reload_pip_if_updated(logger, dependencies_to_install):
    reload_pip = False
    for dependency in dependencies_to_install:
        if dependency.name == "pip":
            reload_pip = True
            break

    if reload_pip:
        __reload_pip(logger)


def __reload_pip(logger):
    logger.debug("Reloading PIP-related modules")
    modules_to_unload = []
    for module_name in sys.modules:
        if module_name.startswith("pip.") or module_name == "pip":
            modules_to_unload.append(module_name)

    for module_name in modules_to_unload:
        del sys.modules[module_name]

    from pybuilder import pip_utils, pip_common
    imp.reload(pip_common)
    imp.reload(pip_utils)
