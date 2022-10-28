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

import sys
from os.path import relpath
from unittest import TestCase

from pybuilder.core import Project, Author, Logger
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
from pybuilder.utils import np, jp
from test_utils import Mock, patch, call, ANY


class CheckSphinxAvailableTests(TestCase):
    def test_should_check_that_sphinx_can_be_executed(self):
        mock_project = Mock(Project)
        mock_logger = Mock(Logger)
        reactor = Mock()
        pyb_env = Mock()
        reactor.python_env_registry = {"pybuilder": pyb_env}
        reactor.pybuilder_venv = pyb_env

        assert_sphinx_is_available(mock_project, mock_logger, reactor)

        pyb_env.verify_can_execute.assert_has_calls(
            [
                call(["sphinx-build", "--version"], "sphinx-build", "plugin python.sphinx"),
                call(["sphinx-apidoc", "--version"], "sphinx-apidoc", "plugin python.sphinx")
            ]
        )

    def test_should_check_that_sphinx_quickstart_can_be_executed(self):
        mock_project = Mock(Project)
        mock_logger = Mock(Logger)
        reactor = Mock()
        pyb_env = Mock()
        reactor.python_env_registry = {"pybuilder": pyb_env}
        reactor.pybuilder_venv = pyb_env

        assert_sphinx_quickstart_is_available(mock_project, mock_logger, reactor)

        pyb_env.verify_can_execute.assert_called_with(
            ["sphinx-quickstart", "--version"], "sphinx-quickstart", "plugin python.sphinx")


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
            self.assertEqual(

                self.project.get_property(property_name),
                property_value)

    def test_should_set_default_values_when_initializing_plugin(self):
        self.project.authors = [
            Author("John Doe", "John.doe@example.com"),
            Author("Jane Doe", "Jane.doe@example.com")]
        initialize_sphinx_plugin(self.project)

        self.project.set_property("sphinx_project_name", "foo")
        self.project.set_property("sphinx_project_version", "1.0")

        self.assertEqual(
            self.project.get_property("sphinx_source_dir"), "docs")
        self.assertEqual(
            self.project.get_property("sphinx_output_dir"), np("docs/_build/"))
        self.assertEqual(
            self.project.get_property("sphinx_config_path"), "docs")
        self.assertEqual(
            self.project.get_property("sphinx_doc_author"), "John Doe, Jane Doe")
        self.assertEqual(
            self.project.get_property("sphinx_doc_builder"), "html")
        self.assertEqual(
            self.project.get_property("sphinx_project_name"), "foo")
        self.assertEqual(
            self.project.get_property("sphinx_project_version"), "1.0")


