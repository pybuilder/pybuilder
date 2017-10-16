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

import datetime
import os
import re
import shutil
import sys
import tempfile
import time
import unittest
from json import loads

from pybuilder.core import Project
from pybuilder.errors import PyBuilderException
from pybuilder.utils import (GlobExpression,
                             Timer,
                             apply_on_files,
                             as_list,
                             discover_files,
                             discover_files_matching,
                             discover_modules,
                             discover_modules_matching,
                             format_timestamp,
                             mkdir,
                             render_report,
                             timedelta_in_millis,
                             fork_process,
                             execute_command,
                             register_test_and_source_path_and_return_test_dir)
from test_utils import patch, Mock


class TimerTest(unittest.TestCase):
    def test_ensure_that_start_starts_timer(self):
        timer = Timer.start()
        self.assertTrue(timer.start_time > 0)
        self.assertFalse(timer.end_time)

    def test_should_raise_exception_when_fetching_millis_of_running_timer(self):
        timer = Timer.start()
        self.assertRaises(PyBuilderException, timer.get_millis)

    def test_should_return_number_of_millis(self):
        timer = Timer.start()
        time.sleep(1)
        timer.stop()
        self.assertTrue(timer.get_millis() > 0)


class RenderReportTest(unittest.TestCase):
    def test_should_render_report(self):
        report = {
            "eggs": ["foo", "bar"],
            "spam": "baz"
        }

        actual_report_as_json_string = render_report(report)

        actual_report = loads(actual_report_as_json_string)
        actual_keys = sorted(actual_report.keys())

        self.assertEquals(actual_keys, ['eggs', 'spam'])
        self.assertEquals(actual_report['eggs'], ["foo", "bar"])
        self.assertEquals(actual_report['spam'], "baz")


class FormatTimestampTest(unittest.TestCase):
    def assert_matches(self, regex, actual, message=None):
        if not re.match(regex, actual):
            if not message:
                message = "'%s' does not match '%s'" % (actual, regex)

            self.fail(message)

    def test_should_format_timestamp(self):
        self.assert_matches(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
                            format_timestamp(datetime.datetime.now()))


class AsListTest(unittest.TestCase):
    def test_should_return_empty_list_when_no_argument_is_given(self):
        self.assertEquals([], as_list())

    def test_should_return_empty_list_when_none_is_given(self):
        self.assertEquals([], as_list(None))

    def test_should_wrap_single_string_as_list(self):
        self.assertEquals(["spam"], as_list("spam"))

    def test_should_wrap_two_strings_as_list(self):
        self.assertEquals(["spam", "eggs"], as_list("spam", "eggs"))

    def test_should_unwrap_single_list(self):
        self.assertEquals(["spam", "eggs"], as_list(["spam", "eggs"]))

    def test_should_unwrap_multiple_lists(self):
        self.assertEquals(
            ["spam", "eggs", "foo", "bar"], as_list(["spam", "eggs"], ["foo", "bar"]))

    def test_should_unwrap_single_tuple(self):
        self.assertEquals(["spam", "eggs"], as_list(("spam", "eggs")))

    def test_should_unwrap_multiple_tuples(self):
        self.assertEquals(
            ["spam", "eggs", "foo", "bar"], as_list(("spam", "eggs"), ("foo", "bar")))

    def test_should_unwrap_mixed_tuples_and_lists_and_strings(self):
        self.assertEquals(["spam", "eggs", "foo", "bar", "foobar"],
                          as_list(("spam", "eggs"), ["foo", "bar"], "foobar"))

    def test_should_unwrap_mixed_tuples_and_lists_and_strings_and_ignore_none_values(self):
        self.assertEquals(
            ["spam", "eggs", "foo", "bar", "foobar"], as_list(None, ("spam", "eggs"),
                                                              None, ["foo", "bar"],
                                                              None, "foobar", None))

    def test_should_return_list_of_function(self):
        def foo():
            pass

        self.assertEquals([foo], as_list(foo))


