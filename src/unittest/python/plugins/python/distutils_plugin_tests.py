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

try:
    TYPE_FILE = file
except NameError:
    from io import FileIO

    TYPE_FILE = FileIO

import unittest

from mock import patch, MagicMock

from test_utils import PyBuilderTestCase
from pybuilder.core import Project, Author, Logger
from pybuilder.plugins.python.distutils_plugin import (build_data_files_string,
                                                       build_dependency_links_string,
                                                       build_install_dependencies_string,
                                                       build_package_data_string,
                                                       build_console_scripts_string,
                                                       default,
                                                       render_manifest_file,
                                                       build_scripts_string,
                                                       render_setup_script,
                                                       initialize_distutils_plugin,
                                                       execute_distutils,
                                                       upload,
                                                       install_distribution,
                                                       build_binary_distribution)


class InstallDependenciesTest(unittest.TestCase):
    def setUp(self):
        self.project = Project(".")

    def test_should_leave_user_specified_properties_when_initializing_plugin(self):

        expected_properties = {
            "distutils_commands": ["foo", "bar"],
            "distutils_issue8876_workaround_enabled": True,
            "distutils_classifiers": [
                "Development Status :: 3 - Beta",
                "Programming Language :: Rust"
            ],
            "distutils_use_setuptools": False
        }

        for property_name, property_value in expected_properties.items():
            self.project.set_property(property_name, property_value)

            initialize_distutils_plugin(self.project)

        for property_name, property_value in expected_properties.items():
            self.assertEquals(
                self.project.get_property("distutils_commands"), ["foo", "bar"])
            self.assertEquals(
                self.project.get_property("distutils_issue8876_workaround_enabled"), True)
            self.assertEquals(
                self.project.get_property("distutils_classifiers"), ["Development Status :: 3 - Beta",
                                                                     "Programming Language :: Rust"])
            self.assertEquals(
                self.project.get_property("distutils_use_setuptools"), False)

    def test_should_return_empty_string_when_no_dependency_is_given(self):
        self.assertEqual("[]", build_install_dependencies_string(self.project))

    def test_should_return_single_dependency_string(self):
        self.project.depends_on("spam")
        self.assertEqual(
            "['spam']", build_install_dependencies_string(self.project))

    def test_should_return_single_dependency_string_with_version(self):
        self.project.depends_on("spam", "0.7")
        self.assertEqual(
            "['spam>=0.7']", build_install_dependencies_string(self.project))

    def test_should_return_multiple_dependencies_string_with_versions(self):
        self.project.depends_on("spam", "0.7")
        self.project.depends_on("eggs")
        self.assertEqual(
            "[\n            'eggs',\n            'spam>=0.7'\n        ]", build_install_dependencies_string(self.project))

    def test_should_not_insert_url_dependency_into_install_requires(self):
        self.project.depends_on("spam")
        self.project.depends_on(
            "pyassert", url="https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz")

        self.assertEqual(
            "['spam']", build_install_dependencies_string(self.project))

    def test_should_not_insert_default_version_operator_when_project_contains_operator_in_version(self):
        self.project.depends_on("spam", "==0.7")
        self.assertEqual(
            "['spam==0.7']", build_install_dependencies_string(self.project))

    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    def test_should_quote_requirements(self, mock_open):
        mock_open.return_value = MagicMock(spec=TYPE_FILE)
        handle = mock_open.return_value.__enter__.return_value
        handle.readlines.return_value = ["foo", "bar"]
        self.project.depends_on_requirements("requirements.txt")

        self.assertEqual(
            "[\n            'foo',\n            'bar'\n        ]", build_install_dependencies_string(self.project))

    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    def test_should_ignore_empty_requirement_lines(self, mock_open):
        mock_open.return_value = MagicMock(spec=TYPE_FILE)
        handle = mock_open.return_value.__enter__.return_value
        handle.readlines.return_value = ["", "foo", "bar"]
        self.project.depends_on_requirements("requirements.txt")

        self.assertEqual(
            "[\n            'foo',\n            'bar'\n        ]", build_install_dependencies_string(self.project))

    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    def test_should_ignore_comments_from_requirements(self, mock_open):
        mock_open.return_value = MagicMock(spec=TYPE_FILE)
        handle = mock_open.return_value.__enter__.return_value
        handle.readlines.return_value = ["#comment", "bar"]
        self.project.depends_on_requirements("requirements.txt")

        self.assertEqual(
            "['bar']", build_install_dependencies_string(self.project))

    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    def test_should_ignore_comments_with_leading_space_from_requirements(self, mock_open):
        mock_open.return_value = MagicMock(spec=TYPE_FILE)
        handle = mock_open.return_value.__enter__.return_value
        handle.readlines.return_value = [" # comment", "bar"]
        self.project.depends_on_requirements("requirements.txt")

        self.assertEqual(
            "['bar']", build_install_dependencies_string(self.project))

    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    def test_should_ignore_editable_urls_from_requirements(self, mock_open):
        mock_open.return_value = MagicMock(spec=TYPE_FILE)
        handle = mock_open.return_value.__enter__.return_value
        handle.readlines.return_value = [
            "foo", "-e git+https://github.com/someuser/someproject.git#egg=some_package"]
        self.project.depends_on_requirements("requirements.txt")

        self.assertEqual(
            "['foo']", build_install_dependencies_string(self.project))

    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    def test_should_ignore_expanded_editable_urls_from_requirements(self, mock_open):
        mock_open.return_value = MagicMock(spec=TYPE_FILE)
        handle = mock_open.return_value.__enter__.return_value
        handle.readlines.return_value = [
            "foo", "--editable git+https://github.com/someuser/someproject.git#egg=some_package"]
        self.project.depends_on_requirements("requirements.txt")

        self.assertEqual(
            "['foo']", build_install_dependencies_string(self.project))


