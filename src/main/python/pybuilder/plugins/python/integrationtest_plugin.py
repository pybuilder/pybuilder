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
import sys

from pybuilder.core import init, use_plugin, task, description, before
from pybuilder.plugins.python.test_plugin_helper import ReportsProcessor
from pybuilder.python_utils import mp_get_context
from pybuilder.terminal import print_text_line, print_file_content, print_text
from pybuilder.terminal import styled_text, fg, GREEN, MAGENTA, GREY
from pybuilder.utils import discover_files_matching, Timer, read_file

use_plugin("core")

from pybuilder.plugins.python.core_plugin import create_venv  # noqa: E402


@init
def initialize_integrationtest_plugin(project):
    project.set_property_if_unset("dir_source_integrationtest_python", "src/integrationtest/python")

    project.set_property_if_unset("integrationtest_breaks_build", True)
    project.set_property_if_unset("integrationtest_parallel", False)
    project.set_property_if_unset("integrationtest_file_glob", "*_tests.py")
    project.set_property_if_unset("integrationtest_additional_environment", {})
    project.set_property_if_unset("integrationtest_additional_commandline", "")
    project.set_property_if_unset("integrationtest_inherit_environment", False)
    project.set_property_if_unset("integrationtest_always_verbose", False)
    project.set_property_if_unset("integrationtest_cpu_scaling_factor", 4)
    project.set_property_if_unset("integrationtest_python_env", "test")
    project.set_property_if_unset("integrationtest_python_env_recreate", False)

    project.set_property_if_unset("integrationtest_file_suffix", None)  # deprecated, use integrationtest_file_glob.


@before("prepare")
def coverage_init(project, logger, reactor):
    em = reactor.execution_manager

    if em.is_task_in_current_execution_plan("coverage") and em.is_task_in_current_execution_plan(
            "run_integration_tests"):
        project.get_property("_coverage_tasks").append(run_integration_tests)
        project.get_property("_coverage_config_prefixes")[run_integration_tests] = "it"
        project.set_property("it_coverage_name", "Python integration test")
        project.set_property("it_coverage_python_env", project.get_property("integrationtest_python_env"))


@task
@description("Runs integration tests based on Python's unittest module")
def run_integration_tests(project, logger, reactor):
    if project.get_property("integrationtest_parallel"):
        logger.warn("Parallel integration test execution is temporarily disabled")

    # if not project.get_property("integrationtest_parallel"):
    reports, total_time = run_integration_tests_sequentially(project, logger, reactor)
    # else:
    #    reports, total_time = run_integration_tests_in_parallel(project, logger)

    reports_processor = ReportsProcessor(project, logger)
    reports_processor.process_reports(reports, total_time)
    reports_processor.report_to_ci_server(project)
    reports_processor.write_report_and_ensure_all_tests_passed()


def run_integration_tests_sequentially(project, logger, reactor):
    logger.debug("Running integration tests sequentially")
    reports_dir = prepare_reports_directory(project)

    report_items = []

    total_time = Timer.start()

    for test in discover_integration_tests_for_project(project, logger):
        report_item = run_single_test(logger, project, reactor, reports_dir, test)
        report_items.append(report_item)

    total_time.stop()

    return report_items, total_time


