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
import shutil
import sys
import tempfile
import unittest
from os.path import join as jp

from pybuilder.plugins.python import _coverage_bootstrap
from pybuilder.plugins.python._coverage_util import (COVERAGE_PROCESS_CONFIG_ENV,
                                                     PYB_COVERAGE_PROCESS_CONFIG_ENV,
                                                     install_coverage_bootstrap,
                                                     )
from unittest import mock  # `test_utils.patch.object` sets `new_callable`, which rules out a positional `new`

from test_utils import patch

CONFIGS = [{"cov_parent_dir": jp("somewhere", "site-packages"),
            "cov_source_path": jp("project", "src", "main", "python", ""),
            "cov_omit_patterns": [jp("project", "excluded", "*"), jp("project", "also_excluded.py")],
            },
           {"cov_parent_dir": jp("elsewhere", "site-packages"),
            "cov_source_path": jp("other", "src", "main", "python", ""),
            "cov_omit_patterns": [jp("other", "vendor", "*"), jp("other", "generated", "*")],
            },
           ]

# Stands in for the real `_coverage_util`, which the bootstrap imports as a top level
# module out of the directory the environment points it at
UTIL_STUB = """\
calls = []
result = None


def start_subprocess_coverage(config):
    calls.append(config)
    return result
"""


