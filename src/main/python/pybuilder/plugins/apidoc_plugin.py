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

import os
import errno

from pybuilder.core import init, task, use_plugin, description, depends, after
from pybuilder.utils import assert_can_execute, execute_command

use_plugin("core")


@init
def init_apidoc_plugin(project):
    """
    Initialize all the plugin default properties.
    """
    project.set_property_if_unset('apidoc_output_folder', 'docs/')
    project.set_property_if_unset('apidoc_src_folder', 'src/main/python/')


@after('prepare')
def assert_apidoc_is_executable(logger):
    """
    Assert that the apidoc script is executable.
    """
    logger.debug('Checking if apidoc is executable.')

    # APIDOC does not have --version command
    assert_can_execute(command_and_arguments=["apidoc", "--h"],
                       prerequisite="apidoc",
                       caller='plugin apidoc_plugin')


@after('prepare')
def assert_apidoc_configuration_file_exist(logger):
    """
    Assert that the apidoc configuration file exist.
    """
    logger.debug("Checking if apidoc configuration file exist.")

    if not os.path.isfile('apidoc.json'):
        raise


@task
@depends('prepare')
@description('Generates API documentation using apidoc.')
def generate_api_documentation_html(project, logger):
    """
    Use the ronn script to convert a markdown source to a gzipped manpage.
    """
    logger.info('Generating API Documentation')
    try:
        os.makedirs(project.get_property('apidoc_folder'))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    apidoc_report_file = project.expand_path("$dir_reports/{0}".format(
        'generate_API_documentation')
    )
    apidoc_command = 'apidoc -i %s -o %s' % (
        project.get_property('apidoc_src_folder'),
        project.get_property('apidoc_output_folder')
    )

    execute_command(apidoc_command, apidoc_report_file, shell=True)
