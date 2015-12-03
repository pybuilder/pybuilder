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

import os
import re

from pybuilder.core import use_plugin, after, init, task
from pybuilder.errors import BuildFailedException
from pybuilder.utils import assert_can_execute, read_file, render_report
from pybuilder.plugins.python.python_plugin_helper import execute_tool_on_modules


DEFAULT_PYCHECKER_ARGUMENTS = ["-Q"]
PYCHECKER_WARNING_PATTERN = re.compile(r'^(.+?):([0-9]+): (.+)$')


use_plugin("python.core")
use_plugin("analysis")


@init
def init_pychecker(project):

    project.plugin_depends_on("pychecker")
    project.set_property_if_unset("pychecker_break_build", True)
    project.set_property_if_unset("pychecker_break_build_threshold", 0)


@after("prepare")
def check_pychecker_available(logger):
    logger.debug("Checking availability of pychecker")
    assert_can_execute(("pychecker", ), "pychecker", "plugin python.pychecker")


def build_command_line(project):
    command_line = ["pychecker"]
    command_args = project.get_property("pychecker_args")

    if command_args:
        command_line += command_args
    else:
        command_line += DEFAULT_PYCHECKER_ARGUMENTS

    return command_line


@task("analyze")
def execute_pychecker(project, logger):
    command_line = build_command_line(project)
    logger.info("Executing pychecker on project sources: %s" % (' '.join(command_line)))

    _, report_file = execute_tool_on_modules(project, "pychecker", command_line, True)

    warnings = read_file(report_file)

    report = parse_pychecker_output(project, warnings)
    project.write_report("pychecker.json", render_report(report.to_json_dict()))

    if len(warnings) != 0:
        logger.warn("Found %d warning%s produced by pychecker. See %s for details.",
                    len(warnings),
                    "s" if len(warnings) != 1 else "",
                    report_file)

        threshold = project.get_property("pychecker_break_build_threshold")

        if project.get_property("pychecker_break_build") and len(warnings) > threshold:
            raise BuildFailedException("Found warnings produced by pychecker")


class PycheckerWarning(object):
    def __init__(self, message, line_number):
        self.message = message
        self.line_number = int(line_number)

    def to_json_dict(self):
        return {"message": self.message, "line_number": self.line_number}


class PycheckerModuleReport(object):
    def __init__(self, name):
        self.name = name
        self.warnings = []

    def add_warning(self, warning):
        self.warnings.append(warning)

    def to_json_dict(self):
        return {
            "name": self.name,
            "warnings": list(map(lambda w: w.to_json_dict(), self.warnings))
        }


class PycheckerReport(object):
    def __init__(self):
        self.module_reports = []

    def get_module_report(self, module):
        for module_report in self.module_reports:
            if module_report.name == module:
                return module_report

        module_report = PycheckerModuleReport(module)
        self.add_module_report(module_report)
        return module_report

    def add_module_report(self, module_report):
        self.module_reports.append(module_report)

    def to_json_dict(self):
        return {"modules": list(map(lambda m: m.to_json_dict(), self.module_reports))}


def parse_pychecker_output(project, warnings):
    report = PycheckerReport()

    sources_base_dir = project.expand_path("$dir_source_main_python")

    for warning in warnings:
        match = PYCHECKER_WARNING_PATTERN.match(warning)
        if not match:
            continue
        file_name = match.group(1)
        line_number = match.group(2)
        message = match.group(3)
        module = file_name.replace(sources_base_dir, "")[1:].replace(os.sep, ".")
        report.get_module_report(module).add_warning(PycheckerWarning(message, line_number))

    return report
