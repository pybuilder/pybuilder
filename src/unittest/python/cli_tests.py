#  This file is part of Python Builder
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

from pybuilder.cli import parse_options, ColoredStdOutLogger, CommandLineUsageException, StdOutLogger
from pybuilder.core import Logger


class StdOutLoggerTest (unittest.TestCase):
    def setUp(self):
        self.stdOutLogger = StdOutLogger(Logger)

    def test_should_return_debug_message_when_debug_level_given(self):
        actualMessage = self.stdOutLogger._level_to_string(Logger.DEBUG)
        self.assertEqual(actualMessage, "[DEBUG]")

    def test_should_return_info_message_when_info_level_given(self):
        actualMessage = self.stdOutLogger._level_to_string(Logger.INFO)
        self.assertEqual(actualMessage, "[INFO] ")

    def test_should_return_warning_message_when_warning_level_given(self):
        actualMessage = self.stdOutLogger._level_to_string(Logger.WARN)
        self.assertEqual(actualMessage, "[WARN] ")

    def test_should_return_error_message_when_any_not_defined_level_given(self):
        actualMessage = self.stdOutLogger._level_to_string(-1)
        self.assertEqual(actualMessage, "[ERROR]")


class ColoredStdOutLoggerTest (unittest.TestCase):
    def setUp(self):
        self.coloredStdOutLogger = ColoredStdOutLogger(Logger)

    def test_should_return_italic_debug_message_when_debug_level_given(self):
        actualMessage = self.coloredStdOutLogger._level_to_string(Logger.DEBUG)
        self.assertEqual(actualMessage, "\x1b[2m[DEBUG]\x1b[0;0m")

    def test_should_return_bold_info_message_when_info_level_given(self):
        actualMessage = self.coloredStdOutLogger._level_to_string(Logger.INFO)
        self.assertEqual(actualMessage, "\x1b[1m[INFO] \x1b[0;0m")

    def test_should_return_brown_and_bold_warning_message_when_warning_level_given(self):
        actualMessage = self.coloredStdOutLogger._level_to_string(Logger.WARN)
        self.assertEqual(actualMessage, "\x1b[1;33m[WARN] \x1b[0;0m")

    def test_should_return_bold_and_red_error_message_when_any_not_defined_level_given(self):
        actualMessage = self.coloredStdOutLogger._level_to_string(-1)
        self.assertEqual(actualMessage, "\x1b[1;31m[ERROR]\x1b[0;0m")


class ParseOptionsTest (unittest.TestCase):
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

    def test_should_parse_empty_arguments (self):
        options, arguments = parse_options([])

        self.assert_options(options)
        self.assertEquals([], arguments)

    def test_should_parse_task_list_without_options (self):
        options, arguments = parse_options(["clean", "spam"])

        self.assert_options(options)
        self.assertEquals(["clean", "spam"], arguments)

    def test_should_parse_empty_arguments_with_option (self):
        options, arguments = parse_options(["-X"])

        self.assert_options(options, debug=True)
        self.assertEquals([], arguments)

    def test_should_parse_arguments_and_option (self):
        options, arguments = parse_options(["-X", "-D", "spam", "eggs"])

        self.assert_options(options, debug=True, project_directory="spam")
        self.assertEquals(["eggs"], arguments)

    def test_should_set_property (self):
        options, arguments = parse_options(["-P", "spam=eggs"])

        self.assert_options(options, property_overrides={"spam": "eggs"})
        self.assertEquals([], arguments)

    def test_should_set_multiple_properties (self):
        options, arguments = parse_options(["-P", "spam=eggs",
                                            "-P", "foo=bar"])

        self.assert_options(options, property_overrides={"spam": "eggs",
                                                         "foo":"bar"})
        self.assertEquals([], arguments)

    def test_should_abort_execution_when_property_definition_has_syntax_error (self):
        self.assertRaises(CommandLineUsageException, parse_options, ["-P", "spam"])

    def test_should_parse_single_environment (self):
        options, arguments = parse_options(["-E", "spam"])

        self.assert_options(options, environments=["spam"])
        self.assertEquals([], arguments)

    def test_should_parse_multiple_environments (self):
        options, arguments = parse_options(["-E", "spam", "-E", "eggs"])

        self.assert_options(options, environments=["spam", "eggs"])
        self.assertEquals([], arguments)

    def test_should_parse_empty_environments (self):
        options, arguments = parse_options([])

        self.assert_options(options, environments=[])
        self.assertEquals([], arguments)
