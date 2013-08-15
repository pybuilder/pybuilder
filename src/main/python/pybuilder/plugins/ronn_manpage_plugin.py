#   This file is part of PyBuilder
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

import os
import errno

from pybuilder.core import init, task, use_plugin, description, after, before
from pybuilder.utils import assert_can_execute, execute_command

use_plugin("core")


@init
def init_ronn_manpage_plugin(project):
    project.set_property_if_unset("dir_manpages", "docs/man")
    project.set_property_if_unset("manpage_source", "README.md")
    project.set_property_if_unset("manpage_section", 1)


@after("prepare")
def assert_ronn_is_executable(logger):
    """
        Asserts that the ronn script is executable.
    """
    logger.debug("Checking if ronn is executable.")

    assert_can_execute(command_and_arguments=["ronn", "--version"],
                       prerequisite="ronn",
                       caller="plugin ronn_manpage_plugin")


@after("prepare")
def assert_gzip_is_executable(logger):
    """
        Asserts that the gzip program is executable.
    """
    logger.debug("Checking if gzip is executable.")

    assert_can_execute(command_and_arguments=["gzip", "--version"],
                       prerequisite="gzip",
                       caller="plugin ronn_manpage_plugin")


@task
@before(("package", "publish"))
@description("Generates manpages using ronn.")
def generate_manpages(project, logger):
    """
        Uses the ronn script to convert a markdown source to a gzipped manpage.
    """
    logger.info('Generating manpages')
    try:
        os.makedirs(project.get_property('dir_manpages'))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    ronn_report_file = project.expand_path("$dir_reports/{0}".format('generate_manpage'))
    generate_manpages_command = build_generate_manpages_command(project)
    execute_command(generate_manpages_command, ronn_report_file, shell=True)


def build_generate_manpages_command(project):
    ronn_pipe_command = 'ronn -r --pipe %s' % project.get_property('manpage_source')
    compressed_manpage_file = '%s.%d.gz' % (project.name, project.get_property('manpage_section'))
    compress_command = 'gzip -9 > %s' % os.path.join(project.get_property('dir_manpages'), compressed_manpage_file)
    generate_manpages_command = '%s | %s' % (ronn_pipe_command, compress_command)
    return generate_manpages_command
