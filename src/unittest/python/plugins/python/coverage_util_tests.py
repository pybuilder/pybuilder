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

import ast
import os
import shutil
import sys
import tempfile
import unittest
from os.path import join as jp, exists, isdir, dirname, normcase as nc
from unittest import mock

from pybuilder.plugins.python import _coverage_util
from pybuilder.plugins.python._coverage_util import (COVERAGE_PROCESS_CONFIG_ENV,
                                                     PYB_COVERAGE_PROCESS_CONFIG_ENV,
                                                     BOOTSTRAP_MODULE_NAME,
                                                     BOOTSTRAP_PTH_NAME,
                                                     BOOTSTRAP_PTH_CONTENT,
                                                     BOOTSTRAP_PREPARE_PTH_CONTENT,
                                                     BOOTSTRAP_START_NAME,
                                                     BOOTSTRAP_START_CONTENT,
                                                     install_coverage_bootstrap,
                                                     start_subprocess_coverage,
                                                     subprocess_coverage_env,
                                                     subprocess_coverage_env_from_environ,
                                                     adopt_subprocess_coverage,
                                                     canonical_path,
                                                     combine_subprocess_coverage,
                                                     patch_coverage,
                                                     save_normalized_coverage,
                                                     )
from pybuilder.python_utils import IS_WIN
from test_utils import patch, Mock

SOURCE_PATH = jp("some", "project", "src", "main", "python", "")
OMIT_PATTERNS = [jp(SOURCE_PATH, "excluded_package", "*"), jp(SOURCE_PATH, "excluded_module.py")]


def make_coverage(serialized="c2VyaWFsaXplZA=="):
    coverage = Mock()
    coverage.config.serialize.return_value = serialized
    return coverage


class SubprocessCoverageEnvTests(unittest.TestCase):
    def setUp(self):
        self.env = subprocess_coverage_env(make_coverage(), SOURCE_PATH, OMIT_PATTERNS)

    def test_should_hand_off_serialized_coverage_config(self):
        self.assertEqual(self.env[COVERAGE_PROCESS_CONFIG_ENV], "c2VyaWFsaXplZA==")

    def test_should_hand_off_where_coverage_can_be_imported_from(self):
        import coverage

        config = ast.literal_eval(self.env[PYB_COVERAGE_PROCESS_CONFIG_ENV])
        self.assertIn("coverage", os.listdir(config["cov_parent_dir"]))
        self.assertTrue(isdir(coverage.__path__[0]))

    def test_should_hand_off_where_the_util_module_can_be_imported_from(self):
        config = ast.literal_eval(self.env[PYB_COVERAGE_PROCESS_CONFIG_ENV])
        self.assertTrue(exists(jp(config["cov_util_dir"], "_coverage_util.py")))
        self.assertTrue(exists(jp(config["cov_util_dir"], "_coverage_bootstrap.py")))

    def test_should_hand_off_normalization_settings(self):
        config = ast.literal_eval(self.env[PYB_COVERAGE_PROCESS_CONFIG_ENV])
        self.assertEqual(config["cov_source_path"], SOURCE_PATH)
        self.assertEqual(config["cov_omit_patterns"], OMIT_PATTERNS)

    def test_should_hand_off_a_literal_that_needs_no_pybuilder_to_read(self):
        # The bootstrap reads this with `ast.literal_eval` in a VEnv that has no
        # PyBuilder on its path
        self.assertIsInstance(ast.literal_eval(self.env[PYB_COVERAGE_PROCESS_CONFIG_ENV]), dict)


