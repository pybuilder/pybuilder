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

import re
import shutil
from functools import partial
from itertools import chain
from os import sep, walk
from os.path import isdir, exists, relpath

from pybuilder.core import description
from pybuilder.core import task, use_plugin, init
from pybuilder.python_env import PythonEnv
from pybuilder.utils import as_list, mkdir, makedirs, jp

HIDDEN_FILE_NAME_PATTERN = re.compile(r'^\..*$')

PYTHON_SOURCES_PROPERTY = "dir_source_main_python"
SCRIPTS_SOURCES_PROPERTY = "dir_source_main_scripts"
DISTRIBUTION_PROPERTY = "dir_dist"
SCRIPTS_TARGET_PROPERTY = "dir_dist_scripts"

use_plugin("core")


@init
def init_python_directories(project):
    project.set_property_if_unset(PYTHON_SOURCES_PROPERTY, "src/main/python")
    project.set_property_if_unset(SCRIPTS_SOURCES_PROPERTY, "src/main/scripts")
    project.set_property_if_unset(SCRIPTS_TARGET_PROPERTY, "scripts")
    project.set_property_if_unset(DISTRIBUTION_PROPERTY,
                                  "$dir_target/dist/{0}-{1}".format(project.name, project.version))

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

    project.set_property_if_unset("venv_names", ["build", "test"])
    project.set_property_if_unset("venv_dependencies", {})
    project.set_property_if_unset("venv_clean", False)

    project.list_packages = partial(list_packages, project)
    project.list_modules = partial(list_modules, project)
    project.list_scripts = partial(list_scripts, project)


@task("prepare", "Creates target VEnvs")
def create_venvs(logger, project, reactor):
    log_dir = project.expand_path("$dir_install_logs")
    logger.debug("Creating log directory '%s'", log_dir)
    mkdir(log_dir)

    per = reactor.python_env_registry
    system_env = per["system"]
    if not project.no_venvs:
        venv_dependencies_map = project.get_property("venv_dependencies")
        if "build" not in venv_dependencies_map:
            venv_dependencies_map["build"] = as_list(project.build_dependencies) + as_list(project.dependencies)
        if "test" not in venv_dependencies_map:
            venv_dependencies_map["test"] = as_list(project.dependencies)

        clear = project.get_property("refresh_venvs") or system_env.is_pypy
        for venv_name in project.get_property("venv_names"):
            create_venv(project, logger, reactor, venv_name, clear)
    else:
        for venv_name in project.get_property("venv_names"):
            per[venv_name] = system_env


def create_venv(project, logger, reactor, venv_name, clear, recreate_if_exists=False):
    if project.no_venvs:
        return

    per = reactor.python_env_registry
    system_env = per["system"]
    venv_dependencies_map = project.get_property("venv_dependencies")
    venv_dir = project.expand_path("$dir_target/venv", venv_name,
                                   system_env.versioned_dir_name)

    try:
        current_env = per[venv_name]
        if not recreate_if_exists:
            logger.info("Reusing target '%s' VEnv in '%s'", venv_name, venv_dir)
            return
        logger.info("Recreating target '%s' VEnv in '%s'%s", venv_name, venv_dir, " (refreshing)" if clear else "")
        venv_func = current_env.recreate_venv
    except KeyError:
        logger.info("Creating target '%s' VEnv in '%s'%s", venv_name, venv_dir, " (refreshing)" if clear else "")
        current_env = PythonEnv(venv_dir, reactor)
        venv_func = current_env.create_venv

    venv_func(with_pip=True,
              symlinks=system_env.venv_symlinks,
              clear=clear,
              offline=project.offline)

    try:
        per[venv_name] = current_env
    except KeyError:
        pass

    venv_dependencies = venv_dependencies_map.get(venv_name)
    if venv_dependencies:
        install_log_path = project.expand_path("$dir_install_logs", "venv_%s_install_logs" % venv_name)
        constraints_file_name = project.get_property("install_dependencies_constraints")
        current_env.install_dependencies(venv_dependencies,
                                         install_log_path=install_log_path,
                                         local_mapping={},
                                         constraints_file_name=constraints_file_name)


def list_packages(project):
    source_path = project.expand_path("$" + PYTHON_SOURCES_PROPERTY)
    result = []
    for root, dirs, files in walk(source_path, followlinks=True):
        if "__init__.py" in files:
            result.append(relpath(root, source_path).replace(sep, "."))

    return sorted(result)


def list_modules(project):
    source_path = project.expand_path("$" + PYTHON_SOURCES_PROPERTY)
    result = []
    for root, dirs, files in walk(source_path, followlinks=True):
        if "__init__.py" in files:
            # This directory is a package, therefore does not require inclusion in the modules
            dirs.clear()
            continue

        for file in files:
            potential_module_file = file
            if potential_module_file.endswith(".py"):
                result.append(relpath(jp(root, potential_module_file), source_path).replace(sep, ".")[:-3])

    return sorted(result)


def list_scripts(project):
    scripts_dir = project.expand_path("$" + SCRIPTS_SOURCES_PROPERTY)
    result = []
    if not exists(scripts_dir):
        return result
    for root, dirs, files in walk(scripts_dir, followlinks=True):
        for script in files:
            if not HIDDEN_FILE_NAME_PATTERN.match(script):
                result.append(script)
        break

    return sorted(result)


@task
@description("Package a python application.")
def package(project, logger):
    init_dist_target(project, logger)

    logger.info("Building distribution in {0}".format(project.expand_path("$" + DISTRIBUTION_PROPERTY)))

    copy_python_sources(project, logger)
    copy_scripts(project, logger)


def copy_scripts(project, logger):
    scripts_target = project.expand_path("$" + DISTRIBUTION_PROPERTY)
    if project.get_property(SCRIPTS_TARGET_PROPERTY):
        scripts_target = project.expand_path("$" + DISTRIBUTION_PROPERTY + "/$" + SCRIPTS_TARGET_PROPERTY)

    if not exists(scripts_target):
        mkdir(scripts_target)

    logger.info("Copying scripts to %s", scripts_target)

    scripts_source = project.expand_path("$" + SCRIPTS_SOURCES_PROPERTY)
    if not exists(scripts_source):
        return
    for script in project.list_scripts():
        logger.debug("Copying script %s to %s", script, scripts_target)
        source_file = project.expand_path("$" + SCRIPTS_SOURCES_PROPERTY, script)
        shutil.copy(source_file, scripts_target)


def copy_python_sources(project, logger):
    for root, dirs, files in walk(project.expand_path("$" + PYTHON_SOURCES_PROPERTY), followlinks=True):
        for pkg in chain(dirs, files):
            if HIDDEN_FILE_NAME_PATTERN.match(pkg):
                continue
            logger.debug("Copying module/package %s", pkg)
            source = project.expand_path("$" + PYTHON_SOURCES_PROPERTY, pkg)
            target = project.expand_path("$" + DISTRIBUTION_PROPERTY, pkg)
            if isdir(source):
                shutil.copytree(source, target,
                                symlinks=False,
                                ignore=shutil.ignore_patterns("*.pyc", ".*"))
            else:
                shutil.copyfile(source, target)
        break


def init_dist_target(project, logger):
    dist_target = project.expand_path("$" + DISTRIBUTION_PROPERTY)

    if exists(dist_target):
        logger.debug("Removing preexisting distribution %s", dist_target)
        shutil.rmtree(dist_target)

    logger.debug("Creating directory %s", dist_target)
    makedirs(dist_target)
