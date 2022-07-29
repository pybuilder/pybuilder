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

import ast
import copy
from os.path import dirname, join

import sys

from pybuilder.core import init, use_plugin, task, depends, dependents, optional
from pybuilder.errors import BuildFailedException
from pybuilder.execution import ExecutionManager
from pybuilder.plugins.python._coverage_util import patch_coverage
from pybuilder.plugins.python.remote_tools.coverage_tool import CoverageTool
from pybuilder.python_utils import StringIO, IS_WIN
from pybuilder.utils import discover_module_files, discover_modules, render_report, as_list, jp, ap, nc

if IS_WIN:
    from fnmatch import fnmatch
else:
    from fnmatch import fnmatchcase as fnmatch

use_plugin("python.core")
use_plugin("analysis")


@init
def init_coverage_properties(project):
    project.plugin_depends_on("coverage", "~=6.0")

    # These settings are for aggregate coverage
    project.set_property_if_unset("coverage_threshold_warn", 70)
    project.set_property_if_unset("coverage_branch_threshold_warn", 0)
    project.set_property_if_unset("coverage_branch_partial_threshold_warn", 0)
    project.set_property_if_unset("coverage_break_build", True)
    project.set_property_if_unset("coverage_exceptions", [])
    project.set_property_if_unset("coverage_concurrency", ["thread"])
    project.set_property_if_unset("coverage_debug", [])
    project.set_property_if_unset("coverage_source_path", "$dir_source_main_python")
    project.set_property_if_unset("coverage_name", project.name.capitalize())

    project.set_property_if_unset("coverage_reset_modules", False)  # deprecated, unused
    project.set_property_if_unset("coverage_reload_modules", None)  # deprecated, unused
    project.set_property_if_unset("coverage_fork", None)  # deprecated, unused
    project.set_property_if_unset("coverage_allow_non_imported_modules", None)  # deprecated, unused

    # Extension points for plugins
    project.set_property_if_unset("_coverage_tasks", [])
    project.set_property_if_unset("_coverage_config_prefixes", {})

    # Plugin-private
    project.set_property("__covered_tasks", None)
    project.set_property("__coverage_config", None)


@task
def prepare(project, logger, reactor):
    em = reactor.execution_manager  # type: ExecutionManager

    if not em.is_task_in_current_execution_plan("coverage"):
        return

    covered_tasks = CoveredTask.covered_tasks(project, reactor)
    project.set_property("__covered_tasks", covered_tasks)

    logger.info("Requested coverage for tasks: %s", ", ".join(str(covered_task) for covered_task in covered_tasks))
    for covered_task in covered_tasks:
        if not em.is_task_in_current_execution_plan(covered_task.name):
            logger.info("Will not run coverage for %r as it's not in the current plan", covered_task)
            continue
        if not em.is_task_before_in_current_execution_plan(covered_task.name, "coverage"):
            raise BuildFailedException("Unable to run coverage for task %r when it's executed after 'coverage'",
                                       covered_task)

        config_prefix = covered_task.config_prefix

        project.set_property_if_unset("%scoverage_threshold_warn" % config_prefix, 70)
        project.set_property_if_unset("%scoverage_branch_threshold_warn" % config_prefix, 0)
        project.set_property_if_unset("%scoverage_branch_partial_threshold_warn" % config_prefix, 0)
        project.set_property_if_unset("%scoverage_break_build" % config_prefix, False)
        project.set_property_if_unset("%scoverage_concurrency" % config_prefix, ["thread"])
        project.set_property_if_unset("%scoverage_python_env" % config_prefix, "pybuilder")
        project.set_property_if_unset("%scoverage_name" % config_prefix, None)