class DependencyLinksTest(unittest.TestCase):
    def setUp(self):
        self.project = Project(".")

    def test_should_return_empty_string_when_no_link_dependency_is_given(self):
        self.assertEqual("[]", build_dependency_links_string(self.project))

    def test_should_return_dependency_link(self):
        self.project.depends_on(
            "pyassert", url="https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz")
        self.assertEqual(
            "['https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz']",
            build_dependency_links_string(self.project))

    def test_should_return_dependency_links(self):
        self.project.depends_on("pyassert1",
                                url="https://github.com/downloads/halimath/pyassert/pyassert1-0.2.2.tar.gz")
        self.project.depends_on("pyassert2",
                                url="https://github.com/downloads/halimath/pyassert/pyassert2-0.2.2.tar.gz")
        self.assertEqual("[\n            'https://github.com/downloads/halimath/pyassert/pyassert1-0.2.2.tar.gz',\n"
                         "            'https://github.com/downloads/halimath/pyassert/pyassert2-0.2.2.tar.gz'\n"
                         "        ]",
                         build_dependency_links_string(self.project))

    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    def test_should_use_editable_urls_from_requirements_as_dependency_links(self, mock_open):
        mock_open.return_value = MagicMock(spec=TYPE_FILE)
        handle = mock_open.return_value.__enter__.return_value
        handle.readlines.return_value = [
            "-e git+https://github.com/someuser/someproject.git#egg=some_package",
            "-e svn+https://github.com/someuser/someproject#egg=some_package"]
        self.project.depends_on_requirements("requirements.txt")

        self.assertEqual(
            "[\n            'git+https://github.com/someuser/someproject.git#egg=some_package',\n"
            "            'svn+https://github.com/someuser/someproject#egg=some_package'\n"
            "        ]",
            build_dependency_links_string(self.project))

    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    def test_should_use_expanded_editable_urls_from_requirements_as_dependency_links(self, mock_open):
        mock_open.return_value = MagicMock(spec=TYPE_FILE)
        handle = mock_open.return_value.__enter__.return_value
        handle.readlines.return_value = [
            "--editable git+https://github.com/someuser/someproject.git#egg=some_package",
            "--editable svn+https://github.com/someuser/someproject#egg=some_package"]
        self.project.depends_on_requirements("requirements.txt")

        self.assertEqual(
            "[\n            'git+https://github.com/someuser/someproject.git#egg=some_package',\n"
            "            'svn+https://github.com/someuser/someproject#egg=some_package'\n"
            "        ]",
            build_dependency_links_string(self.project))

    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    def test_should_use_editable_urls_from_requirements_combined_with_url_dependencies(self, mock_open):
        mock_open.return_value = MagicMock(spec=TYPE_FILE)
        handle = mock_open.return_value.__enter__.return_value
        handle.readlines.return_value = [
            "-e svn+https://github.com/someuser/someproject#egg=some_package"]
        self.project.depends_on(
            "jedi", url="git+https://github.com/davidhalter/jedi")
        self.project.depends_on_requirements("requirements.txt")

        self.assertEqual(
            "[\n            'git+https://github.com/davidhalter/jedi',\n"
            "            'svn+https://github.com/someuser/someproject#egg=some_package'\n"
            "        ]",
            build_dependency_links_string(self.project))


