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

import subprocess

from pybuilder.core import use_plugin, task, init, description

use_plugin('python.core')


@init
def init_pytddmon_plugin(project):
    project.plugin_depends_on('pytddmon', '>=1.0.2')


@task
@description('Start monitoring tests.')
def pytddmon(project, logger):
    import os
    unittest_directory = project.get_property('dir_source_unittest_python')
    environment = os.environ.copy()
    python_path_relative_to_basedir = project.get_property('dir_source_main_python')
    absolute_python_path = os.path.join(project.basedir, python_path_relative_to_basedir)
    environment['PYTHONPATH'] = absolute_python_path

    # necessary because of windows newlines in the pytddmon shebang - must fix upstream first
    python_interpreter = subprocess.check_output('which python', shell=True).rstrip('\n')
    pytddmon_script = subprocess.check_output('which pytddmon.py', shell=True).rstrip('\n')

    subprocess.Popen([python_interpreter, pytddmon_script, '--no-pulse'], shell=False, cwd=unittest_directory, env=environment)