@task
@depends("verify")
@dependents(optional("publish"))
def coverage(project, logger, reactor):
    em = reactor.execution_manager  # type: ExecutionManager

    source_path = nc(project.expand_path(project.get_property("coverage_source_path")))

    # Add a trailing / or \ if not present, for correct `coverage` path interpretation
    source_path = join(source_path, "")

    module_names = discover_modules(source_path)
    module_file_suffixes = discover_module_files(source_path)

    module_exceptions = as_list(project.get_property("coverage_exceptions"))
    module_names, module_files, omit_patterns = _filter_covered_modules(logger, module_names, module_file_suffixes,
                                                                        module_exceptions, source_path)

    for idx, module_name in enumerate(module_names):
        logger.debug("Module %r (file %r) coverage to be verified", module_name, module_files[idx])

    coverage_config = dict(data_file=project.expand_path("$dir_target", "%s.coverage" % project.name),
                           data_suffix=False,
                           cover_pylib=False,
                           config_file=False,
                           branch=True,
                           debug=as_list(project.get_property("coverage_debug")),
                           context=project.name)

    project.set_property("__coverage_config", coverage_config)

    patch_coverage()

    from coverage import coverage as coverage_factory

    cov = coverage_factory(**coverage_config)
    cov.erase()
    cov.save()

    for covered_task in project.get_property("__covered_tasks"):  # type: CoveredTask
        if em.is_task_in_current_execution_plan(covered_task.name):
            task_cov = run_coverage(project, logger, reactor,
                                    covered_task,
                                    source_path,
                                    module_names,
                                    module_files,
                                    omit_patterns)

            cov._data.update(task_cov._data)

    cov.save()

    failure = _build_coverage_report(project, logger, "%s coverage" % project.name, project.name, "", cov,
                                     source_path, module_names, module_files)

    if failure:
        raise failure


def run_coverage(project, logger, reactor, covered_task, source_path, module_names, module_files, omit_patterns):
    config_prefix = covered_task.config_prefix
    logger.info("Collecting coverage information for %r", str(covered_task))

    if project.get_property("%scoverage_fork" % config_prefix) is not None:
        logger.warn("%scoverage_fork is deprecated, coverage always runs in a spawned process", config_prefix)

    if project.get_property("%scoverage_reload_modules" % config_prefix) is not None:
        logger.warn("%scoverage_reload_modules is deprecated - modules are no longer reloaded", config_prefix)

    if project.get_property("%scoverage_reset_modules" % config_prefix) is not None:
        logger.warn("%scoverage_reset_modules is deprecated - modules are no longer reset", config_prefix)

    if project.get_property("%scoverage_allow_non_imported_modules" % config_prefix) is not None:
        logger.warn("%scoverage_allow_non_imported_modules- modules are no longer imported", config_prefix)

    if project.get_property("%scoverage_branch_threshold_warn" % config_prefix) == 0:
        logger.warn("%scoverage_branch_threshold_warn is 0 and branch coverage will not be checked", config_prefix)

    if project.get_property("%scoverage_branch_partial_threshold_warn" % config_prefix) == 0:
        logger.warn("%scoverage_branch_partial_threshold_warn is 0 and partial branch coverage will not be checked",
                    config_prefix)

    coverage_config = dict(data_file=project.expand_path("$dir_target", "%s.coverage" % covered_task.filename),
                           data_suffix=True,
                           cover_pylib=False,
                           config_file=False,
                           branch=True,
                           context=str(covered_task),
                           debug=as_list(project.get_property("%scoverage_debug" % config_prefix,
                                                              project.get_property("coverage_debug"))),
                           concurrency=project.get_property("%scoverage_concurrency" % config_prefix,
                                                            project.get_property("coverage_concurrency")))

    from coverage import coverage as coverage_factory

    cov = coverage_factory(**coverage_config)
    cov.erase()

    cov_tool = CoverageTool(source_path, omit_patterns, **coverage_config)

    em = reactor.execution_manager

    reactor.add_tool(cov_tool)
    try:
        coverage_env_name = project.get_property("%scoverage_python_env" % config_prefix)
        if coverage_env_name:
            current_python_env = reactor.python_env_registry[coverage_env_name]
            reactor.python_env_registry.push_override(coverage_env_name,
                                                      _override_python_env_for_coverage(current_python_env,
                                                                                        coverage_config,
                                                                                        source_path,
                                                                                        omit_patterns))
        try:
            em.execute_task(covered_task.task,
                            logger=logger,
                            project=project,
                            reactor=reactor,
                            _executable=covered_task.executable)
        finally:
            if coverage_env_name:
                reactor.python_env_registry.pop_override(coverage_env_name)
    finally:
        reactor.remove_tool(cov_tool)

    cov.combine()
    cov.save()

    failure = _build_coverage_report(project, logger,
                                     covered_task.coverage_name, covered_task.filename, config_prefix,
                                     cov, source_path, module_names, module_files)

    if failure:
        raise failure

    return cov


