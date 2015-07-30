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

import sys

try:
    from StringIO import StringIO
except ImportError as e:
    from io import StringIO

import os
from distutils import sysconfig

from pybuilder.core import init, after, use_plugin
from pybuilder.utils import discover_modules, render_report, fork_process
from pybuilder.errors import BuildFailedException

use_plugin("python.core")
use_plugin("analysis")


@init
def init_coverage_properties(project):
    project.build_depends_on("coverage")

    project.set_property_if_unset("coverage_threshold_warn", 70)
    project.set_property_if_unset("coverage_break_build", True)
    project.set_property_if_unset("coverage_reload_modules", None)  # deprecated, unused
    project.set_property_if_unset("coverage_exceptions", [])
    project.set_property_if_unset("coverage_fork", None)  # deprecated, unused


@after(("analyze", "verify"), only_once=True)
def verify_coverage(project, logger, reactor):
    run_coverage(project, logger, reactor, "coverage", "coverage", "run_unit_tests")


def run_coverage(project, logger, reactor, execution_prefix, execution_name, target_task, shortest_plan=False):
    logger.info("Collecting coverage information")

    if project.get_property("%s_fork" % execution_prefix) is not None:
        logger.warn(
            "%s_fork is deprecated, coverage always runs in its own fork", execution_prefix)

    if project.get_property("%s_reload_modules" % execution_prefix) is not None:
        logger.warn(
            "%s_reload_modules is deprecated - modules are no longer reloaded", execution_prefix)

    logger.debug("Forking process to do %s analysis", execution_name)
    exit_code, _ = fork_process(target=do_coverage,
                                args=(
                                    project, logger, reactor, execution_prefix, execution_name,
                                    target_task, shortest_plan))
    if exit_code and project.get_property("%s_break_build" % execution_prefix):
        raise BuildFailedException(
            "Forked %s process indicated failure with error code %d" % (execution_name, exit_code))


def do_coverage(project, logger, reactor, execution_prefix, execution_name, target_task, shortest_plan):
    """
    This function MUST ALWAYS execute in a fork.
    The sys.modules will be manipulated extensively to stage the tests properly, which may affect execute down the line.
    It's best to simple let this method exit and the fork die rather than to try to recover.
    """
    source_tree_path = project.get_property("dir_source_main_python")
    module_names = _discover_modules_to_cover(project)

    for module_name in module_names:
        logger.debug("Module '%s' coverage to be verified", module_name)

    _delete_non_essential_modules()

    # Reimport self
    __import__("pybuilder.plugins.python")

    # Starting fresh
    from coverage import coverage as coverage_factory

    coverage = coverage_factory(cover_pylib=False, source=[source_tree_path])

    try:
        project.set_property('__running_coverage',
                             True)  # tell other plugins that we are not really unit testing right now
        _start_coverage(coverage)

        if shortest_plan:
            reactor.execute_task_shortest_plan(target_task)
        else:
            reactor.execute_task(target_task)
    finally:
        _stop_coverage(coverage)
        project.set_property('__running_coverage', False)

    coverage_too_low = False
    threshold = project.get_property("%s_threshold_warn" % execution_prefix)
    exceptions = project.get_property("%s_exceptions" % execution_prefix)

    report = {
        "module_names": []
    }

    sum_lines = 0
    sum_lines_not_covered = 0

    modules = []
    for module_name in module_names:
        try:
            module = sys.modules[module_name]
        except KeyError:
            logger.warn("Module '%s' was not imported by the covered tests", module_name)
            try:
                module = __import__(module_name)
            except SyntaxError as e:
                logger.warn("Coverage for module '%s' cannot be established - the module doesn't compile: %s",
                            module_name, e)
                continue

        modules.append(module)

        module_report_data = build_module_report(coverage, module)
        should_ignore_module = module_name in exceptions

        if not should_ignore_module:
            sum_lines += module_report_data[0]
            sum_lines_not_covered += module_report_data[2]

        module_report = {
            "module": module_name,
            "coverage": module_report_data[4],
            "sum_lines": module_report_data[0],
            "lines": module_report_data[1],
            "sum_lines_not_covered": module_report_data[2],
            "lines_not_covered": module_report_data[3],
        }

        logger.debug("Module coverage report: %s", module_report)
        report["module_names"].append(module_report)
        if module_report_data[4] < threshold:
            msg = "Test coverage below %2d%% for %s: %2d%%" % (threshold, module_name, module_report_data[4])
            if not should_ignore_module:
                logger.warn(msg)
                coverage_too_low = True
            else:
                logger.info(msg)

    if sum_lines == 0:
        overall_coverage = 0
    else:
        overall_coverage = (sum_lines - sum_lines_not_covered) * 100 / sum_lines
    report["overall_coverage"] = overall_coverage

    if overall_coverage < threshold:
        logger.warn("Overall %s is below %2d%%: %2d%%", execution_name, threshold, overall_coverage)
        coverage_too_low = True
    else:
        logger.info("Overall %s is %2d%%", execution_name, overall_coverage)

    project.write_report("%s.json" % execution_prefix, render_report(report))

    _write_summary_report(coverage, project, modules, execution_prefix)

    if coverage_too_low and project.get_property("%s_break_build" % execution_prefix):
        raise BuildFailedException("Test coverage for at least one module is below %d%%", threshold)


