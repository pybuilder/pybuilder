#   -*- coding: utf-8 -*-
#
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

"""Plugin for Sphinx.
"""

__author__ = 'Thomas Prebble'

from pybuilder.core import after
from pybuilder.core import depends
from pybuilder.core import init
from pybuilder.core import task
from pybuilder.core import use_plugin
from pybuilder.utils import assert_can_execute


use_plugin("python.core")


@init
def initialize_sphinx_plugin(project):
    project.build_depends_on("sphinx")


@after("prepare")
def assert_sphinx_is_available(logger):
    """Asserts that the sphinx-build script is available.
    """
    logger.debug("Checking if sphinx-build is available.")

    assert_can_execute(["sphinx-build", "--version"], "sphinx", "plugin python.sphinx")


@task
@depends("prepare")
def analyze(project, logger):
    """Runs sphinx-build against rst sources for the given project.
    """
