#!/usr/bin/env python
#

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
from os.path import dirname, join as jp, normcase as nc

# This is only necessary in PyBuilder sources for bootstrap
build_sources = nc(jp(dirname(__file__), "src/main/python"))
if build_sources not in sys.path:
    sys.path.insert(0, build_sources)

from pybuilder import bootstrap
from pybuilder.core import Author, init, use_plugin

bootstrap()

use_plugin("python.core")
use_plugin("python.pytddmon")
use_plugin("python.distutils")
use_plugin("python.install_dependencies")

use_plugin("copy_resources")
use_plugin("filter_resources")
use_plugin("source_distribution")

use_plugin("python.unittest")

if sys.platform != "win32":
    use_plugin("python.cram")

use_plugin("python.integrationtest")
use_plugin("python.coverage")
use_plugin("python.coveralls")
use_plugin("python.flake8")
use_plugin("filter_resources")

if not sys.version_info[0] == 3:
    use_plugin("python.snakefood")

use_plugin("python.pydev")
use_plugin("python.pycharm")
use_plugin("python.pytddmon")

use_plugin("python.sphinx")

if sys.platform != "win32":
    use_plugin("python.pdoc")

use_plugin("python.vendorize")

name = "pybuilder"
summary = "An extensible, easy-to-use build automation tool for Python"
description = """PyBuilder &#x2014; an easy-to-use build automation tool for Python.

PyBuilder is a software build automation tool written in pure Python mainly targeting Python ecosystem. 
It is based on the concept of dependency-based programming but also comes along with powerful plugin mechanism that 
allows the construction of build life-cycles similar to those known from other famous build tools like 
Apache Maven and Gradle.
"""

authors = [Author("Alexander Metzner", "alexander.metzner@gmail.com"),
           Author("Maximilien Riehl", "max@riehl.io"),
           Author("Michael Gruber", "aelgru@gmail.com"),
           Author("Udo Juettner", "udo.juettner@gmail.com"),
           Author("Marcel Wolf", "marcel.wolf@me.com"),
           Author("Arcadiy Ivanov", "arcadiy@ivanov.biz"),
           Author("Valentin Haenel", "valentin@haenel.co"),
           ]
url = "http://pybuilder.github.io"
license = "Apache License"
version = "0.12.0.dev"

requires_python = ">=2.7,!=3.0,!=3.1,!=3.2,!=3.3,!=3.4"

default_task = ["analyze", "publish"]


@init
def initialize(project):
    project.build_depends_on("pygments")

    project.set_property("verbose", True)

    project.set_property("vendorize_target_dir", "$dir_source_main_python/pybuilder/_vendor")
    project.set_property("vendorize_packages", ["tblib~=1.5",
                                                "tailer~=0.4",
                                                "setuptools<45.0.0",
                                                "virtualenv>16.0.0,<20.0.0",
                                                "colorama~=0.4.3"
                                                ])
    project.set_property("vendorize_cleanup_globs", ["bin",
                                                     "setuptools*",
                                                     "easy_install.py"])

    project.set_property("coverage_break_build", False)
    project.get_property("coverage_exceptions").extend(["pybuilder._vendor",
                                                        "pybuilder._vendor.*",
                                                        "setup"])

    project.set_property("flake8_break_build", True)
    project.set_property("flake8_extend_ignore", "E303")
    project.set_property("flake8_include_test_sources", True)
    project.set_property("flake8_include_scripts", True)
    project.set_property("flake8_exclude_patterns", ",".join([
        project.expand_path("$dir_source_main_python", "pybuilder/_vendor/*")
    ]))
    project.set_property("flake8_max_line_length", 130)

    project.set_property("frosted_include_test_sources", True)
    project.set_property("frosted_include_scripts", True)

    project.set_property("copy_resources_target", "$dir_dist/pybuilder")
    project.get_property("copy_resources_glob").append("LICENSE")
    project.get_property("filter_resources_glob").append("**/pybuilder/__init__.py")
    project.include_file("pybuilder", "LICENSE")
    project.include_file("", "*.whl")  # All included binary wheels from vendors

    project.set_property("sphinx_doc_author", "PyBuilder Team")
    project.set_property("sphinx_doc_builder", "html")
    project.set_property("sphinx_project_name", project.name)
    project.set_property("sphinx_project_version", project.version)

    project.set_property("pdoc_module_name", "pybuilder")

    project.get_property("source_dist_ignore_patterns").extend([".project",
                                                                ".pydevproject",
                                                                ".settings"])

    # PyPy distutils needs os.environ['PATH'] not matter what
    # Also Windows needs PATH for DLL loading in all Pythons
    project.set_property("integrationtest_inherit_environment", True)

    # enable this to build a bdist on vagrant
    # project.set_property("distutils_issue8876_workaround_enabled", True)
    project.set_property("distutils_readme_description", True)
    project.set_property("distutils_description_overwrite", True)
    project.set_property("distutils_console_scripts", ["pyb = pybuilder.cli:main"])
    project.set_property("distutils_classifiers", [
        "Programming Language :: Python",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing"])
