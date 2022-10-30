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

from pybuilder.cli import (parse_options,
                           ColoredStdOutLogger,
                           CommandLineUsageException,
                           StdOutLogger,
                           length_of_longest_string,
                           print_list_of_tasks,
                           DEFAULT_LOG_FORMAT,
                           get_failure_message)
from pybuilder.core import Logger
from pybuilder.errors import PyBuilderException
from test_utils import Mock, patch, call


@patch("pybuilder.cli.print_text_line", return_value=None)
class TaskListTests(unittest.TestCase):
    def setUp(self):
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
        self.mock_reactor.get_tasks.return_value = [self.task_1, self.task_2]

    def test_should_render_minimal_task_list_when_in_quiet_mode(self, print_text_line):
        print_list_of_tasks(self.mock_reactor, quiet=True)

        print_text_line.assert_called_with('task-1:<no description available>\ntask-2:<no description available>')

    def test_should_render_verbose_task_list_without_descriptions_and_dependencies(self, print_text_line):
        print_list_of_tasks(self.mock_reactor, quiet=False)

        print_text_line.assert_has_calls([call('Tasks found for project "any-project-name":'),
                                          call('    task-1 - <no description available>'),
                                          call('    task-2 - <no description available>')])

    def test_should_render_verbose_task_list_with_dependencies(self, print_text_line):
        self.task_1.dependencies = ["any-dependency", "any-other-dependency"]

        print_list_of_tasks(self.mock_reactor, quiet=False)

        print_text_line.assert_has_calls([call('Tasks found for project "any-project-name":'),
                                          call('    task-1 - <no description available>'),
                                          call('             depends on tasks: any-dependency any-other-dependency'),
                                          call('    task-2 - <no description available>')])

    def test_should_render_verbose_task_list_with_descriptions(self, print_text_line):
        self.task_1.description = ["any", "description", "for", "task", "1"]
        self.task_2.description = ["any", "description", "for", "task", "2"]

        print_list_of_tasks(self.mock_reactor, quiet=False)

        print_text_line.assert_has_calls([call('Tasks found for project "any-project-name":'),
                                          call('    task-1 - any description for task 1'),
                                          call('    task-2 - any description for task 2')])



class FormattedTimestampLoggerTest(unittest.TestCase):
    DEFAULT_LOG_FORMAT = "some_fixed_test"

    class StreamWrapper(object):
        def __init__(self, wrapped):
            self.text = ''
            self.__wrapped = wrapped

        def __getattr__(self, name):
            # 'write' is overridden but for every other function, like 'flush', use the original wrapped stream
            return getattr(self.__wrapped, name)

        def write(self, text):
            self.text += text

    def setUp(self):
        self.stdout_logger = StdOutLogger(log_format=FormattedTimestampLoggerTest.DEFAULT_LOG_FORMAT)

    def test_if_log_line_contains_log_format(self):
        import sys

        original = sys.stdout
        try:
            sys.stdout = self.StreamWrapper(sys.stdout)

            self.stdout_logger.info("Test")
            self.assertRegexpMatches(sys.stdout.text, "^" + self.DEFAULT_LOG_FORMAT)
        finally:
            sys.stdout = original


class StdOutLoggerTest(unittest.TestCase):
    def setUp(self):
        self.stdout_logger = StdOutLogger()

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
        self.colored_stdout_logger = ColoredStdOutLogger()

    def test_should_return_italic_debug_message_when_debug_level_given(self):
        actual_message = self.colored_stdout_logger._level_to_string(Logger.DEBUG)
        self.assertEqual(actual_message, "\x1b[2m[DEBUG]\x1b[0m")

    def test_should_return_bold_info_message_when_info_level_given(self):
        actual_message = self.colored_stdout_logger._level_to_string(Logger.INFO)
        self.assertEqual(actual_message, "\x1b[1m[INFO] \x1b[0m")

    def test_should_return_brown_and_bold_warning_message_when_warning_level_given(self):
        actual_message = self.colored_stdout_logger._level_to_string(Logger.WARN)
        self.assertEqual(actual_message, "\x1b[1;33m[WARN] \x1b[0m")

    def test_should_return_bold_and_red_error_message_when_any_not_defined_level_given(self):
        actual_message = self.colored_stdout_logger._level_to_string(-1)
        self.assertEqual(actual_message, "\x1b[1;31m[ERROR]\x1b[0m")


