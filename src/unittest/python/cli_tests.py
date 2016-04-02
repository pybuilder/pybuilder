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

import pybuilder
from pybuilder.cli import (parse_options,
                           ColoredStdOutLogger,
                           CommandLineUsageException,
                           StdOutLogger,
                           length_of_longest_string,
                           print_list_of_tasks)
from pybuilder.core import Logger

from fluentmock import when, verify, Mock, ANY_STRING, UnitTests


class TaskListTests(UnitTests):

    def set_up(self):
        def __eq__(self, other):
            return False

        def __ne__(self, other):
            return not self.__eq__(other)

        def __lt__(self, other):
            return False

        self.mock_reactor = Mock()
        self.mock_reactor.project.name = "any-project-name"
        self.task_1 = Mock()
        self.task_1.__eq__ = __eq__
        self.task_1.__ne__ = __ne__
        self.task_1.__lt__ = __lt__
        self.task_1.name = "task-1"
        self.task_1.description = ""
        self.task_1.dependencies = []
        self.task_2 = Mock()
        self.task_2.__eq__ = __eq__
        self.task_2.__ne__ = __ne__
        self.task_2.__lt__ = __lt__
        self.task_2.name = "task-2"
        self.task_2.description = ""
        self.task_2.dependencies = []
        when(self.mock_reactor).get_tasks().then_return([self.task_1,
                                                         self.task_2])
        when(pybuilder.cli).print_text_line(ANY_STRING).then_return(None)

    def test_should_render_minimal_task_list_when_in_quiet_mode(self):
        print_list_of_tasks(self.mock_reactor, quiet=True)

        verify(pybuilder.cli).print_text_line('task-1:<no description available>\ntask-2:<no description available>')

    def test_should_render_verbose_task_list_without_descriptions_and_dependencies(self):
        print_list_of_tasks(self.mock_reactor, quiet=False)

        verify(pybuilder.cli).print_text_line('Tasks found for project "any-project-name":')
        verify(pybuilder.cli).print_text_line('    task-1 - <no description available>')
        verify(pybuilder.cli).print_text_line('    task-2 - <no description available>')

    def test_should_render_verbose_task_list_with_dependencies(self):
        self.task_1.dependencies = ["any-dependency", "any-other-dependency"]

        print_list_of_tasks(self.mock_reactor, quiet=False)

        verify(pybuilder.cli).print_text_line('Tasks found for project "any-project-name":')
        verify(pybuilder.cli).print_text_line('    task-1 - <no description available>')
        verify(pybuilder.cli).print_text_line('             depends on tasks: any-dependency any-other-dependency')
        verify(pybuilder.cli).print_text_line('    task-2 - <no description available>')

    def test_should_render_verbose_task_list_with_descriptions(self):
        self.task_1.description = ["any", "description", "for", "task", "1"]
        self.task_2.description = ["any", "description", "for", "task", "2"]

        print_list_of_tasks(self.mock_reactor, quiet=False)

        verify(pybuilder.cli).print_text_line('Tasks found for project "any-project-name":')
        verify(pybuilder.cli).print_text_line('    task-1 - anydescriptionfortask1')
        verify(pybuilder.cli).print_text_line('    task-2 - anydescriptionfortask2')


class StdOutLoggerTest(unittest.TestCase):

    def setUp(self):
        self.stdout_logger = StdOutLogger(Logger)

    def test_should_return_debug_message_when_debug_level_given(self):
        actual_message = self.stdout_logger._level_to_string(Logger.DEBUG)
        self.assertEqual(actual_message, "[DEBUG]")

    def test_should_return_info_message_when_info_level_given(self):
        actual_message = self.stdout_logger._level_to_string(Logger.INFO)
        self.assertEqual(actual_message, "[INFO] ")

    def test_should_return_warning_message_when_warning_level_given(self):
        actual_message = self.stdout_logger._level_to_string(Logger.WARN)
        self.assertEqual(actual_message, "[WARN] ")

    def test_should_return_error_message_when_any_not_defined_level_given(self):
        actual_message = self.stdout_logger._level_to_string(-1)
        self.assertEqual(actual_message, "[ERROR]")


