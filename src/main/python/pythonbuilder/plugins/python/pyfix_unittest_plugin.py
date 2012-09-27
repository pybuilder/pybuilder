#  This file is part of pybuilder
#
#  Copyright 2011 - 2012 The pybuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

__author__ = "Alexander Metzner"

from pythonbuilder.core import init, task, description, use_plugin

use_plugin("python.core")

@init
def init_test_source_directory(project):
    project.build_depends_on("pyfix")

    project.set_property_if_unset("dir_source_unittest_python", "src/unittest/python")
    project.set_property_if_unset("pyfix_unittest_file_suffix", "_pyfix_tests.py")


@task
@description("Runs unit tests written using the pyfix test framework")
def run_unit_tests(project, logger):
    import pythonbuilder.plugins.python.pyfix_plugin_impl

    pythonbuilder.plugins.python.pyfix_plugin_impl.run_unit_tests(project, logger)