def _override_python_env_for_coverage(current_python_env, coverage_config, source_path, omit_patterns):
    import coverage as cov_module
    cov_parent_dir = ap(jp(dirname(cov_module.__file__), ".."))

    new_python_env = copy.copy(current_python_env)
    new_python_env.overwrite("executable", tuple(
        current_python_env.executable +
        [ap(jp(dirname(sys.modules[_override_python_env_for_coverage.__module__].__file__), "_coverage_shim.py")),
         repr({"cov_parent_dir": cov_parent_dir,
               "cov_kwargs": coverage_config,
               "cov_source_path": source_path,
               "cov_omit_patterns": omit_patterns,
               },
              )],
    ))
    return new_python_env


def _filter_covered_modules(logger, module_names, module_file_suffixes, modules_exceptions, source_path):
    result_module_names = []
    result_module_files = []
    omit_module_files = []
    module_files = []

    for idx, module_name in enumerate(module_names):
        module_file = nc(jp(source_path, module_file_suffixes[idx]))
        module_files.append(module_file)

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

        if not skip_module:
            with open(module_file, "rb") as f:
                try:
                    ast.parse(f.read(), module_file)
                except SyntaxError:
                    logger.warn("Unable to parse module %r (file %r) due to syntax error and will be excluded" % (
                        module_name, module_file))
                    skip_module = True

        if skip_module:
            logger.debug("Module %r (file %r) was excluded", module_name, module_file)
            omit_module_files.append(module_file)
        else:
            result_module_names.append(module_name)
            result_module_files.append(module_file)

    omit_module_files = _optimize_omit_module_files(module_files, omit_module_files)
    return result_module_names, result_module_files, omit_module_files


def _optimize_omit_module_files(module_files, omit_module_files):
    # This is a stupid implementation but given the number of entries it'll do (until it won't)

    omf_lookup = set(omit_module_files)
    result_omit = set()

    def has_modules_in_dir_not_omitted(od):
        for mf in module_files:
            if mf.startswith(od) and mf not in omf_lookup:
                return True

    for omit in omit_module_files:
        already_omitted = False
        for ro in result_omit:
            if fnmatch(omit, ro):
                already_omitted = True
                break
        if already_omitted:
            continue

        prev_omit = omit
        omit_dir = dirname(omit)
        while prev_omit != omit_dir:
            if has_modules_in_dir_not_omitted(omit_dir):
                result_omit.add(jp(prev_omit, "*") if prev_omit != omit else prev_omit)
                break
            prev_omit = omit_dir
            omit_dir = dirname(omit_dir)

    return sorted(result_omit)


def _build_module_report(cov, module_file):
    return ModuleCoverageReport(cov._analyze(module_file))