class ColoredStdOutLoggerTest(unittest.TestCase):

    def setUp(self):
        self.colored_stdout_logger = ColoredStdOutLogger(Logger)

    def test_should_return_italic_debug_message_when_debug_level_given(self):
        actual_message = self.colored_stdout_logger._level_to_string(Logger.DEBUG)
        self.assertEqual(actual_message, "\x1b[2m[DEBUG]\x1b[0;0m")

    def test_should_return_bold_info_message_when_info_level_given(self):
        actual_message = self.colored_stdout_logger._level_to_string(Logger.INFO)
        self.assertEqual(actual_message, "\x1b[1m[INFO] \x1b[0;0m")

    def test_should_return_brown_and_bold_warning_message_when_warning_level_given(self):
        actual_message = self.colored_stdout_logger._level_to_string(Logger.WARN)
        self.assertEqual(actual_message, "\x1b[1;33m[WARN] \x1b[0;0m")

    def test_should_return_bold_and_red_error_message_when_any_not_defined_level_given(self):
        actual_message = self.colored_stdout_logger._level_to_string(-1)
        self.assertEqual(actual_message, "\x1b[1;31m[ERROR]\x1b[0;0m")


class ParseOptionsTest(unittest.TestCase):

    def assert_options(self, options, **overrides):
        self.assertEquals(options.project_directory,
                          overrides.get("project_directory", "."))
        self.assertEquals(options.debug,
                          overrides.get("debug", False))
        self.assertEquals(options.quiet,
                          overrides.get("quiet", False))
        self.assertEquals(options.list_tasks,
                          overrides.get("list_tasks", False))
        self.assertEquals(options.no_color,
                          overrides.get("no_color", False))
        self.assertEquals(options.property_overrides,
                          overrides.get("property_overrides", {}))
        self.assertEquals(options.start_project,
                          overrides.get("start_project", False))

    def test_should_parse_empty_arguments(self):
        options, arguments = parse_options([])

        self.assert_options(options)
        self.assertEquals([], arguments)

    def test_should_parse_task_list_without_options(self):
        options, arguments = parse_options(["clean", "spam"])

        self.assert_options(options)
        self.assertEquals(["clean", "spam"], arguments)

    def test_should_parse_start_project_without_options(self):
        options, arguments = parse_options(["clean", "spam"])

        self.assert_options(options)
        self.assertEquals(["clean", "spam"], arguments)

    def test_should_parse_empty_arguments_with_option(self):
        options, arguments = parse_options(["-X"])

        self.assert_options(options, debug=True)
        self.assertEquals([], arguments)

    def test_should_parse_arguments_and_option(self):
        options, arguments = parse_options(["-X", "-D", "spam", "eggs"])

        self.assert_options(options, debug=True, project_directory="spam")
        self.assertEquals(["eggs"], arguments)

    def test_should_set_property(self):
        options, arguments = parse_options(["-P", "spam=eggs"])

        self.assert_options(options, property_overrides={"spam": "eggs"})
        self.assertEquals([], arguments)

    def test_should_set_multiple_properties(self):
        options, arguments = parse_options(["-P", "spam=eggs",
                                            "-P", "foo=bar"])

        self.assert_options(options, property_overrides={"spam": "eggs",
                                                         "foo": "bar"})
        self.assertEquals([], arguments)

    def test_should_abort_execution_when_property_definition_has_syntax_error(self):
        self.assertRaises(
            CommandLineUsageException, parse_options, ["-P", "spam"])

    def test_should_parse_single_environment(self):
        options, arguments = parse_options(["-E", "spam"])

        self.assert_options(options, environments=["spam"])
        self.assertEquals([], arguments)

    def test_should_parse_multiple_environments(self):
        options, arguments = parse_options(["-E", "spam", "-E", "eggs"])

        self.assert_options(options, environments=["spam", "eggs"])
        self.assertEquals([], arguments)

    def test_should_parse_empty_environments(self):
        options, arguments = parse_options([])

        self.assert_options(options, environments=[])
        self.assertEquals([], arguments)


class LengthOfLongestStringTests(unittest.TestCase):

    def test_should_return_zero_when_list_is_empty(self):
        self.assertEqual(0, length_of_longest_string([]))

    def test_should_return_one_when_list_contains_string_with_single_character(self):
        self.assertEqual(1, length_of_longest_string(['a']))

    def test_should_return_four_when_list_contains_egg_and_spam(self):
        self.assertEqual(4, length_of_longest_string(['egg', 'spam']))

    def test_should_return_four_when_list_contains_foo_bar_egg_and_spam(self):
        self.assertEqual(
            4, length_of_longest_string(['egg', 'spam', 'foo', 'bar']))