class SubprocessCoverageEnvFromEnvironTests(unittest.TestCase):
    def test_should_pick_out_both_coverage_variables(self):
        environ = {COVERAGE_PROCESS_CONFIG_ENV: "config",
                   PYB_COVERAGE_PROCESS_CONFIG_ENV: "pyb-config",
                   "PATH": "/usr/bin",
                   "PYTHONPATH": "/somewhere",
                   }
        self.assertEqual(subprocess_coverage_env_from_environ(environ),
                         {COVERAGE_PROCESS_CONFIG_ENV: "config",
                          PYB_COVERAGE_PROCESS_CONFIG_ENV: "pyb-config"})

    def test_should_be_empty_when_not_running_under_coverage(self):
        self.assertEqual(subprocess_coverage_env_from_environ({"PATH": "/usr/bin", "HOME": "/home/user"}), {})

    def test_should_pick_out_what_is_there_when_only_one_is_set(self):
        self.assertEqual(subprocess_coverage_env_from_environ({PYB_COVERAGE_PROCESS_CONFIG_ENV: "pyb-config",
                                                               "PATH": "/usr/bin"}),
                         {PYB_COVERAGE_PROCESS_CONFIG_ENV: "pyb-config"})

    def test_should_default_to_the_current_environment(self):
        with patch.dict(os.environ, {COVERAGE_PROCESS_CONFIG_ENV: "config",
                                     PYB_COVERAGE_PROCESS_CONFIG_ENV: "pyb-config"}):
            self.assertEqual(subprocess_coverage_env_from_environ(),
                             {COVERAGE_PROCESS_CONFIG_ENV: "config",
                              PYB_COVERAGE_PROCESS_CONFIG_ENV: "pyb-config"})


class InstallCoverageBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.site_paths = [tempfile.mkdtemp(), tempfile.mkdtemp()]

    def tearDown(self):
        for site_path in self.site_paths:
            shutil.rmtree(site_path, ignore_errors=True)

    def test_should_plant_the_bootstrap_into_every_site_directory(self):
        for site_path in self.site_paths:
            self.assertTrue(install_coverage_bootstrap(site_path, (3, 14, 1)))

        bootstrap_source = jp(dirname(_coverage_util.__file__), "_coverage_bootstrap.py")
        for site_path in self.site_paths:
            with open(jp(site_path, BOOTSTRAP_MODULE_NAME + ".py")) as planted:
                with open(bootstrap_source) as original:
                    self.assertEqual(planted.read(), original.read())

    def test_should_start_from_a_pth_import_line_before_python_3_15(self):
        for version in ((3, 10, 0), (3, 14, 1)):
            for site_path in self.site_paths:
                install_coverage_bootstrap(site_path, version)
                with open(jp(site_path, BOOTSTRAP_PTH_NAME)) as pth_file:
                    pth = pth_file.read()
                self.assertEqual(pth, BOOTSTRAP_PTH_CONTENT)
                # Only lines starting with `import` are executed by `site`
                self.assertTrue(pth.startswith("import "))
                self.assertEqual(len(pth.splitlines()), 1)
                self.assertFalse(exists(jp(site_path, BOOTSTRAP_START_NAME)))

    def test_should_start_from_an_entry_point_from_python_3_15(self):
        for version in ((3, 15, 0), (3, 16, 2)):
            for site_path in self.site_paths:
                install_coverage_bootstrap(site_path, version)
                with open(jp(site_path, BOOTSTRAP_START_NAME)) as start_file:
                    self.assertEqual(start_file.read(), BOOTSTRAP_START_CONTENT)
                self.assertEqual(BOOTSTRAP_START_CONTENT.strip(), "%s:start" % BOOTSTRAP_MODULE_NAME)

    def test_should_leave_the_pth_to_prepare_for_the_entry_point_from_python_3_15(self):
        for site_path in self.site_paths:
            install_coverage_bootstrap(site_path, (3, 15, 0))
            with open(jp(site_path, BOOTSTRAP_PTH_NAME)) as pth_file:
                self.assertEqual(pth_file.read(), BOOTSTRAP_PREPARE_PTH_CONTENT)

    def test_should_not_name_the_start_file_after_the_pth_file(self):
        # PEP 829 has a `.start` supersede the `import` line of the `.pth` it is named
        # after, and that line is the only thing that runs early enough to prepare the
        # interpreter for the entry point - so the two must not be named as a pair
        self.assertNotEqual(BOOTSTRAP_START_NAME[:-len(".start")], BOOTSTRAP_PTH_NAME[:-len(".pth")])

    def test_should_do_nothing_for_a_site_directory_that_does_not_exist(self):
        for missing in (jp(self.site_paths[0], "no-such-dir"), jp(self.site_paths[1], "nor-this-one")):
            self.assertFalse(install_coverage_bootstrap(missing, (3, 15, 0)))
            self.assertFalse(exists(missing))


