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

import json
import sys
import unittest

from pybuilder.cli import (parse_options,
                           ColoredStdOutLogger,
                           StdErrLogger,
                           ColoredStdErrLogger,
                           CommandLineUsageException,
                           StdOutLogger,
                           length_of_longest_string,
                           print_list_of_tasks,
                           print_project_info,
                           _build_project_info,
                           _safe_property_value,
                           _serialize_dependency,
                           DEFAULT_LOG_TIME_FORMAT,
                           get_failure_message)
from pybuilder.core import Logger, Dependency, RequirementsFile
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
        self.stdout_logger = StdOutLogger(log_time_format=FormattedTimestampLoggerTest.DEFAULT_LOG_FORMAT)

    def test_if_log_line_contains_log_time_format(self):
        import sys

        original = sys.stdout
        try:
            sys.stdout = self.StreamWrapper(sys.stdout)

            self.stdout_logger.info("Test")
            self.assertRegex(sys.stdout.text, "^" + self.DEFAULT_LOG_FORMAT)
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
        self.assertEqual(options.project_info,
                         overrides.get("project_info", False))
        self.assertEqual(options.no_color,
                         overrides.get("no_color", False))
        self.assertEqual(options.property_overrides,
                         overrides.get("property_overrides", {}))
        self.assertEqual(options.start_project,
                         overrides.get("start_project", False))
        self.assertEqual(options.log_time_format,
                         overrides.get("log_time_format", None))

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

    def test_setting_of_default_log_time_format(self):
        options, arguments = parse_options(['-f'])

        self.assert_options(options, log_time_format=DEFAULT_LOG_TIME_FORMAT)
        self.assertEqual([], arguments)

    def test_setting_of_a_log_time_format(self):
        test_this_format = '%Y-%m-%d'
        left_over_argument = 'abc'
        options, arguments = parse_options(['-f', test_this_format, left_over_argument])

        self.assert_options(options, log_time_format=test_this_format)
        self.assertEqual([left_over_argument], arguments)

    def test_setting_of_default_log_time_format_with_other_parameter_single_dash(self):
        options, arguments = parse_options(['-f', '-X'])

        self.assert_options(options, log_time_format=DEFAULT_LOG_TIME_FORMAT, debug=True)
        self.assertEqual([], arguments)

    def test_setting_of_default_log_time_format_with_other_parameter_double_dash(self):
        options, arguments = parse_options(['-f', '--debug'])

        self.assert_options(options, log_time_format=DEFAULT_LOG_TIME_FORMAT, debug=True)
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
            self.assertRegex(get_failure_message(), r"Exception: test \(cli_tests.py\:\d+\)")

    def test_pyb_error_message(self):
        try:
            raise PyBuilderException("test")
        except Exception:
            self.assertRegex(get_failure_message(), r"test \(cli_tests.py\:\d+\)")


class ProjectInfoOptionTests(unittest.TestCase):
    def test_should_parse_project_info_short_flag(self):
        options, arguments = parse_options(["-i"])
        self.assertTrue(options.project_info)
        self.assertEqual([], arguments)

    def test_should_parse_project_info_long_flag(self):
        options, arguments = parse_options(["--project-info"])
        self.assertTrue(options.project_info)
        self.assertEqual([], arguments)

    def test_should_default_project_info_to_false(self):
        options, arguments = parse_options([])
        self.assertFalse(options.project_info)

    def test_should_reject_project_info_with_list_tasks(self):
        self.assertRaises(CommandLineUsageException, parse_options, ["-i", "-t"])

    def test_should_reject_project_info_with_list_plan_tasks(self):
        self.assertRaises(CommandLineUsageException, parse_options, ["-i", "-T"])

    def test_should_reject_project_info_with_start_project(self):
        self.assertRaises(CommandLineUsageException, parse_options, ["-i", "--start-project"])

    def test_should_reject_project_info_with_update_project(self):
        self.assertRaises(CommandLineUsageException, parse_options, ["-i", "--update-project"])

    def test_should_allow_project_info_with_environment(self):
        options, _ = parse_options(["-i", "-E", "ci"])
        self.assertTrue(options.project_info)
        self.assertEqual(options.environments, ["ci"])

    def test_should_allow_project_info_with_property_override(self):
        options, _ = parse_options(["-i", "-P", "spam=eggs"])
        self.assertTrue(options.project_info)
        self.assertEqual(options.property_overrides, {"spam": "eggs"})

    def test_should_allow_project_info_with_debug(self):
        options, _ = parse_options(["-i", "-X"])
        self.assertTrue(options.project_info)
        self.assertTrue(options.debug)