def _build_coverage_report(project, logger,
                           coverage_description, coverage_name, config_prefix,
                           cov, source_path, module_names, module_files):
    coverage_too_low = False
    branch_coverage_too_low = False
    branch_partial_coverage_too_low = False
    threshold = project.get_property("%scoverage_threshold_warn" % config_prefix)
    branch_threshold = project.get_property("%scoverage_branch_threshold_warn" % config_prefix)
    branch_partial_threshold = project.get_property("%scoverage_branch_partial_threshold_warn" % config_prefix)

    report = {
        "module_names": []
    }

    sum_lines = 0
    sum_lines_not_covered = 0
    sum_branches = 0
    sum_branches_missing = 0
    sum_branches_partial = 0

    from coverage import files
    old_relative_dir = files.RELATIVE_DIR
    files.RELATIVE_DIR = source_path
    try:
        for idx, module_name in enumerate(module_names):
            module_file = module_files[idx]
            module_report_data = _build_module_report(cov, module_file)

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
                msg = "Test coverage below %2d%% for %s: %2d%%" % (
                    threshold, module_name, module_report_data.code_coverage)
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
            logger.warn("Overall %s coverage is below %2d%%: %2d%%", coverage_name, threshold, overall_coverage)
            coverage_too_low = True
        else:
            logger.info("Overall %s coverage is %2d%%", coverage_name, overall_coverage)

        if overall_branch_coverage < branch_threshold:
            logger.warn("Overall %s branch coverage is below %2d%%: %2d%%", coverage_name, branch_threshold,
                        overall_branch_coverage)
            branch_coverage_too_low = True
        else:
            logger.info("Overall %s branch coverage is %2d%%", coverage_name, overall_branch_coverage)

        if overall_branch_partial_coverage < branch_partial_threshold:
            logger.warn("Overall %s partial branch coverage is below %2d%%: %2d%%", coverage_name,
                        branch_partial_threshold, overall_branch_partial_coverage)
            branch_partial_coverage_too_low = True
        else:
            logger.info("Overall %s partial branch coverage is %2d%%", coverage_name, overall_branch_partial_coverage)

        project.write_report("%s_coverage.json" % coverage_name, render_report(report))

        _write_summary_report(cov, project, module_names, module_files,
                              config_prefix, coverage_description, coverage_name)

        if coverage_too_low and project.get_property("%scoverage_break_build" % config_prefix):
            return BuildFailedException("Test coverage for at least one module is below %d%%", threshold)
        if branch_coverage_too_low and project.get_property("%scoverage_break_build" % config_prefix):
            return BuildFailedException("Test branch coverage for at least one module is below %d%%", branch_threshold)
        if branch_partial_coverage_too_low and project.get_property("%scoverage_break_build" % config_prefix):
            return BuildFailedException("Test partial branch coverage for at least one module is below %d%%",
                                        branch_partial_threshold)

    finally:
        files.RELATIVE_DIR = old_relative_dir


def _write_summary_report(cov, project, module_names, module_files, config_prefix, execution_description,
                          execution_name):
    from coverage import CoverageException

    summary = StringIO()
    try:
        cov.report(module_files, file=summary)
        try:
            cov.xml_report(module_files,
                           outfile=project.expand_path("$dir_reports", "%s_coverage.xml" % execution_name))
            cov.html_report(module_files,
                            directory=project.expand_path("$dir_reports", "%s_coverage_html" % execution_name),
                            title=execution_description)
        except CoverageException:
            pass  # coverage raises when there is no data
        project.write_report("%s_coverage" % execution_name, summary.getvalue())
    finally:
        summary.close()


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


class CoveredTask(object):
    def __init__(self, project, reactor, em, callable_):
        self.name = reactor.normalize_candidate_name(callable_)
        self.task = em.get_task(self.name)
        self.executable = self.task.executable(callable_)
        self.callable = callable_

        config_prefixes = project.get_property("_coverage_config_prefixes")
        if callable_ not in config_prefixes:
            raise BuildFailedException("Task %r in %r registered for coverage but did not specify its config prefix",
                                       self.name, self.executable.source)
        self.config_prefix = config_prefixes[callable_] + "_"
        self.filename = "%s.%s" % (self.executable.source, self.name)
        self.coverage_name = "%s coverage" % project.get_property("%scoverage_name" % self.config_prefix, self)

    @staticmethod
    def covered_tasks(project, reactor):
        em = reactor.execution_manager  # type: ExecutionManager

        return [CoveredTask(project, reactor, em, callable_) for callable_ in project.get_property("_coverage_tasks")]

    def __str__(self):
        return "%s:%s" % (self.executable.source, self.name)

    def __repr__(self):
        return "CoveredTask{name: %r, task: %r, executable: %r, config_prefix: %r, callable: %r}" % (self.name,
                                                                                                     self.task,
                                                                                                     self.executable,
                                                                                                     self.config_prefix,
                                                                                                     self.callable)
