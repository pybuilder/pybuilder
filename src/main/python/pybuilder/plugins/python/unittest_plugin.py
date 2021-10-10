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

import sys
import unittest
from functools import reduce
from types import MethodType, FunctionType

from pybuilder.ci_server_interaction import test_proxy_for
from pybuilder.core import init, task, description, use_plugin, before
from pybuilder.errors import BuildFailedException
from pybuilder.plugins.python.remote_tools.unittest_tool import start_unittest_tool, PipeShutdownError, \
    logger as tool_logger
from pybuilder.python_utils import StringIO
from pybuilder.terminal import print_text_line
from pybuilder.utils import discover_modules_matching, render_report

use_plugin("python.core")


@init
def init_test_source_directory(project):
    project.plugin_depends_on("unittest-xml-reporting", "~=3.0.4")

    project.set_property_if_unset("dir_source_unittest_python", "src/unittest/python")
    project.set_property_if_unset("unittest_breaks_build", True)
    project.set_property_if_unset("unittest_module_glob", "*_tests")
    project.set_property_if_unset("unittest_file_suffix", None)  # deprecated, use unittest_module_glob.
    project.set_property_if_unset("unittest_test_method_prefix", None)
    project.set_property_if_unset("unittest_python_env", "build")
    project.set_property_if_unset("unittest_runner", (
        lambda stream: __import__("xmlrunner").XMLTestRunner(output=project.expand_path("$dir_target/reports"),
                                                             stream=stream), "_make_result"))


@before("prepare")
def coverage_init(project, logger, reactor):
    em = reactor.execution_manager

    if em.is_task_in_current_execution_plan("coverage") and em.is_task_in_current_execution_plan("run_unit_tests"):
        project.get_property("_coverage_tasks").append(run_unit_tests)
        project.get_property("_coverage_config_prefixes")[run_unit_tests] = "ut"
        project.set_property("ut_coverage_name", "Python unit test")
        # project.set_property("ut_coverage_python_env", project.get_property("unittest_python_env"))


@task
@description("Runs unit tests based on Python's unittest module")
def run_unit_tests(project, logger, reactor):
    run_tests(project, logger, reactor, "unittest", "unit tests")


def run_tests(project, logger, reactor, execution_prefix, execution_name):
    logger.info("Running %s", execution_name)
    test_dir = project.expand_path("$dir_source_%s_python" % execution_prefix)
    src_dir = project.expand_path("$dir_source_main_python")

    file_suffix = project.get_property("%s_file_suffix" % execution_prefix)
    if file_suffix is not None:
        logger.warn(
            "%(prefix)s_file_suffix is deprecated, please use %(prefix)s_module_glob" % {"prefix": execution_prefix})
        module_glob = "*{0}".format(file_suffix)
        if module_glob.endswith(".py"):
            module_glob = module_glob[:-3]
        project.set_property("%s_module_glob" % execution_prefix, module_glob)
    else:
        module_glob = project.get_property("%s_module_glob" % execution_prefix)

    logger.info("Executing %s from Python modules in %s", execution_name, test_dir)
    logger.debug("Including files matching '%s'", module_glob)

    try:
        test_method_prefix = project.get_property("%s_test_method_prefix" % execution_prefix)
        runner_generator = project.get_property("%s_runner" % execution_prefix)
        result, console_out = execute_tests_matching(
            reactor.python_env_registry[project.get_property("unittest_python_env")],
            reactor.tools, runner_generator, logger, test_dir, module_glob, [test_dir, src_dir],
            test_method_prefix,
            project.get_property("remote_debug"),
            project.get_property("remote_tracing"))

        if result.testsRun == 0:
            logger.warn("No %s executed.", execution_name)
        else:
            logger.info("Executed %d %s", result.testsRun, execution_name)

        write_report(execution_prefix, project, logger, result, console_out)

        break_build = project.get_property("%s_breaks_build" % execution_prefix)
        if not result.wasSuccessful():
            msg = "There were %d error(s) and %d failure(s) in %s" % (
                len(result.errors), len(result.failures), execution_name)
            if break_build:
                raise BuildFailedException(msg)
            else:
                logger.warn(msg)
        logger.info("All %s passed.", execution_name)
    except ImportError as e:
        import traceback

        _, _, import_error_traceback = sys.exc_info()
        file_with_error, error_line, _, statement_causing_error = traceback.extract_tb(import_error_traceback)[-1]
        logger.error("Import error in test file {0}, due to statement '{1}' on line {2}".format(
            file_with_error, statement_causing_error, error_line))
        logger.error("Error importing %s: %s", execution_prefix, e)
        raise BuildFailedException("Unable to execute %s." % execution_name)


def execute_tests(pyenv, tools, runner_generator, logger, test_source, suffix, sys_paths, test_method_prefix=None,
                  remote_debug=0, remote_tracing=0):
    return execute_tests_matching(pyenv, tools, runner_generator, logger, test_source, "*{0}".format(suffix),
                                  test_method_prefix, remote_debug=remote_debug, remote_tracing=remote_tracing)


