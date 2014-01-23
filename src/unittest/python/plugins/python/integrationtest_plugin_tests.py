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

from pybuilder.plugins.python.integrationtest_plugin import TaskPoolProgress


class TaskPoolProgressTests(unittest.TestCase):

    def setUp(self):
        self.progress = TaskPoolProgress(42, 8)

    def test_should_create_new_progress(self):
        self.assertEqual(self.progress.workers_count, 8)
        self.assertEqual(self.progress.finished_tasks_count, 0)
        self.assertEqual(self.progress.total_tasks_count, 42)

    def test_should_have_max_amount_of_tasks_running_when_limited_by_workers(self):
        self.assertEqual(self.progress.running_tests_count, 8)

    def test_should_have_max_amount_of_tasks_running_when_limited_by_tasks(self):
        progress = TaskPoolProgress(2, 4)

        self.assertEqual(progress.running_tests_count, 2)

    def test_should_have_max_amount_of_tasks_running_when_limited_by_tasks_after_updating(self):
        self.progress.update(40)

        self.assertEqual(self.progress.running_tests_count, 2)

    def test_should_have_tasks_that_are_neither_running_nor_finished_as_waiting(self):
        self.assertEqual(self.progress.waiting_tests_count, 42 - 8)

    def test_should_have_tasks_that_are_neither_running_nor_finished_as_waiting_after_updating(self):
        self.progress.update(2)

        self.assertEqual(self.progress.waiting_tests_count, 40 - 8)

    def test_should_not_be_finished_when_tasks_are_still_todo(self):
        self.assertFalse(self.progress.is_finished)

    def test_should_not_be_finished_when_tasks_are_still_running(self):
        progress = TaskPoolProgress(1, 1)

        self.assertFalse(progress.is_finished)

    def test_should_be_finished_when_all_tasks_are_finished(self):
        progress = TaskPoolProgress(1, 1)
        progress.update(1)

        self.assertTrue(progress.is_finished)

    @patch('pybuilder.plugins.python.integrationtest_plugin.sys.stdout')
    def test_should_be_displayed_when_tty_given(self, stdout):
        stdout.isatty.return_value = True

        self.assertTrue(self.progress.can_be_displayed)

    @patch('pybuilder.plugins.python.integrationtest_plugin.sys.stdout')
    def test_should_not_be_displayed_when_no_tty_given(self, stdout):
        stdout.isatty.return_value = False

        self.assertFalse(self.progress.can_be_displayed)

    @patch('pybuilder.plugins.python.integrationtest_plugin.styled_text')
    def test_should_render_progress(self, styled):
        styled.side_effect = lambda text, *styles: text
        progress = TaskPoolProgress(8, 2)
        progress.update(3)

        self.assertEqual(progress.render(),
                         '\r[---//|||]')
