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
from pybuilder.utils import discover_modules, render_report, fork_process, is_windows
from pybuilder.coverage_utils import patch_multiprocessing, reverse_patch_multiprocessing
from pybuilder.errors import BuildFailedException

use_plugin("python.core")
use_plugin("analysis")


@init
def init_coverage_properties(project):
    project.plugin_depends_on("coverage", "~=4.5")

    project.set_property_if_unset("coverage_threshold_warn", 70)
    project.set_property_if_unset("coverage_branch_threshold_warn", 0)
    project.set_property_if_unset("coverage_branch_partial_threshold_warn", 0)
    project.set_property_if_unset("coverage_break_build", True)
    project.set_property_if_unset("coverage_allow_non_imported_modules", True)
    project.set_property_if_unset("coverage_reload_modules", None)  # deprecated, unused
    project.set_property_if_unset("coverage_reset_modules", False)
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

    if project.get_property("%s_branch_threshold_warn" % execution_prefix) == 0:
        logger.warn("%s_branch_threshold_warn is 0 and branch coverage will not be checked", execution_prefix)

    if project.get_property("%s_branch_partial_threshold_warn" % execution_prefix) == 0:
        logger.warn("%s_branch_partial_threshold_warn is 0 and partial branch coverage will not be checked",
                    execution_prefix)

    logger.debug("Forking process to do %s analysis", execution_name)
    exit_code, _ = fork_process(logger,
                                target=do_coverage,
                                args=(project, logger, reactor, execution_prefix, execution_name, target_task,
                                      shortest_plan))

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
    reset_modules = project.get_property("%s_reset_modules" % execution_prefix)
    allow_non_imported_modules = project.get_property("%s_allow_non_imported_modules" % execution_prefix)
    module_names = _discover_modules_to_cover(project)

    for module_name in module_names:
        logger.debug("Module '%s' coverage to be verified", module_name)

    if reset_modules and not is_windows():
        _delete_non_essential_modules()
        __import__("pybuilder.plugins.python")  # Reimport self

    # Starting fresh
    from coverage import coverage as coverage_factory

    coverage = coverage_factory(cover_pylib=False, branch=True, source=[source_tree_path])

    patch_multiprocessing(coverage.config)
    try:
        try:
            _start_coverage(project, coverage)

            if shortest_plan:
                reactor.execute_task_shortest_plan(target_task)
            else:
                reactor.execute_task(target_task)
        finally:
            _stop_coverage(project, coverage)
    finally:
        reverse_patch_multiprocessing()

    module_exceptions = project.get_property("%s_exceptions" % execution_prefix)
    modules, non_imported_modules = _list_all_covered_modules(logger, module_names, module_exceptions,
                                                              allow_non_imported_modules)

    failure = _build_coverage_report(project, logger, execution_name, execution_prefix, coverage, modules)

    if non_imported_modules and not allow_non_imported_modules:
        raise BuildFailedException("Some modules have not been imported and have no coverage")

    if failure:
        raise failure


def _start_coverage(project, coverage):
    project.set_property('__running_coverage',
                         True)  # tell other plugins that we are not really unit testing right now
    coverage.erase()
    coverage.start()


def _stop_coverage(project, coverage):
    coverage.stop()
    project.set_property('__running_coverage', False)
    coverage.combine()


def _list_all_covered_modules(logger, module_names, modules_exceptions, allow_non_imported_modules):
    modules = []
    non_imported_modules = []
    for module_name in module_names:
        if module_name in modules_exceptions:
            logger.debug("Module '%s' was excluded", module_name)
            continue
        try:
            module = sys.modules[module_name]
        except KeyError:
            non_imported_modules.append(module_name)
            if allow_non_imported_modules:
                logger_func = logger.warn
            else:
                logger_func = logger.error

            logger_func("Module '%s' was not imported by the covered tests", module_name)
            try:
                module = __import__(module_name)
            except SyntaxError as e:
                logger.warn("Coverage for module '%s' cannot be established - syntax error: %s", module_name, e)
                continue
            except Exception as e:
                logger.warn("Coverage for module '%s' cannot be established - module failed: %s", module_name, e)
                continue

        if module not in modules and hasattr(module, "__file__"):
            modules.append(module)
    return modules, non_imported_modules