class CoverageBootstrapTests(unittest.TestCase):
    """Exercises the stub a VEnv's `.pth`/`.start` file runs at interpreter startup.

    It runs where PyBuilder is not importable, so it has to reach `_coverage_util`
    through the directory named in the environment rather than by package import.
    """

    def setUp(self):
        self.util_dir = tempfile.mkdtemp()
        with open(jp(self.util_dir, "_coverage_util.py"), "wt") as util_stub:
            util_stub.write(UTIL_STUB)
        self.addCleanup(shutil.rmtree, self.util_dir, True)

        # These very tests can run as a measured subprocess of a covered build, in
        # which case the real bootstrap has already imported the real `_coverage_util`
        # under this name - put whatever was there back when we are done with it
        self.real_util = sys.modules.pop("_coverage_util", None)
        self.addCleanup(self._restore_real_util)

    def _restore_real_util(self):
        sys.modules.pop("_coverage_util", None)
        if self.real_util is not None:
            sys.modules["_coverage_util"] = self.real_util

    def _environ_for(self, config, util_dir=None):
        config = dict(config, cov_util_dir=self.util_dir if util_dir is None else util_dir)
        return ({PYB_COVERAGE_PROCESS_CONFIG_ENV: repr(config),
                 COVERAGE_PROCESS_CONFIG_ENV: "serialized-coverage-config",
                 }, config)

    def test_should_start_coverage_with_the_config_from_the_environment(self):
        for config in CONFIGS:
            sys.modules.pop("_coverage_util", None)
            environ, expected_config = self._environ_for(config)
            with patch.dict(os.environ, environ):
                self.assertIsNone(_coverage_bootstrap.start())
            self.assertEqual(sys.modules["_coverage_util"].calls, [expected_config])

    def test_should_return_what_it_started(self):
        for config in CONFIGS:
            sys.modules.pop("_coverage_util", None)
            environ, _ = self._environ_for(config)
            with patch.dict(os.environ, environ):
                _coverage_bootstrap.start()
                util = sys.modules["_coverage_util"]
                util.result = "started coverage"
                util.calls.clear()
                self.assertEqual(_coverage_bootstrap.start(), "started coverage")

    def test_should_do_nothing_without_the_whole_hand_off(self):
        # Half a hand-off measures nothing, so it must not be paid for either: what
        # follows this guard is the expensive part of every interpreter's startup
        full, _ = self._environ_for(CONFIGS[0])
        for environ in ({},
                        {PYB_COVERAGE_PROCESS_CONFIG_ENV: "", COVERAGE_PROCESS_CONFIG_ENV: ""},
                        {PYB_COVERAGE_PROCESS_CONFIG_ENV: full[PYB_COVERAGE_PROCESS_CONFIG_ENV]},
                        {COVERAGE_PROCESS_CONFIG_ENV: full[COVERAGE_PROCESS_CONFIG_ENV]},
                        ):
            with patch.dict(os.environ, environ, clear=True):
                self.assertIsNone(_coverage_bootstrap.start())
            self.assertNotIn("_coverage_util", sys.modules)

    def test_should_do_nothing_when_the_interpreter_cannot_import_yet(self):
        # pip empties `sys.path` for the duration of the site processing its build
        # isolation does, so an interpreter can reach this hook with the standard
        # library out of reach. `site` reports a raising `.pth` by importing
        # `traceback`, which fails the same way, and startup is aborted.
        for config in CONFIGS:
            sys.modules.pop("_coverage_util", None)
            environ, _ = self._environ_for(config)
            path = list(sys.path)
            with patch.dict(os.environ, environ), patch.dict(sys.modules, {"ast": None}):
                self.assertIsNone(_coverage_bootstrap.start())
            self.assertEqual(sys.path, path)

    def test_should_do_nothing_when_the_hand_off_cannot_be_read(self):
        # The planted hook and the variables it acts on both outlive the build that
        # set them up, so a stale or damaged hand-off is something it has to survive
        for config in ("not a literal {", repr(["wrong", "shape"]), repr({"no": "keys we need"})):
            environ = {PYB_COVERAGE_PROCESS_CONFIG_ENV: config,
                       COVERAGE_PROCESS_CONFIG_ENV: "serialized-coverage-config",
                       }
            path = list(sys.path)
            with patch.dict(os.environ, environ, clear=True):
                self.assertIsNone(_coverage_bootstrap.start())
            self.assertEqual(sys.path, path)

    def test_should_not_import_a_parser_before_it_knows_there_is_work(self):
        # `import ast` costs about 1.5ms, which every interpreter this VEnv ever runs
        # would otherwise pay, long after the build that planted the hook is over
        self.assertNotIn("ast", vars(_coverage_bootstrap))

    def test_should_do_nothing_when_the_util_module_is_not_where_it_should_be(self):
        for config in CONFIGS:
            sys.modules.pop("_coverage_util", None)
            environ, _ = self._environ_for(config, util_dir=jp(self.util_dir, "gone"))
            with patch.dict(os.environ, environ):
                self.assertIsNone(_coverage_bootstrap.start())
            self.assertNotIn("_coverage_util", sys.modules)

    def test_should_not_leave_the_util_dir_on_sys_path(self):
        for util_dir in (None, jp(self.util_dir, "gone")):
            for config in CONFIGS:
                sys.modules.pop("_coverage_util", None)
                path = list(sys.path)
                environ, _ = self._environ_for(config, util_dir=util_dir)
                with patch.dict(os.environ, environ):
                    _coverage_bootstrap.start()
                self.assertEqual(sys.path, path)

    def test_should_put_what_site_needs_to_reach_the_entry_point_within_reach(self):
        # pip empties `sys.path` for the duration of the site processing its build
        # isolation does. `site` needs `pkgutil` to resolve a PEP 829 entry point and
        # `traceback` to report a failure to, imports both lazily, and aborts startup
        # when the second one fails while reporting the first.
        stdlib_dir = os.path.dirname(os.__file__)
        emptied = [path for path in sys.path if path != stdlib_dir]

        with patch.dict(sys.modules):
            for name in ("pkgutil", "traceback"):
                sys.modules.pop(name, None)
            with mock.patch.object(sys, "path", emptied):
                self.assertIsNone(_coverage_bootstrap.prepare())

                self.assertIn("pkgutil", sys.modules)
                self.assertIn("traceback", sys.modules)
                # pip takes whatever site processing added to `sys.path` as the set of
                # paths to drop from the real one, so it has to be left alone
                self.assertEqual(sys.path, emptied)

    def test_should_prepare_nothing_when_the_interpreter_needs_no_help(self):
        # This runs at the start of every interpreter the VEnv ever runs, so the usual
        # case - a standard library that was never out of reach - has to stay free
        with patch.dict(sys.modules):
            sys.modules.pop("pkgutil", None)
            self.assertIsNone(_coverage_bootstrap.prepare())
            self.assertNotIn("pkgutil", sys.modules)

    def test_should_never_let_preparation_escape_into_site_processing(self):
        with mock.patch.object(sys, "path", None):
            self.assertIsNone(_coverage_bootstrap.prepare())

    def test_should_not_import_anything_a_plain_venv_does_not_have(self):
        site_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, site_path, True)
        install_coverage_bootstrap(site_path, (3, 15, 0))

        with open(jp(site_path, "pybuilder_coverage_bootstrap.py")) as planted:
            import_lines = [line for line in planted.read().splitlines()
                            if line.startswith(("import ", "from "))]

        self.assertTrue(import_lines)
        for import_line in import_lines:
            self.assertNotIn("pybuilder", import_line)
            self.assertNotIn("coverage", import_line)
