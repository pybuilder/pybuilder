#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
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

from pybuilder.core import init, use_plugin, task, description
from pybuilder.utils import execute_command, Timer
from pybuilder.terminal import print_text_line, print_file_content, print_text
from pybuilder.plugins.python.test_plugin_helper import ReportsProcessor

from pybuilder.terminal import styled_text, fg, GREEN, MAGENTA, GREY

use_plugin("python.core")

FINISHED_SYMBOL = "-"
PENDING_SYMBOL = "/"
WAITING_SYMBOL = "|"


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
    if not project.get_property("integrationtest_parallel"):
        reports, total_time = run_integration_tests_sequentially(
            project, logger)
    else:
        reports, total_time = run_integration_tests_in_parallel(
            project, logger)

    reports_processor = ReportsProcessor(project, logger)
    reports_processor.process_reports(reports, total_time)
    reports_processor.write_report_and_ensure_all_tests_passed()


def run_integration_tests_sequentially(project, logger):
    logger.debug("Running integration tests sequentially")
    reports_dir = prepare_reports_directory(project)

    report_items = []

    total_time = Timer.start()

    for test in discover_integration_tests_for_project(project):
        report_item = run_single_test(logger, project, reports_dir, test)
        report_items.append(report_item)

    total_time.stop()

    return (report_items, total_time)


def run_integration_tests_in_parallel(project, logger):
    logger.info("Running integration tests in parallel")
    import multiprocessing
    tests = multiprocessing.Queue()
    reports = multiprocessing.Queue()
    reports_dir = prepare_reports_directory(project)
    cpu_scaling_factor = project.get_property(
        'integrationtest_cpu_scaling_factor', 4)
    cpu_count = multiprocessing.cpu_count()
    worker_pool_size = cpu_count * cpu_scaling_factor
    logger.debug(
        "Running integration tests in parallel with {0} processes ({1} cpus found)".format(
            worker_pool_size,
            cpu_count))

    total_time = Timer.start()
    for test in discover_integration_tests_for_project(project):
        tests.put(test)
    total_tests_count = tests.qsize()
    progress = TaskPoolProgress(total_tests_count, worker_pool_size)

    def pick_and_run_tests_then_report(tests, reports, reports_dir, logger, project):
        while True:
            try:
                test = tests.get_nowait()
                report_item = run_single_test(
                    logger, project, reports_dir, test, not progress.can_be_displayed)
                reports.put(report_item)
            except:
                break

    pool = []
    for i in range(worker_pool_size):
        p = multiprocessing.Process(
            target=pick_and_run_tests_then_report, args=(tests, reports, reports_dir, logger, project))
        pool.append(p)
        p.start()

    import time
    while not progress.is_finished:
        finished_tests_count = reports.qsize()
        progress.update(finished_tests_count)
        if progress.can_be_displayed:
            bar = progress.render()
            print_text(bar, flush=True)
        time.sleep(.5)

    progress.mark_as_finished()

    total_time.stop()

    iterable_reports = []
    while True:
        try:
            iterable_reports.append(reports.get_nowait())
        except:
            break

    return (iterable_reports, total_time)


def discover_integration_tests(source_path, suffix=".py"):
    result = []
    for root, _, files in os.walk(source_path):
        for file_name in files:
            if file_name.endswith(suffix):
                result.append(os.path.join(root, file_name))
    return result


def discover_integration_tests_for_project(project):
    integrationtest_source_dir = project.expand_path(
        "$dir_source_integrationtest_python")
    integrationtest_suffix = project.expand("$integrationtest_file_suffix")
    return discover_integration_tests(integrationtest_source_dir, integrationtest_suffix)


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


def run_single_test(logger, project, reports_dir, test, output_test_names=True):
    name, _ = os.path.splitext(os.path.basename(test))
    if output_test_names:
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


class TaskPoolProgress(object):

    def __init__(self, total_tasks_count, workers_count):
        self.total_tasks_count = total_tasks_count
        self.finished_tasks_count = 0
        self.workers_count = workers_count

    def update(self, finished_tasks_count):
        self.finished_tasks_count = finished_tasks_count

    def render(self):
        finished_tests_progress = styled_text(FINISHED_SYMBOL * self.finished_tasks_count, fg(GREEN))
        running_tests_count = self.running_tests_count
        running_tests_progress = styled_text(PENDING_SYMBOL * running_tests_count, fg(MAGENTA))
        waiting_tests_count = self.waiting_tests_count
        waiting_tests_progress = styled_text(WAITING_SYMBOL * waiting_tests_count, fg(GREY))

        return "\r[%s%s%s]" % (finished_tests_progress, running_tests_progress, waiting_tests_progress)

    def mark_as_finished(self):
        if self.can_be_displayed:
            print_text_line()

    @property
    def running_tests_count(self):
        pending_tasks = (self.total_tasks_count - self.finished_tasks_count)
        if pending_tasks > self.workers_count:
            return self.workers_count
        return pending_tasks

    @property
    def waiting_tests_count(self):
        return (self.total_tasks_count - self.finished_tasks_count - self.running_tests_count)

    @property
    def is_finished(self):
        return (self.finished_tasks_count == self.total_tasks_count)

    @property
    def can_be_displayed(self):
        if sys.stdout.isatty():
            return True
        return False
