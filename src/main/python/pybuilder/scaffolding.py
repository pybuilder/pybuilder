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

import io
import os
import string

from pybuilder.terminal import print_text_line

_input = input

DEFAULT_SOURCE_DIRECTORY = 'src/main/python'
DEFAULT_UNITTEST_DIRECTORY = 'src/unittest/python'
DEFAULT_SCRIPTS_DIRECTORY = 'src/main/scripts'
DEFAULT_DOCS_DIRECTORY = 'docs'
PLUGINS_TO_SUGGEST = ['python.flake8', 'python.coverage', 'python.distutils']


def prompt_user(description, default):
    message = "{0} (default: '{1}') : ".format(description, default)
    return _input(message)


def collect_project_information():
    default_project_name = os.path.basename(os.getcwd())
    project_name = prompt_user('Project name', default_project_name) or default_project_name
    scaffolding = PythonProjectScaffolding(project_name)

    dir_source_main_python = prompt_user('Source directory', DEFAULT_SOURCE_DIRECTORY)
    dir_docs = prompt_user('Docs directory', DEFAULT_DOCS_DIRECTORY)
    dir_source_unittest_python = prompt_user('Unittest directory', DEFAULT_UNITTEST_DIRECTORY)
    dir_source_main_scripts = prompt_user("Scripts directory", DEFAULT_SCRIPTS_DIRECTORY)

    plugins = suggest_plugins(PLUGINS_TO_SUGGEST)
    scaffolding.add_plugins(plugins)

    if dir_source_main_python:
        scaffolding.dir_source_main_python = dir_source_main_python
    if dir_source_unittest_python:
        scaffolding.dir_source_unittest_python = dir_source_unittest_python
    if dir_source_main_scripts:
        scaffolding.dir_source_main_scripts = dir_source_main_scripts
    if dir_docs:
        scaffolding.dir_docs = dir_docs

    return scaffolding


def suggest_plugins(plugins):
    chosen_plugins = [plugin for plugin in [suggest(plugin) for plugin in plugins] if plugin]
    return chosen_plugins


def suggest(plugin):
    choice = prompt_user('Use plugin %s (Y/n)?' % plugin, 'y')
    plugin_enabled = not choice or choice.lower() == 'y'
    return plugin if plugin_enabled else None


def start_project():
    try:
        scaffolding = collect_project_information()
    except KeyboardInterrupt:
        print_text_line('\nCanceled.')
        return 1

    descriptor = scaffolding.render_build_descriptor()

    with io.open("build.py", "wt", encoding="utf-8") as build_descriptor_file:
        build_descriptor_file.write(descriptor)

    scaffolding.set_up_project()
    _create_setup_file()
    _create_pyproject_file()
    return 0


def update_project():
    _create_setup_file()
    _create_pyproject_file()
    return 0


def _create_pyproject_file():
    pyproject_contents = '''[build-system]
requires = ["pybuilder>=0.12.0"]
build-backend = "pybuilder.pep517"
'''
    if os.path.exists("pyproject.toml"):
        choice = prompt_user("Overwrite 'pyproject.toml' (y/N)?", 'n')
        overwrite = not choice or choice.lower() == 'y'
        if not overwrite:
            return
        os.unlink("pyproject.toml")
    with io.open("pyproject.toml", "wt", encoding="utf-8") as pyproject_file:
        pyproject_file.write(pyproject_contents)
    print_text_line("\nCreated 'pyproject.toml'.")