def run_integration_tests_in_parallel(project, logger):
    logger.info("Running integration tests in parallel")
    ctx = mp_get_context("spawn")
    tests = ctx.Queue()
    reports = ConsumingQueue(ctx)
    reports_dir = prepare_reports_directory(project)
    cpu_scaling_factor = project.get_property("integrationtest_cpu_scaling_factor")
    cpu_count = ctx.cpu_count()
    worker_pool_size = cpu_count * cpu_scaling_factor
    logger.debug(
        "Running integration tests in parallel with {0} processes ({1} cpus found)".format(
            worker_pool_size,
            cpu_count))

    total_time = Timer.start()
    # fail OSX has no sem_getvalue() implementation so no queue size
    total_tests_count = 0
    for test in discover_integration_tests_for_project(project, logger):
        tests.put(test)
        total_tests_count += 1
    progress = TaskPoolProgress(total_tests_count, worker_pool_size)

    def pick_and_run_tests_then_report(tests, reports, reports_dir, logger, project):
        while True:
            try:
                test = tests.get_nowait()
                report_item = run_single_test(
                    logger, project, reports_dir, test, not progress.can_be_displayed)
                reports.put(report_item)
            except ctx.Empty:
                break
            except Exception as e:
                logger.error("Failed to run test %r : %s" % (test, str(e)))
                failed_report = {
                    "test": test,
                    "test_file": test,
                    "time": 0,
                    "success": False,
                    "exception": str(e)
                }
                reports.put(failed_report)
                continue

    pool = []
    for i in range(worker_pool_size):
        p = ctx.Process(target=pick_and_run_tests_then_report,
                        args=(tests, reports, reports_dir, logger, project))
        pool.append(p)
        p.start()

    import time
    while not progress.is_finished:
        reports.consume_available_items()
        finished_tests_count = reports.size
        progress.update(finished_tests_count)
        progress.render_to_terminal()
        time.sleep(1)

    progress.mark_as_finished()

    total_time.stop()

    return reports.items, total_time


def discover_integration_tests(source_path, suffix=".py"):
    return discover_files_matching(source_path, "*{0}".format(suffix))


def discover_integration_tests_matching(source_path, file_glob):
    return discover_files_matching(source_path, file_glob)


def discover_integration_tests_for_project(project, logger=None):
    integrationtest_source_dir = project.expand_path("$dir_source_integrationtest_python")
    integrationtest_suffix = project.get_property("integrationtest_file_suffix")
    if integrationtest_suffix is not None:
        if logger is not None:
            logger.warn(
                "integrationtest_file_suffix is deprecated, please use integrationtest_file_glob"
            )
        project.set_property("integrationtest_file_glob", "*{0}".format(integrationtest_suffix))
    integrationtest_glob = project.expand("$integrationtest_file_glob")
    return discover_files_matching(integrationtest_source_dir, integrationtest_glob)


def add_additional_environment_keys(env, project):
    additional_environment = project.get_property("integrationtest_additional_environment")

    if not isinstance(additional_environment, dict):
        raise ValueError("Additional environment %r is not a map." %
                         additional_environment)
    for key in additional_environment:
        env[key] = additional_environment[key]


def prepare_environment(project):
    env = {
        "PYTHONPATH": os.pathsep.join((project.expand_path("$dir_dist"),
                                       project.expand_path("$dir_source_integrationtest_python")))
    }

    add_additional_environment_keys(env, project)

    return env


def prepare_reports_directory(project):
    reports_dir = project.expand_path("$dir_reports/integrationtests")
    if not os.path.exists(reports_dir):
        os.mkdir(reports_dir)
    return reports_dir


def run_single_test(logger, project, reactor, reports_dir, test, output_test_names=True):
    additional_integrationtest_commandline_text = project.get_property("integrationtest_additional_commandline")

    if additional_integrationtest_commandline_text:
        additional_integrationtest_commandline = tuple(additional_integrationtest_commandline_text.split(" "))
    else:
        additional_integrationtest_commandline = ()

    name, _ = os.path.splitext(os.path.basename(test))

    if output_test_names:
        logger.info("Running integration test %s", name)

    venv_name = project.get_property("integrationtest_python_env")
    python_env = reactor.python_env_registry[venv_name]
    create_venv(project, logger, reactor, venv_name, True,
                recreate_if_exists=project.get_property("integrationtest_python_env_recreate"))
    env = prepare_environment(project)
    command_and_arguments = python_env.executable + [test]
    command_and_arguments += additional_integrationtest_commandline

    report_file_name = os.path.join(reports_dir, name)
    error_file_name = report_file_name + ".err"

    test_time = Timer.start()
    return_code = python_env.execute_command(command_and_arguments, report_file_name, env,
                                             error_file_name=error_file_name,
                                             inherit_env=project.get_property("integrationtest_inherit_environment"))
    test_time.stop()
    report_item = {
        "test": name,
        "test_file": test,
        "time": test_time.get_millis(),
        "success": True
    }
    if return_code != 0:
        logger.error("Integration test failed: %s, exit code %d", test, return_code)
        report_item["success"] = False
        report_item["exception"] = ''.join(read_file(error_file_name)).replace('\'', '')

        if project.get_property("verbose") or project.get_property("integrationtest_always_verbose"):
            print_file_content(report_file_name)
            print_text_line()
            print_file_content(error_file_name)

    elif project.get_property("integrationtest_always_verbose"):
        print_file_content(report_file_name)
        print_text_line()
        print_file_content(error_file_name)

    return report_item