class ParseOptionsTest(unittest.TestCase):
    def assert_options(self, options, **overrides):
        self.assertEqual(options.project_directory,
                         overrides.get("project_directory", "."))
        self.assertEqual(options.debug,
                         overrides.get("debug", False))
        self.assertEqual(options.quiet,
                         overrides.get("quiet", False))
        self.assertEqual(options.list_tasks,
                         overrides.get("list_tasks", False))
        self.assertEqual(options.no_color,
                         overrides.get("no_color", False))
        self.assertEqual(options.property_overrides,
                         overrides.get("property_overrides", {}))
        self.assertEqual(options.start_project,
                         overrides.get("start_project", False))
        self.assertEqual(options.log_format,
                         overrides.get("log_format", None))

    def test_should_parse_empty_arguments(self):
        options, arguments = parse_options([])

        self.assert_options(options)
        self.assertEqual([], arguments)

    def test_should_parse_task_list_without_options(self):
        options, arguments = parse_options(["clean", "spam"])

        self.assert_options(options)
        self.assertEqual(["clean", "spam"], arguments)

    def test_should_parse_start_project_without_options(self):
        options, arguments = parse_options(["clean", "spam"])

        self.assert_options(options)
        self.assertEqual(["clean", "spam"], arguments)

    def test_should_parse_empty_arguments_with_option(self):
        options, arguments = parse_options(["-X"])

        self.assert_options(options, debug=True)
        self.assertEqual([], arguments)

    def test_should_parse_arguments_and_option(self):
        options, arguments = parse_options(["-X", "-D", "spam", "eggs"])

        self.assert_options(options, debug=True, project_directory="spam")
        self.assertEqual(["eggs"], arguments)

    def test_should_set_property(self):
        options, arguments = parse_options(["-P", "spam=eggs"])

        self.assert_options(options, property_overrides={"spam": "eggs"})
        self.assertEqual([], arguments)

    def test_should_set_property_with_equals_sign(self):
        options, arguments = parse_options(["-P", "spam==eg=gs"])

        self.assert_options(options, property_overrides={"spam": "=eg=gs"})
        self.assertEqual([], arguments)

    def test_should_set_multiple_properties(self):
        options, arguments = parse_options(["-P", "spam=eggs",
                                            "-P", "foo=bar"])

        self.assert_options(options, property_overrides={"spam": "eggs",
                                                         "foo": "bar"})
        self.assertEqual([], arguments)

    def test_should_abort_execution_when_property_definition_has_syntax_error(self):
        self.assertRaises(
            CommandLineUsageException, parse_options, ["-P", "spam"])

    def test_should_parse_single_environment(self):
        options, arguments = parse_options(["-E", "spam"])

        self.assert_options(options, environments=["spam"])
        self.assertEqual([], arguments)

    def test_should_parse_multiple_environments(self):
        options, arguments = parse_options(["-E", "spam", "-E", "eggs"])

        self.assert_options(options, environments=["spam", "eggs"])
        self.assertEqual([], arguments)

    def test_should_parse_empty_environments(self):
        options, arguments = parse_options([])

        self.assert_options(options, environments=[])
        self.assertEqual([], arguments)

    def test_setting_of_default_log_format(self):
        options, arguments = parse_options(['-f'])

        self.assert_options(options, log_format=DEFAULT_LOG_FORMAT)
        self.assertEqual([], arguments)

    def test_setting_of_a_log_format(self):
        test_this_format = '%Y-%m-%d'
        left_over_argument = 'abc'
        options, arguments = parse_options(['-f', test_this_format, left_over_argument])

        self.assert_options(options, log_format=test_this_format)
        self.assertEqual([left_over_argument], arguments)

    def test_setting_of_default_log_format_with_other_parameter_single_dash(self):
        options, arguments = parse_options(['-f', '-X'])

        self.assert_options(options, log_format=DEFAULT_LOG_FORMAT, debug=True)
        self.assertEqual([], arguments)

    def test_setting_of_default_log_format_with_other_parameter_double_dash(self):
        options, arguments = parse_options(['-f', '--debug'])

        self.assert_options(options, log_format=DEFAULT_LOG_FORMAT, debug=True)
        self.assertEqual([], arguments)


class LengthOfLongestStringTests(unittest.TestCase):
    def test_should_return_zero_when_list_is_empty(self):
        self.assertEqual(0, length_of_longest_string([]))

    def test_should_return_one_when_list_contains_string_with_no_characters(self):
        self.assertEqual(0, length_of_longest_string([""]))

    def test_should_return_one_when_list_contains_string_with_single_character(self):
        self.assertEqual(1, length_of_longest_string(["a"]))

    def test_should_return_four_when_list_contains_egg_and_spam(self):
        self.assertEqual(4, length_of_longest_string(["egg", "spam"]))

    def test_should_return_four_when_list_contains_foo_bar_egg_and_spam(self):
        self.assertEqual(4, length_of_longest_string(["egg", "spam", "foo", "bar"]))


class ErrorHandlingTests(unittest.TestCase):
    def test_generic_error_message(self):
        try:
            raise Exception("test")
        except Exception:
            self.assertRegexpMatches(get_failure_message(), r"Exception: test \(cli_tests.py\:\d+\)")

    def test_pyb_error_message(self):
        try:
            raise PyBuilderException("test")
        except Exception:
            self.assertRegexpMatches(get_failure_message(), r"test \(cli_tests.py\:\d+\)")