class DefaultTest(unittest.TestCase):
    def test_should_return_empty_string_as_default_when_given_value_is_none(self):
        self.assertEqual("", default(None))

    def test_should_return_given_default_when_given_value_is_none(self):
        self.assertEqual("default", default(None, default="default"))

    def test_should_return_value_string_when_value_given(self):
        self.assertEqual("value", default("value"))

    def test_should_return_value_string_when_value_and_default_given(self):
        self.assertEqual("value", default("value", default="default"))


class BuildDataFilesStringTest(unittest.TestCase):
    def setUp(self):
        self.project = Project(".")

    def test_should_return_empty_data_files_string(self):
        self.assertEqual("[]", build_data_files_string(self.project))

    def test_should_return_data_files_string_including_several_files(self):
        self.project.install_file("bin", "activate")
        self.project.install_file("bin", "command-stub")
        self.project.install_file("bin", "rsync")
        self.project.install_file("bin", "ssh")

        self.assertEqual(
            "[\n            ('bin', ['activate', 'command-stub', 'rsync', 'ssh'])\n        ]",
            build_data_files_string(self.project))

    def test_should_return_data_files_string_with_files_to_be_installed_in_several_destinations(self):
        self.project.install_file("/usr/bin", "pyb")
        self.project.install_file("/etc", "pyb.cfg")
        self.project.install_file("data", "pyb.dat")
        self.project.install_file("data", "howto.txt")
        self.assertEqual("[\n            ('/usr/bin', ['pyb']),\n"
                         "            ('/etc', ['pyb.cfg']),\n"
                         "            ('data', ['pyb.dat', 'howto.txt'])\n"
                         "        ]",
                         build_data_files_string(self.project))


class BuildPackageDataStringTest(unittest.TestCase):
    def setUp(self):
        self.project = Project('.')

    def test_should_return_empty_package_data_string_when_no_files_to_include_given(self):
        self.assertEqual('{}', build_package_data_string(self.project))

    def test_should_return_package_data_string_when_including_file(self):
        self.project.include_file("spam", "egg")

        self.assertEqual(
            "{\n"
            "            'spam': ['egg']\n"
            "        }", build_package_data_string(self.project))

    def test_should_return_package_data_string_when_including_three_files(self):
        self.project.include_file("spam", "egg")
        self.project.include_file("ham", "eggs")
        self.project.include_file("monty", "python")

        self.assertEqual("{\n"
                         "            'ham': ['eggs'],\n"
                         "            'monty': ['python'],\n"
                         "            'spam': ['egg']\n"
                         "        }", build_package_data_string(self.project))

    def test_should_return_package_data_string_with_keys_in_alphabetical_order(self):
        self.project.include_file("b", "beta")
        self.project.include_file("m", "Mu")
        self.project.include_file("e", "epsilon")
        self.project.include_file("k", "Kappa")
        self.project.include_file("p", "psi")
        self.project.include_file("z", "Zeta")
        self.project.include_file("i", "Iota")
        self.project.include_file("a", "alpha")
        self.project.include_file("d", "delta")
        self.project.include_file("t", "theta")
        self.project.include_file("l", "lambda")
        self.project.include_file("x", "chi")

        self.assertEqual("{\n"
                         "            'a': ['alpha'],\n"
                         "            'b': ['beta'],\n"
                         "            'd': ['delta'],\n"
                         "            'e': ['epsilon'],\n"
                         "            'i': ['Iota'],\n"
                         "            'k': ['Kappa'],\n"
                         "            'l': ['lambda'],\n"
                         "            'm': ['Mu'],\n"
                         "            'p': ['psi'],\n"
                         "            't': ['theta'],\n"
                         "            'x': ['chi'],\n"
                         "            'z': ['Zeta']\n"
                         "        }", build_package_data_string(self.project))


