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
from mock import Mock, call, patch

from pybuilder.core import Project
from pybuilder.plugins.python.pyfix_unittest_plugin import init_test_source_directory


class InitTestSourceDirectoryTests(TestCase):

    @patch('pybuilder.plugins.python.pyfix_plugin_impl.execute_tests_matching')
    def test_should_set_pyfix_dependency(self, mock_execute_tests_matching):

        mock_project = Mock(Project)

        init_test_source_directory(mock_project)

        mock_project.build_depends_on.assert_called_with('pyfix')

    @patch('pybuilder.plugins.python.pyfix_plugin_impl.execute_tests_matching')
    def test_should_set_default_properties(self, mock_execute_tests_matching):

        mock_project = Mock(Project)

        init_test_source_directory(mock_project)

        self.assertEquals(mock_project.set_property_if_unset.call_args_list,
                          [call('dir_source_unittest_python', 'src/unittest/python'),
                           call('pyfix_unittest_module_glob', '*_pyfix_tests'),
                           call('pyfix_unittest_file_suffix', None)])