class CoverageStartupTestCase(unittest.TestCase):
    def setUp(self):
        import coverage

        self.coverage_module = coverage
        self.config = {"cov_parent_dir": jp("does", "not", "need", "to", "exist"),
                       "cov_util_dir": jp("neither", "does", "this"),
                       "cov_source_path": SOURCE_PATH,
                       "cov_omit_patterns": OMIT_PATTERNS,
                       }
        _coverage_util.adopted_coverage = None
        self.addCleanup(setattr, _coverage_util, "adopted_coverage", None)

    def _process_startup(self, started, previously_started=None):
        """Stands in for `coverage.process_startup`, which flags itself once it ran."""

        def process_startup():
            process_startup.calls += 1
            if started is None or hasattr(process_startup, "coverage"):
                return None
            process_startup.coverage = started
            return started

        process_startup.calls = 0
        if previously_started is not None:
            process_startup.coverage = previously_started
        return process_startup


class AdoptSubprocessCoverageTests(CoverageStartupTestCase):
    """The shim and the tool adopt rather than stand down, so that a Coverage started
    by Coverage's own startup hook - which knows nothing about normalization - still
    gets its data mapped back onto the sources."""

    def test_should_report_nothing_to_adopt_when_no_startup_hook_ran(self):
        with mock.patch.object(self.coverage_module, "process_startup", self._process_startup(None)), \
                patch("atexit.register") as register:
            self.assertIsNone(adopt_subprocess_coverage(SOURCE_PATH, OMIT_PATTERNS))

        self.assertIsNone(_coverage_util.adopted_coverage)
        self.assertFalse(register.called)

    def test_should_adopt_what_a_startup_hook_started(self):
        for already_started in (Mock(name="from_coverage_pth"), Mock(name="from_our_pth")):
            _coverage_util.adopted_coverage = None
            with mock.patch.object(self.coverage_module, "process_startup",
                                   self._process_startup(None, previously_started=already_started)), \
                    patch("atexit.register") as register:
                self.assertIs(adopt_subprocess_coverage(SOURCE_PATH, OMIT_PATTERNS), already_started)

            self.assertIs(_coverage_util.adopted_coverage, already_started)
            self.assertFalse(already_started._auto_save)
            self.assertEqual(register.call_count, 1)

    def test_should_take_over_the_save_so_it_is_normalized(self):
        already_started = Mock(name="already_started")
        with mock.patch.object(self.coverage_module, "process_startup",
                               self._process_startup(None, previously_started=already_started)), \
                patch("atexit.register") as register, \
                patch("pybuilder.plugins.python._coverage_util.save_normalized_coverage") as save:
            adopt_subprocess_coverage(SOURCE_PATH, OMIT_PATTERNS)
            register.call_args[0][0]()

        already_started.stop.assert_called_once_with()
        save.assert_called_once_with(already_started, SOURCE_PATH, OMIT_PATTERNS)

    def test_should_hand_back_the_same_coverage_without_adopting_twice(self):
        already_started = Mock(name="already_started")
        with mock.patch.object(self.coverage_module, "process_startup",
                               self._process_startup(None, previously_started=already_started)), \
                patch("atexit.register") as register:
            first = adopt_subprocess_coverage(SOURCE_PATH, OMIT_PATTERNS)
            second = adopt_subprocess_coverage(SOURCE_PATH, OMIT_PATTERNS)

        self.assertIs(first, already_started)
        self.assertIs(second, already_started)
        self.assertEqual(register.call_count, 1)