class RenderSetupScriptTest(PyBuilderTestCase):
    def setUp(self):
        self.project = create_project()

    def test_should_remove_hardlink_capabilities_when_workaround_is_enabled(self):
        self.project.set_property(
            "distutils_issue8876_workaround_enabled", True)

        actual_setup_script = render_setup_script(self.project)

        self.assertTrue("import os\ndel os.link\n" in actual_setup_script)

    def test_should_not_remove_hardlink_capabilities_when_workaround_is_disabled(self):
        self.project.set_property(
            "distutils_issue8876_workaround_enabled", False)

        actual_setup_script = render_setup_script(self.project)

        self.assertFalse("import os\ndel os.link\n" in actual_setup_script)

    def test_should_render_build_scripts_properly_when_dir_scripts_is_provided(self):
        self.project.set_property("dir_dist_scripts", 'scripts')
        actual_build_script = build_scripts_string(self.project)
        self.assertEquals(
            "[\n            'scripts/spam',\n"
            "            'scripts/eggs'\n"
            "        ]", actual_build_script)

    def test_should_render_setup_file(self):
        actual_setup_script = render_setup_script(self.project)

        self.assert_line_by_line_equal("""#!/usr/bin/env python

from distutils.core import setup

if __name__ == '__main__':
    setup(
        name = 'Spam and Eggs',
        version = '1.2.3',
        description = '''This is a simple integration-test for distutils plugin.''',
        long_description = '''As you might have guessed we have nothing to say here.''',
        author = "Udo Juettner, Michael Gruber",
        author_email = "udo.juettner@gmail.com, aelgru@gmail.com",
        license = 'WTFPL',
        url = 'http://github.com/pybuilder/pybuilder',
        scripts = [
            'spam',
            'eggs'
        ],
        packages = [
            'spam',
            'eggs'
        ],
        py_modules = [
            'spam',
            'eggs'
        ],
        classifiers = [
            'Development Status :: 5 - Beta',
            'Environment :: Console'
        ],
        entry_points = {},
        data_files = [
            ('dir', ['file1', 'file2'])
        ],
        package_data = {
            'spam': ['eggs']
        },
        install_requires = ['sometool'],
        dependency_links = ['https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz'],
        zip_safe=True
    )
""", actual_setup_script)

    def test_should_render_console_scripts_when_property_is_set(self):
        self.project.set_property("distutils_console_scripts", ["release = zest.releaser.release:main",
                                                                "prerelease = zest.releaser.prerelease:main"])

#        actual_setup_script = render_setup_script(self.project)
        actual_setup_script = build_console_scripts_string(self.project)

        self.assertEquals("{'console_scripts': [\n"
                          "            'release = zest.releaser.release:main',\n"
                          "            'prerelease = zest.releaser.prerelease:main'\n"
                          "        ]}", actual_setup_script)

    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    def test_should_render_runtime_dependencies_when_requirements_file_used(self, mock_open):
        mock_open.return_value = MagicMock(spec=TYPE_FILE)
        handle = mock_open.return_value.__enter__.return_value
        handle.readlines.return_value = ["", "foo", "bar"]
        self.project.depends_on_requirements("requirements.txt")

        actual_setup_script = build_install_dependencies_string(self.project)
        self.assertEquals("[\n"
                          "            'sometool',\n"
                          "            'foo',\n"
                          "            'bar'\n"
                          "        ]", actual_setup_script)


