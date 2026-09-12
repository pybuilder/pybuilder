#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2026 PyBuilder Team
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

"""The project a subprocess coverage integration test builds, and how it is judged.

Both the VEnv and the `--no-venvs` test measure the same thing and have to keep
measuring the same thing to be worth comparing, so they share the project they build
rather than each carrying a copy of it.
"""

import json
import textwrap

# Only ever imported by a subprocess a unit test spawns
IN_SUBPROCESS_SOURCE = textwrap.dedent("""
    def only_called_in_a_subprocess(value):
        if value > 0:
            return "positive"
        return "not positive"
    """)

# Only ever imported by an integration test, which runs out of the built distribution,
# so what it measures only lands under the sources once the paths have been normalized
IN_INTEGRATION_SOURCE = textwrap.dedent("""
    def only_called_by_an_integration_test(value):
        if value > 0:
            return "it positive"
        return "it not positive"
    """)

UNIT_TEST_SOURCE = textwrap.dedent("""
    import os
    import subprocess
    import sys
    import unittest
    from os.path import abspath, dirname, join as jp

    SOURCE_PATH = jp(dirname(dirname(dirname(abspath(__file__)))), "main", "python")

    PROGRAM = ("from covered_code.in_subprocess import only_called_in_a_subprocess\\n"
               "print(only_called_in_a_subprocess(1))\\n"
               "print(only_called_in_a_subprocess(-1))\\n")


    class CodeTests(unittest.TestCase):
        def test_module_is_only_ever_imported_by_a_subprocess(self):
            env = dict(os.environ)
            env["PYTHONPATH"] = SOURCE_PATH

            result = subprocess.run([sys.executable, "-c", PROGRAM], env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.split(), ["positive", "not", "positive"])
    """)

INTEGRATION_TEST_SOURCE = textwrap.dedent("""
    import unittest

    from covered_code.in_integration import only_called_by_an_integration_test


    class CodeIntegrationTests(unittest.TestCase):
        def test_positive(self):
            self.assertEqual(only_called_by_an_integration_test(1), "it positive")

        def test_not_positive(self):
            self.assertEqual(only_called_by_an_integration_test(-1), "it not positive")


    if __name__ == "__main__":
        unittest.main()
    """)

# An integration test is given an environment built from scratch, which on Windows is
# not enough for a Python to start at all - it needs PATH to load its DLLs, and without
# SystemRoot it cannot even seed its hash randomization. Every project here that runs
# integration tests says so, the same way PyBuilder's own build does.
INTEGRATION_TEST_PROPERTIES = """
    project.set_property("integrationtest_inherit_environment", True)"""

UNIT_TEST_REPORT = "target/reports/pybuilder.plugins.python.unittest_plugin.run_unit_tests_coverage.json"
INTEGRATION_TEST_REPORT = ("target/reports/"
                           "pybuilder.plugins.python.integrationtest_plugin.run_integration_tests_coverage.json")


class SubprocessCoverageTestSupport(object):
    """Writes the measured project, and reads the verdict back out of the reports.

    Mixed into a `BaseIntegrationTestSupport` subclass, whose file writing and path
    handling it uses.
    """

    def write_measured_project(self, name, plugins, with_integration_tests=False):
        self.write_build_file(textwrap.dedent("""
            from pybuilder.core import init, use_plugin

            %(plugins)s

            name = "%(name)s"

            @init
            def init(project):
                project.set_property("coverage_break_build", False)
            %(integration_test_properties)s
        """) % {"name": name,
                "plugins": "\n".join('use_plugin("%s")' % plugin for plugin in plugins),
                "integration_test_properties": INTEGRATION_TEST_PROPERTIES if with_integration_tests else ""})

        self.create_directory("src/main/python/covered_code")
        self.create_directory("src/unittest/python")

        self.write_file("src/main/python/covered_code/__init__.py", "")
        self.write_file("src/main/python/covered_code/in_subprocess.py", IN_SUBPROCESS_SOURCE)
        self.write_file("src/unittest/python/code_tests.py", UNIT_TEST_SOURCE)

        if with_integration_tests:
            self.create_directory("src/integrationtest/python")
            self.write_file("src/main/python/covered_code/in_integration.py", IN_INTEGRATION_SOURCE)
            self.write_file("src/integrationtest/python/code_integration_tests.py", INTEGRATION_TEST_SOURCE)

    def assert_fully_covered(self, report_name, module_name):
        with open(self.full_path(report_name)) as report_file:
            report = json.load(report_file)

        modules = {module["module"]: module for module in report["module_names"]}
        self.assertIn(module_name, modules)

        module = modules[module_name]
        self.assertEqual(module["sum_lines_not_covered"], 0,
                         "lines %r of %s went unmeasured" % (module["lines_not_covered"], module_name))
        self.assertEqual(module["branches_missing"], 0)