def _start_coverage(coverage):
    coverage.erase()
    coverage.start()


def _stop_coverage(coverage):
    coverage.stop()


def build_module_report(coverage, module):
    analysis_result = coverage.analysis(module)

    lines_total = len(analysis_result[1])
    lines_not_covered = len(analysis_result[2])
    lines_covered = lines_total - lines_not_covered

    if lines_total == 0:
        code_coverage = 100
    elif lines_covered == 0:
        code_coverage = 0
    else:
        code_coverage = lines_covered * 100 / lines_total

    return (lines_total, analysis_result[1],
            lines_not_covered, analysis_result[2],
            code_coverage)


def _write_summary_report(coverage, project, modules, execution_prefix):
    from coverage import CoverageException

    summary = StringIO()
    coverage.report(modules, file=summary)
    try:
        coverage.xml_report(outfile=project.expand_path("$dir_reports/%s.xml" % execution_prefix))
        coverage.save()
    except CoverageException:
        pass  # coverage raises when there is no data
    project.write_report(execution_prefix, summary.getvalue())
    summary.close()


def _discover_modules_to_cover(project):
    return discover_modules(project.expand_path("$dir_source_main_python"))


def _delete_non_essential_modules():
    sys_packages, sys_modules = _get_system_assets()
    for module_name in list(sys.modules.keys()):
        module = sys.modules[module_name]
        if module:
            if not _is_module_essential(module.__name__, sys_packages, sys_modules):
                _delete_module(module_name, module)


def _delete_module(module_name, module):
    del sys.modules[module_name]
    try:
        delattr(module, module_name)
    except AttributeError:
        pass


def _is_module_essential(module_name, sys_packages, sys_modules):
    if module_name in sys.builtin_module_names:
        return True

    if module_name in sys_modules:
        return True

    # Essential since we're in a fork for communicating exceptions back
    sys_packages.append("tblib")

    for package in sys_packages:
        if module_name == package or module_name.startswith(package + "."):
            return True

    return False


def _get_system_assets():
    """
    Returns all system packages and all modules that should not be touched during module deletion

    @return: tuple(packages, modules) to ignore
    """
    canon_sys_path = [os.path.realpath(package_dir) for package_dir in sys.path]
    std_lib = sysconfig.get_python_lib(standard_lib=True)
    canon_sys_path = [package_dir for package_dir in canon_sys_path if package_dir.startswith(std_lib)]

    packages = []
    package_dirs = []
    modules = []
    module_files = []
    for top, files, files in os.walk(std_lib):
        for nm in files:
            if nm == "__init__.py":
                init_file = os.path.join(top, nm)
                package_dirs.append(init_file[:-len("__init__.py") - len(os.sep)])
            elif nm[-3:] in (".so", ".py") or nm[-4:] in (".pyd", ".dll"):
                module_file = os.path.join(top, nm)
                module_files.append(module_file)

    for package_dir in package_dirs:
        for sys_path_dir in canon_sys_path:
            if package_dir.startswith(sys_path_dir):
                package_parts = package_dir[len(sys_path_dir) + len(os.sep):].split(os.sep)
                for idx, part in enumerate(package_parts):
                    if part not in packages:
                        if idx + 1 == len(package_parts):
                            packages.append(".".join(package_parts))
                        else:
                            break

    for module_file in module_files:
        module_dir = os.path.dirname(module_file)
        for sys_path_dir in canon_sys_path:
            if module_dir == sys_path_dir:
                modules.append(os.path.basename(module_file).split(".")[0])
                break

    return packages, modules