class TimedeltaInMillisTest(unittest.TestCase):
    def assertMillis(self, expected_millis, **timedelta_constructor_args):
        self.assertEquals(expected_millis, timedelta_in_millis(
            datetime.timedelta(**timedelta_constructor_args)))

    def test_should_return_number_of_millis_for_timedelta_with_microseconds_less_than_one_thousand(self):
        self.assertMillis(0, microseconds=500)

    def test_should_return_number_of_millis_for_timedelta_with_microseconds(self):
        self.assertMillis(1, microseconds=1000)

    def test_should_return_number_of_millis_for_timedelta_with_seconds(self):
        self.assertMillis(5000, seconds=5)

    def test_should_return_number_of_millis_for_timedelta_with_minutes(self):
        self.assertMillis(5 * 60 * 1000, minutes=5)

    def test_should_return_number_of_millis_for_timedelta_with_hours(self):
        self.assertMillis(5 * 60 * 60 * 1000, hours=5)

    def test_should_return_number_of_millis_for_timedelta_with_days(self):
        self.assertMillis(5 * 24 * 60 * 60 * 1000, days=5)


class DiscoverFilesTest(unittest.TestCase):
    fake_dir_contents = ["README.md", ".gitignore", "spam.py", "eggs.py", "eggs.py~"]

    @patch("pybuilder.utils.os.walk", return_value=[("spam", [], fake_dir_contents)])
    def test_should_only_return_py_suffix(self, walk):
        expected_result = ["spam/spam.py", "spam/eggs.py"]
        actual_result = set(discover_files("spam", ".py"))
        self.assertEquals(set(expected_result), actual_result)
        walk.assert_called_with("spam")

    @patch("pybuilder.utils.os.walk", return_value=[("spam", [], fake_dir_contents)])
    def test_should_only_return_py_glob(self, walk):
        expected_result = ["spam/README.md"]
        actual_result = set(discover_files_matching("spam", "README.?d"))
        self.assertEquals(set(expected_result), actual_result)
        walk.assert_called_with("spam")


class DiscoverModulesTest(unittest.TestCase):
    @patch("pybuilder.utils.os.walk", return_value=[("spam", [], ["eggs.pi"])])
    def test_should_return_empty_list_when_directory_contains_single_file_not_matching_suffix(self, walk):
        self.assertEquals([], discover_modules("spam", ".py"))
        walk.assert_called_with("spam")

    @patch("pybuilder.utils.os.walk", return_value=[("spam", [], ["eggs.py"])])
    def test_should_return_list_with_single_module_when_directory_contains_single_file(self, walk):
        self.assertEquals(["eggs"], discover_modules("spam", ".py"))
        walk.assert_called_with("spam")

    @patch("pybuilder.utils.os.walk", return_value=[("pet_shop", [],
                                                     ["parrot.txt", "parrot.py", "parrot.pyc", "parrot.py~",
                                                      "slug.py"])])
    def test_should_only_match_py_files_regardless_of_glob(self, walk):
        expected_result = ["parrot"]
        actual_result = discover_modules_matching("pet_shop", "*parrot*")
        self.assertEquals(set(expected_result), set(actual_result))
        walk.assert_called_with("pet_shop")

    @patch("pybuilder.utils.os.walk", return_value=[("spam", [], ["eggs.py"])])
    def test_glob_should_return_list_with_single_module_when_directory_contains_single_file(self, walk):
        self.assertEquals(["eggs"], discover_modules_matching("spam", "*"))
        walk.assert_called_with("spam")

    @patch("pybuilder.utils.os.walk", return_value=[("spam", ["eggs"], []),
                                                    ("spam/eggs", [], ["__init__.py"])])
    def test_glob_should_return_list_with_single_module_when_directory_contains_package(self, walk):
        self.assertEquals(["eggs"], discover_modules_matching("spam", "*"))

        walk.assert_called_with("spam")

    @patch("pybuilder.utils.discover_files_matching", return_value=['/path/to/tests/reactor_tests.py'])
    def test_should_not_eat_first_character_of_modules_when_source_path_ends_with_slash(self, _):
        self.assertEquals(["reactor_tests"], discover_modules_matching("/path/to/tests/", "*"))

    @patch("pybuilder.utils.discover_files_matching", return_value=['/path/to/tests/reactor_tests.py'])
    def test_should_honor_suffix_without_stripping_it_from_module_names(self, _):
        self.assertEquals(["reactor_tests"], discover_modules_matching("/path/to/tests/", "*_tests"))


