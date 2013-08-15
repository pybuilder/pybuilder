#  This file is part of PyBuilder
#
#  Copyright 2011-2013 PyBuilder Team
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
from pybuilder.core import Project
from pybuilder.plugins.ronn_manpage_plugin import build_generate_manpages_command


class RonnManpagePluginTests(unittest.TestCase):

    def test_should_generate_command_abiding_to_configuration(self):
        project = Project('egg')
        project.set_property("dir_manpages", "docs/man")
        project.set_property("manpage_source", "README.md")
        project.set_property("manpage_section", 1)

        self.assertEqual(build_generate_manpages_command(project), 'ronn -r --pipe README.md | gzip -9 > docs/man/egg.1.gz')
