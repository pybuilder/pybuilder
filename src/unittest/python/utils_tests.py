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

import datetime
import os
import re
import shutil
import tempfile
import time
import unittest
from json import loads
from os.path import dirname, exists
from os.path import join as jp
from os.path import normcase as nc

from test_utils import Mock, patch

from pybuilder.errors import PyBuilderException
from pybuilder.utils import (
    Timer,
    apply_on_files,
    as_list,
    discover_files,
    discover_files_matching,
    discover_modules,
    discover_modules_matching,
    execute_command,
    format_timestamp,
    mkdir,
    render_report,
    timedelta_in_millis,
)


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
        report = {"eggs": ["foo", "bar"], "spam": "baz"}

        actual_report_as_json_string = render_report(report)

        actual_report = loads(actual_report_as_json_string)
        actual_keys = sorted(actual_report.keys())

        self.assertEqual(actual_keys, ["eggs", "spam"])
        self.assertEqual(actual_report["eggs"], ["foo", "bar"])
        self.assertEqual(actual_report["spam"], "baz")


class FormatTimestampTest(unittest.TestCase):
    def assert_matches(self, regex, actual, message=None):
        if not re.match(regex, actual):
            if not message:
                message = "'%s' does not match '%s'" % (actual, regex)

            self.fail(message)

    def test_should_format_timestamp(self):
        self.assert_matches(
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
            format_timestamp(datetime.datetime.now()),
        )


class AsListTest(unittest.TestCase):
    def test_should_return_empty_list_when_no_argument_is_given(self):
        self.assertEqual([], as_list())

    def test_should_return_empty_list_when_none_is_given(self):
        self.assertEqual([], as_list(None))

    def test_should_wrap_single_string_as_list(self):
        self.assertEqual(["spam"], as_list("spam"))

    def test_should_wrap_two_strings_as_list(self):
        self.assertEqual(["spam", "eggs"], as_list("spam", "eggs"))

    def test_should_unwrap_single_list(self):
        self.assertEqual(["spam", "eggs"], as_list(["spam", "eggs"]))

    def test_should_unwrap_multiple_lists(self):
        self.assertEqual(
            ["spam", "eggs", "foo", "bar"], as_list(["spam", "eggs"], ["foo", "bar"])
        )

    def test_should_unwrap_single_tuple(self):
        self.assertEqual(["spam", "eggs"], as_list(("spam", "eggs")))

    def test_should_unwrap_multiple_tuples(self):
        self.assertEqual(
            ["spam", "eggs", "foo", "bar"], as_list(("spam", "eggs"), ("foo", "bar"))
        )

    def test_should_unwrap_mixed_tuples_and_lists_and_strings(self):
        self.assertEqual(
            ["spam", "eggs", "foo", "bar", "foobar"],
            as_list(("spam", "eggs"), ["foo", "bar"], "foobar"),
        )

    def test_should_unwrap_mixed_tuples_and_lists_and_strings_and_ignore_none_values(
        self,
    ):
        self.assertEqual(
            ["spam", "eggs", "foo", "bar", "foobar"],
            as_list(None, ("spam", "eggs"), None, ["foo", "bar"], None, "foobar", None),
        )

    def test_should_return_list_of_function(self):
        def foo():
            pass

        self.assertEqual([foo], as_list(foo))


class TimedeltaInMillisTest(unittest.TestCase):
    def assertMillis(self, expected_millis, **timedelta_constructor_args):
        self.assertEqual(
            expected_millis,
            timedelta_in_millis(datetime.timedelta(**timedelta_constructor_args)),
        )

    def test_should_return_number_of_millis_for_timedelta_with_microseconds_less_than_one_thousand(
        self,
    ):
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
    fake_dir_contents = ["readme.md", ".gitignore", "spam.py", "eggs.py", "eggs.py~"]

    @patch("pybuilder.utils.os.walk", return_value=[("spam", [], fake_dir_contents)])
    def test_should_only_return_py_suffix(self, walk):
        expected_result = [nc("spam/spam.py"), nc("spam/eggs.py")]
        actual_result = set(discover_files("spam", ".py"))
        self.assertEqual(set(expected_result), actual_result)
        walk.assert_called_with("spam", followlinks=True)

    @patch("pybuilder.utils.os.walk", return_value=[("spam", [], fake_dir_contents)])
    def test_should_only_return_py_glob(self, walk):
        expected_result = [nc("spam/readme.md")]
        actual_result = set(discover_files_matching("spam", "readme.?d"))
        self.assertEqual(set(expected_result), actual_result)
        walk.assert_called_with("spam", followlinks=True)