class StdErrLoggerTest(unittest.TestCase):
    class StreamWrapper(object):
        def __init__(self, wrapped):
            self.text = ''
            self.__wrapped = wrapped

        def __getattr__(self, name):
            return getattr(self.__wrapped, name)

        def write(self, text):
            self.text += text

    def test_stderr_logger_should_write_to_stderr(self):
        logger = StdErrLogger()
        original = sys.stderr
        try:
            sys.stderr = self.StreamWrapper(sys.stderr)
            logger.info("Test message")
            self.assertIn("Test message", sys.stderr.text)
        finally:
            sys.stderr = original

    def test_stderr_logger_should_not_write_to_stdout(self):
        logger = StdErrLogger()
        original_out = sys.stdout
        original_err = sys.stderr
        try:
            sys.stdout = self.StreamWrapper(sys.stdout)
            sys.stderr = self.StreamWrapper(sys.stderr)
            logger.info("Test message")
            self.assertEqual("", sys.stdout.text)
            self.assertIn("Test message", sys.stderr.text)
        finally:
            sys.stdout = original_out
            sys.stderr = original_err

    def test_colored_stderr_logger_should_write_to_stderr(self):
        logger = ColoredStdErrLogger()
        original = sys.stderr
        try:
            sys.stderr = self.StreamWrapper(sys.stderr)
            logger.info("Test message")
            self.assertIn("Test message", sys.stderr.text)
        finally:
            sys.stderr = original


class SafePropertyValueTests(unittest.TestCase):
    def test_should_pass_through_none(self):
        self.assertIsNone(_safe_property_value(None))

    def test_should_pass_through_string(self):
        self.assertEqual(_safe_property_value("hello"), "hello")

    def test_should_pass_through_int(self):
        self.assertEqual(_safe_property_value(42), 42)

    def test_should_pass_through_float(self):
        self.assertEqual(_safe_property_value(3.14), 3.14)

    def test_should_pass_through_bool(self):
        self.assertEqual(_safe_property_value(True), True)
        self.assertEqual(_safe_property_value(False), False)

    def test_should_convert_list(self):
        self.assertEqual(_safe_property_value([1, "a", True]), [1, "a", True])

    def test_should_convert_tuple(self):
        self.assertEqual(_safe_property_value((1, "a")), [1, "a"])

    def test_should_convert_nested_dict(self):
        self.assertEqual(_safe_property_value({"k": [1, 2]}), {"k": [1, 2]})

    def test_should_convert_set_to_sorted_list(self):
        result = _safe_property_value({3, 1, 2})
        self.assertEqual(result, [1, 2, 3])

    def test_should_repr_non_serializable_objects(self):
        class Custom:
            def __repr__(self):
                return "<custom>"
        self.assertEqual(_safe_property_value(Custom()), "<custom>")


class SerializeDependencyTests(unittest.TestCase):
    def test_should_serialize_dependency_with_version(self):
        dep = Dependency("requests", ">=2.28")
        result = _serialize_dependency(dep)
        self.assertEqual(result["name"], "requests")
        self.assertEqual(result["type"], "dependency")
        self.assertIn("version", result)
        self.assertIn("url", result)
        self.assertIn("extras", result)
        self.assertIn("markers", result)
        self.assertIn("declaration_only", result)

    def test_should_serialize_dependency_without_version(self):
        dep = Dependency("mock")
        result = _serialize_dependency(dep)
        self.assertEqual(result["name"], "mock")
        self.assertIsNone(result["version"])

    def test_should_serialize_requirements_file(self):
        req = RequirementsFile("requirements.txt")
        result = _serialize_dependency(req)
        self.assertEqual(result["name"], "requirements.txt")
        self.assertEqual(result["type"], "requirements_file")
        self.assertIsNone(result["version"])
        self.assertIn("declaration_only", result)