class StartSubprocessCoverageTests(CoverageStartupTestCase):
    def test_should_start_and_adopt_coverage(self):
        started = Mock(name="started")
        with patch.dict(os.environ, {COVERAGE_PROCESS_CONFIG_ENV: "config"}), \
                mock.patch.object(self.coverage_module, "process_startup", self._process_startup(started)), \
                patch("atexit.register") as register:
            self.assertIs(start_subprocess_coverage(self.config), started)

        self.assertIs(_coverage_util.adopted_coverage, started)
        self.assertFalse(started._auto_save)
        self.assertEqual(register.call_count, 1)

    def test_should_adopt_coverage_that_another_startup_hook_started(self):
        # Coverage's own `.pth` sorts ahead of ours when both are installed, so by the
        # time we run, `process_startup` has already done its work and returns None
        already_started = Mock(name="already_started")
        with patch.dict(os.environ, {COVERAGE_PROCESS_CONFIG_ENV: "config"}), \
                mock.patch.object(self.coverage_module, "process_startup",
                                  self._process_startup(None, previously_started=already_started)), \
                patch("atexit.register"):
            self.assertIs(start_subprocess_coverage(self.config), already_started)

        self.assertIs(_coverage_util.adopted_coverage, already_started)
        self.assertFalse(already_started._auto_save)

    def test_should_only_adopt_once_when_a_site_directory_is_visible_twice(self):
        started = Mock(name="started")
        process_startup = self._process_startup(started)
        with patch.dict(os.environ, {COVERAGE_PROCESS_CONFIG_ENV: "config"}), \
                mock.patch.object(self.coverage_module, "process_startup", process_startup), \
                patch("atexit.register") as register:
            first = start_subprocess_coverage(self.config)
            second = start_subprocess_coverage(self.config)

        self.assertIs(first, started)
        self.assertIsNone(second)
        self.assertEqual(process_startup.calls, 1)
        self.assertEqual(register.call_count, 1)

    def test_should_save_normalized_coverage_on_exit(self):
        started = Mock(name="started")
        with patch.dict(os.environ, {COVERAGE_PROCESS_CONFIG_ENV: "config"}), \
                mock.patch.object(self.coverage_module, "process_startup", self._process_startup(started)), \
                patch("atexit.register") as register, \
                patch("pybuilder.plugins.python._coverage_util.save_normalized_coverage") as save:
            start_subprocess_coverage(self.config)
            register.call_args[0][0]()

        started.stop.assert_called_once_with()
        save.assert_called_once_with(started, SOURCE_PATH, OMIT_PATTERNS)

    def test_should_do_nothing_without_a_coverage_config_to_start_from(self):
        for environ in ({}, {COVERAGE_PROCESS_CONFIG_ENV: ""}):
            with patch.dict(os.environ, environ, clear=True), \
                    mock.patch.object(self.coverage_module, "process_startup", self._process_startup(Mock())), \
                    patch("atexit.register") as register:
                self.assertIsNone(start_subprocess_coverage(self.config))
            self.assertIsNone(_coverage_util.adopted_coverage)
            self.assertFalse(register.called)

    def test_should_do_nothing_when_coverage_cannot_be_imported(self):
        with patch.dict(os.environ, {COVERAGE_PROCESS_CONFIG_ENV: "config"}), \
                patch.dict(sys.modules, {"coverage": None}), \
                patch("atexit.register") as register:
            self.assertIsNone(start_subprocess_coverage(self.config))

        self.assertIsNone(_coverage_util.adopted_coverage)
        self.assertFalse(register.called)

    def test_should_not_leave_the_coverage_parent_dir_on_sys_path(self):
        path = list(sys.path)
        with patch.dict(os.environ, {COVERAGE_PROCESS_CONFIG_ENV: "config"}), \
                mock.patch.object(self.coverage_module, "process_startup", self._process_startup(Mock())), \
                patch("atexit.register"):
            start_subprocess_coverage(self.config)
        self.assertEqual(sys.path, path)

    def test_should_do_nothing_when_process_startup_has_nothing_to_report(self):
        with patch.dict(os.environ, {COVERAGE_PROCESS_CONFIG_ENV: "config"}), \
                mock.patch.object(self.coverage_module, "process_startup", self._process_startup(None)), \
                patch("atexit.register") as register:
            self.assertIsNone(start_subprocess_coverage(self.config))

        self.assertIsNone(_coverage_util.adopted_coverage)
        self.assertFalse(register.called)


