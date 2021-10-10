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

from pybuilder.plugins.python.remote_tools import start_tool, RemoteObjectPipe, Tool, logger, PipeShutdownError

__all__ = ["start_unittest_tool", "PipeShutdownError", logger]


class UnitTestTool(Tool):
    def __init__(self, sys_paths, test_modules, test_method_prefix):
        self.sys_paths = sys_paths
        self.test_modules = test_modules
        self.test_method_prefix = test_method_prefix

    def start(self, pipe):
        # type: (RemoteObjectPipe) -> None
        for path in reversed(self.sys_paths):
            sys.path.insert(0, path)

        import unittest
        loader = unittest.defaultTestLoader
        if self.test_method_prefix:
            loader.testMethodPrefix = self.test_method_prefix

        try:
            tests = loader.loadTestsFromNames(self.test_modules)
            pipe.expose("unittest_tests", tests)
        except SystemExit as e:
            raise e
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            pipe.expose("unittest_tests", e, error=True)

        pipe.register_remote_type(unittest.BaseTestSuite)
        pipe.register_remote_type(unittest.TestCase)

    def stop(self, pipe):
        pipe.hide("unittest_tests")


def start_unittest_tool(pyenv, tools, sys_paths, test_modules, test_method_prefix, logging=0, tracing=0):
    tool = UnitTestTool(sys_paths, test_modules, test_method_prefix)
    return start_tool(pyenv, tools + [tool], name="unittest", logging=logging, tracing=tracing)