@patch("pybuilder.cli.print_text_line", return_value=None)
class ProjectInfoTests(unittest.TestCase):
    def _create_mock_reactor(self):
        def __eq__(self, other):
            return False

        def __ne__(self, other):
            return not self.__eq__(other)

        def __lt__(self, other):
            return False

        mock_reactor = Mock()
        mock_reactor.project.name = "test-project"
        mock_reactor.project.version = "1.0.0"
        mock_reactor.project.dist_version = "1.0.0"
        mock_reactor.project.basedir = "/test"
        mock_reactor.project.summary = "Test summary"
        mock_reactor.project.description = "Test description"
        mock_reactor.project.author = "Test Author"
        mock_reactor.project.authors = ["Author One", "Author Two"]
        mock_reactor.project.maintainer = ""
        mock_reactor.project.maintainers = []
        mock_reactor.project.license = "Apache-2.0"
        mock_reactor.project.url = "https://example.com"
        mock_reactor.project.urls = {"Homepage": "https://example.com", "Source": "https://github.com/example"}
        mock_reactor.project.requires_python = ">=3.10"
        mock_reactor.project.default_task = "publish"
        mock_reactor.project.obsoletes = []
        mock_reactor.project.explicit_namespaces = []
        mock_reactor.project.environments = ()
        mock_reactor.project.properties = {"verbose": False, "basedir": "/test"}
        mock_reactor.project.dependencies = []
        mock_reactor.project.build_dependencies = []
        mock_reactor.project.plugin_dependencies = []
        mock_reactor.project.extras_dependencies = {}
        mock_reactor.project.manifest_included_files = []
        mock_reactor.project.package_data = {}
        mock_reactor.project.files_to_install = []
        mock_reactor.get_plugins.return_value = ["python.core", "python.unittest"]
        task_1 = Mock()
        task_1.__eq__ = __eq__
        task_1.__ne__ = __ne__
        task_1.__lt__ = __lt__
        task_1.name = "clean"
        task_1.description = ["Cleans", "the", "output"]
        task_1.dependencies = []
        task_2 = Mock()
        task_2.__eq__ = __eq__
        task_2.__ne__ = __ne__
        task_2.__lt__ = __lt__
        task_2.name = "publish"
        task_2.description = ["Publishes", "the", "project"]
        dep = Mock()
        dep.name = "clean"
        dep.optional = False
        task_2.dependencies = [dep]
        mock_reactor.get_tasks.return_value = [task_1, task_2]
        return mock_reactor

    def test_should_output_valid_json(self, print_text_line):
        reactor = self._create_mock_reactor()
        print_project_info(reactor, [])

        output = print_text_line.call_args[0][0]
        info = json.loads(output)
        self.assertEqual(info["project"]["name"], "test-project")
        self.assertEqual(info["project"]["version"], "1.0.0")

    def test_should_call_execute_initializers(self, print_text_line):
        reactor = self._create_mock_reactor()
        print_project_info(reactor, ["ci"])

        reactor.execution_manager.execute_initializers.assert_called_once()
        call_kwargs = reactor.execution_manager.execute_initializers.call_args
        self.assertEqual(call_kwargs[0][0], ["ci"])

    def test_should_set_environments_on_project(self, print_text_line):
        reactor = self._create_mock_reactor()
        print_project_info(reactor, ["ci", "production"])

        self.assertEqual(reactor.project._environments, ("ci", "production"))

    def test_should_include_plugins(self, print_text_line):
        reactor = self._create_mock_reactor()
        print_project_info(reactor, [])

        output = print_text_line.call_args[0][0]
        info = json.loads(output)
        self.assertEqual(info["plugins"], ["python.core", "python.unittest"])

    def test_should_include_tasks(self, print_text_line):
        reactor = self._create_mock_reactor()
        print_project_info(reactor, [])

        output = print_text_line.call_args[0][0]
        info = json.loads(output)
        self.assertEqual(len(info["tasks"]), 2)
        task_names = [t["name"] for t in info["tasks"]]
        self.assertIn("clean", task_names)
        self.assertIn("publish", task_names)

    def test_should_include_task_dependencies(self, print_text_line):
        reactor = self._create_mock_reactor()
        print_project_info(reactor, [])

        output = print_text_line.call_args[0][0]
        info = json.loads(output)
        publish_task = [t for t in info["tasks"] if t["name"] == "publish"][0]
        self.assertEqual(len(publish_task["dependencies"]), 1)
        self.assertEqual(publish_task["dependencies"][0]["name"], "clean")
        self.assertFalse(publish_task["dependencies"][0]["optional"])

    def test_should_include_project_metadata(self, print_text_line):
        reactor = self._create_mock_reactor()
        print_project_info(reactor, [])

        output = print_text_line.call_args[0][0]
        info = json.loads(output)
        self.assertEqual(info["project"]["summary"], "Test summary")
        self.assertEqual(info["project"]["license"], "Apache-2.0")
        self.assertEqual(info["project"]["url"], "https://example.com")
        self.assertEqual(info["project"]["requires_python"], ">=3.10")
        self.assertEqual(info["project"]["default_task"], "publish")
        self.assertEqual(info["project"]["authors"], ["Author One", "Author Two"])

    def test_should_include_properties(self, print_text_line):
        reactor = self._create_mock_reactor()
        reactor.project.properties = {"verbose": False, "basedir": "/test", "custom_prop": "custom_val"}
        print_project_info(reactor, [])

        output = print_text_line.call_args[0][0]
        info = json.loads(output)
        self.assertEqual(info["properties"]["custom_prop"], "custom_val")
        self.assertEqual(info["properties"]["basedir"], "/test")

    def test_should_include_pybuilder_version(self, print_text_line):
        reactor = self._create_mock_reactor()
        print_project_info(reactor, [])

        output = print_text_line.call_args[0][0]
        info = json.loads(output)
        self.assertIn("pybuilder_version", info)

    def test_should_include_dependency_sections(self, print_text_line):
        reactor = self._create_mock_reactor()
        print_project_info(reactor, [])

        output = print_text_line.call_args[0][0]
        info = json.loads(output)
        self.assertIn("runtime", info["dependencies"])
        self.assertIn("build", info["dependencies"])
        self.assertIn("plugin", info["dependencies"])
        self.assertIn("extras", info["dependencies"])