class RenderManifestFileTest(unittest.TestCase):
    def test_should_render_manifest_file(self):
        project = create_project()

        actual_manifest_file = render_manifest_file(project)

        self.assertEqual("""include file1
include file2
include spam/eggs
""", actual_manifest_file)


class ExecuteDistUtilsTest(PyBuilderTestCase):
    def setUp(self):
        self.project = create_project()
        self.project.set_property("dir_reports", "whatever reports")
        self.project.set_property("dir_dist", "whatever dist")

    @patch("os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    @patch("subprocess.Popen")
    def test_should_accept_array_of_simple_commands(self, popen, *args):
        popen().wait.return_value = 0

        commands = ["a", "b", "c"]
        execute_distutils(self.project, MagicMock(Logger), commands)

        self.assertEquals(popen_distutils_args(self, 3, popen),
                          commands)

    @patch("os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    @patch("subprocess.Popen")
    def test_should_accept_array_of_compound_commands(self, popen, *args):
        popen().wait.return_value = 0

        commands = ["a", "b", "c"]
        execute_distutils(self.project, MagicMock(Logger), [commands])

        self.assertEquals(popen_distutils_args(self, 1, popen), commands)


class TasksTest(PyBuilderTestCase):
    def setUp(self):
        self.project = create_project()
        self.project.set_property("dir_reports", "whatever reports")
        self.project.set_property("dir_dist", "whatever dist")
        self.project.set_property("distutils_commands", ["sdist", "bdist_dumb"])

    @patch("os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    @patch("subprocess.Popen")
    def test_upload(self, popen, *args):
        popen().wait.return_value = 0

        upload(self.project, MagicMock(Logger))
        self.assertEquals(popen_distutils_args(self, 1, popen), ["sdist", "bdist_dumb"] + ["upload"])

    @patch("os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    @patch("subprocess.Popen")
    def test_install(self, popen, *args):
        popen().wait.return_value = 0

        install_distribution(self.project, MagicMock(Logger))

    @patch("os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    @patch("subprocess.Popen")
    def test_binary_distribution(self, popen, *args):
        popen().wait.return_value = 0

        build_binary_distribution(self.project, MagicMock(Logger))
        self.assertEquals(popen_distutils_args(self, 2, popen), ["sdist", "bdist_dumb"])


def popen_distutils_args(self, call_count, popen):
    self.assertEquals(len([call_args[0] for call_args in popen.call_args_list if len(call_args[0]) > 0]), call_count)
    return [item for call_args in popen.call_args_list if len(call_args[0]) > 0 for item in call_args[0][0][2:]]


def create_project():
    project = Project("/")
    project.build_depends_on("testingframework")
    project.depends_on("sometool")
    project.depends_on(
        "pyassert", url="https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz")
    project.name = "Spam and Eggs"
    project.version = "1.2.3"
    project.summary = "This is a simple integration-test for distutils plugin."
    project.description = "As you might have guessed we have nothing to say here."
    project.authors = [
        Author("Udo Juettner", "udo.juettner@gmail.com"), Author("Michael Gruber", "aelgru@gmail.com")]
    project.license = "WTFPL"
    project.url = "http://github.com/pybuilder/pybuilder"

    def return_dummy_list():
        return ["spam", "eggs"]

    project.list_scripts = return_dummy_list
    project.list_packages = return_dummy_list
    project.list_modules = return_dummy_list

    project.set_property("distutils_classifiers", [
        "Development Status :: 5 - Beta", "Environment :: Console"])
    project.install_file("dir", "file1")
    project.install_file("dir", "file2")
    project.include_file("spam", "eggs")

    return project