class SphinxBuildCommandTests(TestCase):
    def setUp(self):
        self.project = Project("basedir")
        self.logger = Mock(Logger)
        self.reactor = Mock()
        self.pyb_env = pyb_env = Mock()
        self.reactor.python_env_registry = {"pybuilder": pyb_env}
        self.reactor.pybuilder_venv = pyb_env

        pyb_env.execute_command.return_value = 0
        pyb_env.version = (2, 7, 12, 'final', 0)
        pyb_env.executable = ["/a/b"]
        pyb_env.exec_dir = "/a"

    def test_should_generate_sphinx_build_command_per_project_properties(self):
        self.project.set_property("sphinx_config_path", "docs/")
        self.project.set_property("sphinx_source_dir", "docs/")
        self.project.set_property("sphinx_output_dir", "docs/_build/")
        self.project.set_property("sphinx_doc_builder", "JSONx")

        sphinx_build_command = get_sphinx_build_command(self.project, Mock(), "JSONx")

        self.assertEqual(sphinx_build_command,
                         [ANY, "-b", "JSONx",
                          np(jp(self.project.basedir, "docs/")),
                          np(jp(self.project.basedir, "docs/_build/"))])

    def test_should_generate_sphinx_build_command_verbose(self):
        self.project.set_property("sphinx_config_path", "docs/")
        self.project.set_property("sphinx_source_dir", "docs/")
        self.project.set_property("sphinx_output_dir", "docs/_build/")
        self.project.set_property("sphinx_doc_builder", "JSONx")
        self.project.set_property("verbose", True)

        sphinx_build_command = get_sphinx_build_command(self.project, Mock(), "JSONx")

        self.assertEqual(sphinx_build_command,
                         [ANY, "-b", "JSONx", "-v",
                          np(jp(self.project.basedir, "docs/")),
                          np(jp(self.project.basedir, "docs/_build/"))])

    def test_should_generate_sphinx_build_command_debug(self):
        self.project.set_property("sphinx_config_path", "docs/")
        self.project.set_property("sphinx_source_dir", "docs/")
        self.project.set_property("sphinx_output_dir", "docs/_build/")
        self.project.set_property("sphinx_doc_builder", "JSONx")

        logger = Mock()
        logger.level = 1
        logger.DEBUG = 1

        sphinx_build_command = get_sphinx_build_command(self.project, logger, "JSONx")

        self.assertEqual(sphinx_build_command,
                         [ANY, "-b", "JSONx", "-vvvv",
                          np(jp(self.project.basedir, "docs/")),
                          np(jp(self.project.basedir, "docs/_build/"))])

    def test_should_generate_sphinx_build_command_forced_builder_dir(self):
        self.project.set_property("sphinx_config_path", "docs/")
        self.project.set_property("sphinx_source_dir", "docs/")
        self.project.set_property("sphinx_output_dir", "docs/_build/")
        self.project.set_property("sphinx_doc_builder", "JSONx")
        self.project.set_property("sphinx_output_per_builder", True)

        sphinx_build_command = get_sphinx_build_command(self.project, Mock(), "JSONx")

        self.assertEqual(sphinx_build_command,
                         [ANY, "-b", "JSONx",
                          np(jp(self.project.basedir, "docs/")),
                          np(jp(self.project.basedir, "docs/_build/JSONx"))])

    def test_should_generate_sphinx_build_command_builder_dir(self):
        self.project.set_property("sphinx_config_path", "docs/")
        self.project.set_property("sphinx_source_dir", "docs/")
        self.project.set_property("sphinx_output_dir", "docs/_build/")
        self.project.set_property("sphinx_doc_builder", ["JSONx", "pdf"])

        sphinx_build_command = get_sphinx_build_command(self.project, Mock(), "JSONx")

        self.assertEqual(sphinx_build_command,
                         [ANY, "-b", "JSONx",
                          np(jp(self.project.basedir, "docs/")),
                          np(jp(self.project.basedir, "docs/_build/JSONx"))
                          ])

    def test_should_generate_sphinx_quickstart_command_with_project_properties(self):
        self.project.set_property("sphinx_doc_author", "bar")
        self.project.set_property("sphinx_project_name", "foo")
        self.project.set_property("sphinx_project_version", "3")
        self.project.set_property("sphinx_source_dir", "docs/")

        sphinx_quickstart_command = get_sphinx_quickstart_command(self.project)

        self.assertEqual(sphinx_quickstart_command,
                         [ANY, "-q", "-p", "foo", "-a", "bar", "-v", "3",
                          np(jp(self.project.basedir, "docs/"))
                          ])

    def test_should_execute_command_regardless_of_verbose(self):
        self.project.set_property("verbose", True)
        self.project.set_property("dir_target", "spam")
        initialize_sphinx_plugin(self.project)

        run_sphinx_build(["foo"], "bar", Mock(), self.project, self.reactor)
        self.assertEqual(self.pyb_env.execute_command.call_count, 1)

    def test_get_sphinx_apidoc_command_enabled(self):
        sphinx_mock = Mock()
        sys.modules["sphinx"] = sphinx_mock

        try:
            sphinx_mock.version_info = (1, 2, 3, 4, 5)

            self.project.set_property("sphinx_run_apidoc", True)
            self.project.set_property("dir_target", "dir_target")
            self.project.set_property("dir_source_main_python", "dir_source")
            self.project.set_property("sphinx_project_name", "project_name")

            self.assertEqual(get_sphinx_apidoc_command(self.project, self.reactor),
                             [ANY,
                              "-H",
                              "project_name",
                              "-o",
                              np(jp(self.project.basedir, "dir_target/sphinx_pyb/apidoc")),
                              np(jp(self.project.basedir, "dir_source"))
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

            self.assertEqual(get_sphinx_apidoc_command(self.project, self.reactor),
                             [ANY,
                              "-H",
                              "project_name",
                              "-o",
                              np(jp(self.project.basedir, "dir_target/sphinx_pyb/apidoc")),
                              np(jp(self.project.basedir, "dir_source"))
                              ]
                             )
            self.reactor.pybuilder_venv.version = (3, 5, 6, 'final', 0)
            self.assertEqual(get_sphinx_apidoc_command(self.project, self.reactor),
                             [ANY,
                              "-H",
                              "project_name",
                              "--implicit-namespaces",
                              "-o",
                              np(jp(self.project.basedir, "dir_target/sphinx_pyb/apidoc")),
                              np(jp(self.project.basedir, "dir_source"))
                              ])
        finally:
            del sys.modules["sphinx"]

    @patch("pybuilder.plugins.python.sphinx_plugin.open", create=True)
    @patch("pybuilder.plugins.python.sphinx_plugin.rmtree")
    @patch("pybuilder.plugins.python.sphinx_plugin.exists")
    @patch("pybuilder.plugins.python.sphinx_plugin.mkdir")
    @patch("pybuilder.plugins.python.sphinx_plugin.symlink")
    def test_sphinx_pyb_quickstart_generate(self,
                                            symlink,
                                            mkdir,
                                            exists,
                                            rmtree,
                                            open
                                            ):
        exists.return_value = False

        self.project.set_property("sphinx_source_dir", "sphinx_source_dir")
        self.project.set_property("sphinx_config_path", "sphinx_config_path")
        self.project.set_property("dir_target", "dir_target")
        self.project.set_property("dir_source_main_python", "dir_source")
        self.project.set_property("sphinx_project_name", "project_name")

        sphinx_pyb_quickstart_generate(self.project, Mock(), self.reactor)

        open().__enter__().write.assert_called_with("""\
# Automatically generated by PyB
import sys
from os.path import normcase as nc, normpath as np, join as jp, dirname, exists

sphinx_pyb_dir = nc(np(jp(dirname(__file__) if __file__ else '.', %r)))
sphinx_pyb_module = 'sphinx_pyb_conf'
sphinx_pyb_module_file = nc(np(jp(sphinx_pyb_dir, sphinx_pyb_module + '.py')))

sys.path.insert(0, sphinx_pyb_dir)

if not exists(sphinx_pyb_module_file):
    raise RuntimeError("No PyB-based Sphinx configuration found in " + sphinx_pyb_module_file)

from sphinx_pyb_conf import *

# Overwrite PyB-settings here statically if that's the thing that you want
""" % relpath(np(jp(self.project.basedir, "../dir_target/sphinx_pyb")), self.project.basedir))
        symlink.assert_called_with(relpath(np(jp(self.project.basedir, "../dir_target/sphinx_pyb/apidoc")),
                                           self.project.basedir),
                                   np(jp(self.project.basedir, "sphinx_source_dir/apidoc")),
                                   target_is_directory=True)

    @patch("pybuilder.plugins.python.sphinx_plugin.open", create=True)
    @patch("pybuilder.plugins.python.sphinx_plugin.rmtree")
    @patch("pybuilder.plugins.python.sphinx_plugin.exists")
    @patch("pybuilder.plugins.python.sphinx_plugin.mkdir")
    def test_sphinx_generate(self,
                             mkdir,
                             exists,
                             rmtree,
                             open
                             ):
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
            self.project.set_property("sphinx_doc_builder", ["JSONx", "pdf"])

            sphinx_generate(self.project, Mock(), self.reactor)
        finally:
            del sys.modules["sphinx"]

        exists.assert_called_with(np(jp(self.project.basedir, "dir_target/sphinx_pyb/apidoc")))
        rmtree.assert_called_with(np(jp(self.project.basedir, "dir_target/sphinx_pyb/apidoc")))
        mkdir.assert_called_with(np(jp(self.project.basedir, "dir_target/sphinx_pyb/apidoc")))

        open().__enter__().write.assert_has_calls([call("a = 1\n"), call("b = 'foo'\n"), call(
            "\nimport sys\nsys.path.insert(0, %r)\n" % np(jp(self.project.basedir, "dir_source")))], any_order=True)
        self.pyb_env.execute_command.assert_has_calls([
            call(self.reactor.pybuilder_venv.executable + ["-c", ANY,
                                                           "-H", "project_name", "-o",
                                                           np(jp(self.project.basedir, "dir_target/sphinx_pyb/apidoc")),
                                                           np(jp(self.project.basedir, "dir_source"))],
                 np(jp(self.project.basedir, "dir_target/reports/sphinx-apidoc")), shell=False),
            call(self.reactor.pybuilder_venv.executable + ["-c", ANY, "-b", "JSONx",
                                                           np(jp(self.project.basedir, "sphinx_config_path")),
                                                           np(jp(self.project.basedir, "sphinx_output_dir/JSONx"))],
                 np(jp(self.project.basedir, "dir_target/reports/sphinx_JSONx")), shell=False),
            call(self.reactor.pybuilder_venv.executable + ["-c", ANY, "-b", "pdf",
                                                           np(jp(self.project.basedir, "sphinx_config_path")),
                                                           np(jp(self.project.basedir, "sphinx_output_dir/pdf"))],
                 np(jp(self.project.basedir, "dir_target/reports/sphinx_pdf")), shell=False)])

    @patch("pybuilder.plugins.python.sphinx_plugin.open", create=True)
    @patch("pybuilder.plugins.python.sphinx_plugin.rmtree")
    @patch("pybuilder.plugins.python.sphinx_plugin.exists")
    @patch("pybuilder.plugins.python.sphinx_plugin.mkdir")
    def test_apidoc_does_not_run_when_off(self,
                                          mkdir,
                                          exists,
                                          rmtree,
                                          open
                                          ):
        self.project.set_property("sphinx_run_apidoc", False)

        generate_sphinx_apidocs(self.project, Mock(), self.reactor)
        exists.assert_not_called()
