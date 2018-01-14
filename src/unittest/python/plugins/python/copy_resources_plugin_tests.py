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

import unittest

from pybuilder.core import Project
from pybuilder.plugins.copy_resources_plugin import package, copy_resource
from test_utils import Mock, patch, ANY


class CopyResourcesTest(unittest.TestCase):
    def setUp(self):
        self.project = Project("basedir")
        self.project.name = 'copy-resources'
        self.project.version = '1.2.3'

    @patch("pybuilder.plugins.copy_resources_plugin.apply_on_files")
    def test_copy_resources_placeholders(self, apply_on_files):

        self.project.set_property("copy_resources_target", "/some/dir/${name}")
        self.project.set_property("copy_resources_glob", ['path1/${name}', 'path2/${version}'])

        package(self.project, Mock())
        apply_on_files.assert_called_with(
            ANY,
            ANY,
            ['path1/copy-resources', 'path2/1.2.3'],
            'basedir/some/dir/copy-resources',
            ANY)

    @patch("pybuilder.plugins.copy_resources_plugin.shutil.copy")
    @patch("pybuilder.plugins.copy_resources_plugin.os.path.exists", return_value=True)
    def test_copy_resources_copy_resource(self, exists, copy):
        copy_resource('/path/absolute_file_name', 'relative_file_name', 'target', Mock())
        target_path = 'target/relative_file_name'
        copy.assert_called_with('/path/absolute_file_name', target_path)
