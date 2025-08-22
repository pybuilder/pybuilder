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

try:
    TYPE_FILE = file
except NameError:
    from io import FileIO

    TYPE_FILE = FileIO

import unittest

from pybuilder.core import Project, Author, Logger
from pybuilder.errors import BuildFailedException
from pybuilder.pip_utils import PIP_MODULE_STANZA
from pybuilder.plugins.python.distutils_plugin import (build_data_files_string,
                                                       build_dependency_links_string,
                                                       build_install_dependencies_string,
                                                       build_package_data_string,
                                                       build_entry_points_string,
                                                       build_namespace_packages_string,
                                                       default,
                                                       render_manifest_file,
                                                       build_scripts_string,
                                                       render_setup_script,
                                                       initialize_distutils_plugin,
                                                       execute_distutils,
                                                       upload,
                                                       install_distribution,
                                                       build_binary_distribution,
                                                       _normalize_setup_post_pre_script,
                                                       build_string_from_array,
                                                       build_setup_keywords,
                                                       )
from pybuilder.utils import np
from test_utils import (PyBuilderTestCase,
                        patch,
                        call,
                        MagicMock,
                        Mock,
                        ANY
                        )


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
            self.assertEqual(
                self.project.get_property("distutils_commands"), ["foo", "bar"])
            self.assertEqual(
                self.project.get_property("distutils_issue8876_workaround_enabled"), True)
            self.assertEqual(
                self.project.get_property("distutils_classifiers"), ["Development Status :: 3 - Beta",
                                                                     "Programming Language :: Rust"])
            self.assertEqual(
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
            "[\n            'eggs',\n            'spam>=0.7'\n        ]",
            build_install_dependencies_string(self.project))

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
        self.assertEqual(
            "[\n            'scripts/spam',\n"
            "            'scripts/eggs'\n"
            "        ]", actual_build_script)

    def test_should_render_setup_file(self):
        actual_setup_script = render_setup_script(self.project)

        self.assert_line_by_line_equal("""#!/usr/bin/env python
#   -*- coding: utf-8 -*-

from setuptools import setup
from setuptools.command.install import install as _install

class install(_install):
    def pre_install_script(self):
        pass

    def post_install_script(self):
        pass

    def run(self):
        self.pre_install_script()

        _install.run(self)

        self.post_install_script()

if __name__ == '__main__':
    setup(
        name = 'Spam and Eggs',
        version = '1.2.3',
        description = 'This is a simple integration-test for distutils plugin.',
        long_description = 'As you might have guessed we have nothing to say here.',
        long_description_content_type = None,
        classifiers = [
            'Development Status :: 5 - Beta',
            'Environment :: Console'
        ],
        keywords = '',

        author = 'Udo Juettner, Michael Gruber',
        author_email = 'udo.juettner@gmail.com, aelgru@gmail.com',
        maintainer = '',
        maintainer_email = '',

        license = 'WTFPL',

        url = 'http://github.com/pybuilder/pybuilder',
        project_urls = {
            'a': 'http://a',
            'b': 'http://b'
        },

        scripts = [
            'spam',
            'eggs'
        ],
        packages = [
            'spam',
            'eggs'
        ],
        namespace_packages = [
            'foo.bar',
            'quick.brown.fox'
        ],
        py_modules = [
            'spam',
            'eggs'
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
        zip_safe = True,
        cmdclass = {'install': install},
        python_requires = '',
        obsoletes = [],
    )
""", actual_setup_script)

    def test_should_render_setup_file_install_script_wrappers(self):
        self.project.pre_install_script("pre_install_test()")
        self.project.post_install_script("post_install_test()")
        actual_setup_script = render_setup_script(self.project)
        self.assert_line_by_line_equal("""#!/usr/bin/env python
#   -*- coding: utf-8 -*-

from setuptools import setup
from setuptools.command.install import install as _install

class install(_install):
    def pre_install_script(self):
        pre_install_test()

    def post_install_script(self):
        post_install_test()

    def run(self):
        self.pre_install_script()

        _install.run(self)

        self.post_install_script()

if __name__ == '__main__':
    setup(
        name = 'Spam and Eggs',
        version = '1.2.3',
        description = 'This is a simple integration-test for distutils plugin.',
        long_description = 'As you might have guessed we have nothing to say here.',
        long_description_content_type = None,
        classifiers = [
            'Development Status :: 5 - Beta',
            'Environment :: Console'
        ],
        keywords = '',

        author = 'Udo Juettner, Michael Gruber',
        author_email = 'udo.juettner@gmail.com, aelgru@gmail.com',
        maintainer = '',
        maintainer_email = '',

        license = 'WTFPL',

        url = 'http://github.com/pybuilder/pybuilder',
        project_urls = {
            'a': 'http://a',
            'b': 'http://b'
        },

        scripts = [
            'spam',
            'eggs'
        ],
        packages = [
            'spam',
            'eggs'
        ],
        namespace_packages = [
            'foo.bar',
            'quick.brown.fox'
        ],
        py_modules = [
            'spam',
            'eggs'
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
        zip_safe = True,
        cmdclass = {'install': install},
        python_requires = '',
        obsoletes = [],
    )
""", actual_setup_script)

    def test_should_render_console_scripts_when_property_is_set(self):
        self.project.set_property("distutils_console_scripts", ["release = zest.releaser.release:main",
                                                                "prerelease = zest.releaser.prerelease:main"])

        actual_setup_script = build_entry_points_string(self.project)
        self.assertEqual("{\n"
                         "            'console_scripts': [\n"
                         "                'release = zest.releaser.release:main',\n"
                         "                'prerelease = zest.releaser.prerelease:main'\n"
                         "            ]\n"
                         "        }", actual_setup_script)

    def test_should_render_console_script_when_property_is_set(self):
        self.project.set_property("distutils_console_scripts", ["release = zest.releaser.release:main"])

        actual_setup_script = build_entry_points_string(self.project)
        self.assertEqual("{\n"
                         "            'console_scripts': ['release = zest.releaser.release:main']\n"
                         "        }", actual_setup_script)

    def test_should_render_entry_points_when_property_is_set(self):
        self.project.set_property("distutils_entry_points", {'foo_entry': ["release = zest.releaser.release:main",
                                                                           "release1 = zest.releaser.release1:main"],
                                                             'bar_entry': ["prerelease = zest.releaser.prerelease:main"]
                                                             })

        actual_setup_script = build_entry_points_string(self.project)
        self.assertEqual("{\n"
                         "            'bar_entry': ['prerelease = zest.releaser.prerelease:main'],\n"
                         "            'foo_entry': [\n"
                         "                'release = zest.releaser.release:main',\n"
                         "                'release1 = zest.releaser.release1:main'\n"
                         "            ]\n"
                         "        }", actual_setup_script)

    def test_should_render_setup_keywords_when_property_is_set(self):
        self.project.set_property("distutils_setup_keywords", "a b c")
        actual_setup_script = build_setup_keywords(self.project)
        self.assertEqual("'a b c'", actual_setup_script)

        self.project.set_property("distutils_setup_keywords", ["a"])
        actual_setup_script = build_setup_keywords(self.project)
        self.assertEqual("'a'", actual_setup_script)

        self.project.set_property("distutils_setup_keywords", ("a b",))
        actual_setup_script = build_setup_keywords(self.project)
        self.assertEqual("'a b'", actual_setup_script)

    def test_should_render_single_entry_pointproperty_is_set(self):
        self.project.set_property("distutils_entry_points", {'foo_entry': "release = zest.releaser.release:main"})

        actual_setup_script = build_entry_points_string(self.project)
        self.assertEqual("{\n"
                         "            'foo_entry': ['release = zest.releaser.release:main']\n"
                         "        }", actual_setup_script)

    def test_should_fail_with_entry_points_and_console_scripts_set(self):
        self.project.set_property("distutils_console_scripts", object())
        self.project.set_property("distutils_entry_points", object())

        self.assertRaises(BuildFailedException, build_entry_points_string, self.project)

    def test_should_render_explicit_namespaces(self):
        actual_setup_script = build_namespace_packages_string(self.project)
        self.assertEqual("""[
            'foo.bar',
            'quick.brown.fox'
        ]""", actual_setup_script)

    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    def test_should_render_runtime_dependencies_when_requirements_file_used(self, mock_open):
        mock_open.return_value = MagicMock(spec=TYPE_FILE)
        handle = mock_open.return_value.__enter__.return_value
        handle.readlines.return_value = ["", "foo", "bar"]
        self.project.depends_on_requirements("requirements.txt")

        actual_setup_script = build_install_dependencies_string(self.project)
        self.assertEqual("[\n"
                         "            'sometool',\n"
                         "            'foo',\n"
                         "            'bar'\n"
                         "        ]", actual_setup_script)

    def test_normalize_setup_post_pre_script(self):
        test_script = '''
a
    b
        c
    d
e
'''
        expected_script = '''
        a
            b
                c
            d
        e
'''
        self.assert_line_by_line_equal(expected_script, _normalize_setup_post_pre_script(test_script))


