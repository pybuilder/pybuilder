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

import os
import subprocess
import sys
import unittest

import pybuilder.extern  # noqa: F401 - makes the vendored `virtualenv` importable
from base_itest_support import BaseIntegrationTestSupport
from coverage_itest_support import SubprocessCoverageTestSupport, UNIT_TEST_REPORT, INTEGRATION_TEST_REPORT
from pybuilder.plugins.python._coverage_util import subprocess_coverage_env_from_environ
from pybuilder.python_env import create_venv, venv_symlinks, _venv_python_executable

# `pyb` itself, for a Python that has no PyBuilder console script installed
RUN_PYBUILDER = "import sys; from pybuilder.cli import main; sys.exit(main())"


class NoVenvsSubprocessCoverageTest(SubprocessCoverageTestSupport, BaseIntegrationTestSupport):
    """Subprocesses have to be measured with `--no-venvs` too, where nothing is ours to plant into.

    Every environment of such a build is the Python PyBuilder was started with, so the
    startup hook PyBuilder plants into the VEnvs it builds is deliberately not planted
    here. What makes measurement happen instead is Coverage's own startup hook, which
    lives in that Python next to the Coverage the build installed into it - and what
    makes the result usable is that the hook's Coverage gets adopted rather than stacked
    on, so its data goes through path normalization before it is saved.

    The build therefore cannot run in this test's own interpreter: it needs a Python it
    is free to install Coverage into. It gets a throwaway VEnv of its own, and is run at
    arm's length the way a user would run it.
    """

    def test(self):
        self.write_measured_project("no_venvs_coverage_tests",
                                    ["python.core", "python.unittest", "python.integrationtest", "python.coverage"],
                                    with_integration_tests=True)

        self.build_without_venvs()

        self.assert_fully_covered(UNIT_TEST_REPORT, "covered_code.in_subprocess")
        self.assert_fully_covered(INTEGRATION_TEST_REPORT, "covered_code.in_integration")

    def build_without_venvs(self):
        """Runs the build at arm's length, in a Python of its own that it may install into."""
        venv_dir = self.full_path("venv")
        create_venv(venv_dir, with_pip=True, symlinks=venv_symlinks)

        # The build has to arrive at its own hand-off rather than inherit ours. What a
        # measured process writes goes next to the data file its configuration names,
        # so inheriting would scatter this project - a temp directory that is gone by
        # the time anything reads a report - through the data of the build running us.
        env = {name: value for name, value in os.environ.items()
               if name not in subprocess_coverage_env_from_environ()}

        # Verbose, because a failing task of this build is the only account of it there
        # will ever be: it reports what a test of its own printed only when asked to
        result = subprocess.run([_venv_python_executable(venv_dir, sys.platform), "-c", RUN_PYBUILDER,
                                 "-v", "--no-venvs", "coverage"],
                                cwd=self.tmp_directory, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True)

        self.assertEqual(result.returncode, 0, result.stdout)

        # The build this test judges runs out of reach of the report this test lands in,
        # so hand its output on: without it a failure here says only that something went
        # unmeasured, with nothing about the build that failed to measure it.
        print(result.stdout)

        return result.stdout


if __name__ == "__main__":
    unittest.main()
