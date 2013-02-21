#   This file is part of Python Builder
#
#   Copyright 2011-2013 PyBuilder Team
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

from pybuilder.core import init, use_plugin, Author

use_plugin("python.core")
use_plugin("python.distutils")
use_plugin("python.install_dependencies")

use_plugin("copy_resources")
use_plugin("filter_resources")
use_plugin("source_distribution")

use_plugin("python.coverage")
use_plugin("python.unittest")
use_plugin("python.integrationtest")
use_plugin("python.flake8")
use_plugin("python.pylint")
use_plugin("python.pymetrics")

use_plugin("python.pydev")


summary = "An extensible, easy to use continuous build tool for Python"
description = """python-builder is a continuous build tool for multiple languages.

python-builder primarily targets Python projects but due to its extensible
nature it can be used for other languages as well.

python-builder features a powerful yet easy to use plugin mechanism which 
allows programmers to extend the tool in an unlimited way.  
"""

authors = [Author("Alexander Metzner", "alexander.metzner@gmail.com"),
           Author("Michael Gruber", "aelgru@gmail.com"),
           Author("Udo Juettner", "udo.juettner@gmail.com")]
url = "http://pybuilder.github.com"
license = "Apache License"
version = "0.9.4"

default_task = ["analyze", "publish"]

@init
def initialize(project):
    project.build_depends_on("mockito")
    project.build_depends_on("pymetrics")
    project.build_depends_on("pyassert")

    # Need to define that manually, because the pyfix plugin is not used directly.
    project.build_depends_on("pyfix")

    project.set_property("coverage_break_build", False)
    project.get_property("coverage_exceptions").append("pybuilder.cli")
    project.get_property("coverage_exceptions").append("pybuilder.plugins.core_plugin")

    project.set_property("copy_resources_target", "$dir_dist")
    project.get_property("copy_resources_glob").append("LICENSE")

    project.get_property("filter_resources_glob").append("**/pybuilder/__init__.py")

    project.set_property("flake8_verbose_output", True)
    project.set_property("flake8_break_build", True)
    project.set_property("flake8_ignore", "E211,E302,E501,W404,W801")

    #   E211 whitespace before '('
    #   E302 expected 2 blank lines
    #   E501 line too long
    #   W291 trailing whitespace
    #   W404 'from pybuilder.core import *' used; unable to detect undefined names
    #   W801 redefinition of unused 'StringIO'

    project.get_property("source_dist_ignore_patterns").append(".project")
    project.get_property("source_dist_ignore_patterns").append(".pydevproject")
    project.get_property("source_dist_ignore_patterns").append(".settings")

    project.get_property("distutils_commands").append("bdist_egg")
    project.set_property("distutils_classifiers", [
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python',
          'Topic :: Software Development :: Build Tools',
          'Topic :: Software Development :: Quality Assurance',
          'Topic :: Software Development :: Testing'])
