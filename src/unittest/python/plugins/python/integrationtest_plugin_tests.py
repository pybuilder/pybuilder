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
try:
    from queue import Empty
except ImportError:
    from Queue import Empty

from mock import patch

from pybuilder.core import Project
from pybuilder.plugins.python.integrationtest_plugin import (
    TaskPoolProgress,
    add_additional_environment_keys,
    ConsumingQueue,
    init_test_source_directory
    )


class TaskPoolProgressTests(unittest.TestCase):

    def setUp(self):
        self.progress = TaskPoolProgress(42, 8)
        self.project = Project("basedir")

    def test_should_generate_command_abiding_to_configuration(self):

        expected_properties = {
            "dir_source_integrationtest_python": "src/integrationtest/python",
            "integrationtest_file_glob": "*_tests.py",
            "integrationtest_file_suffix": None,
            "integrationtest_additional_environment": {},
            "integrationtest_inherit_environment": False,
            "integrationtest_always_verbose": False
            }
        for property_name, property_value in expected_properties.items():
            self.project.set_property(property_name, property_value)

            init_test_source_directory(self.project)

        for property_name, property_value in expected_properties.items():
            self.assertEquals(

                self.project.get_property(property_name),
                property_value)

    def test_should_create_new_progress(self):
        self.assertEqual(self.progress.workers_count, 8)
        self.assertEqual(self.progress.finished_tasks_count, 0)
        self.assertEqual(self.progress.total_tasks_count, 42)

    def test_should_have_max_amount_of_tasks_running_when_limited_by_workers(self):
        self.assertEqual(self.progress.running_tasks_count, 8)

    def test_should_have_max_amount_of_tasks_running_when_limited_by_tasks(self):
        progress = TaskPoolProgress(2, 4)

        self.assertEqual(progress.running_tasks_count, 2)

    def test_should_have_max_amount_of_tasks_running_when_limited_by_tasks_after_updating(self):
        self.progress.update(40)

        self.assertEqual(self.progress.running_tasks_count, 2)

    def test_should_have_tasks_that_are_neither_running_nor_finished_as_waiting(self):
        self.assertEqual(self.progress.waiting_tasks_count, 42 - 8)

    def test_should_have_tasks_that_are_neither_running_nor_finished_as_waiting_after_updating(self):
        self.progress.update(2)

        self.assertEqual(self.progress.waiting_tasks_count, 40 - 8)

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
                         '[---ᗧ//|||]')

    @patch('pybuilder.plugins.python.integrationtest_plugin.styled_text')
    def test_should_not_render_pacman_when_finished(self, styled):
        styled.side_effect = lambda text, *styles: text
        progress = TaskPoolProgress(8, 2)
        progress.update(8)

        self.assertEqual(progress.render(),
                         '[--------] ')

    @patch('pybuilder.plugins.python.integrationtest_plugin.styled_text')
    @patch('pybuilder.plugins.python.integrationtest_plugin.print_text')
    @patch('pybuilder.plugins.python.integrationtest_plugin.TaskPoolProgress.can_be_displayed')
    def test_should_erase_previous_progress_on_subsequent_renders(self, _, print_text, styled):
        styled.side_effect = lambda text, *styles: text
        progress = TaskPoolProgress(8, 2)
        progress.update(2)

        progress.render_to_terminal()
        print_text.assert_called_with('[--ᗧ//||||]', flush=True)
        progress.render_to_terminal()
        print_text.assert_called_with(
            '\b' * (10 + len('ᗧ')) + '[--ᗧ//||||]', flush=True)


class IntegrationTestConfigurationTests(unittest.TestCase):

    def test_should_merge_additional_environment_into_current_one(self):
        project = Project('any-directory')
        project.set_property(
            'integrationtest_additional_environment', {'foo': 'bar'})
        environment = {'bar': 'baz'}

        add_additional_environment_keys(environment, project)

        self.assertEqual(environment,
                         {
                             'foo': 'bar',
                             'bar': 'baz'
                         })

    def test_should_override_current_environment_keys_with_additional_environment(self):
        project = Project('any-directory')
        project.set_property(
            'integrationtest_additional_environment', {'foo': 'mooh'})
        environment = {'foo': 'bar'}

        add_additional_environment_keys(environment, project)

        self.assertEqual(environment,
                         {
                             'foo': 'mooh'
                         })

    def test_should_fail_when_additional_environment_is_not_a_map(self):
        project = Project('any-directory')
        project.set_property(
            'integrationtest_additional_environment', 'meow')
        self.assertRaises(
            ValueError, add_additional_environment_keys, {}, project)


class ConsumingQueueTests(unittest.TestCase):

    @patch('pybuilder.plugins.python.integrationtest_plugin.ConsumingQueue.get_nowait')
    def test_should_consume_no_items_when_underlying_queue_empty(self, underlying_nowait_get):
        queue = ConsumingQueue()

        def empty_queue_get_nowait():
            raise Empty()

        underlying_nowait_get.side_effect = empty_queue_get_nowait

        queue.consume_available_items()

        self.assertEqual(queue.items, [])

    @patch('pybuilder.plugins.python.integrationtest_plugin.ConsumingQueue.get_nowait')
    def test_should_consume_one_item_when_underlying_queue_has_one(self, underlying_nowait_get):
        queue = ConsumingQueue()

        def empty_queue_get_nowait():
            yield "any-item"
            raise Empty()

        # generator, needs initialization!
        underlying_nowait_get.side_effect = empty_queue_get_nowait()

        queue.consume_available_items()

        self.assertEqual(queue.items, ['any-item'])

    @patch('pybuilder.plugins.python.integrationtest_plugin.ConsumingQueue.get_nowait')
    def test_should_consume_many_items_when_underlying_queue_has_them(self, underlying_nowait_get):
        queue = ConsumingQueue()

        def empty_queue_get_nowait():
            yield "any-item"
            yield "any-other-item"
            yield "some stuff"
            raise Empty()

        # generator, needs initialization!
        underlying_nowait_get.side_effect = empty_queue_get_nowait()

        queue.consume_available_items()

        self.assertEqual(queue.items, ['any-item',
                                       'any-other-item',
                                       'some stuff'])

    @patch('pybuilder.plugins.python.integrationtest_plugin.ConsumingQueue.get_nowait')
    def test_should_give_item_size_of_zero_when_underlying_queue_is_empty(self, underlying_nowait_get):
        queue = ConsumingQueue()

        def empty_queue_get_nowait():
            raise Empty()

        # not a generator, beware!!!!
        underlying_nowait_get.side_effect = empty_queue_get_nowait

        queue.consume_available_items()

        self.assertEqual(queue.size, 0)

    @patch('pybuilder.plugins.python.integrationtest_plugin.ConsumingQueue.get_nowait')
    def test_should_give_item_size_of_n_when_underlying_queue_has_n_elements(self, underlying_nowait_get):
        queue = ConsumingQueue()

        def empty_queue_get_nowait():
            yield 'first'
            yield 'second'
            yield 'third'
            raise Empty()

        # generator, needs initialization!
        underlying_nowait_get.side_effect = empty_queue_get_nowait()

        queue.consume_available_items()

        self.assertEqual(queue.size, 3)