class CanonicalPathTests(unittest.TestCase):
    """Canonicalization exists only to agree with Coverage, so that is what it is held to."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp_dir, True)

    def test_should_spell_a_path_the_way_coverage_spells_what_it_measures(self):
        from coverage.files import abs_file

        for name in ("module.py", jp("package", "module.py")):
            path = jp(self.tmp_dir, name)
            self.assertEqual(canonical_path(path), nc(abs_file(path)))

    @unittest.skipIf(IS_WIN, "symlinks need a privilege Windows does not hand out by default")
    def test_should_spell_a_path_reached_through_a_link_the_way_coverage_does(self):
        from coverage.files import abs_file

        real_dir = jp(self.tmp_dir, "real")
        linked_dir = jp(self.tmp_dir, "linked")
        os.makedirs(real_dir)
        os.symlink(real_dir, linked_dir)

        for name in ("module.py", jp("package", "module.py")):
            path = jp(linked_dir, name)
            self.assertEqual(canonical_path(path), nc(abs_file(path)))
            self.assertNotEqual(canonical_path(path), nc(path))


class _Collector(object):
    """Stands in for Coverage's collector, which owns both the data and the mapping."""

    def __init__(self, data, file_tracers):
        self.data = data
        self.file_tracers = file_tracers
        self.file_mapper = None

    def cached_mapped_file(self, path):
        return self.file_mapper(path)


class _Coverage(object):
    def __init__(self, data, file_tracers):
        self._collector = _Collector(data, file_tracers)
        self.saves = 0

    def save(self):
        self.saves += 1


@unittest.skipIf(IS_WIN, "symlinks need a privilege Windows does not hand out by default")
class SaveNormalizedCoverageTests(unittest.TestCase):
    """What was measured has to be recognized when Coverage and the build reached it by
    different names.

    Coverage identifies a file by its `realpath`, which is not how the build reached it
    when anything on the way is a link: a macOS temp directory is reached through /var
    and measured as /private/var, and a Windows one through an 8.3 short name and
    measured expanded. Data spelled Coverage's way used to be discarded as not being
    under the source path.
    """

    def setUp(self):
        tmp_dir = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp_dir, True)

        self.source_path = jp(tmp_dir, "src", "main", "python", "")
        self.dist_path = jp(tmp_dir, "target", "dist", "project")
        for parent in (self.source_path, self.dist_path):
            os.makedirs(jp(parent, "covered"))
            for name in ("module.py", "other.py"):
                with open(jp(parent, "covered", name), "wt") as module_file:
                    module_file.write("pass\n")

        # The distribution the build put on `sys.path`, under the name the build reached
        # it by rather than the one Coverage will measure it under
        self.linked_dist_path = jp(tmp_dir, "linked-dist")
        os.symlink(self.dist_path, self.linked_dist_path)

        self.measured = {jp(self.dist_path, "covered", "module.py"): [1, 2],
                         jp(self.dist_path, "covered", "other.py"): [3, 4],
                         }
        self.expected = {jp(self.source_path, "covered", "module.py"): [1, 2],
                         jp(self.source_path, "covered", "other.py"): [3, 4],
                         }

    def _save(self, data, file_tracers=None, paths=None):
        coverage = _Coverage(data, {} if file_tracers is None else file_tracers)
        save_normalized_coverage(coverage, self.source_path, OMIT_PATTERNS,
                                 paths=[self.linked_dist_path, self.source_path] if paths is None else paths)
        return coverage

    def test_should_map_what_was_measured_through_a_link_onto_the_sources(self):
        coverage = self._save(dict(self.measured))

        self.assertEqual(coverage._collector.data, self.expected)
        self.assertEqual(coverage.saves, 1)

    def test_should_map_the_file_tracers_of_what_was_measured_through_a_link(self):
        coverage = self._save({}, file_tracers=dict(self.measured))

        self.assertEqual(coverage._collector.file_tracers, self.expected)

    def test_should_keep_what_was_measured_under_the_sources_themselves(self):
        coverage = self._save(dict(self.expected))

        self.assertEqual(coverage._collector.data, self.expected)

    def test_should_still_discard_what_is_no_part_of_the_sources(self):
        elsewhere = {jp(self.source_path, "..", "..", "..", "elsewhere.py"): [1],
                     jp(os.path.dirname(self.dist_path), "sdist.py"): [2],
                     }
        coverage = self._save(dict(elsewhere))

        self.assertEqual(coverage._collector.data, {})


