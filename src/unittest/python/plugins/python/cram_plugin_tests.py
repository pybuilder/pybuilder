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

from mock import patch

from pybuilder.core import Project
from pybuilder.plugins.python.cram_plugin import (
    _command,
    _find_files,
    _report_file,

)


class CramPluginTests(unittest.TestCase):

    def test_command_respects_no_verbose(self):
        project = Project('.')
        project.set_property('verbose', False)
        expected = ['cram']
        received = _command(project)
        self.assertEquals(expected, received)

    def test_command_respects_verbose(self):
        project = Project('.')
        project.set_property('verbose', True)
        expected = ['cram', '--verbose']
        received = _command(project)
        self.assertEquals(expected, received)

    @patch('pybuilder.plugins.python.cram_plugin.discover_files_matching')
    def test_find_files(self, discover_mock):
        project = Project('.')
        project.set_property('dir_source_cmdlinetest', '/any/dir')
        expected = ['/any/dir/test.cram']
        discover_mock.return_value = expected
        received = _find_files(project)
        self.assertEquals(expected, received)
        discover_mock.assert_called_once_with('/any/dir', '*.cram')

    def test_report(self):
        project = Project('.')
        project.set_property('dir_reports', '/any/dir')
        expected = './any/dir/cram.err'
        received = _report_file(project)
        self.assertEquals(expected, received)