def _build_module_report(coverage, module):
    return ModuleCoverageReport(coverage._analyze(module))


def _build_coverage_report(project, logger, execution_name, execution_prefix, coverage, modules):
    coverage_too_low = False
    branch_coverage_too_low = False
    branch_partial_coverage_too_low = False
    threshold = project.get_property("%s_threshold_warn" % execution_prefix)
    branch_threshold = project.get_property("%s_branch_threshold_warn" % execution_prefix)
    branch_partial_threshold = project.get_property("%s_branch_partial_threshold_warn" % execution_prefix)

    report = {
        "module_names": []
    }

    sum_lines = 0
    sum_lines_not_covered = 0
    sum_branches = 0
    sum_branches_missing = 0
    sum_branches_partial = 0

    for module in modules:
        module_name = module.__name__

        module_report_data = _build_module_report(coverage, module)

        sum_lines += module_report_data.n_lines_total
        sum_lines_not_covered += module_report_data.n_lines_missing
        sum_branches += module_report_data.n_branches
        sum_branches_missing += module_report_data.n_branches_missing
        sum_branches_partial += module_report_data.n_branches_partial

        module_report = {
            "module": module_name,
            "coverage": module_report_data.code_coverage,
            "sum_lines": module_report_data.n_lines_total,
            "lines": module_report_data.lines_total,
            "sum_lines_not_covered": module_report_data.n_lines_missing,
            "lines_not_covered": module_report_data.lines_missing,
            "branches": module_report_data.n_branches,
            "branches_partial": module_report_data.n_branches_partial,
            "branches_missing": module_report_data.n_branches_missing
        }

        logger.debug("Module coverage report: %s", module_report)
        report["module_names"].append(module_report)
        if module_report_data.code_coverage < threshold:
            msg = "Test coverage below %2d%% for %s: %2d%%" % (threshold, module_name, module_report_data.code_coverage)
            logger.warn(msg)
            coverage_too_low = True
        if module_report_data.branch_coverage < branch_threshold:
            msg = "Branch coverage below %2d%% for %s: %2d%%" % (
                branch_threshold, module_name, module_report_data.branch_coverage)
            logger.warn(msg)
            branch_coverage_too_low = True

        if module_report_data.branch_partial_coverage < branch_partial_threshold:
            msg = "Partial branch coverage below %2d%% for %s: %2d%%" % (
                branch_partial_threshold, module_name, module_report_data.branch_partial_coverage)
            logger.warn(msg)
            branch_partial_coverage_too_low = True

    if sum_lines == 0:
        overall_coverage = 100
    else:
        overall_coverage = (sum_lines - sum_lines_not_covered) * 100 / sum_lines

    if sum_branches == 0:
        overall_branch_coverage = 100
        overall_branch_partial_coverage = 100
    else:
        overall_branch_coverage = (sum_branches - sum_branches_missing) * 100 / sum_branches
        overall_branch_partial_coverage = (sum_branches - sum_branches_partial) * 100 / sum_branches

    report["overall_coverage"] = overall_coverage
    report["overall_branch_coverage"] = overall_branch_coverage
    report["overall_branch_partial_coverage"] = overall_branch_partial_coverage

    if overall_coverage < threshold:
        logger.warn("Overall %s is below %2d%%: %2d%%", execution_name, threshold, overall_coverage)
        coverage_too_low = True
    else:
        logger.info("Overall %s is %2d%%", execution_name, overall_coverage)

    if overall_branch_coverage < branch_threshold:
        logger.warn("Overall %s branch coverage is below %2d%%: %2d%%", execution_name, branch_threshold,
                    overall_branch_coverage)
        branch_coverage_too_low = True
    else:
        logger.info("Overall %s branch coverage is %2d%%", execution_name, overall_branch_coverage)

    if overall_branch_partial_coverage < branch_partial_threshold:
        logger.warn("Overall %s partial branch coverage is below %2d%%: %2d%%", execution_name,
                    branch_partial_threshold, overall_branch_partial_coverage)
        branch_partial_coverage_too_low = True
    else:
        logger.info("Overall %s partial branch coverage is %2d%%", execution_name, overall_branch_partial_coverage)

    project.write_report("%s.json" % execution_prefix, render_report(report))

    _write_summary_report(coverage, project, modules, execution_prefix, execution_name)

    if coverage_too_low and project.get_property("%s_break_build" % execution_prefix):
        return BuildFailedException("Test coverage for at least one module is below %d%%", threshold)
    if branch_coverage_too_low and project.get_property("%s_break_build" % execution_prefix):
        return BuildFailedException("Test branch coverage for at least one module is below %d%%", branch_threshold)
    if branch_partial_coverage_too_low and project.get_property("%s_break_build" % execution_prefix):
        return BuildFailedException("Test partial branch coverage for at least one module is below %d%%",
                                    branch_partial_threshold)


