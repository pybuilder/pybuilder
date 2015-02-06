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

import os
import re
import shutil

from pybuilder.core import init, task, description, use_plugin

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

    def list_packages():
        source_path = project.expand_path("$dir_source_main_python")
        for root, dirnames, _ in os.walk(source_path):
            for directory in dirnames:
                full_path = os.path.join(root, directory)
                if os.path.exists(os.path.join(full_path, "__init__.py")):
                    package = full_path.replace(source_path, "")
                    if package.startswith(os.sep):
                        package = package[1:]
                    package = package.replace(os.sep, ".")
                    yield package

    def list_modules():
        source_path = project.expand_path("$dir_source_main_python")
        for potential_module_file in os.listdir(source_path):
            potential_module_path = os.path.join(source_path, potential_module_file)
            if os.path.isfile(potential_module_path) and potential_module_file.endswith(".py"):
                yield potential_module_file[:-len(".py")]

    project.list_packages = list_packages
    project.list_modules = list_modules

    def list_scripts():
        scripts_dir = project.expand_path("$dir_source_main_scripts")
        if not os.path.exists(scripts_dir):
            return
        for script in os.listdir(scripts_dir):
            if os.path.isfile(os.path.join(scripts_dir, script)):
                yield script

    project.list_scripts = list_scripts


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

    if not os.path.exists(scripts_target):
        os.mkdir(scripts_target)

    logger.info("Copying scripts to %s", scripts_target)

    scripts_source = project.expand_path("$" + SCRIPTS_SOURCES_PROPERTY)
    if not os.path.exists(scripts_source):
        return
    for script in project.list_scripts():
        logger.debug("Copying script %s", script)
        source_file = project.expand_path("$" + SCRIPTS_SOURCES_PROPERTY, script)
        shutil.copy(source_file, scripts_target)


def copy_python_sources(project, logger):
    for package in os.listdir(project.expand_path("$" + PYTHON_SOURCES_PROPERTY)):
        if HIDDEN_FILE_NAME_PATTERN.match(package):
            continue
        logger.debug("Copying module/ package %s", package)
        source = project.expand_path("$" + PYTHON_SOURCES_PROPERTY, package)
        target = project.expand_path("$" + DISTRIBUTION_PROPERTY, package)
        if os.path.isdir(source):
            shutil.copytree(source, target,
                            symlinks=False,
                            ignore=shutil.ignore_patterns("*.pyc", ".*"))
        else:
            shutil.copyfile(source, target)


def init_dist_target(project, logger):
    dist_target = project.expand_path("$" + DISTRIBUTION_PROPERTY)

    if os.path.exists(dist_target):
        logger.debug("Removing preexisting distribution %s", dist_target)
        shutil.rmtree(dist_target)

    logger.debug("Creating directory %s", dist_target)
    os.makedirs(dist_target)
