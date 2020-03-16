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
from os import chdir, getcwd
from os.path import join as jp, dirname, exists, isfile, isdir
from runpy import run_path
from shutil import copytree, copy2

import base_itest_support


class SmokeIntegrationTestSupport(base_itest_support.BaseIntegrationTestSupport):
    """This class runs the actual project at arm's length as opposed to deeply integrating with it.
    This is mostly useful for smoke tests where the project just runs pass-fail.
    """

    PROJECT_FILES = ["build.py", "src", "README.md", "LICENSE"]

    def setUp(self):
        super(SmokeIntegrationTestSupport, self).setUp()
        cur_dir = dirname(base_itest_support.__file__)
        prev_dir = None

        self.src_dir = None
        while cur_dir != prev_dir:
            candidate_build_py = jp(cur_dir, "build.py")
            if exists(candidate_build_py) and isfile(candidate_build_py):
                self.src_dir = cur_dir
                break
            prev_dir = cur_dir
            cur_dir = dirname(prev_dir)

        if not self.src_dir:
            raise RuntimeError("Unable to find location of the project's build.py")

        for src in self.PROJECT_FILES:
            src_file = jp(self.src_dir, src)
            if isdir(src_file):
                copytree(src_file, jp(self.tmp_directory, src))
            else:
                copy2(src_file, self.tmp_directory)

        self.build_py = jp(self.tmp_directory, "build.py")

    def smoke_test(self, *args):
        old_argv = list(sys.argv)
        del sys.argv[:]
        sys.argv.append(self.build_py)
        sys.argv.extend(args)

        old_modules = dict(sys.modules)
        old_meta_path = list(sys.meta_path)
        old_cwd = getcwd()
        chdir(self.tmp_directory)
        try:
            return run_path(self.build_py, run_name="__main__")
        except SystemExit as e:
            self.assertEqual(e.code, 0, "Test did not exit successfully")
        finally:
            del sys.argv[:]
            sys.argv.extend(old_argv)

            sys.modules.clear()
            sys.modules.update(old_modules)

            del sys.meta_path[:]
            sys.meta_path.extend(old_meta_path)
            chdir(old_cwd)

    def tearDown(self):
        try:
            pass
        finally:
            super(SmokeIntegrationTestSupport, self).tearDown()