class DiscoverModulesTest(unittest.TestCase):
    @patch("pybuilder.utils.os.walk", return_value=[("spam", [], ["eggs.pi"])])
    def test_should_return_empty_list_when_directory_contains_single_file_not_matching_suffix(
        self, walk
    ):
        self.assertEqual([], discover_modules("spam", ".py"))
        walk.assert_called_with("spam", followlinks=True)

    @patch("pybuilder.utils.os.walk", return_value=[("spam", [], ["eggs.py"])])
    def test_should_return_list_with_single_module_when_directory_contains_single_file(
        self, walk
    ):
        self.assertEqual(["eggs"], discover_modules("spam", ".py"))
        walk.assert_called_with("spam", followlinks=True)

    @patch(
        "pybuilder.utils.os.walk",
        return_value=[
            (
                "pet_shop",
                [],
                ["parrot.txt", "parrot.py", "parrot.pyc", "parrot.py~", "slug.py"],
            )
        ],
    )
    def test_should_only_match_py_files_regardless_of_glob(self, walk):
        expected_result = ["parrot"]
        actual_result = discover_modules_matching("pet_shop", "*parrot*")
        self.assertEqual(set(expected_result), set(actual_result))
        walk.assert_called_with("pet_shop", followlinks=True)

    @patch("pybuilder.utils.os.walk", return_value=[("spam", [], ["eggs.py"])])
    def test_glob_should_return_list_with_single_module_when_directory_contains_single_file(
        self, walk
    ):
        self.assertEqual(["eggs"], discover_modules_matching("spam", "*"))
        walk.assert_called_with("spam", followlinks=True)

    @patch(
        "pybuilder.utils.os.walk",
        return_value=[("spam", ["eggs"], []), ("spam/eggs", [], ["__init__.py"])],
    )
    def test_glob_should_return_list_with_single_module_when_directory_contains_package(
        self, walk
    ):
        self.assertEqual(["eggs"], discover_modules_matching("spam", "*"))

        walk.assert_called_with("spam", followlinks=True)

    @patch(
        "pybuilder.utils.os.walk",
        return_value=[("/path/to/tests", [], ["reactor_tests.py"])],
    )
    def test_should_not_eat_first_character_of_modules_when_source_path_ends_with_slash(
        self, _
    ):
        self.assertEqual(
            ["reactor_tests"], discover_modules_matching("/path/to/tests/", "*")
        )

    @patch(
        "pybuilder.utils.os.walk",
        return_value=[("/path/to/tests", [], ["reactor_tests.py"])],
    )
    def test_should_honor_suffix_without_stripping_it_from_module_names(self, _):
        self.assertEqual(
            ["reactor_tests"], discover_modules_matching("/path/to/tests/", "*_tests")
        )

    @patch(
        "pybuilder.utils.os.walk",
        return_value=[
            ("python", ["a", "b", "name"], []),
            ("python/a", ["b"], ["module.py", "__init__.py"]),
            ("python/a/b", [], ["module.py", "__init__.py"]),
            ("python/b", [], ["module.py", "__init__.py"]),
            ("python/name", ["space"], []),
            ("python/name/space", ["x"], ["module.py"]),
            ("python/name/space/x", [], ["__init__.py", "module.py"]),
        ],
    )
    def test_packages_and_ns_modules_only(self, _):
        self.assertEqual(
            ["a", "a.b", "b", "name.space.module", "name.space.x"],
            discover_modules_matching("python", "*", include_package_modules=False),
        )

    @patch(
        "pybuilder.utils.os.walk",
        return_value=[
            ("python", ["a", "b", "name"], []),
            ("python/a", ["b"], ["module.py", "__init__.py"]),
            ("python/a/b", [], ["module.py", "__init__.py"]),
            ("python/b", [], ["module.py", "__init__.py"]),
            ("python/name", ["space"], []),
            ("python/name/space", ["x"], ["module.py"]),
            ("python/name/space/x", [], ["__init__.py", "module.py"]),
        ],
    )
    def test_non_package_modules_and_ns_modules_only(self, _):
        self.assertEqual(
            [
                "a.module",
                "a.b.module",
                "b.module",
                "name.space.module",
                "name.space.x.module",
            ],
            discover_modules_matching("python", "*", include_packages=False),
        )

    @patch(
        "pybuilder.utils.os.walk",
        return_value=[
            ("python", ["a", "b", "name"], []),
            ("python/a", ["b"], ["module.py", "__init__.py"]),
            ("python/a/b", [], ["module.py", "__init__.py"]),
            ("python/b", [], ["module.py", "__init__.py"]),
            ("python/name", ["space"], []),
            ("python/name/space", ["x"], ["module.py"]),
            ("python/name/space/x", [], ["__init__.py", "module.py"]),
        ],
    )
    def test_packages_and_package_modules_only(self, _):
        self.assertEqual(
            [
                "a.module",
                "a",
                "a.b.module",
                "a.b",
                "b.module",
                "b",
                "name.space.x",
                "name.space.x.module",
            ],
            discover_modules_matching("python", "*", include_namespace_modules=False),
        )


