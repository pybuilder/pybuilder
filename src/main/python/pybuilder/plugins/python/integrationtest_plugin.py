#  This file is part of PyBuilder
#
#  Copyright 2011-2013 PyBuilder Team
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

from pybuilder.errors import BuildFailedException
from pybuilder.core import init, use_plugin, task, description
from pybuilder.utils import execute_command, render_report, Timer
from pybuilder.terminal import print_text_line, print_file_content

use_plugin("python.core")


@init
def init_test_source_directory(project):
    project.set_property_if_unset(
        "dir_source_integrationtest_python", "src/integrationtest/python")
    project.set_property_if_unset("integrationtest_file_suffix", "_tests.py")
    project.set_property_if_unset("integrationtest_additional_environment", {})
    project.set_property_if_unset("integrationtest_inherit_environment", False)


@task
@description("Runs integration tests based on Python's unittest module")
def run_integration_tests(project, logger):
    if not project.get_property('integrationtest_parallel'):
        return run_integration_tests_sequentially(project, logger)

    return run_integration_tests_in_parallel(project, logger)


def run_integration_tests_sequentially(project, logger):
    reports_dir = prepare_reports_directory(project)

    test_failed = 0
    tests_executed = 0
    report_items = []

    total_time = Timer.start()

    for test in discover_integration_tests(project.expand_path("$dir_source_integrationtest_python"),
                                           project.expand("$integrationtest_file_suffix")):

        report_item = run_single_test(logger, project, reports_dir, test)
        report_items.append(report_item)

        if not report_item["success"]:
            test_failed += 1

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


def run_integration_tests_in_parallel(project, logger):
    import multiprocessing
    tests = multiprocessing.Queue()
    reports = multiprocessing.Queue()
    reports_dir = prepare_reports_directory(project)
    worker_pool_size = project.get_property('integrationtest_workers', None) or multiprocessing.cpu_count() * 4

    tests_failed = 0
    tests_executed = 0

    total_time = Timer.start()

    for test in discover_integration_tests(project.expand_path("$dir_source_integrationtest_python"),
                                           project.expand("$integrationtest_file_suffix")):
        tests.put(test)

    def pick_and_run_tests_then_report(tests, reports, reports_dir, logger, project):
        while True:
            try:
                test = tests.get_nowait()
                report_item = run_single_test(
                    logger, project, reports_dir, test)
                reports.put(report_item)
            except:
                break

    pool = []
    for i in range(worker_pool_size):
        p = multiprocessing.Process(
            target=pick_and_run_tests_then_report, args=(tests, reports, reports_dir, logger, project))
        pool.append(p)
        p.start()

    for worker in pool:
        worker.join()

    total_time.stop()

    tests_failed = 0
    tests_executed = 0

    iterable_reports = []
    while True:
        try:
            iterable_reports.append(reports.get_nowait())
        except:
            break

    for report in iterable_reports:
        if not report['success']:
            tests_failed += 1
        tests_executed += 1

    test_report = {
        "time": total_time.get_millis(),
        "success": tests_failed == 0,
        "num_of_tests": tests_executed,
        "tests_failed": tests_failed,
        "tests": iterable_reports
    }

    project.write_report("integrationtest.json", render_report(test_report))
    logger.info("Executed %d integration tests.", tests_executed)
    if tests_failed:
        raise BuildFailedException("Integration test(s) failed.")


def discover_integration_tests(source_path, suffix=".py"):
    result = []
    for root, _, files in os.walk(source_path):
        for file_name in files:
            if file_name.endswith(suffix):
                result.append(os.path.join(root, file_name))
    return result


def add_additional_environment_keys(env, project):
    additional_environment = project.get_property(
        "integrationtest_additional_environment", {})
    # TODO: assert that additional env is a map
    for key in additional_environment:
        env[key] = additional_environment[key]


def inherit_environment(env, project):
    if project.get_property("integrationtest_inherit_environment", False):
        for key in os.environ:
            if key not in env:
                env[key] = os.environ[key]


def prepare_environment(project):
    env = {
        "PYTHONPATH": os.pathsep.join((project.expand_path("$dir_dist"),
                                       project.expand_path("$dir_source_integrationtest_python")))
    }

    inherit_environment(env, project)

    add_additional_environment_keys(env, project)

    return env


def prepare_reports_directory(project):
    reports_dir = project.expand_path("$dir_reports/integrationtests")
    if not os.path.exists(reports_dir):
        os.mkdir(reports_dir)
    return reports_dir


def run_single_test(logger, project, reports_dir, test, ):
    name, _ = os.path.splitext(os.path.basename(test))
    logger.info("Running integration test %s", name)
    env = prepare_environment(project)
    test_time = Timer.start()
    command_and_arguments = (sys.executable, test)
    report_file_name = os.path.join(reports_dir, name)
    error_file_name = report_file_name + ".err"
    return_code = execute_command(
        command_and_arguments, report_file_name, env, error_file_name=error_file_name)
    test_time.stop()
    report_item = {
        "test": name,
        "test_file": test,
        "time": test_time.get_millis(),
        "success": True
    }
    if return_code != 0:
        logger.error("Integration test failed: %s", test)
        report_item["success"] = False

        if project.get_property("verbose"):
            print_file_content(report_file_name)
            print_text_line()
            print_file_content(error_file_name)

    return report_item
