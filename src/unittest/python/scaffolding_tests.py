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

from mock import patch, call
from unittest import TestCase

from pybuilder.scaffolding import (PythonProjectScaffolding,
                                   collect_project_information,
                                   suggest,
                                   suggest_plugins)


class PythonProjectScaffoldingTests(TestCase):

    def test_should_set_up_scaffolding_with_defaults(self):
        scaffolding = PythonProjectScaffolding('some-project')

        self.assertEqual(scaffolding.dir_source_main_python, 'src/main/python')
        self.assertEqual(
            scaffolding.dir_source_unittest_python, 'src/unittest/python')
        self.assertEqual(scaffolding.dir_docs, 'docs')
        self.assertEqual(
            scaffolding.dir_source_main_scripts, 'src/main/scripts')

    def test_should_build_empty_initializer_when_defaults_are_used(self):
        scaffolding = PythonProjectScaffolding('some-project')
        scaffolding.build_initializer()

        self.assertEqual(scaffolding.initializer, '''@init
def set_properties(project):
    pass''')

    def test_should_build_initializer_for_custom_source_dir(self):
        scaffolding = PythonProjectScaffolding('some-project')
        scaffolding.dir_source_main_python = 'src'
        scaffolding.build_initializer()

        self.assertEqual(scaffolding.initializer, '''@init
def set_properties(project):
    project.set_property("dir_source_main_python", "src")''')

    def test_should_build_initializer_for_custom_test_dir(self):
        scaffolding = PythonProjectScaffolding('some-project')
        scaffolding.dir_source_unittest_python = 'test'
        scaffolding.build_initializer()

        self.assertEqual(scaffolding.initializer, '''@init
def set_properties(project):
    project.set_property("dir_source_unittest_python", "test")''')

    def test_should_build_initializer_for_custom_test_and_source_dir(self):
        scaffolding = PythonProjectScaffolding('some-project')
        scaffolding.dir_source_unittest_python = 'test'
        scaffolding.dir_source_main_python = 'src'
        scaffolding.build_initializer()

        self.assertEqual(scaffolding.initializer, '''@init
def set_properties(project):
    project.set_property("dir_source_main_python", "src")
    project.set_property("dir_source_unittest_python", "test")''')

    def test_should_render_build_descriptor_with_custom_dirs(self):
        scaffolding = PythonProjectScaffolding('some-project')
        scaffolding.dir_source_unittest_python = 'test'
        scaffolding.dir_source_main_python = 'src'

        self.assertEqual(scaffolding.render_build_descriptor(), '''\
from pybuilder.core import use_plugin, init

use_plugin("python.sphinx")
use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.install_dependencies")


name = "some-project"
default_task = "publish"


@init
def set_properties(project):
    project.set_property("dir_source_main_python", "src")
    project.set_property("dir_source_unittest_python", "test")
''')

    def test_should_render_build_descriptor_without_custom_dirs(self):
        scaffolding = PythonProjectScaffolding('some-project')

        self.assertEqual(scaffolding.render_build_descriptor(), '''\
from pybuilder.core import use_plugin, init

use_plugin("python.sphinx")
use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.install_dependencies")


name = "some-project"
default_task = "publish"


@init
def set_properties(project):
    pass
''')

    def test_should_render_build_descriptor_with_additional_imports(self):
        scaffolding = PythonProjectScaffolding('some-project')
        scaffolding.add_plugins(['foo', 'bar'])

        self.assertTrue('\nuse_plugin("foo")\nuse_plugin("bar")\n' in scaffolding.render_build_descriptor())

    @patch('pybuilder.scaffolding.os')
    def test_should_set_up_project_when_directories_missing(self, mock_os):
        scaffolding = PythonProjectScaffolding('some-project')
        mock_os.path.exists.return_value = False

        scaffolding.set_up_project()

        self.assertEqual(mock_os.makedirs.call_args_list,
                         [
                             call('src/main/python'),
                             call('src/unittest/python'),
                             call('docs'),
                             call('src/main/scripts')
                         ])

    @patch('pybuilder.scaffolding.os')
    def test_should_set_up_project_when_directories_present(self, mock_os):
        scaffolding = PythonProjectScaffolding('some-project')
        mock_os.path.exists.return_value = True

        scaffolding.set_up_project()

        self.assertFalse(mock_os.called)


class CollectProjectInformationTests(TestCase):

    @patch('pybuilder.scaffolding.os')
    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_prompt_user_with_defaults(self, prompt, os):
        os.path.basename.return_value = 'project'
        collect_project_information()

        self.assertEqual(prompt.call_args_list,
                         [
                             call('Project name', 'project'),
                             call('Source directory', 'src/main/python'),
                             call('Docs directory', 'docs'),
                             call('Unittest directory', 'src/unittest/python'),
                             call('Scripts directory', 'src/main/scripts'),
                             call('Use plugin python.sphinx (Y/n)?', 'y'),
                             call('Use plugin python.flake8 (Y/n)?', 'y'),
                             call('Use plugin python.coverage (Y/n)?', 'y'),
                             call('Use plugin python.distutils (Y/n)?', 'y')
                         ])

    @patch('pybuilder.scaffolding.os')
    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_collect_project_name(self, prompt, os):
        prompt.return_value = 'project'
        scaffolding = collect_project_information()

        self.assertEqual(scaffolding.project_name, 'project')

    @patch('pybuilder.scaffolding.os')
    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_collect_source_dir(self, prompt, os):
        prompt.return_value = 'src'
        scaffolding = collect_project_information()

        self.assertEqual(scaffolding.dir_source_main_python, 'src')

    @patch('pybuilder.scaffolding.os')
    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_collect_test_dir(self, prompt, os):
        prompt.return_value = 'test'
        scaffolding = collect_project_information()

        self.assertEqual(scaffolding.dir_source_unittest_python, 'test')

    @patch('pybuilder.scaffolding.os')
    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_collect_scripts_dir(self, prompt, os):
        prompt.return_value = 'scripts'
        scaffolding = collect_project_information()

        self.assertEqual(scaffolding.dir_source_main_scripts, 'scripts')


class PluginSuggestionTests(TestCase):

    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_filter_out_plugins_that_were_not_chosen(self, prompt):
        prompt.side_effect = ['', 'n', 'y', 'N', 'Y']
        chosen_plugins = suggest_plugins(['plugin-1', 'plugin-2', 'plugin-3', 'plugin-4', 'plugin-5'])

        self.assertEqual(chosen_plugins, ['plugin-1', 'plugin-3', 'plugin-5'])

    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_return_plugin_when_choice_is_skipped(self, prompt):
        prompt.return_value = ''

        self.assertEqual(suggest('plugin'), 'plugin')

    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_return_plugin_when_plugin_is_chosen_lowercase(self, prompt):
        prompt.return_value = 'y'

        self.assertEqual(suggest('plugin'), 'plugin')

    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_return_plugin_when_plugin_is_chosen_uppercase(self, prompt):
        prompt.return_value = 'Y'

        self.assertEqual(suggest('plugin'), 'plugin')

    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_return_non_when_plugin_is_refused_lowercase(self, prompt):
        prompt.return_value = 'n'

        self.assertEqual(suggest('plugin'), None)

    @patch('pybuilder.scaffolding.prompt_user')
    def test_should_return_non_when_plugin_is_refused_uppercase(self, prompt):
        prompt.return_value = 'N'

        self.assertEqual(suggest('plugin'), None)
