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
from os.path import join as jp
from unittest import TestCase

from pybuilder.core import Project, Logger
from pybuilder.plugins.python.coverage_plugin import (init_coverage_properties,
                                                      _build_module_report,
                                                      _build_coverage_report,
                                                      _optimize_omit_module_files,
                                                      )
from test_utils import patch, MagicMock, Mock

if sys.version_info[0] < 3:  # if major is less than 3
    import_patch = "__builtin__.__import__"
else:
    import_patch = "builtins.__import__"


class CoveragePluginTests(TestCase):
    def setUp(self):
        self.project = Project("basedir")

    def test_should_leave_user_specified_properties_when_initializing_plugin(self):

        expected_properties = {
            "coverage_threshold_warn": 120,
            "coverage_branch_threshold_warn": 120,
            "coverage_branch_partial_threshold_warn": 120,
            "coverage_break_build": False,
            "coverage_reload_modules": False,
            "coverage_exceptions": ["foo"],
            "coverage_fork": True
        }

        for property_name, property_value in expected_properties.items():
            self.project.set_property(property_name, property_value)

            init_coverage_properties(self.project)

        for property_name, property_value in expected_properties.items():
            self.assertEqual(self.project.get_property("coverage_threshold_warn"), 120)
            self.assertEqual(self.project.get_property("coverage_branch_threshold_warn"), 120)
            self.assertEqual(self.project.get_property("coverage_branch_partial_threshold_warn"), 120)
            self.assertEqual(self.project.get_property("coverage_break_build"), False)
            self.assertEqual(self.project.get_property("coverage_reload_modules"), False)
            self.assertEqual(self.project.get_property("coverage_exceptions"), ["foo"])
            self.assertEqual(self.project.get_property("coverage_fork"), True)

    @patch("coverage.results.Analysis")
    @patch("coverage.coverage")
    def test_build_module_report_zero_content(self, coverage, analysis):
        coverage._analyze.return_value = analysis
        n = analysis.numbers
        n.n_statements = 0
        n.n_excluded = 0
        n.n_missing = 0
        n.n_branches = 0
        n.n_partial_branches = 0
        n.n_missing_branches = 0

        report = _build_module_report(coverage, MagicMock())
        self.assertEqual(report.code_coverage, 100)
        self.assertEqual(report.branch_coverage, 100)
        self.assertEqual(report.branch_partial_coverage, 100)

    @patch("coverage.results.Analysis")
    @patch("coverage.coverage")
    def test_build_module_report_zero_coverage(self, coverage, analysis):
        coverage._analyze.return_value = analysis
        n = analysis.numbers
        n.n_statements = 10
        n.n_excluded = 0
        n.n_missing = 10
        n.n_branches = 10
        n.n_partial_branches = 10
        n.n_missing_branches = 10

        report = _build_module_report(coverage, MagicMock())
        self.assertEqual(report.code_coverage, 0)
        self.assertEqual(report.branch_coverage, 0)
        self.assertEqual(report.branch_partial_coverage, 0)

    @patch("coverage.results.Analysis")
    @patch("coverage.coverage")
    def test_build_module_report_half_coverage(self, coverage, analysis):
        coverage._analyze.return_value = analysis
        n = analysis.numbers
        n.n_statements = 10
        n.n_excluded = 0
        n.n_missing = 5
        n.n_branches = 10
        n.n_partial_branches = 5
        n.n_missing_branches = 5

        report = _build_module_report(coverage, MagicMock())
        self.assertEqual(report.code_coverage, 50)
        self.assertEqual(report.branch_coverage, 50)
        self.assertEqual(report.branch_partial_coverage, 50)

    @patch("coverage.coverage")
    def test_build_coverage_report_no_modules(self, coverage):
        execution_name = "mock"
        execution_description = "mock coverage"
        config_prefix = "mock_coverage"
        project = Mock()
        source_path = ""
        module_names = []
        module_files = []
        project.get_property.side_effect = [70, 70, 70, [], False, False, False]
        self.assertTrue(_build_coverage_report(project, MagicMock(Logger), execution_description, execution_name,
                                               config_prefix, coverage, source_path, module_names,
                                               module_files) is None)

    @patch("pybuilder.plugins.python.coverage_plugin.render_report")
    @patch("coverage.coverage")
    def test_build_coverage_report_two_module(self, coverage, render_report):
        execution_name = "mock"
        execution_description = "mock coverage"
        config_prefix = "mock_coverage"
        project = Mock()
        source_path = ""
        module_names = ["module_a", "module_b"]
        module_files = ["module_a.py", "module_b.py"]

        project.get_property.side_effect = [70, 70, 70, False, False, False]

        module_a_coverage = Mock()
        module_a_coverage.statements = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        module_a_coverage.excluded = []
        module_a_coverage.missing = [1, 2, 3, 4, 5]
        n = module_a_coverage.numbers
        n.n_statements = 10
        n.n_excluded = 0
        n.n_missing = 5
        n.n_branches = 8
        n.n_partial_branches = 5
        n.n_missing_branches = 5

        module_b_coverage = Mock()
        module_b_coverage.statements = [1, 2, 3, 4, 5]
        module_b_coverage.excluded = []
        module_b_coverage.missing = [1, 2]
        n = module_b_coverage.numbers
        n.n_statements = 4
        n.n_excluded = 0
        n.n_missing = 2
        n.n_branches = 8
        n.n_partial_branches = 3
        n.n_missing_branches = 3

        coverage._analyze.side_effect = [module_a_coverage, module_b_coverage]
        self.assertTrue(_build_coverage_report(project, MagicMock(Logger), execution_description, execution_name,
                                               config_prefix, coverage, source_path, module_names,
                                               module_files) is None)
        report = render_report.call_args[0][0]
        self.assertEqual(report["overall_coverage"], 50)
        self.assertEqual(report["overall_branch_coverage"], 50)
        self.assertEqual(report["overall_branch_partial_coverage"], 50)

    def test__optimize_omit_module_files(self):
        module_files = ["/a/b/c/d/x.py",
                        "/a/b/c/d/y.py",
                        "/a/x/z.py",
                        "/a/b/o.py"
                        ]

        self.assertEqual(_optimize_omit_module_files(module_files, ["/a/b/c/d/x.py",
                                                                    "/a/b/c/d/y.py"]),
                         [jp("/a/b/c", "*")])

        self.assertEqual(_optimize_omit_module_files(module_files, ["/a/z.py",
                                                                    "/a/b/o.py"]),
                         ["/a/b/o.py", "/a/z.py"])

        self.assertEqual(_optimize_omit_module_files(module_files, ["/a/b/c/d/x.py"]),
                         ["/a/b/c/d/x.py"])