def _write_summary_report(coverage, project, modules, execution_prefix, execution_name):
    from coverage import CoverageException

    summary = StringIO()
    try:
        coverage.report(modules, file=summary)
        try:
            coverage.xml_report(modules, outfile=project.expand_path("$dir_reports/%s.xml" % execution_prefix))
            coverage.html_report(modules, directory=project.expand_path("$dir_reports/%s_html" % execution_prefix),
                                 title=execution_name)
            coverage.save()
        except CoverageException:
            pass  # coverage raises when there is no data
        project.write_report(execution_prefix, summary.getvalue())
    finally:
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

    # Issue 523: Coverage 4.4.2 breaks without this
    if module_name == "__main__":
        return True

    # Essential since we're in a fork for communicating exceptions back
    sys_packages.append("tblib")
    sys_packages.append("pybuilder.errors")

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
    std_lib = os.path.realpath(sysconfig.get_python_lib(standard_lib=True))
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
            elif nm[-3:] in (".so", ".py") or nm[-4:] in (".pyd", ".dll", ".pyw") or nm[-2:] == ".o":
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
                module_name_parts = os.path.basename(module_file).split(".")
                module_name = module_name_parts[0]
                if module_name_parts[1] in ("so", "dll", "o") and module_name_parts[0].endswith("module"):
                    module_name = module_name[:-6]
                modules.append(module_name)
                break

    return packages, modules


class ModuleCoverageReport(object):
    def __init__(self, coverage_analysis):
        self.lines_total = sorted(coverage_analysis.statements)
        self.lines_excluded = sorted(coverage_analysis.excluded)
        self.lines_missing = sorted(coverage_analysis.missing)
        numbers = coverage_analysis.numbers
        self.n_lines_total = numbers.n_statements
        self.n_lines_excluded = numbers.n_excluded
        self.n_lines_missing = numbers.n_missing
        self.n_lines_covered = self.n_lines_total - self.n_lines_missing
        self.n_branches = numbers.n_branches
        self.n_branches_partial = numbers.n_partial_branches
        self.n_branches_missing = numbers.n_missing_branches
        self.n_branches_covered = self.n_branches - self.n_branches_missing
        self.n_branches_partial_covered = self.n_branches - self.n_branches_partial

        if self.n_lines_total == 0:
            self.code_coverage = 100
        else:
            self.code_coverage = self.n_lines_covered * 100 / self.n_lines_total

        if self.n_branches == 0:
            self.branch_coverage = 100
            self.branch_partial_coverage = 100
        else:
            self.branch_coverage = self.n_branches_covered * 100 / self.n_branches
            self.branch_partial_coverage = self.n_branches_partial_covered * 100 / self.n_branches