class ConsumingQueue(object):

    def __init__(self, ctx):
        self._items = []
        self._queue = ctx.Queue()
        self._ctx = ctx

    def consume_available_items(self):
        try:
            while True:
                item = self.get_nowait()
                self._items.append(item)
        except self._ctx.Empty:
            pass

    def put(self, *args, **kwargs):
        return self._queue.put(*args, **kwargs)

    def get_nowait(self, *args, **kwargs):
        return self._queue.get_nowait(*args, **kwargs)

    @property
    def items(self):
        return self._items

    @property
    def size(self):
        return len(self.items)


class TaskPoolProgress(object):
    """
    Class that renders progress for a set of tasks run in parallel.
    The progress is based on
    * the amount of total tasks, which must be static
    * the amount of workers running in parallel.
    The bar can be updated with the amount of tasks that have been successfully
    executed and render its progress.
    """

    BACKSPACE = "\b"
    FINISHED_SYMBOL = "-"
    PENDING_SYMBOL = "/"
    WAITING_SYMBOL = "|"
    PACMAN_FORWARD = "ᗧ"
    NO_PACMAN = ""

    def __init__(self, total_tasks_count, workers_count):
        self.total_tasks_count = total_tasks_count
        self.finished_tasks_count = 0
        self.workers_count = workers_count
        self.last_render_length = 0

    def update(self, finished_tasks_count):
        self.finished_tasks_count = finished_tasks_count

    def render(self):
        pacman = self.pacman_symbol
        finished_tests_progress = styled_text(
            self.FINISHED_SYMBOL * self.finished_tasks_count, fg(GREEN))
        running_tasks_count = self.running_tasks_count
        running_tests_progress = styled_text(
            self.PENDING_SYMBOL * running_tasks_count, fg(MAGENTA))
        waiting_tasks_count = self.waiting_tasks_count
        waiting_tasks_progress = styled_text(
            self.WAITING_SYMBOL * waiting_tasks_count, fg(GREY))
        trailing_space = ' ' if not pacman else ''

        return "[%s%s%s%s]%s" % (
            finished_tests_progress, pacman, running_tests_progress, waiting_tasks_progress, trailing_space)

    def render_to_terminal(self):
        if self.can_be_displayed:
            text_to_render = self.render()
            characters_to_be_erased = self.last_render_length
            self.last_render_length = len(text_to_render)
            text_to_render = "%s%s" % (characters_to_be_erased * self.BACKSPACE, text_to_render)
            print_text(text_to_render, flush=True)

    def mark_as_finished(self):
        if self.can_be_displayed:
            print_text_line()

    @property
    def pacman_symbol(self):
        if self.is_finished:
            return self.NO_PACMAN
        else:
            return self.PACMAN_FORWARD

    @property
    def running_tasks_count(self):
        pending_tasks = (self.total_tasks_count - self.finished_tasks_count)
        if pending_tasks > self.workers_count:
            return self.workers_count
        return pending_tasks

    @property
    def waiting_tasks_count(self):
        return self.total_tasks_count - self.finished_tasks_count - self.running_tasks_count

    @property
    def is_finished(self):
        return self.finished_tasks_count == self.total_tasks_count

    @property
    def can_be_displayed(self):
        if sys.stdout.isatty():
            return True
        return False
