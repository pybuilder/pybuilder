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

import sys
from logging import Logger
from unittest import TestCase

from pybuilder.core import Project, Author
from pybuilder.errors import BuildFailedException
from pybuilder.plugins.python.sphinx_plugin import (assert_sphinx_is_available,
                                                    assert_sphinx_quickstart_is_available,
                                                    get_sphinx_build_command,
                                                    get_sphinx_quickstart_command,
                                                    initialize_sphinx_plugin,
                                                    run_sphinx_build,
                                                    get_sphinx_apidoc_command,
                                                    sphinx_pyb_quickstart_generate,
                                                    sphinx_generate,
                                                    generate_sphinx_apidocs)
from test_utils import Mock, patch, call


class CheckSphinxAvailableTests(TestCase):
    @patch('pybuilder.plugins.python.sphinx_plugin.assert_can_execute')
    def test_should_check_that_sphinx_can_be_executed(self, mock_assert_can_execute):
        mock_logger = Mock(Logger)

        assert_sphinx_is_available(mock_logger)

        mock_assert_can_execute.assert_has_calls(
            [
                call(['sphinx-build', '--version'], 'sphinx', 'plugin python.sphinx'),
                call(['sphinx-apidoc', '--version'], 'sphinx', 'plugin python.sphinx')
            ]
        )

    @patch('pybuilder.plugins.python.sphinx_plugin.assert_can_execute')
    def test_should_check_that_sphinx_quickstart_can_be_executed(self, mock_assert_can_execute):
        mock_logger = Mock(Logger)

        assert_sphinx_quickstart_is_available(mock_logger)
        mock_assert_can_execute.assert_called_with(
            ['sphinx-quickstart', '--version'], 'sphinx', 'plugin python.sphinx')


class SphinxPluginInitializationTests(TestCase):
    def setUp(self):
        self.project = Project("basedir")

    def test_should_leave_user_specified_properties_when_initializing_plugin(self):

        expected_properties = {
            "sphinx_source_dir": "source_dir",
            "sphinx_output_dir": "output_dir",
            "sphinx_config_path": "config_path",
            "sphinx_doc_author": "author",
            "sphinx_doc_builder": "doc_builder",
            "sphinx_project_name": "project_name",
            "sphinx_project_version": "project_version"
        }

        for property_name, property_value in expected_properties.items():
            self.project.set_property(property_name, property_value)

            initialize_sphinx_plugin(self.project)

        for property_name, property_value in expected_properties.items():
            self.assertEquals(

                self.project.get_property(property_name),
                property_value)

    def test_should_set_default_values_when_initializing_plugin(self):
        self.project.authors = [
            Author("John Doe", "John.doe@example.com"),
            Author("Jane Doe", "Jane.doe@example.com")]
        initialize_sphinx_plugin(self.project)

        self.project.set_property("sphinx_project_name", "foo")
        self.project.set_property("sphinx_project_version", "1.0")

        self.assertEquals(
            self.project.get_property("sphinx_source_dir"), "docs")
        self.assertEquals(
            self.project.get_property("sphinx_output_dir"), "docs/_build/")
        self.assertEquals(
            self.project.get_property("sphinx_config_path"), "docs")
        self.assertEquals(
            self.project.get_property("sphinx_doc_author"), 'John Doe, Jane Doe')
        self.assertEquals(
            self.project.get_property("sphinx_doc_builder"), "html")
        self.assertEquals(
            self.project.get_property("sphinx_project_name"), "foo")
        self.assertEquals(
            self.project.get_property("sphinx_project_version"), "1.0")


