#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2015 PyBuilder Team
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

"""This package exists to provide minimal-import shim

There should never be any global imports either here or in any subclasses of ToolShim.
"""
import sys

if sys.version_info[0] == 2:
    from contextlib import closing


class ToolShim:
    def __init__(self):
        """Provides an abstraction for a remote tool started in a separate process
        No global imports should be either in this class or any subclasses thereof.
        This class and all subclasses must be picklable, so don't drag the entire
        """
        self.data_w = None  # type: multiprocessing.connection.Connection

    def main(self):
        """Actually starts a tool's job"""
        pass

    if sys.version_info[0] == 2:

        def _main(self):
            with closing(self.data_w):
                self.main()
    else:
        def _main(self):
            with self.data_w:
                self.main()
