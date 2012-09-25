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

try:
    from StringIO import StringIO
except (ImportError) as e:
    from io import StringIO

import sys
import unittest

from pythonbuilder.core import init, task, description, use_plugin
from pythonbuilder.errors import BuildFailedException
from pythonbuilder.utils import discover_modules, render_report

use_plugin("python.core")

@init
def init_test_source_directory (project):
    project.set_property_if_unset("dir_source_unittest_python", "src/unittest/python")
    project.set_property_if_unset("unittest_file_suffix", "_tests.py")
        
@task
@description("Runs unit tests based on Python's unittest module")
def run_unit_tests (project, logger):
    sys.path.append(project.expand_path("$dir_source_main_python"))
    test_dir = project.expand_path("$dir_source_unittest_python")
    sys.path.append(test_dir)
    
    suffix = project.expand("$unittest_file_suffix")
    
    logger.info("Executing unittests in %s", test_dir)
    logger.debug("Including files ending with '%s'", suffix)

    try:    
        result, console_out = execute_tests(test_dir, suffix)
        
        if result.testsRun == 0:
            logger.warn("No unittests executed.")
        else:
            logger.info("Executed %d unittests", result.testsRun)
        
        write_report("unittest", project, logger, result, console_out)
        
        if not result.wasSuccessful():
            raise BuildFailedException("There were test errors.")
        logger.info("All unittests passed.")
    except ImportError as e:
        logger.error("Error importing unittests: %s", e)
        raise BuildFailedException("Unable to execute unit tests.")

def execute_tests (test_source, suffix):
    output_log_file = StringIO()
    
    try:
        test_modules = discover_modules(test_source, suffix)
        tests = unittest.defaultTestLoader.loadTestsFromNames(test_modules)
        result = unittest.TextTestRunner(stream=output_log_file).run(tests)
        return (result, output_log_file.getvalue())
    finally:
        output_log_file.close()
        
def write_report(name, project, logger, result, console_out):
    project.write_report("%s" % name, console_out)    
    
    report = {"tests-run":result.testsRun, 
        "errors":[], 
        "failures":[]}
    for error in result.errors:
        report["errors"].append({"test":error[0].id(), "traceback":error[1]})
        logger.error("Test has error: %s", error[0].id())
    
    for failure in result.failures:
        report["failures"].append({"test":failure[0].id(), "traceback":failure[1]})
        logger.error("Test failed: %s", failure[0].id())
    
    project.write_report("%s.json" % name, render_report(report))
