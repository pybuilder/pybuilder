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

from unittest import TestCase

from pybuilder.core import Project
from pybuilder.plugins.python.pytest_plugin import initialize_pytest_plugin
from test_utils import Mock


class PytestPluginInitializationTests(TestCase):
    def setUp(self):
        self.project = Project("basedir")

    def test_should_set_dependency(self):
        mock_project = Mock(Project)
        initialize_pytest_plugin(mock_project)
        mock_project.plugin_depends_on.assert_called_with('pytest')

    def test_should_set_default_values_when_initializing_plugin(self):
        initialize_pytest_plugin(self.project)

        self.assertEquals(
            self.project.get_property("dir_source_pytest_python"), "src/unittest/python")
        self.assertEquals(
            self.project.get_property("pytest_report_file"), "target/reports/junit.xml")
        self.assertEquals(
            self.project.get_property("pytest_extra_args"), [])

    def test_should_leave_user_specified_properties_when_initializing_plugin(self):

        expected_properties = {
            "dir_source_pytest_python": "source_dir",
            "pytest_report_file": "output_dir/report_file",
            "pytest_extra_args": ['-a']
        }

        for property_name, property_value in expected_properties.items():
            self.project.set_property(property_name, property_value)

        initialize_pytest_plugin(self.project)

        for property_name, property_value in expected_properties.items():
            self.assertEquals(
                self.project.get_property(property_name),
                property_value)


# PyByuilder build dependency on pytest was removed by PyBuilder developers' request:
# https://github.com/pybuilder/pybuilder/pull/448#discussion_r93954475
# So we need to disable next tests and decrease % coverage.
# This functionality is covered by next integreation test:
# should_correctly_pass_failure_pytest_plugin_tests
# should_run_pytest_plugin_tests
#
# class PytestPluginAssertAvailableTests(TestCase):
#     def setUp(self):
#         self.project = Project("basedir")
#
#     @patch('pytest.__version__')
#     def test_should_assert_available(self, pytest_version):
#         logger_mock = Mock()
#         assert_pytest_available(logger_mock)
#         self.assertEqual(logger_mock.debug.call_count, 2)
#
#
# class PytestPluginRunTests(TestCase):
#     def setUp(self):
#         self.project = Project("basedir")
#         self.project.set_property('verbose', True)
#         self.project.set_property('dir_source_main_python', 'src')
#         initialize_pytest_plugin(self.project)
#
#     @patch('pytest.main', return_value=None)
#     def test_should_call_pytest_main_with_arguments(self, main):
#         run_unit_tests(self.project, Mock())
#         main.assert_called_with(['basedir/src/unittest/python', '-s', '-v', '--junit-xml',
#                                  'basedir/target/reports/junit.xml'])
#
#     @patch('pytest.main', return_value=1)
#     def test_should_raise_if_pytest_return_code(self, main):
#         self.assertRaises(
#             BuildFailedException,
#             run_unit_tests,
#             self.project,
#             Mock()
#             )