class GlobExpressionTest(unittest.TestCase):
    def test_static_expression_should_match_exact_file_name(self):
        self.assertTrue(GlobExpression("spam.eggs").matches("spam.eggs"))

    def test_static_expression_should_not_match_different_file_name(self):
        self.assertFalse(GlobExpression("spam.eggs").matches("spam.egg"))

    def test_dynamic_file_expression_should_match_any_character(self):
        self.assertTrue(GlobExpression("spam.egg*").matches("spam.eggs"))

    def test_dynamic_file_expression_should_match_no_character(self):
        self.assertTrue(GlobExpression("spam.egg*").matches("spam.egg"))

    def test_dynamic_file_expression_should_not_match_different_file_part(self):
        self.assertFalse(GlobExpression("spam.egg*").matches("foo.spam.egg"))

    def test_dynamic_file_expression_should_not_match_directory_part(self):
        self.assertFalse(GlobExpression("*spam.egg").matches("foo/spam.egg"))

    def test_dynamic_directory_expression_should_match_file_in_directory(self):
        self.assertTrue(GlobExpression("**/spam.egg").matches("foo/spam.egg"))
        self.assertTrue(GlobExpression("**/spam.egg").matches("bar/spam.egg"))


class ApplyOnFilesTest(unittest.TestCase):
    @patch("pybuilder.utils.os.walk", return_value=[("spam", [], ["a", "b", "c"])])
    def test_should_apply_callback_to_all_files_when_expression_matches_all_files(self, walk):
        absolute_file_names = []
        relative_file_names = []

        def callback(absolute_file_name, relative_file_name):
            absolute_file_names.append(absolute_file_name)
            relative_file_names.append(relative_file_name)

        apply_on_files("spam", callback, "*")
        self.assertEquals(["spam/a", "spam/b", "spam/c"], absolute_file_names)
        self.assertEquals(["a", "b", "c"], relative_file_names)

        walk.assert_called_with("spam")

    @patch("pybuilder.utils.os.walk", return_value=[("spam", [], ["a", "b", "c"])])
    def test_should_apply_callback_to_one_file_when_expression_matches_one_file(self, walk):
        called_on_file = []

        def callback(absolute_file_name, relative_file_name):
            called_on_file.append(absolute_file_name)

        apply_on_files("spam", callback, "a")
        self.assertEquals(["spam/a"], called_on_file)

        walk.assert_called_with("spam")

    @patch("pybuilder.utils.os.walk", return_value=[("spam", [], ["a"])])
    def test_should_pass_additional_arguments_to_closure(self, walk):
        called_on_file = []

        def callback(absolute_file_name, relative_file_name, additional_argument):
            self.assertEquals("additional argument", additional_argument)
            called_on_file.append(absolute_file_name)

        apply_on_files("spam", callback, "a", "additional argument")
        self.assertEquals(["spam/a"], called_on_file)

        walk.assert_called_with("spam")


class MkdirTest(unittest.TestCase):
    def setUp(self):
        self.basedir = tempfile.mkdtemp(self.__class__.__name__)
        self.any_directory = os.path.join(self.basedir, "any_dir")

    def tearDown(self):
        shutil.rmtree(self.basedir)

    def test_should_make_directory_if_it_does_not_exist(self):
        mkdir(self.any_directory)

        self.assertTrue(os.path.exists(self.any_directory))
        self.assertTrue(os.path.isdir(self.any_directory))

    def test_should_make_directory_with_parents_if_it_does_not_exist(self):
        self.any_directory = os.path.join(self.any_directory, "any_child")

        mkdir(self.any_directory)

        self.assertTrue(os.path.exists(self.any_directory))
        self.assertTrue(os.path.isdir(self.any_directory))

    def test_should_not_make_directory_if_it_already_exists(self):
        os.mkdir(self.any_directory)

        mkdir(self.any_directory)

        self.assertTrue(os.path.exists(self.any_directory))
        self.assertTrue(os.path.isdir(self.any_directory))

    def test_raise_exception_when_file_with_dirname_already_exists(self):
        with open(self.any_directory, "w") as existing_file:
            existing_file.write("caboom")

        self.assertRaises(PyBuilderException, mkdir, self.any_directory)

        self.assertTrue(os.path.exists(self.any_directory))
        self.assertFalse(os.path.isdir(self.any_directory))