def _create_setup_file():
    setup_py_file_contents = '''#!/usr/bin/env python
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

#
# This script allows to support installation via:
#   pip install git+git://<project>@<branch>
#
# This script is designed to be used in combination with `pip install` ONLY
#
# DO NOT RUN MANUALLY
#

import os
import subprocess
import sys
import glob
import shutil

from sys import version_info
py3 = version_info[0] == 3
py2 = not py3
if py2:
    FileNotFoundError = OSError


def install_pyb():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pybuilder"])
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


script_dir = os.path.dirname(os.path.realpath(__file__))
exit_code = 0

try:
    subprocess.check_call(["pyb", "--version"])
except FileNotFoundError as e:
    if py3 or py2 and e.errno == 2:
        install_pyb()
    else:
        raise
except subprocess.CalledProcessError as e:
    if e.returncode == 127:
        install_pyb()
    else:
        sys.exit(e.returncode)

try:
    from pybuilder.cli import main
    # verbose, debug, skip all optional...
    if main("-v", "-X", "-o", "--reset-plugins", "clean", "package"):
        raise RuntimeError("PyBuilder build failed")

    from pybuilder.reactor import Reactor
    reactor = Reactor.current_instance()
    project = reactor.project
    dist_dir = project.expand_path("$dir_dist")

    for src_file in glob.glob(os.path.join(dist_dir, "*")):
        file_name = os.path.basename(src_file)
        target_file_name = os.path.join(script_dir, file_name)
        if os.path.exists(target_file_name):
            if os.path.isdir(target_file_name):
                shutil.rmtree(target_file_name)
            else:
                os.remove(target_file_name)
        shutil.move(src_file, script_dir)
    setup_args = sys.argv[1:]
    subprocess.check_call([sys.executable, "setup.py"] + setup_args, cwd=script_dir)
except subprocess.CalledProcessError as e:
    exit_code = e.returncode
sys.exit(exit_code)
'''
    if os.path.exists("setup.py"):
        choice = prompt_user("Overwrite 'setup.py' (y/N)?", 'n')
        overwrite = not choice or choice.lower() == 'y'
        if not overwrite:
            return
        os.unlink("setup.py")
    with io.open("setup.py", "wt", encoding="utf-8") as setup_descriptor_file:
        setup_descriptor_file.write(setup_py_file_contents)
    print_text_line("\nCreated 'setup.py'.")


class PythonProjectScaffolding(object):
    DESCRIPTOR_TEMPLATE = string.Template("""#   -*- coding: utf-8 -*-
from pybuilder.core import $core_imports

$activated_plugins


name = "${project_name}"
default_task = "publish"


$initializer
""")

    INITIALIZER_HEAD = '''@init
def set_properties(project):
'''

    def __init__(self, project_name):
        self.project_name = project_name
        self.dir_source_main_python = DEFAULT_SOURCE_DIRECTORY
        self.dir_source_unittest_python = DEFAULT_UNITTEST_DIRECTORY
        self.dir_source_main_scripts = DEFAULT_SCRIPTS_DIRECTORY
        self.dir_docs = DEFAULT_DOCS_DIRECTORY
        self.core_imports = ['use_plugin']
        self.plugins = ['python.core', 'python.unittest']
        self.initializer = ''

    def add_plugins(self, plugins):
        self.plugins.extend(plugins)

    def render_build_descriptor(self):
        self.build_initializer()
        self.build_imports()
        self.core_imports = ', '.join(self.core_imports)
        return self.DESCRIPTOR_TEMPLATE.substitute(self.__dict__)

    def build_imports(self):
        self.activated_plugins = '\n'.join(['use_plugin("%s")' % plugin for plugin in self.plugins])

    def build_initializer(self):
        self.core_imports.append('init')

        properties_to_set = []
        if not self.is_default_source_main_python:
            properties_to_set.append(('dir_source_main_python', self.dir_source_main_python))
        if not self.is_default_source_unittest_python:
            properties_to_set.append(('dir_source_unittest_python', self.dir_source_unittest_python))
        if not self.is_default_source_main_scripts:
            properties_to_set.append(('dir_source_main_scripts', self.dir_source_main_scripts))
        if not self.is_default_docs:
            properties_to_set.append(('dir_docs', self.dir_docs))

        initializer_body = self._build_initializer_body_with_properties(properties_to_set)

        self.initializer = self.INITIALIZER_HEAD + initializer_body

    @property
    def is_default_source_main_python(self):
        return self.dir_source_main_python == DEFAULT_SOURCE_DIRECTORY

    @property
    def is_default_source_unittest_python(self):
        return self.dir_source_unittest_python == DEFAULT_UNITTEST_DIRECTORY

    @property
    def is_default_docs(self):
        return self.dir_docs == DEFAULT_DOCS_DIRECTORY

    @property
    def is_default_source_main_scripts(self):
        return self.dir_source_main_scripts == DEFAULT_SCRIPTS_DIRECTORY

    def set_up_project(self):
        for needed_directory in (self.dir_source_main_python,
                                 self.dir_source_unittest_python,
                                 self.dir_docs,
                                 self.dir_source_main_scripts):
            if not os.path.exists(needed_directory):
                os.makedirs(needed_directory)

    @staticmethod
    def _build_initializer_body_with_properties(properties_to_set):
        initializer_body = ''
        initializer_body += '\n'.join(
            ['    project.set_property("{0}", "{1}")'.format(k, v) for k, v in properties_to_set])

        if not initializer_body:
            initializer_body += '    pass'

        return initializer_body