class SphinxBuildCommandTests(TestCase):
    def setUp(self):
        self.project = Project("basedir")

    def test_should_generate_sphinx_build_command_per_project_properties(self):
        self.project.set_property("sphinx_config_path", "docs/")
        self.project.set_property("sphinx_source_dir", "docs/")
        self.project.set_property("sphinx_output_dir", "docs/_build/")
        self.project.set_property("sphinx_doc_builder", 'JSONx')

        sphinx_build_command = get_sphinx_build_command(self.project, Mock(), 'JSONx')

        self.assertEqual(sphinx_build_command,
                         ["sphinx", "-b", "JSONx", "basedir/docs/", "basedir/docs/_build/"])

    def test_should_generate_sphinx_build_command_verbose(self):
        self.project.set_property("sphinx_config_path", "docs/")
        self.project.set_property("sphinx_source_dir", "docs/")
        self.project.set_property("sphinx_output_dir", "docs/_build/")
        self.project.set_property("sphinx_doc_builder", 'JSONx')
        self.project.set_property("verbose", True)

        sphinx_build_command = get_sphinx_build_command(self.project, Mock(), 'JSONx')

        self.assertEqual(sphinx_build_command,
                         ["sphinx", "-b", "JSONx", "-v", "basedir/docs/", "basedir/docs/_build/"])

    def test_should_generate_sphinx_build_command_debug(self):
        self.project.set_property("sphinx_config_path", "docs/")
        self.project.set_property("sphinx_source_dir", "docs/")
        self.project.set_property("sphinx_output_dir", "docs/_build/")
        self.project.set_property("sphinx_doc_builder", 'JSONx')

        logger = Mock()
        logger.threshold = 1
        logger.DEBUG = 1

        sphinx_build_command = get_sphinx_build_command(self.project, logger, 'JSONx')

        self.assertEqual(sphinx_build_command,
                         ["sphinx", "-b", "JSONx", "-vvvv", "basedir/docs/", "basedir/docs/_build/"])

    def test_should_generate_sphinx_build_command_forced_builder_dir(self):
        self.project.set_property("sphinx_config_path", "docs/")
        self.project.set_property("sphinx_source_dir", "docs/")
        self.project.set_property("sphinx_output_dir", "docs/_build/")
        self.project.set_property("sphinx_doc_builder", 'JSONx')
        self.project.set_property("sphinx_output_per_builder", True)

        sphinx_build_command = get_sphinx_build_command(self.project, Mock(), 'JSONx')

        self.assertEqual(sphinx_build_command,
                         ["sphinx", "-b", "JSONx", "basedir/docs/", "basedir/docs/_build/JSONx"])

    def test_should_generate_sphinx_build_command_builder_dir(self):
        self.project.set_property("sphinx_config_path", "docs/")
        self.project.set_property("sphinx_source_dir", "docs/")
        self.project.set_property("sphinx_output_dir", "docs/_build/")
        self.project.set_property("sphinx_doc_builder", ['JSONx', 'pdf'])

        sphinx_build_command = get_sphinx_build_command(self.project, Mock(), 'JSONx')

        self.assertEqual(sphinx_build_command,
                         ["sphinx", "-b", "JSONx", "basedir/docs/", "basedir/docs/_build/JSONx"])

    def test_should_generate_sphinx_quickstart_command_with_project_properties(self):
        self.project.set_property("sphinx_doc_author", "bar")
        self.project.set_property("sphinx_project_name", "foo")
        self.project.set_property("sphinx_project_version", "3")
        self.project.set_property("sphinx_source_dir", "docs/")

        sphinx_quickstart_command = get_sphinx_quickstart_command(self.project)

        self.assertEqual(sphinx_quickstart_command,
                         ["sphinx.quickstart", "-q", "-p", "foo", "-a", "bar", "-v", "3", "basedir/docs/"])

    @patch('pybuilder.plugins.python.sphinx_plugin.execute_command', return_value=0)
    def test_should_execute_command_regardless_of_verbose(self, exec_command):
        self.project.set_property("verbose", True)
        self.project.set_property("dir_target", "spam")
        initialize_sphinx_plugin(self.project)

        run_sphinx_build(["foo"], "bar", Mock(), self.project)
        self.assertEquals(exec_command.call_count, 1)

    def test_get_sphinx_apidoc_command_enabled(self):
        sphinx_mock = Mock()
        sys.modules["sphinx"] = sphinx_mock
        try:
            sphinx_mock.version_info = (1, 2, 3, 4, 5)

            self.project.set_property("sphinx_run_apidoc", True)
            self.project.set_property("dir_target", "dir_target")
            self.project.set_property("dir_source_main_python", "dir_source")
            self.project.set_property("sphinx_project_name", "project_name")

            self.assertEqual(get_sphinx_apidoc_command(self.project),
                             ['sphinx.apidoc',
                              '-H',
                              'project_name',
                              '-o',
                              'basedir/dir_target/sphinx_pyb/apidoc',
                              'basedir/dir_source'
                              ]
                             )
        finally:
            del sys.modules["sphinx"]

    def test_get_sphinx_apidoc_command_enabled_with_pep420(self):
        sphinx_mock = Mock()
        sys.modules["sphinx"] = sphinx_mock

        try:
            sphinx_mock.version_info = (1, 5, 3, 4, 5)

            self.project.set_property("sphinx_run_apidoc", True)
            self.project.set_property("dir_target", "dir_target")
            self.project.set_property("dir_source_main_python", "dir_source")
            self.project.set_property("sphinx_project_name", "project_name")

            self.assertEqual(get_sphinx_apidoc_command(self.project),
                             ['sphinx.apidoc',
                              '-H',
                              'project_name',
                              '--implicit-namespaces',
                              '-o',
                              'basedir/dir_target/sphinx_pyb/apidoc',
                              'basedir/dir_source'
                              ] if sys.version_info[:3] >= (3, 3) else
                             ['sphinx.apidoc',
                              '-H',
                              'project_name',
                              '-o',
                              'basedir/dir_target/sphinx_pyb/apidoc',
                              'basedir/dir_source'
                              ]
                             )
        finally:
            del sys.modules["sphinx"]

    @patch("pybuilder.plugins.python.sphinx_plugin.open", create=True)
    @patch("pybuilder.plugins.python.sphinx_plugin.rmtree")
    @patch("pybuilder.plugins.python.sphinx_plugin.exists")
    @patch("pybuilder.plugins.python.sphinx_plugin.mkdir")
    @patch("pybuilder.plugins.python.sphinx_plugin.os.symlink")
    @patch("pybuilder.plugins.python.sphinx_plugin.execute_command")
    def test_sphinx_pyb_quickstart_generate(self,
                                            execute_command,
                                            symlink,
                                            mkdir,
                                            exists,
                                            rmtree,
                                            open
                                            ):
        execute_command.return_value = 0
        exists.return_value = False

        self.project.set_property("sphinx_source_dir", "sphinx_source_dir")
        self.project.set_property("sphinx_config_path", "sphinx_config_path")
        self.project.set_property("dir_target", "dir_target")
        self.project.set_property("dir_source_main_python", "dir_source")
        self.project.set_property("sphinx_project_name", "project_name")

        sphinx_pyb_quickstart_generate(self.project, Mock())

        open().__enter__().write.assert_called_with("""\
# Automatically generated by PyB
import sys
from os import path

sphinx_pyb_dir = path.abspath(path.join(path.dirname(__file__) if __file__ else ".", "../basedir/dir_target/sphinx_pyb"))
sphinx_pyb_module = "sphinx_pyb_conf"
sphinx_pyb_module_file = path.abspath(path.join(sphinx_pyb_dir, sphinx_pyb_module + ".py"))

sys.path.insert(0, sphinx_pyb_dir)

if not path.exists(sphinx_pyb_module_file):
    raise RuntimeError("No PyB-based Sphinx configuration found in " + sphinx_pyb_module_file)

from sphinx_pyb_conf import *

# Overwrite PyB-settings here statically if that's the thing that you want
""")
        symlink.assert_called_with("../basedir/dir_target/sphinx_pyb/apidoc",
                                   "basedir/sphinx_source_dir/apidoc",
                                   target_is_directory=True)

    @patch("pybuilder.plugins.python.sphinx_plugin.sphinx_quickstart_generate")
    def test_sphinx_pyb_quickstart_generate_raise_symlink_unavailable(self, sphinx_quickstart_generate):
        import os
        delattr(os, 'symlink')
        self.assertRaises(
            BuildFailedException,
            sphinx_pyb_quickstart_generate,
            self.project,
            Mock()
        )
        self.assertFalse(sphinx_quickstart_generate.called)

    @patch("pybuilder.plugins.python.sphinx_plugin.open", create=True)
    @patch("pybuilder.plugins.python.sphinx_plugin.rmtree")
    @patch("pybuilder.plugins.python.sphinx_plugin.exists")
    @patch("pybuilder.plugins.python.sphinx_plugin.mkdir")
    @patch("pybuilder.plugins.python.sphinx_plugin.execute_command")
    def test_sphinx_generate(self,
                             execute_command,
                             mkdir,
                             exists,
                             rmtree,
                             open
                             ):
        execute_command.return_value = 0
        exists.return_value = True

        sphinx_mock = Mock()
        sys.modules["sphinx"] = sphinx_mock

        try:
            sphinx_mock.version_info = (1, 5, 3, 4, 5)

            self.project.set_property("sphinx_source_dir", "sphinx_source_dir")
            self.project.set_property("sphinx_config_path", "sphinx_config_path")
            self.project.set_property("sphinx_output_dir", "sphinx_output_dir")
            self.project.set_property("dir_target", "dir_target")
            self.project.set_property("dir_source_main_python", "dir_source")
            self.project.set_property("sphinx_project_name", "project_name")
            self.project.set_property("sphinx_project_conf", {"a": 1, "b": "foo"})
            self.project.set_property("sphinx_run_apidoc", True)
            self.project.set_property("sphinx_doc_builder", ['JSONx', 'pdf'])

            sphinx_generate(self.project, Mock())
        finally:
            del sys.modules["sphinx"]

        exists.assert_called_with("basedir/dir_target/sphinx_pyb/apidoc")
        rmtree.assert_called_with("basedir/dir_target/sphinx_pyb/apidoc")
        mkdir.assert_called_with("basedir/dir_target/sphinx_pyb/apidoc")
        open().__enter__().write.assert_has_calls([call("a = 1\n"), call("b = 'foo'\n"), call(
            "\nimport sys\nsys.path.insert(0, 'basedir/dir_source')\n")], any_order=True)
        execute_command.assert_has_calls([
            call([sys.executable, '-m', 'sphinx.apidoc', '-H', 'project_name', '-o',
                  'basedir/dir_target/sphinx_pyb/apidoc', 'basedir/dir_source']
                 if sys.version_info[:2] < (3, 3) else
                 [sys.executable, '-m', 'sphinx.apidoc', '-H', 'project_name', '--implicit-namespaces', '-o',
                  'basedir/dir_target/sphinx_pyb/apidoc', 'basedir/dir_source'],
                 'basedir/dir_target/reports/sphinx-apidoc', shell=False),
            call([sys.executable, '-m', 'sphinx', '-b', 'JSONx', 'basedir/sphinx_config_path',
                  'basedir/sphinx_output_dir/JSONx'],
                 'basedir/dir_target/reports/sphinx_JSONx', shell=False),
            call([sys.executable, '-m', 'sphinx', '-b', 'pdf', 'basedir/sphinx_config_path',
                  'basedir/sphinx_output_dir/pdf'],
                 'basedir/dir_target/reports/sphinx_pdf', shell=False)])

    @patch("pybuilder.plugins.python.sphinx_plugin.open", create=True)
    @patch("pybuilder.plugins.python.sphinx_plugin.rmtree")
    @patch("pybuilder.plugins.python.sphinx_plugin.exists")
    @patch("pybuilder.plugins.python.sphinx_plugin.mkdir")
    @patch("pybuilder.plugins.python.sphinx_plugin.execute_command")
    def test_apidoc_does_not_run_when_off(self,
                                          execute_command,
                                          mkdir,
                                          exists,
                                          rmtree,
                                          open
                                          ):
        self.project.set_property("sphinx_run_apidoc", False)

        generate_sphinx_apidocs(self.project, Mock())
        exists.assert_not_called()