class UtilityMethodTest(PyBuilderTestCase):
    def test_build_string_from_array_empty(self):
        self.assert_line_by_line_equal('[]', build_string_from_array([]))

    def test_build_string_from_array_simple(self):
        self.assert_line_by_line_equal("['a']", build_string_from_array(['a']))

    def test_build_string_from_array_of_array_of_empty(self):
        self.assert_line_by_line_equal('''[[]]''', build_string_from_array([[]]))

    def test_build_string_from_array_of_array_single_element(self):
        self.assert_line_by_line_equal('''[['a']]''', build_string_from_array([['a']]))

    def test_build_string_from_array_of_array_multiple_elements(self):
        self.assert_line_by_line_equal('''[[
                'a',
                'b'
            ]]''', build_string_from_array([['a', 'b']]))

    def test_build_string_from_array_of_arrays_single_element(self):
        self.assert_line_by_line_equal('''[
            ['a'],
            ['b']
        ]''', build_string_from_array([['a'], ['b']]))

    def test_build_string_from_array_of_arrays_multiple_elements(self):
        self.assert_line_by_line_equal('''[
            [
                'a',
                'b'
            ],
            [
                'c',
                'd'
            ]
        ]''', build_string_from_array([['a', 'b'], ['c', 'd']]))


class RenderManifestFileTest(unittest.TestCase):
    def test_should_render_manifest_file(self):
        project = create_project()

        actual_manifest_file = render_manifest_file(project)

        self.assertEqual("""include file1
include file2
include %s
""" % np("spam/eggs"), actual_manifest_file)


