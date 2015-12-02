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

from pybuilder.core import init, task, description, use_plugin

__author__ = "Alexander Metzner"

use_plugin("python.core")


@init
def init_test_source_directory(project):
    project.plugin_depends_on("pyfix")

    project.set_property_if_unset("dir_source_unittest_python", "src/unittest/python")
    project.set_property_if_unset("pyfix_unittest_module_glob", "*_pyfix_tests")
    project.set_property_if_unset("pyfix_unittest_file_suffix", None)  # deprecated, use pyfix_unittest_module_glob.


@task
@description("Runs unit tests written using the pyfix test framework")
def run_unit_tests(project, logger):
    import pybuilder.plugins.python.pyfix_plugin_impl

    pybuilder.plugins.python.pyfix_plugin_impl.run_unit_tests(project, logger)
