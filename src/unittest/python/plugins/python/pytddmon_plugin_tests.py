#   This file is part of PyBuilder
#
#   Copyright 2011-2013 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import unittest
from mock import Mock, patch, ANY

from pybuilder.core import Project
from pybuilder.plugins.python import pytddmon_plugin


class PytddmonPluginTests(unittest.TestCase):

    @patch('pybuilder.plugins.python.pytddmon_plugin.subprocess')
    def test_should_run_pytddmon(self, subprocess):
        subprocess.check_output.side_effect = lambda *args, **kwargs: ' '.join(a for a in args)
        project = Project('/path/to/project', name='pybuilder')
        project.set_property('dir_source_main_python', 'path/to/source')
        project.set_property(
            'dir_source_unittest_python', 'src/unittest/python')

        pytddmon_plugin.pytddmon(project, Mock())

        subprocess.Popen.assert_called_with(
            ['which python', 'which pytddmon.py'], shell=False, cwd='src/unittest/python', env=ANY)