class ForkTest(unittest.TestCase):
    def testForkNoException(self):
        def test_func():
            return "success"

        val = fork_process(Mock(), target=test_func)

        self.assertEquals(len(val), 2)
        self.assertEquals(val[0], 0)
        self.assertEquals(val[1], "success")

    def testForkParamPassing(self):
        def test_func(foo, bar):
            return "%s%s" % (foo, bar)

        val = fork_process(Mock(), target=test_func, kwargs={"foo": "foo", "bar": 10})
        self.assertEquals(len(val), 2)
        self.assertEquals(val[0], 0)
        self.assertEquals(val[1], "foo10")

        val = fork_process(Mock(), target=test_func, args=("foo", 20))
        self.assertEquals(len(val), 2)
        self.assertEquals(val[0], 0)
        self.assertEquals(val[1], "foo20")

    def testForkWithException(self):
        def test_func():
            raise PyBuilderException("Test failure message")

        try:
            val = fork_process(Mock(), target=test_func)
            val = fork_process(Mock(), target=test_func)
            self.fail("should not have reached here, returned %s" % val)
        except:
            ex_type, ex, tb = sys.exc_info()
            self.assertEquals(ex_type, PyBuilderException)
            self.assertEquals(ex.message, "Test failure message")
            self.assertTrue(tb)

    def testForkWithValuePicklingError(self):
        class FooError(Exception):
            def __init__(self):
                self.val = 'Blah'

        def test_func():
            return FooError()

        try:
            fork_process(Mock(), target=test_func)
            self.fail("should not have reached here")
        except:
            ex_type, ex, tb = sys.exc_info()
            self.assertEquals(ex_type, Exception)
            self.assertTrue(str(ex).startswith("Fatal error occurred in the forked process"))
            self.assertTrue("Can't pickle" in str(ex))
            self.assertTrue("FooError" in str(ex))

    def testForkWithExceptionPicklingError(self):
        class FooError(Exception):
            def __init__(self):
                self.val = 'Blah'

        def test_func():
            raise FooError()

        try:
            val = fork_process(Mock(), target=test_func)
            self.fail("should not have reached here, returned %s" % val)
        except:
            ex_type, ex, tb = sys.exc_info()
            self.assertEquals(ex_type, Exception)
            self.assertTrue(str(ex).startswith("Fatal error occurred in the forked process"))
            self.assertTrue("Can't pickle" in str(ex))
            self.assertTrue("FooError" in str(ex))

    def testForkWithSendPicklingError(self):
        class Foo(object):
            @staticmethod
            def bar():
                pass

        class FooError(Exception):
            def __init__(self, message):
                super(Exception, self).__init__(message)

        def test_func():
            raise FooError(Foo.bar)

        try:
            val = fork_process(Mock(), target=test_func)
            self.fail("should not have reached here, returned %s" % val)
        except:
            ex_type, ex, tb = sys.exc_info()
            self.assertEquals(ex_type, Exception)
            self.assertTrue(str(ex).startswith("Fatal error occurred in the forked process"))
            self.assertTrue("Can't pickle" in str(ex))
            self.assertTrue("FooError" in str(ex))
            self.assertTrue("This error masked the send error '<function" in str(ex))
            self.assertTrue("raise FooError(Foo.bar)" in str(ex))


class CommandExecutionTest(unittest.TestCase):
    @patch("pybuilder.utils.open", create=True)
    @patch("pybuilder.utils.Popen")
    def test_execute_command(self, popen, _):
        popen.return_value = Mock()
        popen.return_value.wait.return_value = 0
        self.assertEquals(execute_command(["test", "commands"]), 0)
        self.assertEquals(execute_command(["test", "commands"], outfile_name="test.out"), 0)
        self.assertEquals(
            execute_command(["test", "commands"], outfile_name="test.out", error_file_name="test.out.err"), 0)


class PythonPathTests(unittest.TestCase):
    def setUp(self):
        self.project = Project('/path/to/project')
        self.project.set_property('dir_source_unittest_python', 'unittest')
        self.project.set_property('dir_source_main_python', 'src')

    def test_should_register_source_paths(self):
        system_path = ['some/python/path']

        register_test_and_source_path_and_return_test_dir(self.project, system_path, "unittest")

        self.assertTrue('/path/to/project/unittest' in system_path)
        self.assertTrue('/path/to/project/src' in system_path)

    def test_should_put_project_sources_before_other_sources(self):
        system_path = ['irrelevant/sources']

        register_test_and_source_path_and_return_test_dir(self.project, system_path, "unittest")

        test_sources_index_in_path = system_path.index('/path/to/project/unittest')
        main_sources_index_in_path = system_path.index('/path/to/project/src')
        irrelevant_sources_index_in_path = system_path.index('irrelevant/sources')
        self.assertTrue(test_sources_index_in_path < irrelevant_sources_index_in_path and
                        main_sources_index_in_path < irrelevant_sources_index_in_path)
