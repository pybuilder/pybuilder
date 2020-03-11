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

import os
import shutil

from pybuilder.core import init, task, use_plugin, description

use_plugin("core")


@init
def init_source_distribution(project):
    source_distribution_directory = "$dir_target/dist/%s-%s-src" % (project.name, project.version)
    project.set_property_if_unset("dir_source_dist", source_distribution_directory)
    project.set_property_if_unset("source_dist_ignore_patterns", ["*.pyc", ".hg*", ".svn", ".CVS"])


@task
@description("Bundles a source distribution for shipping.")
def build_source_distribution(project, logger):
    source_distribution_directory = project.expand_path("$dir_source_dist")
    logger.info("Building source distribution in {0}".format(source_distribution_directory))

    if os.path.exists(source_distribution_directory):
        shutil.rmtree(source_distribution_directory)

    ignore_patterns = ["target"]
    configured_patterns = project.get_property("source_dist_ignore_patterns")
    if configured_patterns:
        ignore_patterns += configured_patterns

    shutil.copytree(project.basedir,
                    source_distribution_directory,
                    ignore=shutil.ignore_patterns(*ignore_patterns))
