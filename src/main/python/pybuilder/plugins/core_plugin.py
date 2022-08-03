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

import os
import shutil
from functools import partial

from pybuilder.core import init, task, description, depends, optional
from pybuilder.utils import jp


@init
def init(project):
    project.set_property("dir_target", "target")
    project.set_property("dir_reports", jp("$dir_target", "reports"))
    project.set_property("dir_logs", jp("$dir_target", "logs"))

    project.set_property_if_unset("remote_debug", 0)
    project.set_property_if_unset("remote_tracing", 0)

    project.write_report = partial(write_report, project)


def write_report(project, file, *content):
    with open(project.expand_path("$dir_reports", file), "w") as report_file:
        report_file.writelines(content)


@task
@description("Cleans the generated output.")
def clean(project, logger):
    target_directory = project.expand_path("$dir_target")
    logger.info("Removing target directory %s", target_directory)
    shutil.rmtree(target_directory, ignore_errors=True)


@task
@description("Prepares the project for building.")
def prepare(project, logger, reactor):
    target_directory = project.expand_path("$dir_target")
    if not os.path.exists(target_directory):
        logger.debug("Creating target directory %s", target_directory)
        os.mkdir(target_directory)

    reports_directory = project.expand_path("$dir_reports")
    if not os.path.exists(reports_directory):
        logger.debug("Creating reports directory %s", reports_directory)
        os.mkdir(reports_directory)

    reactor.python_env_registry["pybuilder"].install_dependencies(project.plugin_dependencies,
                                                                  package_type="plugin")


@task
@depends(prepare)
@description("Compiles source files that need compilation.")
def compile_sources():
    pass


@task
@depends(compile_sources)
@description("Runs all unit tests.")
def run_unit_tests():
    pass


@task
@depends(compile_sources, optional(run_unit_tests))
@description("Packages the application.")
def package():
    pass


@task
@depends(package)
@description("Runs integration tests on the packaged application.")
def run_integration_tests():
    pass


@task
@depends(optional(run_integration_tests))
@description("Verifies the project and possibly integration tests.")
def verify():
    pass


@task
@depends(package, optional(verify))
@description("Publishes the project.")
def publish():
    pass


@task
@depends(package, optional(publish))
@description("Installs the published project.")
def install():
    pass


@task(description="Print the module path.")
def print_module_path(project):
    print(project.expand_path("$dir_source_main_python"))


@task(description="Print the script path.")
def print_scripts_path(project):
    print(project.expand_path("$dir_source_main_scripts"))
