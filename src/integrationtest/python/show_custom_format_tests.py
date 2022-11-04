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
import contextlib
import unittest
from io import StringIO

from itest_support import IntegrationTestSupport


class Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file(
            """
from pybuilder.core import init, task

name = "integration-test"
default_task = "any_task"

@task
def any_task (project):
    pass
"""
        )

        def _prepare(log_time_format=None) -> str:
            f = StringIO()
            with contextlib.redirect_stdout(f):
                reactor = self.prepare_reactor(log_time_format=log_time_format)
                reactor.build()
            f.seek(0)
            return f.read()

        run_without_log_time_format = _prepare(None).splitlines()[0]
        run_with_log_time_format = _prepare("%Y-%m-%d %H:%M:%S").splitlines()[0]

        self.assertIn(run_without_log_time_format, run_with_log_time_format)
        self.assertNotIn(run_with_log_time_format, run_without_log_time_format)

        should_be_format = run_with_log_time_format.replace(
            run_without_log_time_format, ""
        ).strip()
        self.assertRegex(should_be_format, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")


if __name__ == "__main__":
    unittest.main()
