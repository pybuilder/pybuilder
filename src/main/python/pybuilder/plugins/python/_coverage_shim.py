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

import ast
import sys


# import runpy

class CoverageImporter:
    def __init__(self, coverage_parent_dir):
        self.coverage_parent_dir = coverage_parent_dir

    def find_module(self, fullname, path=None):
        """
        Return self when fullname starts with `coverage`.
        """
        if fullname == "coverage" or fullname.startswith("coverage."):
            return self

    def load_module(self, fullname):
        """
        Load coverage only and remove coverage from path thereafter
        """
        sys.path.append(self.coverage_parent_dir)
        try:
            __import__(fullname)
        finally:
            del sys.path[-1]

    def install(self):
        """
        Install this importer into sys.meta_path if not already present.
        """
        if self not in sys.meta_path:
            sys.meta_path.append(self)


if __name__ == "__main__":
    self = sys.argv[0]
    config_literal = sys.argv[1]
    del sys.argv[:2]
    del sys.path[0]

    config = ast.literal_eval(config_literal)

    CoverageImporter(config["cov_parent_dir"]).install()

    from coverage import coverage as coverage_factory
    from coverage.execfile import PyRunner

    coverage = coverage_factory(*(config.get("cov_args", ())), **(config.get("cov_kwargs", {})))

    args = sys.argv
    module = False
    if args and args[0] == "-m":
        module = True
        args = args[1:]

    runner = PyRunner(args, as_module=module)
    runner.prepare()

    coverage.start()
    try:
        runner.run()
    finally:
        coverage.stop()
        coverage.save()