def execute_tests_matching(pyenv, tools, runner_generator, logger, test_source, file_glob, sys_paths,
                           test_method_prefix=None, remote_debug=0, remote_tracing=0):
    output_log_file = StringIO()
    try:
        test_modules = discover_modules_matching(test_source, file_glob)
        runner = _instrument_runner(runner_generator,
                                    logger,
                                    _create_runner(runner_generator, output_log_file))

        exit_code = None
        try:
            proc, pipe = start_unittest_tool(pyenv, tools, sys_paths, test_modules, test_method_prefix,
                                             logging=remote_debug, tracing=remote_tracing)
            try:
                pipe.register_remote(runner)
                pipe.register_remote_type(unittest.result.TestResult)
                tests = pipe.get_exposed("unittest_tests")
                result = runner.run(tests)
            except PipeShutdownError:
                pass
            finally:
                try:
                    pipe.close()
                finally:
                    try:
                        proc.join()
                    finally:
                        try:
                            exit_code = proc.exitcode
                        finally:
                            try:
                                proc.close()
                            except AttributeError:
                                pass

            if exit_code:
                raise BuildFailedException("Unittest tool failed with exit code %s", exit_code)

            remote_closed_cause = pipe.remote_close_cause()
            if remote_closed_cause is not None:
                raise remote_closed_cause
        finally:
            del tool_logger.handlers[:]

        return result, output_log_file.getvalue()
    finally:
        output_log_file.close()


def _create_runner(runner_generator, output_log_file=None):
    if (isinstance(runner_generator, list) or isinstance(runner_generator, tuple)) and len(runner_generator) > 1:
        runner_generator = runner_generator[0]
    if not hasattr(runner_generator, '__call__'):
        runner_generator = reduce(getattr, runner_generator.split("."), sys.modules[__name__])
    return runner_generator(output_log_file)


def _get_make_result_method_name(runner_generator):
    if (isinstance(runner_generator, list) or isinstance(runner_generator, tuple)) and len(runner_generator) > 1:
        method = runner_generator[1]
        if type(method) == MethodType or type(method) == FunctionType:
            method = method.__name__
    else:
        method = "_makeResult"
    return method


def _instrument_runner(runner_generator, logger, runner):
    method_name = _get_make_result_method_name(runner_generator)
    old_make_result = getattr(runner, method_name)
    runner.logger = logger

    def _instrumented_make_result(self):
        result = old_make_result()
        return _instrument_result(logger, result)

    setattr(runner, method_name, MethodType(_instrumented_make_result, runner))
    return runner


def _instrument_result(logger, result):
    old_startTest = result.startTest
    old_addError = result.addError
    old_addFailure = result.addFailure

    def startTest(self, test):
        self.test_names.append(str(test))
        self.logger.debug("starting %s", test)
        old_startTest(test)

    def addError(self, test, err):
        exception_type, exception, traceback = err
        self.failed_test_names_and_reasons[test] = '{0}: {1}'.format(exception_type, exception).replace('\'', '')
        old_addError(test, err)

    def addFailure(self, test, err):
        exception_type, exception, traceback = err
        self.failed_test_names_and_reasons[test] = '{0}: {1}'.format(exception_type, exception).replace('\'', '')
        old_addFailure(test, err)

    result.startTest = MethodType(startTest, result)
    result.addError = MethodType(addError, result)
    result.addFailure = MethodType(addFailure, result)

    result.test_names = []
    result.failed_test_names_and_reasons = {}
    result.logger = logger
    return result


def _register_test_and_source_path_and_return_test_dir(project, system_path, execution_prefix):
    """This function is deprecated and will be removed and should not be used by any new code"""
    test_dir = project.expand_path("$dir_source_%s_python" % execution_prefix)
    system_path.insert(0, test_dir)
    system_path.insert(0, project.expand_path("$dir_source_main_python"))

    return test_dir


def write_report(name, project, logger, result, console_out):
    project.write_report("%s" % name, console_out)

    report = {"tests-run": result.testsRun,
              "errors": [],
              "failures": []}

    for error in result.errors:
        report["errors"].append({"test": error[0].id(),
                                 "traceback": error[1]})
        logger.error("Test has error: %s", error[0].id())

        if project.get_property("verbose"):
            print_text_line(error[1])

    for failure in result.failures:
        report["failures"].append({"test": failure[0].id(),
                                   "traceback": failure[1]})
        logger.error("Test failed: %s", failure[0].id())

        if project.get_property("verbose"):
            print_text_line(failure[1])

    project.write_report("%s.json" % name, render_report(report))

    report_to_ci_server(project, result)


def report_to_ci_server(project, result):
    for test_name in result.test_names:
        with test_proxy_for(project).and_test_name(test_name) as test:
            if test_name in result.failed_test_names_and_reasons:
                test.fails(result.failed_test_names_and_reasons.get(test_name))
