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
from test_utils import Mock, patch
from pybuilder.core import Project
from logging import Logger
from pybuilder.plugins.python.stdeb_plugin import (
    assert_py2dsc_deb_is_available,
    get_py2dsc_deb_command,
    assert_dpkg_is_available)


class CheckStdebAvailableTests(TestCase):

    @patch('pybuilder.plugins.python.stdeb_plugin.assert_can_execute')
    def test_should_check_that_py2dsc_deb_can_be_executed(self, mock_assert_can_execute):

        mock_logger = Mock(Logger)

        assert_py2dsc_deb_is_available(mock_logger)

        expected_command_line = ['py2dsc-deb', '-h']
        mock_assert_can_execute.assert_called_with(
            expected_command_line, 'py2dsc-deb', 'plugin python.stdeb')

    @patch('pybuilder.plugins.python.stdeb_plugin.assert_can_execute')
    def test_should_check_that_dpkg_buildpackage_can_be_executed(self, mock_assert_can_execute):

        mock_logger = Mock(Logger)

        assert_dpkg_is_available(mock_logger)

        expected_command_line = ['dpkg-buildpackage', '--help']
        mock_assert_can_execute.assert_called_with(
            expected_command_line, 'dpkg-buildpackage', 'plugin python.stdeb')


class StdebBuildCommandTests(TestCase):

    def setUp(self):
        self.project = Project("basedir")

    def test_should_generate_stdeb_build_command_with_project_properties(self):
        self.project.set_property(
            "deb_package_maintainer", "foo <foo@bar.com>")
        self.project.set_property("path_final_build", "/path/to/final/build")
        self.project.set_property("path_to_source_tarball", "/path/to/source/")

        py2dsc_deb_command = get_py2dsc_deb_command(self.project)

        self.assertEqual(
            py2dsc_deb_command, "py2dsc-deb --maintainer 'foo <foo@bar.com>' -d '/path/to/final/build' /path/to/source/")
