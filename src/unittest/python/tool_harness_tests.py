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

from unittest import TestCase

from _pybuilder import ToolShim


class TestShim(ToolShim):
    def main(self):
        import sys
        print("Hello shim!")
        print("Blah!", sys.stdout.fileno())
        self.data_w.send("Hello shim object!")


class ToolHarnessBehaviorTests(TestCase):
    def setUp(self):
        from pybuilder.pluginhelper.tool_harness import ToolRunner

        self.runner = ToolRunner()

    def tearDown(self):
        self.runner.terminate()
        self.runner.wait()

    def testOneTask(self):
        def handle_io(stream_fd, ts, data):
            if data:
                print(str(stream_fd) + ": " + data)

        def handle_data(ts, data):
            if data:
                print("D: " + str(data))

        proc = self.runner.task(TestShim(), handle_io, handle_data)
        proc.wait()
        self.assertTrue(proc.pid is not None)
        self.runner.close()
