#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import unittest

from pybuilder.testutils import assert_is_not_locally_installed
from mock import patch, Mock

class PipPackagesTests(unittest.TestCase):

    @patch('pybuilder.testutils.pip.get_installed_distributions')
    def test_should_not_raise_error_when_package_is_not_locally_installed(self, installed):
        package_1 = Mock()
        package_1.project_name = 'any-package-other-than-foobar'
        installed.return_value = [package_1]
        assert_is_not_locally_installed('foobar')

    @patch('pybuilder.testutils.pip.get_installed_distributions')
    def test_should_raise_error_when_package_is_locally_installed(self, installed):
        package_1 = Mock()
        package_1.project_name = 'any-package-other-than-foobar'
        package_2 = Mock()
        package_2.project_name = 'foobar'
        installed.return_value = [package_1, package_2]

        self.assertRaises(AssertionError, assert_is_not_locally_installed, 'foobar')
