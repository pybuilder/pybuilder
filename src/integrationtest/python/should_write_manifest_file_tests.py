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

from os.path import normcase as nc
from itest_support import IntegrationTestSupport


class Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file("""
from pybuilder.core import use_plugin, init

use_plugin('python.core')
use_plugin('python.distutils')

name = 'integration-test'
default_task = 'publish'

@init
def init (project):
    project.include_file('spam', 'eggs')
    project.install_file('spam_dir', 'more_spam')
    project.install_file('eggs_dir', 'more_eggs')
""")
        self.create_directory("src/main/python/spam")
        self.write_file("src/main/python/spam/eggs", "")
        self.write_file("src/main/python/more_spam", "")
        self.write_file("src/main/python/more_eggs", "")

        reactor = self.prepare_reactor()
        reactor.build()

        self.assert_directory_exists(
            "target/dist/integration-test-1.0.dev0")
        self.assert_directory_exists(
            "target/dist/integration-test-1.0.dev0/spam")
        self.assert_file_empty(
            "target/dist/integration-test-1.0.dev0/spam/eggs")
        self.assert_file_empty(
            "target/dist/integration-test-1.0.dev0/more_spam")
        self.assert_file_empty(
            "target/dist/integration-test-1.0.dev0/more_eggs")

        manifest_in = "target/dist/integration-test-1.0.dev0/MANIFEST.in"

        self.assert_file_exists(manifest_in)
        self.assert_file_permissions(0o664, manifest_in)
        self.assert_file_content(manifest_in, """include %s
include more_spam
include more_eggs
""" % nc("spam/eggs"))


if __name__ == "__main__":
    unittest.main()