class ApplyOnFilesTest(unittest.TestCase):
    @patch("pybuilder.utils.iglob", return_value=["spam/a", "spam/b", "spam/c"])
    def test_should_apply_callback_to_all_files_when_expression_matches_all_files(
        self, walk
    ):
        absolute_file_names = []
        relative_file_names = []

        def callback(absolute_file_name, relative_file_name):
            absolute_file_names.append(absolute_file_name)
            relative_file_names.append(relative_file_name)

        apply_on_files("spam", callback, "*")
        self.assertEqual(["spam/a", "spam/b", "spam/c"], absolute_file_names)
        self.assertEqual(["a", "b", "c"], relative_file_names)

        walk.assert_called_with(nc("spam/*"), recursive=True)

    @patch("pybuilder.utils.iglob", return_value=["spam/a"])
    def test_should_apply_callback_to_one_file_when_expression_matches_one_file(
        self, walk
    ):
        called_on_file = []

        def callback(absolute_file_name, relative_file_name):
            called_on_file.append(absolute_file_name)

        apply_on_files("spam", callback, "a")
        self.assertEqual(["spam/a"], called_on_file)

        walk.assert_called_with(nc("spam/a"), recursive=True)

    @patch("pybuilder.utils.iglob", return_value=["spam/a"])
    def test_should_pass_additional_arguments_to_closure(self, walk):
        called_on_file = []

        def callback(absolute_file_name, relative_file_name, additional_argument):
            self.assertEqual("additional argument", additional_argument)
            called_on_file.append(absolute_file_name)

        apply_on_files("spam", callback, "a", "additional argument")
        self.assertEqual(["spam/a"], called_on_file)

        walk.assert_called_with(nc("spam/a"), recursive=True)


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


def fork_test_func_send_pickle():
    class Foo():
        @staticmethod
        def bar():
            pass

    class FooError(Exception):
        def __init__(self, message):
            super(Exception, self).__init__(message)

    raise FooError(Foo.bar)


def fork_test_func_success():
    return "success"


def fork_test_func_arg_passing(foo, bar):
    return "%s%s" % (foo, bar)


def fork_test_func_raise():
    class FooError(Exception):
        def __init__(self):
            self.val = "Blah"

    raise FooError()


def fork_test_func_return():
    class FooError(Exception):
        def __init__(self):
            self.val = "Blah"

    return FooError()


def fork_test_func_exc():
    raise PyBuilderException("Test failure message")


def find_project_base_dir():
    cur_dir = dirname(nc(__file__))
    while True:
        if exists(jp(cur_dir, "build.py")):
            return cur_dir
        new_cur_dir = nc(jp(cur_dir, ".."))
        if new_cur_dir == cur_dir:
            return None
        cur_dir = new_cur_dir


class CommandExecutionTest(unittest.TestCase):
    @patch("pybuilder.utils.open", create=True)
    @patch("pybuilder.utils.Popen")
    def test_execute_command(self, popen, _):
        popen.return_value = Mock()
        popen.return_value.wait.return_value = 0
        self.assertEqual(execute_command(["test", "commands"]), 0)
        self.assertEqual(
            execute_command(["test", "commands"], outfile_name="test.out"), 0
        )
        self.assertEqual(
            execute_command(
                ["test", "commands"],
                outfile_name="test.out",
                error_file_name="test.out.err",
            ),
            0,
        )
