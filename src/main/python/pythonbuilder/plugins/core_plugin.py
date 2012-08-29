#  This file is part of Python Builder
#   
#  Copyright 2011 The Python Builder Team
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
import os
import shutil

from pythonbuilder.core import init, task, description, depends

@init
def init (project):
    project.set_property("dir_target", "target")
    project.set_property("dir_reports", "$dir_target/reports")
    project.set_property("dir_logs", "$dir_target/logs")
    
    def write_report (file, *content):
        with open(project.expand_path("$dir_reports", file), "w") as report_file:
            report_file.writelines(content)
    project.write_report = write_report

@task
@description("Cleans the generated output.")
def clean (project, logger):
    target_directory = project.expand_path("$dir_target")
    logger.info("Removing target directory %s", target_directory)
    shutil.rmtree(target_directory, ignore_errors=True)

@task
@description("Prepares the project for building.")
def prepare (project, logger):
    target_directory = project.expand_path("$dir_target")
    if not os.path.exists(target_directory):
        logger.debug("Creating target directory %s", target_directory)
        os.mkdir(target_directory)
    
    reports_directory = project.expand_path("$dir_reports")
    if not os.path.exists(reports_directory):
        logger.debug("Creating reports directory %s", reports_directory)
        os.mkdir(reports_directory)

@task
@depends(prepare)
@description("Compiles source files that need compilation.")
def compile_sources ():
    pass

@task
@depends(compile_sources)
@description("Runs all unit tests.")
def run_unit_tests ():
    pass

@task
@depends(run_unit_tests)
@description("Packages the application.")
def package ():
    pass

@task
@depends(package)
@description("Runs integration tests on the packaged application.")
def run_integration_tests ():
    pass

@task
@depends(run_integration_tests)
@description("Verifies the project and possibly integration tests.")
def verify ():
    pass

@task
@depends(verify)
@description("Publishes the project.")
def publish ():
    pass