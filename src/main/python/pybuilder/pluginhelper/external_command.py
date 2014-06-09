#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
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

from pybuilder.plugins.python.python_plugin_helper import execute_tool_on_source_files
from pybuilder.utils import read_file


class ExternalCommandResult(object):

    def __init__(self, exit_code, report_file, report_lines, error_report_file, error_report_lines):
        self.exit_code = exit_code
        self.report_file = report_file
        self.report_lines = report_lines
        self.error_report_file = error_report_file
        self.error_report_lines = error_report_lines


class ExternalCommandBuilder(object):

    def __init__(self, command_name, project):
        self.command_name = command_name
        self.parts = [command_name]
        self.project = project

    def use_argument(self, argument):
        self.parts.append(argument)
        return self

    def formatted_with_property(self, property_name):
        property_value = self.project.get_property(property_name)
        self.parts[-1] = self.parts[-1].format(property_value)
        return self

    def formatted_with_truthy_property(self, property_name):
        return self.formatted_with_property(property_name).only_if_property_is_truthy(property_name)

    def only_if_property_is_truthy(self, property_name):
        property_value = self.project.get_property(property_name)
        if not property_value:
            del self.parts[-1]
        return self

    @property
    def as_string(self):
        return ' '.join(self.parts)

    def run_on_production_source_files(self, logger, include_test_sources=False, include_scripts=False):
        execution_result = execute_tool_on_source_files(project=self.project,
                                                        name=self.command_name,
                                                        command_and_arguments=self.parts,
                                                        include_test_sources=include_test_sources,
                                                        include_scripts=include_scripts,
                                                        logger=logger)
        exit_code, report_file = execution_result
        report_lines = read_file(report_file)
        error_report_file = '{0}.err'.format(report_file)  # TODO @mriehl not dry, execute_tool... should return this
        error_report_lines = read_file(error_report_file)
        return ExternalCommandResult(exit_code, report_file, report_lines, error_report_file, error_report_lines)

    def run_on_production_and_test_source_files(self, logger):
        return self.run_on_production_source_files(logger, include_test_sources=True)

    def run_on_production_and_test_source_files_and_scripts(self, logger):
        return self.run_on_production_source_files(logger, include_test_sources=True, include_scripts=True)
