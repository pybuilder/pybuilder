#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import os
import string

from pybuilder.terminal import print_text_line

try:
    input
except NameError:
    input = raw_input  # NOQA
                       # flake8 sees this as an error on python 3, but there is
                       # no NameError due to `input` on py3...

DEFAULT_SOURCE_DIRECTORY = 'src/main/python'
DEFAULT_UNITTEST_DIRECTORY = 'src/unittest/python'


def prompt_user(description, default):
    message = "{0} (default: '{1}') : ".format(description, default)
    return input(message)


def collect_project_information():
    default_project_name = os.path.basename(os.getcwd())
    project_name = prompt_user('Project name', default_project_name) or default_project_name
    scaffolding = PythonProjectScaffolding(project_name)

    dir_source_main_python = prompt_user('Source directory', DEFAULT_SOURCE_DIRECTORY)
    dir_source_unittest_python = prompt_user(
        'Unittest directory', DEFAULT_UNITTEST_DIRECTORY)

    if dir_source_main_python:
        scaffolding.dir_source_main_python = dir_source_main_python
    if dir_source_unittest_python:
        scaffolding.dir_source_unittest_python = dir_source_unittest_python

    return scaffolding


def start_project():
    try:
        scaffolding = collect_project_information()
    except:
        print_text_line('Canceled.')
        return 1

    descriptor = scaffolding.render_build_descriptor()

    with open('build.py', 'w') as build_descriptor_file:
        build_descriptor_file.write(descriptor)

    scaffolding.set_up_project()
    return 0


class PythonProjectScaffolding(object):

    descriptor_template = string.Template("""
from pybuilder.core import $core_imports

use_plugin("python.core")
use_plugin("python.unittest")

name = "${project_name}"
default_task = "publish"

$initializer

""")

    def __init__(self, project_name):
        self.project_name = project_name
        self.dir_source_main_python = DEFAULT_SOURCE_DIRECTORY
        self.dir_source_unittest_python = DEFAULT_UNITTEST_DIRECTORY
        self.core_imports = ['use_plugin']
        self.initializer = ''

    def render_build_descriptor(self):
        self.build_initializer()
        self.core_imports = ', '.join(self.core_imports)
        return self.descriptor_template.substitute(self.__dict__)

    def build_initializer(self):
        if self.is_default_source_main_python and self.is_default_source_unittest_python:
            return

        self.core_imports.append('init')

        properties_to_set = []
        if not self.is_default_source_main_python:
            properties_to_set.append(('dir_source_main_python', self.dir_source_main_python))
        if not self.is_default_source_unittest_python:
            properties_to_set.append(('dir_source_unittest_python', self.dir_source_unittest_python))

        self.initializer = '''@init
def set_properties(project):
'''
        self.initializer += '\n'.join(
            ['    project.set_property("{0}", "{1}")'.format(k, v) for k, v in properties_to_set])

    @property
    def is_default_source_main_python(self):
        return self.dir_source_main_python == DEFAULT_SOURCE_DIRECTORY

    @property
    def is_default_source_unittest_python(self):
        return self.dir_source_unittest_python == DEFAULT_UNITTEST_DIRECTORY

    def set_up_project(self):
        for needed_directory in (self.dir_source_main_python,
                                 self.dir_source_unittest_python):
            if not os.path.exists(needed_directory):
                os.makedirs(needed_directory)
