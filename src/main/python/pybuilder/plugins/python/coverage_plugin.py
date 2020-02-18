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

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from pybuilder.core import init, use_plugin, task, depends, dependents, optional
from pybuilder.utils import discover_modules, render_report
from pybuilder.execution import ExecutionManager

from pybuilder.plugins.python.remote_tools.coverage_tool import CoverageTool
from pybuilder.errors import BuildFailedException

use_plugin("python.core")
use_plugin("analysis")


@init
def init_coverage_properties(project):
    project.plugin_depends_on("coverage", "~=5.0")

    project.set_property_if_unset("coverage_tasks", ["run_unit_tests"])
    project.set_property_if_unset("coverage_task_configs", {"run_unit_tests": "coverage"})

    for task_name in project.get_property("coverage_tasks"):
        execution_prefix = project.get_property("coverage_task_configs").get(task_name, task_name)

        project.set_property_if_unset("%s_threshold_warn" % execution_prefix, 70)
        project.set_property_if_unset("%s_branch_threshold_warn" % execution_prefix, 0)
        project.set_property_if_unset("%s_branch_partial_threshold_warn" % execution_prefix, 0)
        project.set_property_if_unset("%s_break_build" % execution_prefix, True)
        project.set_property_if_unset("%s_allow_non_imported_modules" % execution_prefix, True)
        project.set_property_if_unset("%s_exceptions" % execution_prefix, [])
        project.set_property_if_unset("%s_concurrency" % execution_prefix, ["thread"])

        project.set_property_if_unset("%s_reset_modules" % execution_prefix, False)  # deprecated, unused
        project.set_property_if_unset("%s_reload_modules" % execution_prefix, None)  # deprecated, unused
        project.set_property_if_unset("%s_fork" % execution_prefix, None)  # deprecated, unused


@task
def prepare(project, logger, reactor):
    em = reactor.execution_manager  # type: ExecutionManager

    if not em.is_task_in_current_execution_plan("coverage"):
        return

    task_names = [task_name for task_name in project.get_property("coverage_tasks")]
    logger.info("Requested coverage for tasks: %s", ",".join(task_names))
    for task_name in task_names:
        if not em.is_task_in_current_execution_plan(task_name):
            logger.info("Will not run coverage for '%s' as it's not in the current plan", task_name)
            continue
        if not em.is_task_before_in_current_execution_plan(task_name, "coverage"):
            raise BuildFailedException("Unable to run coverage for task '%s' if it isn't executed before 'coverage'",
                                       task_name)


@task
@depends("verify")
@dependents(optional("publish"))
def coverage(project, logger, reactor):
    em = reactor.execution_manager  # type: ExecutionManager

    task_configs = project.get_property("coverage_task_configs")

    for task_name in project.get_property("coverage_tasks"):
        if em.is_task_in_current_execution_plan(task_name):
            run_coverage(project, logger, reactor, task_configs.get(task_name, task_name),
                         "%s coverage" % task_name, task_name)


