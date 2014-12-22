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

import unittest

from mock import patch, Mock

from pybuilder.plugins.python.outdated_dependencies_plugin import (
    get_outdated_versions)


class OutdatedDependenciesTest(unittest.TestCase):

    @patch("pybuilder.plugins.python.outdated_dependencies_plugin.ListCommand")
    def test_should_return_no_outdated_version_when_no_versions_installed(self, list_command):
        list_command_instance = list_command.return_value
        list_command_instance.parse_args.return_value = ("values", "arguments")
        list_command_instance.find_packages_latests_versions.return_value = []

        outdated_versions = [version for version in get_outdated_versions()]

        self.assertEqual(outdated_versions, [])

    @patch("pybuilder.plugins.python.outdated_dependencies_plugin.ListCommand")
    def test_should_return_outdated_version(self, list_command):
        list_command_instance = list_command.return_value
        list_command_instance.parse_args.return_value = ("values", "arguments")
        outdated_dependency = Mock(parsed_version=3)
        fresh_dependency = (Mock(parsed_version=3))
        list_command_instance.find_packages_latests_versions.return_value = [
            (outdated_dependency, 5, 5), (fresh_dependency, 3, 3)]

        outdated_versions = [version for version in get_outdated_versions()]

        self.assertEqual(outdated_versions, [(outdated_dependency, 5)])
