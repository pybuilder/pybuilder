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

from test_utils import Mock, patch

from pybuilder.core import Project
from pybuilder.errors import BuildFailedException
from pybuilder.plugins.python.pdoc_plugin import (
    pdoc_compile_docs,
    pdoc_init,
    pdoc_prepare,
)


class PdocPluginTests(unittest.TestCase):
    def setUp(self):
        self.logger = Mock()
        self.project = Project(".")
        self.project.set_property("dir_target", "dir_target_value")
        self.project.set_property(
            "dir_source_main_python", "dir_source_main_python_value"
        )
        self.project.set_property("dir_reports", "dir_reports_value")

        self.reactor = Mock()
        pyb_env = Mock()
        pyb_env.environ = {"PATH": "a"}
        pyb_env.execute_command.return_value = 0
        self.reactor.python_env_registry = {"pybuilder": pyb_env}
        self.reactor.pybuilder_venv = pyb_env

    @patch("pybuilder.plugins.python.pdoc_plugin.os.mkdir")
    @patch("pybuilder.plugins.python.pdoc_plugin.os.path.exists")
    def test_pdoc_prepare_works(self, os_path_exists, os_mkdir):
        pdoc_init(self.project)

        os_path_exists.return_value = False
        pdoc_prepare(self.project, self.logger, self.reactor)
        self.assertEqual(os_mkdir.call_count, 1)

        os_path_exists.return_value = True
        pdoc_prepare(self.project, self.logger, self.reactor)
        self.assertEqual(os_mkdir.call_count, 1)

        self.assertEqual(self.reactor.pybuilder_venv.verify_can_execute.call_count, 2)

    @patch("pybuilder.plugins.python.pdoc_plugin.tail_log")
    @patch("pybuilder.plugins.python.pdoc_plugin.os.mkdir")
    @patch("pybuilder.plugins.python.pdoc_plugin.os.path.exists")
    def test_pdoc_requires_module_name(self, *_):
        pdoc_init(self.project)

        self.assertRaises(
            BuildFailedException,
            pdoc_compile_docs,
            self.project,
            self.logger,
            self.reactor,
        )

    @patch("pybuilder.plugins.python.pdoc_plugin.tail_log")
    @patch("pybuilder.plugins.python.pdoc_plugin.os.mkdir")
    @patch("pybuilder.plugins.python.pdoc_plugin.os.path.exists")
    def test_pdoc_html_adds_html_dir(self, *_):
        pdoc_init(self.project)
        self.project.set_property("pdoc_module_name", "pdoc_module_name_value")

        self.project.set_property("pdoc_command_args", [])
        pdoc_compile_docs(self.project, self.logger, self.reactor)
        pyb_env = self.reactor.pybuilder_venv
        pyb_env.execute_command.assert_called_with(
            ["pdoc", "pdoc_module_name_value"],
            cwd=self.project.expand_path("$dir_target", "pdocs"),
            env={
                "PYTHONPATH": self.project.expand_path("$dir_source_main_python"),
                "PATH": pyb_env.environ["PATH"],
            },
            outfile_name=self.project.expand_path("$dir_reports", "pdoc"),
            error_file_name=self.project.expand_path("$dir_reports", "pdoc.err"),
        )

        self.project.set_property("pdoc_command_args", ["--html"])
        pdoc_compile_docs(self.project, self.logger, self.reactor)
        pyb_env.execute_command.assert_called_with(
            [
                "pdoc",
                "--html",
                "--html-dir",
                self.project.expand_path("$dir_target", "pdocs"),
                "pdoc_module_name_value",
            ],
            cwd=self.project.expand_path("$dir_target", "pdocs"),
            env={
                "PYTHONPATH": self.project.expand_path("$dir_source_main_python"),
                "PATH": pyb_env.environ["PATH"],
            },
            outfile_name=self.project.expand_path("$dir_reports", "pdoc"),
            error_file_name=self.project.expand_path("$dir_reports", "pdoc.err"),
        )
