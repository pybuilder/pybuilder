#!/usr/bin/env python
#
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

import sys

sys.path.insert(0, 'src/main/python')  # This is only necessary in PyBuilder sources for bootstrap

from pybuilder import bootstrap
from pybuilder.core import Author, init, use_bldsup, use_plugin

bootstrap()

use_plugin("pypi:pybuilder_external_plugin_demo")
use_plugin("python.core")
use_plugin("python.pytddmon")
use_plugin("python.distutils")
use_plugin("python.install_dependencies")

use_plugin("copy_resources")
use_plugin("filter_resources")
use_plugin("source_distribution")

use_plugin("python.coverage")
use_plugin("python.unittest")
use_plugin("python.integrationtest")
use_plugin("python.flake8")
use_plugin("python.frosted")


if not sys.version_info[0:2] == (3, 2):
    use_plugin("python.cram")

use_plugin("python.pydev")
use_plugin("python.pycharm")
use_plugin("python.pytddmon")

use_bldsup()
use_plugin("pdoc")

summary = "An extensible, easy to use continuous build tool for Python"
description = """PyBuilder is a build automation tool for python.

PyBuilder is a software build tool written in pure Python which mainly targets Python applications.
It is based on the concept of dependency based programming but also comes along with powerful plugin mechanism that
allows the construction of build life cycles similar to those known from other famous build tools like Apache Maven.
"""

authors = [Author("Alexander Metzner", "alexander.metzner@gmail.com"),
           Author("Maximilien Riehl", "max@riehl.io"),
           Author("Michael Gruber", "aelgru@gmail.com"),
           Author("Udo Juettner", "udo.juettner@gmail.com")]
url = "http://pybuilder.github.io"
license = "Apache License"
version = "0.10.44"

default_task = ["analyze", "publish"]


@init
def initialize(project):
    project.build_depends_on("fluentmock")
    project.build_depends_on("mock")
    project.build_depends_on("mockito-without-hardcoded-distribute-version")
    project.build_depends_on("pyfix")  # required test framework
    project.build_depends_on("pyassert")
    project.build_depends_on("wheel")
    project.build_depends_on("pygments")
    if sys.version_info[0:2] == (2, 6):
        project.build_depends_on("importlib") # for fluentmock

    project.set_property("verbose", True)

    project.set_property("coverage_break_build", False)
    project.get_property("coverage_exceptions").append("pybuilder.cli")
    project.get_property("coverage_exceptions").append("pybuilder.plugins.core_plugin")

    project.set_property('flake8_break_build', True)
    project.set_property('flake8_include_test_sources', True)
    project.set_property('flake8_include_scripts', True)
    project.set_property('flake8_max_line_length', 130)

    project.set_property('frosted_include_test_sources', True)
    project.set_property('frosted_include_scripts', True)

    project.set_property("copy_resources_target", "$dir_dist")
    project.get_property("copy_resources_glob").append("LICENSE")
    project.get_property("filter_resources_glob").append("**/pybuilder/__init__.py")

    project.get_property("source_dist_ignore_patterns").append(".project")
    project.get_property("source_dist_ignore_patterns").append(".pydevproject")
    project.get_property("source_dist_ignore_patterns").append(".settings")

    # enable this to build a bdist on vagrant
    # project.set_property("distutils_issue8876_workaround_enabled", True)
    project.get_property("distutils_commands").append("bdist_wheel")
    project.set_property("distutils_console_scripts", ["pyb_ = pybuilder.cli:main"])
    project.set_property("distutils_classifiers", [
                         'Programming Language :: Python',
                         'Programming Language :: Python :: Implementation :: CPython',
                         'Programming Language :: Python :: Implementation :: PyPy',
                         'Programming Language :: Python :: 2.6',
                         'Programming Language :: Python :: 2.7',
                         'Programming Language :: Python :: 3',
                         'Programming Language :: Python :: 3.2',
                         'Programming Language :: Python :: 3.3',
                         'Programming Language :: Python :: 3.4',
                         'Development Status :: 4 - Beta',
                         'Environment :: Console',
                         'Intended Audience :: Developers',
                         'License :: OSI Approved :: Apache Software License',
                         'Topic :: Software Development :: Build Tools',
                         'Topic :: Software Development :: Quality Assurance',
                         'Topic :: Software Development :: Testing'])