class CombineSubprocessCoverageTests(unittest.TestCase):
    """What a subprocess wrote has to be recognized even though nothing of PyBuilder's
    was there to spell it PyBuilder's way.

    Under `--no-venvs` the only thing measuring a subprocess is Coverage's own startup
    hook, so `patch_coverage` never runs there and the data is saved spelled the way the
    file system spells it, where everything here is normcased. On Windows those are two
    different strings for one file, and the data went to waste.
    """

    def setUp(self):
        # What the plugin does before it touches any coverage at all. It is what decides
        # how Coverage spells a path it canonicalizes, so the answer here must not depend
        # on whether some other test got to it first.
        patch_coverage()

        self.tmp_dir = canonical_path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp_dir, True)

        self.source_path = jp(self.tmp_dir, "src", "main", "python", "")
        os.makedirs(jp(self.source_path, "covered"))

        # Spelled the way everything on PyBuilder's side of this is spelled, which is
        # what the data is supposed to come out as however the subprocess spelled it
        self.measured_files = []
        for name in ("module.py", "other.py"):
            path = jp(self.source_path, "covered", name)
            with open(path, "wt") as module_file:
                module_file.write("pass\npass\n")
            self.measured_files.append(path)

        self.data_file = jp(self.tmp_dir, "task.coverage")

    def _differently_cased(self, path):
        """The same file, spelled the way a Coverage nobody patched would spell it."""
        return path.replace(jp(self.tmp_dir, "src", ""), jp(self.tmp_dir, "SRC", ""), 1)

    def _write_what_a_subprocess_measured(self, spelling=lambda path: path):
        import coverage

        data = coverage.CoverageData(basename=self.data_file, suffix="subprocess")
        data.add_lines({spelling(path): [1, 2] for path in self.measured_files})
        data.write()

    def _combine(self):
        import coverage

        cov = coverage.coverage(data_file=self.data_file, data_suffix=False, config_file=False)
        combine_subprocess_coverage(cov, self.source_path)
        return cov

    def test_should_map_what_a_subprocess_spelled_its_own_way_onto_the_sources(self):
        self._write_what_a_subprocess_measured(self._differently_cased)

        cov = self._combine()

        self.assertEqual(sorted(cov.get_data().measured_files()), sorted(self.measured_files))

    def test_should_combine_what_was_already_spelled_the_way_the_build_spells_it(self):
        self._write_what_a_subprocess_measured()

        cov = self._combine()

        self.assertEqual(sorted(cov.get_data().measured_files()), sorted(self.measured_files))
