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
import sys

from pythonbuilder.errors import BuildFailedException
from pythonbuilder.core import init, use_plugin, task, description
from pythonbuilder.utils import execute_command, render_report, Timer

use_plugin("python.core")

@init
def init_test_source_directory (project):
    project.set_property_if_unset("dir_source_integrationtest_python", "src/integrationtest/python")
    project.set_property_if_unset("integrationtest_file_suffix", "_tests.py")

@task
@description("Runs integration tests based on Python's unittest module")
def run_integration_tests (project, logger):
    reports_dir = project.expand_path("$dir_reports/integrationtests")
    if not os.path.exists(reports_dir):
        os.mkdir(reports_dir)
    
    test_failed = 0
    
    tests_executed = 0
    
    total_time = Timer.start()
    
    report_items = []
    
    for test in discover_integration_tests(project.expand_path("$dir_source_integrationtest_python"),
                                           project.expand("$integrationtest_file_suffix")):
        name, _ = os.path.splitext(os.path.basename(test))
        logger.info("Running integration test %s", name)

        env = {
            "PYTHONPATH": os.pathsep.join((project.expand_path("$dir_dist"),
                                           project.expand_path("$dir_source_integrationtest_python")))
        }

        test_time = Timer.start()

        return_code = execute_command((sys.executable, test),
                                      os.path.join(reports_dir, name),
                                      env)
        test_time.stop()

        report_item = {
            "test": name,
            "test_file": test,
            "time": test_time.get_millis(),
            "success": True
        }

        if return_code != 0:
            test_failed += 1
            logger.error("Integration test failed: %s", test)
            report_item["success"] = False
        report_items.append(report_item)
            
        tests_executed += 1
    
    total_time.stop()
    
    test_report = {
        "time": total_time.get_millis(),
        "success": test_failed == 0,
        "num_of_tests": tests_executed,
        "tests_failed": test_failed,
        "tests": report_items
    }
    
    project.write_report("integrationtest.json", render_report(test_report))
    
    logger.info("Executed %d integration tests.", tests_executed)
    if test_failed:
        raise BuildFailedException("Integration test(s) failed.")
    
def discover_integration_tests (source_path, suffix=".py"):
    result = []
    for root, _, files in os.walk(source_path):
        for file_name in files:
            if file_name.endswith(suffix):
                result.append(os.path.join(root, file_name))
    return result    
