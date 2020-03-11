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

import string

from pybuilder.core import init, after, use_plugin
from pybuilder.utils import apply_on_files, read_file, write_file

use_plugin("core")


@init
def init_filter_resources_plugin(project):
    project.set_property_if_unset("filter_resources_target", "$dir_target")
    project.set_property_if_unset("filter_resources_glob", [])


@after("package", only_once=True)
def filter_resources(project, logger):
    globs = project.get_mandatory_property("filter_resources_glob")
    if not globs:
        logger.warn("No resources to filter configured. Consider removing plugin.")
        return

    target = project.expand_path("$filter_resources_target")
    logger.info("Filter resources matching %s in %s", " ".join(globs), target)

    project_dict_wrapper = ProjectDictWrapper(project, logger)

    apply_on_files(target, filter_resource, globs, project_dict_wrapper, logger)


def filter_resource(absolute_file_name, relative_file_name, dictionary, logger):
    logger.debug("Filtering resource %s", absolute_file_name)
    content = "".join(read_file(absolute_file_name))
    filtered = string.Template(content).safe_substitute(dictionary)
    write_file(absolute_file_name, filtered)


class ProjectDictWrapper(object):

    def __init__(self, project, logger):
        self.project = project
        self.logger = logger

    def __getitem__(self, key):
        fallback_when_no_substitution_possible = "${%s}" % key
        if hasattr(self.project, key):
            return getattr(self.project, key)
        if self.project.has_property(key):
            return self.project.get_property(key)
        self.logger.warn(
            "Skipping impossible substitution for '{0}' - there is no matching project attribute or property.".format(key))
        return fallback_when_no_substitution_possible
