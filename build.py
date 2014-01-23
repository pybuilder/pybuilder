#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
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

import os
import subprocess

from pybuilder.core import init, use_plugin, Author, task
from pybuilder.errors import MissingPrerequisiteException

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

use_plugin("python.pydev")
use_plugin("python.pycharm")
use_plugin("python.pytddmon")


summary = "An extensible, easy to use continuous build tool for Python"
description = """PyBuilder is a continuous build tool for multiple languages.

PyBuilder primarily targets Python projects but due to its extensible
nature it can be used for other languages as well.

PyBuilder features a powerful yet easy to use plugin mechanism which
allows programmers to extend the tool in an unlimited way.
"""

authors = [Author("Alexander Metzner", "alexander.metzner@gmail.com"),
           Author("Maximilien Riehl", "max@riehl.io"),
           Author("Michael Gruber", "aelgru@gmail.com"),
           Author("Udo Juettner", "udo.juettner@gmail.com")]
url = "http://pybuilder.github.io"
license = "Apache License"
version = "0.9.22"

default_task = ["analyze", "publish"]


@init
def initialize(project):
    project.build_depends_on("mockito-without-hardcoded-distribute-version")
    project.build_depends_on("mock")
    project.build_depends_on("pyfix")  # required test framework
    project.build_depends_on("pyassert")
    project.build_depends_on("wheel")

    project.set_property("coverage_break_build", False)
    project.get_property("coverage_exceptions").append("pybuilder.cli")
    project.get_property("coverage_exceptions").append("pybuilder.plugins.core_plugin")

    project.set_property("integrationtest_parallel", True)
    project.set_property("integrationtest_cpu_scaling_factor", 1)

    project.set_property("copy_resources_target", "$dir_dist")
    project.get_property("copy_resources_glob").append("LICENSE")
    project.get_property("filter_resources_glob").append("**/pybuilder/__init__.py")


    project.set_property("flake8_verbose_output", True)
    project.set_property("flake8_break_build", True)
    project.set_property('flake8_include_test_sources', True)
    project.set_property("flake8_max_line_length", 130)

    project.get_property("source_dist_ignore_patterns").append(".project")
    project.get_property("source_dist_ignore_patterns").append(".pydevproject")
    project.get_property("source_dist_ignore_patterns").append(".settings")

    project.get_property("distutils_commands").append("bdist_wheel")
    project.set_property("distutils_classifiers", [
                         'Programming Language :: Python',
                         'Programming Language :: Python :: Implementation :: CPython',
                         'Programming Language :: Python :: Implementation :: PyPy',
                         'Programming Language :: Python :: 2.6',
                         'Programming Language :: Python :: 2.7',
                         'Programming Language :: Python :: 3',
                         'Programming Language :: Python :: 3.2',
                         'Programming Language :: Python :: 3.3',
                         'Development Status :: 3 - Alpha',
                         'Environment :: Console',
                         'Intended Audience :: Developers',
                         'License :: OSI Approved :: Apache Software License',
                         'Topic :: Software Development :: Build Tools',
                         'Topic :: Software Development :: Quality Assurance',
                         'Topic :: Software Development :: Testing'])


@task
def pdoc_generate(project, logger):
    try:
        import pdoc
        logger.debug("pdoc is installed in version %s" % pdoc.__version__)

    except ImportError:
        raise MissingPrerequisiteException("pdoc", caller=pdoc_generate.__name__)

    logger.info("Generating pdoc documentation")

    command_and_arguments = ["pdoc", "--html", "pybuilder", "--all-submodules", "--overwrite", "--html-dir", "api-doc"]
    source_directory = project.get_property("dir_source_main_python")
    environment = {"PYTHONPATH": source_directory,
                   "PATH": os.environ["PATH"]}

    subprocess.check_call(command_and_arguments, shell=False, env=environment)