class ExecuteDistUtilsTest(PyBuilderTestCase):
    def setUp(self):
        self.project = create_project()
        self.project.set_property("dir_reports", "whatever reports")
        self.project.set_property("dir_dist", "whatever dist")

        self.pyb_env = Mock()
        self.pyb_env.executable = ["a/b"]
        self.pyb_env.env_dir = "a"
        self.pyb_env.run_process_and_wait.return_value = 0

    @patch("pybuilder.plugins.python.distutils_plugin.os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    def test_should_accept_array_of_simple_commands(self, *_):
        commands = ["a", "b", "c"]

        execute_distutils(self.project, MagicMock(Logger), self.pyb_env, commands)

        self.pyb_env.run_process_and_wait.assert_has_calls(
            [call(self.pyb_env.executable + [ANY, ANY, cmd, self.project.expand_path("$dir_dist")], ANY, ANY) for cmd in
             commands])

    @patch("pybuilder.plugins.python.distutils_plugin.os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    def test_should_accept_array_of_compound_commands(self, *_):
        commands = ["a", "b", "c"]

        execute_distutils(self.project, MagicMock(Logger), self.pyb_env, [commands])

        self.pyb_env.run_process_and_wait.assert_has_calls(
            [call(self.pyb_env.executable + [ANY, ANY] + commands + [self.project.expand_path("$dir_dist")], ANY, ANY)])


class UploadTests(PyBuilderTestCase):
    def setUp(self):
        self.project = create_project()
        self.project.set_property("dir_reports", "whatever reports")
        self.project.set_property("dir_dist", "whatever dist")

        self.reactor = Mock()
        self.pyb_env = Mock()
        self.pyb_env.executable = ["a/b"]
        self.pyb_env.env_dir = "a"
        self.pyb_env.run_process_and_wait.return_value = 0
        self.reactor.python_env_registry = {"pybuilder": self.pyb_env}
        self.reactor.pybuilder_venv = self.pyb_env

    @patch("pybuilder.plugins.python.distutils_plugin.os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    @patch("pybuilder.plugins.python.distutils_plugin.os.walk")
    def test_upload_with_register(self, walk, *_):
        walk.return_value = [["dist", "", ["a", "b"]]]

        self.project.set_property("distutils_upload_register", True)

        upload(self.project, MagicMock(Logger), self.reactor)

        self.pyb_env.run_process_and_wait.assert_has_calls([
            call(self.pyb_env.executable + ["-m", "twine", "register",
                                            self.project.expand_path("$dir_dist", "dist", "a")], ANY, ANY),
            call(self.pyb_env.executable + ["-m", "twine", "register",
                                            self.project.expand_path("$dir_dist", "dist", "b")], ANY, ANY),
            call(self.pyb_env.executable + ["-m", "twine", "upload",
                                            self.project.expand_path("$dir_dist", "dist", "a"),
                                            self.project.expand_path("$dir_dist", "dist", "b")], ANY, ANY)
        ])

    @patch("pybuilder.plugins.python.distutils_plugin.os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    @patch("pybuilder.plugins.python.distutils_plugin.os.walk")
    def test_upload(self, walk, *_):
        walk.return_value = [["dist", "", ["a", "b"]]]

        upload(self.project, MagicMock(Logger), self.reactor)

        self.pyb_env.run_process_and_wait.assert_has_calls(
            [call(self.pyb_env.executable + ["-m", "twine", "upload",
                                             self.project.expand_path("$dir_dist", "dist", "a"),
                                             self.project.expand_path("$dir_dist", "dist", "b")], ANY, ANY)])

    @patch("pybuilder.plugins.python.distutils_plugin.os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    @patch("pybuilder.plugins.python.distutils_plugin.os.walk")
    def test_upload_with_repo(self, walk, *_):
        walk.return_value = [["dist", "", ["a", "b"]]]
        self.project.set_property("distutils_upload_repository", "test repo")

        upload(self.project, MagicMock(Logger), self.reactor)

        self.pyb_env.run_process_and_wait.assert_has_calls([
            call(self.pyb_env.executable + ["-m", "twine", "upload", "--repository-url", "test repo",
                                            self.project.expand_path("$dir_dist", "dist", "a"),
                                            self.project.expand_path("$dir_dist", "dist", "b")], ANY, ANY)])

    @patch("pybuilder.plugins.python.distutils_plugin.os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    @patch("pybuilder.plugins.python.distutils_plugin.os.walk")
    def test_upload_with_repo_and_repo_key(self, walk, *_):
        walk.return_value = [["dist", "", ["a", "b"]]]
        self.project.set_property("distutils_upload_repository", "test repo")
        self.project.set_property("distutils_upload_repository_key", "test repo key")

        upload(self.project, MagicMock(Logger), self.reactor)

        self.pyb_env.run_process_and_wait.assert_has_calls([
            call(self.pyb_env.executable + ["-m", "twine", "upload", "--repository-url", "test repo",
                                            self.project.expand_path("$dir_dist", "dist", "a"),
                                            self.project.expand_path("$dir_dist", "dist", "b")], ANY, ANY)])

    @patch("pybuilder.plugins.python.distutils_plugin.os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    @patch("pybuilder.plugins.python.distutils_plugin.os.walk")
    def test_upload_with_repo_key_only(self, walk, *_):
        walk.return_value = [["dist", "", ["a", "b"]]]
        self.project.set_property("distutils_upload_repository_key", "test repo key")

        upload(self.project, MagicMock(Logger), self.reactor)

        self.pyb_env.run_process_and_wait.assert_has_calls([
            call(self.pyb_env.executable + ["-m", "twine", "upload", "--repository", "test repo key",
                                            self.project.expand_path("$dir_dist", "dist", "a"),
                                            self.project.expand_path("$dir_dist", "dist", "b")], ANY, ANY)])

    @patch("pybuilder.plugins.python.distutils_plugin.os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    @patch("pybuilder.plugins.python.distutils_plugin.os.walk")
    def test_upload_with_signature(self, walk, *_):
        walk.return_value = [["dist", "", ["a", "b"]]]
        self.project.set_property("distutils_upload_sign", True)

        upload(self.project, MagicMock(Logger), self.reactor)

        self.pyb_env.run_process_and_wait.assert_has_calls([
            call(self.pyb_env.executable + ["-m", "twine", "upload", "--sign",
                                            self.project.expand_path("$dir_dist", "dist", "a"),
                                            self.project.expand_path("$dir_dist", "dist", "b")], ANY, ANY)])

    @patch("pybuilder.plugins.python.distutils_plugin.os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    @patch("pybuilder.plugins.python.distutils_plugin.os.walk")
    def test_upload_with_signature_and_identity(self, walk, *_):
        walk.return_value = [["dist", "", ["a", "b"]]]
        self.project.set_property("distutils_upload_sign", True)
        self.project.set_property("distutils_upload_sign_identity", "abcd")

        upload(self.project, MagicMock(Logger), self.reactor)

        self.pyb_env.run_process_and_wait.assert_has_calls([
            call(self.pyb_env.executable + ["-m", "twine", "upload", "--sign", "--identity", "abcd",
                                            self.project.expand_path("$dir_dist", "dist", "a"),
                                            self.project.expand_path("$dir_dist", "dist", "b")], ANY, ANY)])


class TasksTest(PyBuilderTestCase):
    def setUp(self):
        self.project = create_project()
        self.project.set_property("dir_reports", "whatever reports")
        self.project.set_property("dir_dist", "whatever dist")
        self.project.set_property("distutils_commands", ["sdist", "bdist_dumb"])

        self.reactor = Mock()
        self.pyb_env = Mock()
        self.pyb_env.executable = ["a/b"]
        self.pyb_env.env_dir = "a"
        self.pyb_env.run_process_and_wait.return_value = 0
        self.reactor.python_env_registry = {"system": self.pyb_env}
        self.reactor.pybuilder_venv = self.pyb_env

    @patch("pybuilder.plugins.python.distutils_plugin.os.mkdir")
    @patch("pybuilder.pip_utils.open", create=True)
    def test_install(self, *_):
        install_distribution(self.project, MagicMock(Logger), self.reactor)

        self.pyb_env.execute_command.assert_called_with(
            self.pyb_env.executable + PIP_MODULE_STANZA + ["install", "--force-reinstall",
                                                           self.project.expand_path("$dir_dist")],
            cwd=".", env=ANY, outfile_name=ANY, error_file_name=ANY, shell=False, no_path_search=True)

    @patch("pybuilder.plugins.python.distutils_plugin.os.mkdir")
    @patch("pybuilder.pip_utils.open", create=True)
    def test_install_with_index_url(self, *_):
        self.project.set_property("install_dependencies_index_url", "index_url")
        self.project.set_property("install_dependencies_extra_index_url", "extra_index_url")

        install_distribution(self.project, MagicMock(Logger), self.reactor)

        self.pyb_env.execute_command.assert_called_with(
            self.pyb_env.executable + PIP_MODULE_STANZA +
            ["install", "--index-url", "index_url", "--extra-index-url", "extra_index_url", "--force-reinstall",
             self.project.expand_path("$dir_dist")], cwd=".", env=ANY, outfile_name=ANY, error_file_name=ANY,
            shell=False,
            no_path_search=True)

    @patch("pybuilder.plugins.python.distutils_plugin.os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    @patch("pybuilder.plugins.python.distutils_plugin.os.walk")
    def test_binary_distribution(self, walk, *_):
        walk.return_value = [("root", (), ("file1", "file2"))]

        build_binary_distribution(self.project, MagicMock(Logger), self.reactor)

        self.pyb_env.run_process_and_wait.assert_has_calls(
            [call(self.pyb_env.executable + [ANY, ANY, "--sdist", self.project.expand_path("$dir_dist")], ANY, ANY),
             call(self.pyb_env.executable + [ANY, ANY, "--bdist_dumb", self.project.expand_path("$dir_dist")], ANY,
                  ANY),
             call(self.pyb_env.executable + ["-m", "twine", "check",
                                             self.project.expand_path("$dir_dist", "dist", "file1"),
                                             self.project.expand_path("$dir_dist", "dist", "file2")], ANY, ANY)])

    @patch("pybuilder.plugins.python.distutils_plugin.os.mkdir")
    @patch("pybuilder.plugins.python.distutils_plugin.open", create=True)
    @patch("pybuilder.plugins.python.distutils_plugin.os.walk")
    def test_binary_distribution_with_command_options(self, walk, *_):
        self.project.set_property("distutils_command_options", {"sdist": ['--formats', 'bztar']})

        walk.return_value = [("root", (), ("file1", "file2"))]

        build_binary_distribution(self.project, MagicMock(Logger), self.reactor)

        self.pyb_env.run_process_and_wait.assert_has_calls(
            [call(self.pyb_env.executable + [ANY, ANY, "--sdist", "-C--formats", "-Cbztar",
                                             self.project.expand_path("$dir_dist")],
                  ANY, ANY),
             call(self.pyb_env.executable + [ANY, ANY, "--bdist_dumb", self.project.expand_path("$dir_dist")], ANY,
                  ANY),
             call(self.pyb_env.executable + ["-m", "twine", "check",
                                             self.project.expand_path("$dir_dist", "dist", "file1"),
                                             self.project.expand_path("$dir_dist", "dist", "file2")], ANY, ANY)])


def popen_distutils_args(self, call_count, proc_runner):
    self.assertEqual(proc_runner.call_count, call_count)
    return [call_args[0][0][2:] for call_args in proc_runner.call_args_list]


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
    project.urls = {"b": "http://b",
                    "a": "http://a",
                    }
    project.explicit_namespaces = ["foo.bar", "quick.brown.fox"]

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

    project.set_property("distutils_zip_safe", True)
    return project
