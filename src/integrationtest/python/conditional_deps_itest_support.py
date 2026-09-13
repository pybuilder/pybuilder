#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2026 PyBuilder Team
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

import ast
import textwrap
from os.path import join as jp

from itest_support import IntegrationTestSupport
from pybuilder.pip_utils import get_packages_info

BUILD_FILE = """
from pybuilder.core import use_plugin, init

use_plugin("python.core")
use_plugin("python.distutils")
use_plugin("python.install_dependencies")

name = "conditional-deps"
version = "1.0"
default_task = "publish"


@init
def init(project):
    project.set_property("install_dependencies_extras", %(extras)s)

    # The same distribution pinned differently per interpreter: exactly one applies anywhere
    project.depends_on("six", "==1.15.0", markers="python_version < '3.0'")
    project.depends_on("six", "==1.17.0", markers="python_version >= '3.0'")

    project.depends_on("colorama", ">=0.4", extra="security")
    project.depends_on("pywin32", ">=300", extra="windows", markers="sys_platform == 'win32'")
"""


class ConditionalDependenciesTestSupport(IntegrationTestSupport):
    """A project declaring a conditional pin and two extras groups, one of them conditional.

    Each subclass builds it once, under one `install_dependencies_extras` setting. A reactor
    cannot be prepared twice in one process, so a second setting means a second test module.
    """

    def build_project(self, extras):
        self.write_build_file(BUILD_FILE % {"extras": extras})
        self.create_directory("src/main/python")
        self.write_file(jp("src", "main", "python", "conditional_deps.py"), textwrap.dedent(
            """
            def spam():
                return "eggs"
            """))
        reactor = self.prepare_reactor()
        reactor.build("publish")
        return reactor

    def setup_call_keywords(self, reactor):
        """Keyword arguments of the generated setup.py's setup() call, as Python values.

        Parsing rather than string matching also asserts that what was generated is valid Python,
        which naive quoting of a marker such as ``sys_platform == 'win32'`` is not.
        """
        with open(reactor.project.expand_path("$dir_dist", "setup.py")) as setup_script:
            tree = ast.parse(setup_script.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "setup":
                keywords = {}
                for keyword in node.keywords:
                    try:
                        keywords[keyword.arg] = ast.literal_eval(keyword.value)
                    except ValueError:
                        pass
                return keywords

        raise AssertionError("no setup() call in the generated setup.py")

    def constraints(self, reactor, venv_name="build"):
        constraints_file = jp(reactor.python_env_registry[venv_name].env_dir, "constraints_file")
        with open(constraints_file) as constraints:
            return [line.strip() for line in constraints if line.strip()]

    def installed(self, reactor, venv_name="build"):
        return get_packages_info(reactor.python_env_registry[venv_name].site_paths)
