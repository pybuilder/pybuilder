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

import os
import shutil
import stat
import tempfile
import unittest

try:
    from StringIO import StringIO
except (ImportError) as e:
    from io import StringIO

from pybuilder.core import Logger
from pybuilder.cli import StdOutLogger
from pybuilder.execution import ExecutionManager
from pybuilder.reactor import Reactor


class IntegrationTestSupport(unittest.TestCase):
    def setUp(self):
        self.tmp_directory = tempfile.mkdtemp(prefix="IntegrationTestSupport")

    def tearDown(self):
        if self.tmp_directory and os.path.exists(self.tmp_directory):
            shutil.rmtree(self.tmp_directory)

    def full_path(self, name):
        parts = [self.tmp_directory] + name.split(os.sep)
        return os.path.join(*parts)

    def create_directory(self, name):
        os.makedirs(self.full_path(name))

    def write_file(self, name, *content):
        with open(self.full_path(name), "w") as file:
            file.writelines(content)

    def write_build_file(self, content):
        self.write_file("build.py", content)

    def assert_directory_exists(self, name):
        full_path = self.full_path(name)
        self.assertTrue(os.path.exists(full_path), msg="Directory does not exist: %s" % (full_path))
        self.assertTrue(os.path.isdir(full_path), msg="Not a directory: %s" % (full_path))

    def assert_file_does_not_exist(self, name):
        full_path = self.full_path(name)
        self.assertFalse(os.path.exists(full_path), msg="File should NOT exist: %s" % (full_path))

    def assert_file_exists(self, name):
        full_path = self.full_path(name)
        self.assertTrue(os.path.exists(full_path), msg="File does not exist: %s" % (full_path))
        self.assertTrue(os.path.isfile(full_path), msg="Not a file: %s" % (full_path))

    def assert_file_permissions(self, expected_permissions, name):
        full_path = self.full_path(name)
        actual_file_permissions = stat.S_IMODE(os.stat(full_path).st_mode)
        self.assertEqual(oct(expected_permissions), oct(actual_file_permissions))

    def assert_file_empty(self, name):
        self.assert_file_exists(name)
        full_path = self.full_path(name)
        self.assertEquals(0, os.path.getsize(full_path), msg="File %s is not empty." % (full_path))

    def assert_file_contains(self, name, expected_content_part):
        full_path = self.full_path(name)
        with open(full_path) as file:
            content = file.read()
            self.assertTrue(expected_content_part in content)

    def assert_file_content(self, name, expected_file_content):
        if expected_file_content == "":
            self.assert_file_empty(name)

        count_of_new_lines = expected_file_content.count("\n")

        if count_of_new_lines == 0:
            expected_lines = 1
        else:
            expected_lines = count_of_new_lines

        expected_content = StringIO(expected_file_content)
        actual_line_number = 0

        full_path = self.full_path(name)
        with open(full_path) as file:
            for actual_line in file:
                actual_line_number += 1
                actual_line_showing_escaped_new_line = actual_line.replace("\n", "\\n")

                expected_line = expected_content.readline()
                expected_line_showing_escaped_new_line = expected_line.replace("\n", "\\n")

                message = 'line {0} is not as expected.\n   expected: "{1}"\n    but got: "{2}"'.format(
                    actual_line_number, expected_line_showing_escaped_new_line, actual_line_showing_escaped_new_line)
                self.assertEquals(expected_line, actual_line, message)

        self.assertEqual(expected_lines, actual_line_number)

    def prepare_reactor(self):
        logger = StdOutLogger(threshold=Logger.DEBUG)
        execution_manager = ExecutionManager(logger)
        reactor = Reactor(logger, execution_manager)
        reactor.prepare_build(project_directory=self.tmp_directory)
        return reactor
