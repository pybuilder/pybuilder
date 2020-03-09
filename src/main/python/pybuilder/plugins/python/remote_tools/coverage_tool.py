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

from pybuilder.plugins.python.remote_tools import RemoteObjectPipe, Tool

__all__ = ["CoverageTool"]


class CoverageTool(Tool):
    def __init__(self, source_path, omit_patterns, *cov_args, **cov_kwargs):
        self.source_path = source_path
        self.omit_patterns = omit_patterns
        self.cov_args = cov_args
        self.cov_kwargs = cov_kwargs
        self.coverage = None

    def start(self, pipe):
        # type: (RemoteObjectPipe) -> None
        from .._coverage_util import patch_coverage

        patch_coverage()

        from coverage import coverage as coverage_factory

        coverage = coverage_factory(*self.cov_args, **self.cov_kwargs)
        self.coverage = coverage
        coverage.start()

    def stop(self, pipe):
        # type: (RemoteObjectPipe) -> None
        from .._coverage_util import save_normalized_coverage

        self.coverage.stop()
        save_normalized_coverage(self.coverage, self.source_path, self.omit_patterns)