def run_coverage(project, logger, reactor, execution_prefix, execution_name, target_task):
    logger.info("Collecting coverage information for %r", target_task)

    if project.get_property("%s_fork" % execution_prefix) is not None:
        logger.warn(
            "%s_fork is deprecated, coverage always runs in a spawned process", execution_prefix)

    if project.get_property("%s_reload_modules" % execution_prefix) is not None:
        logger.warn(
            "%s_reload_modules is deprecated - modules are no longer reloaded", execution_prefix)

    if project.get_property("%s_reset_modules" % execution_prefix) is not None:
        logger.warn(
            "%s_reset_modules is deprecated - modules are no longer reset", execution_prefix)

    if project.get_property("%s_branch_threshold_warn" % execution_prefix) == 0:
        logger.warn("%s_branch_threshold_warn is 0 and branch coverage will not be checked", execution_prefix)

    if project.get_property("%s_branch_partial_threshold_warn" % execution_prefix) == 0:
        logger.warn("%s_branch_partial_threshold_warn is 0 and partial branch coverage will not be checked",
                    execution_prefix)

    source_tree_path = project.get_property("dir_source_main_python")
    allow_non_imported_modules = project.get_property("%s_allow_non_imported_modules" % execution_prefix)
    module_names = _discover_modules_to_cover(project)

    for module_name in module_names:
        logger.debug("Module '%s' coverage to be verified", module_name)

    coverage_config = dict(data_file=project.expand_path("$dir_target", "%s.coverage" % target_task),
                           data_suffix=True,
                           cover_pylib=False,
                           config_file=False,
                           branch=True,
                           source=[source_tree_path],
                           context=target_task,
                           concurrency=project.get_property("%s_concurrency"))

    from coverage import coverage as coverage_factory

    cov = coverage_factory(**coverage_config)
    cov.erase()

    cov_tool = CoverageTool(**coverage_config)

    reactor.add_tool(cov_tool)

    em = reactor.execution_manager

    task = em.get_task(target_task)

    import gc
    gc.collect()
    gc.disable()

    try:
        em.execute_task(task,
                        logger=logger,
                        project=project,
                        reactor=reactor)

        reactor.remove_tool(cov_tool)

        cov.combine()
        cov.load()

        module_exceptions = project.get_property("%s_exceptions" % execution_prefix)
        modules, non_imported_modules = _list_all_covered_modules(logger, module_names, module_exceptions,
                                                                  allow_non_imported_modules)

        failure = _build_coverage_report(project, logger, execution_name, execution_prefix, cov, modules)

    finally:
        gc.enable()

    if non_imported_modules and not allow_non_imported_modules:
        raise BuildFailedException("Some modules have not been imported and have no coverage")

    if failure:
        raise failure


def _list_all_covered_modules(logger, module_names, modules_exceptions, allow_non_imported_modules):
    modules = []
    non_imported_modules = []
    for module_name in module_names:
        skip_module = False
        for module_exception in modules_exceptions:
            if module_exception.endswith("*"):
                if module_name.startswith(module_exception[:-1]):
                    skip_module = True
                    break
            else:
                if module_name == module_exception:
                    skip_module = True
                    break

        if skip_module:
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


def _build_module_report(cov, module):
    return ModuleCoverageReport(cov._analyze(module))


def _build_coverage_report(project, logger, execution_name, execution_prefix, cov, modules):
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

        module_report_data = _build_module_report(cov, module)

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

    _write_summary_report(cov, project, modules, execution_prefix, execution_name)

    if coverage_too_low and project.get_property("%s_break_build" % execution_prefix):
        return BuildFailedException("Test coverage for at least one module is below %d%%", threshold)
    if branch_coverage_too_low and project.get_property("%s_break_build" % execution_prefix):
        return BuildFailedException("Test branch coverage for at least one module is below %d%%", branch_threshold)
    if branch_partial_coverage_too_low and project.get_property("%s_break_build" % execution_prefix):
        return BuildFailedException("Test partial branch coverage for at least one module is below %d%%",
                                    branch_partial_threshold)


def _write_summary_report(cov, project, modules, execution_prefix, execution_name):
    from coverage import CoverageException

    summary = StringIO()
    try:
        cov.report(modules, file=summary)
        try:
            cov.xml_report(modules, outfile=project.expand_path("$dir_reports/%s.xml" % execution_prefix))
            cov.html_report(modules, directory=project.expand_path("$dir_reports/%s_html" % execution_prefix),
                            title=execution_name)
            cov.save()
        except CoverageException:
            pass  # coverage raises when there is no data
        project.write_report(execution_prefix, summary.getvalue())
    finally:
        summary.close()


def _discover_modules_to_cover(project):
    return discover_modules(project.expand_path("$dir_source_main_python"))


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
