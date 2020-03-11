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

from pybuilder.core import init, task, use_plugin
from pybuilder.utils import apply_on_files

use_plugin("core")


@init
def init_copy_resources_plugin(project):
    project.set_property_if_unset("copy_resources_target", "$dir_target")
    project.set_property_if_unset("copy_resources_glob", [])


@task
def package(project, logger):
    globs = project.get_mandatory_property("copy_resources_glob")
    if not globs:
        logger.warn("No resources to copy configured. Consider removing plugin.")
        return

    source = project.basedir
    target = project.expand_path("$copy_resources_target")
    logger.info("Copying resources matching '%s' from %s to %s", " ".join(globs), source, target)

    apply_on_files(source, copy_resource, globs, target, logger)


def copy_resource(absolute_file_name, relative_file_name, target, logger):
    logger.debug("Copying resource %s", relative_file_name)

    absolute_target_file_name = os.path.join(target, relative_file_name)
    parent = os.path.dirname(absolute_target_file_name)
    if not os.path.exists(parent):
        os.makedirs(parent)
    shutil.copy(absolute_file_name, absolute_target_file_name)
