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

import unittest

from pybuilder.core import Project
from pybuilder.pluginhelper.external_command import ExternalCommandBuilder
from test_utils import Mock, patch, call, ANY


class ExternalCommandBuilderTests(unittest.TestCase):

    def setUp(self):
        self.project = Project('/base/dir')
        self.command = ExternalCommandBuilder('command-name', self.project)

    def test_should_only_use_command_name_by_default(self):
        self.assertEqual(self.command.as_string, 'command-name')

    def test_should_add_unconditional_argument_to_command(self):
        self.command.use_argument('--foo=bar')

        self.assertEqual(self.command.as_string, 'command-name --foo=bar')

    def test_should_add_conditional_argument_when_property_is_truthy(self):
        self.project.set_property('verbose', True)
        self.command.use_argument('--verbose').only_if_property_is_truthy('verbose')

        self.assertEqual(self.command.as_string, 'command-name --verbose')

    def test_should_not_add_conditional_argument_when_property_is_falsy(self):
        self.project.set_property('verbose', False)
        self.command.use_argument('--verbose').only_if_property_is_truthy('verbose')

        self.assertEqual(self.command.as_string, 'command-name')

    def test_should_add_conditional_argument_when_property_is_truthy_after_unconditional_argument(self):
        self.project.set_property('verbose', True)
        self.command.use_argument('--cool').use_argument('--verbose').only_if_property_is_truthy('verbose')

        self.assertEqual(self.command.as_string, 'command-name --cool --verbose')

    def test_should_not_add_conditional_argument_when_property_is_falsy_after_unconditional_argument(self):
        self.project.set_property('verbose', False)
        self.command.use_argument('--cool').use_argument('--verbose').only_if_property_is_truthy('verbose')

        self.assertEqual(self.command.as_string, 'command-name --cool')

    def test_should_format_unconditional_argument_with_property_when_given(self):
        self.project.set_property('name', 'value')
        self.command.use_argument('--name={0}').formatted_with_property('name')

        self.assertEqual(self.command.as_string, 'command-name --name=value')

    def test_should_format_unconditional_argument_with_value_when_given(self):
        self.command.use_argument('--name={0}').formatted_with('value')

        self.assertEqual(self.command.as_string, 'command-name --name=value')

    def test_should_include_conditional_argument_with_formatting_when_property_is_falsy(self):
        self.project.set_property('name', 'value')
        self.command.use_argument('--name={0}').formatted_with_property('name').only_if_property_is_truthy('name')

        self.assertEqual(self.command.as_string, 'command-name --name=value')

    def test_should_omit_conditional_argument_with_formatting_when_property_is_falsy(self):
        self.project.set_property('name', 'value')
        self.project.set_property('falsy', None)
        self.command.use_argument('--name={0}').formatted_with_property('name').only_if_property_is_truthy('falsy')

        self.assertEqual(self.command.as_string, 'command-name')

    def test_should_include_conditional_argument_with_truthy_formatting(self):
        self.project.set_property('name', 'value')
        self.command.use_argument('--name={0}').formatted_with_truthy_property('name')

        self.assertEqual(self.command.as_string, 'command-name --name=value')

    def test_should_omit_conditional_argument_with_falsy_formatting(self):
        self.project.set_property('name', None)
        self.command.use_argument('--name={0}').formatted_with_truthy_property('name')

        self.assertEqual(self.command.as_string, 'command-name')


class ExternalCommandExecutionTests(unittest.TestCase):

    def setUp(self):
        self.project = Project('/base/dir')
        self.command = ExternalCommandBuilder('command-name', self.project)
        self.command.use_argument('--foo').use_argument('--bar')

    @patch("pybuilder.pluginhelper.external_command.execute_command")
    @patch("pybuilder.pluginhelper.external_command.read_file")
    def test_should_execute_external_command(self, _, execute_command):
        self.command.run("any-outfile-name")

        execute_command.assert_called_with(
            ['command-name', '--foo', '--bar'],
            'any-outfile-name',
            env=ANY)

    @patch('pybuilder.pluginhelper.external_command.read_file')
    @patch('pybuilder.pluginhelper.external_command.execute_tool_on_source_files')
    def test_should_execute_external_command_on_production_source_files_dirs_only(self, execution, read):
        execution.return_value = 0, '/tmp/reports/command-name'
        logger = Mock()
        self.command.run_on_production_source_files(logger, include_dirs_only=True)

        execution.assert_called_with(
            include_dirs_only=True,
            include_test_sources=False,
            include_scripts=False,
            project=self.project,
            logger=logger,
            command_and_arguments=['command-name', '--foo', '--bar'],
            name='command-name')

    @patch('pybuilder.pluginhelper.external_command.read_file')
    @patch('pybuilder.pluginhelper.external_command.execute_tool_on_source_files')
    def test_should_execute_external_command_on_production_source_files(self, execution, read):
        execution.return_value = 0, '/tmp/reports/command-name'
        logger = Mock()
        self.command.run_on_production_source_files(logger)

        execution.assert_called_with(
            include_dirs_only=False,
            include_test_sources=False,
            include_scripts=False,
            project=self.project,
            logger=logger,
            command_and_arguments=['command-name', '--foo', '--bar'],
            name='command-name')

    @patch('pybuilder.pluginhelper.external_command.read_file')
    @patch('pybuilder.pluginhelper.external_command.execute_tool_on_source_files')
    def test_should_execute_external_command_on_production_and_test_source_files(self, execution, read):
        execution.return_value = 0, '/tmp/reports/command-name'
        logger = Mock()
        self.command.run_on_production_and_test_source_files(logger)

        execution.assert_called_with(
            include_dirs_only=False,
            include_test_sources=True,
            include_scripts=False,
            project=self.project,
            logger=logger,
            command_and_arguments=['command-name', '--foo', '--bar'],
            name='command-name')

    @patch('pybuilder.pluginhelper.external_command.read_file')
    @patch('pybuilder.pluginhelper.external_command.execute_tool_on_source_files')
    def test_should_execute_external_command_and_return_execution_result(self, execution, read):
        execution.return_value = 0, '/tmp/reports/command-name'
        read.side_effect = lambda argument: {
            '/tmp/reports/command-name': ['Running...', 'OK all done!'],
            '/tmp/reports/command-name.err': ['Oh no! I am not python8 compatible!', 'I will explode now.']
        }[argument]
        logger = Mock()

        result = self.command.run_on_production_source_files(logger)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.report_file, '/tmp/reports/command-name')
        self.assertEqual(read.call_args_list[0], call('/tmp/reports/command-name'))
        self.assertEqual(result.report_lines, ['Running...', 'OK all done!'])
        self.assertEqual(result.error_report_file, '/tmp/reports/command-name.err')
        self.assertEqual(read.call_args_list[1], call('/tmp/reports/command-name.err'))
        self.assertEqual(result.error_report_lines, ['Oh no! I am not python8 compatible!', 'I will explode now.'])
