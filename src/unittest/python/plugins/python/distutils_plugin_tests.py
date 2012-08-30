#  This file is part of Python Builder
#   
#  Copyright 2011 The Python Builder Team
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
import unittest

from pythonbuilder.core import Project, Author
from pythonbuilder.plugins.python.distutils_plugin import (build_data_files_string, 
                                                           build_dependency_links_string,
                                                           build_install_dependencies_string,
                                                           build_package_data_string, 
                                                           default, 
                                                           render_manifest_file,
                                                           render_setup_script)


class InstallDependenciesTest (unittest.TestCase):
    def setUp(self):
        self.project = Project(".")
        
    def test_should_return_empty_string_when_no_dependency_is_given (self):
        self.assertEqual("", build_install_dependencies_string(self.project))
        
    def test_should_return_single_dependency_string (self):
        self.project.depends_on("spam")
        self.assertEqual('install_requires = [ "spam" ],', build_install_dependencies_string(self.project))

    def test_should_return_single_dependency_string_with_version (self):
        self.project.depends_on("spam", "0.7")
        self.assertEqual('install_requires = [ "spam>=0.7" ],', build_install_dependencies_string(self.project))

    def test_should_return_multiple_dependencies_string_with_versions (self):
        self.project.depends_on("spam", "0.7")
        self.project.depends_on("eggs")
        self.assertEqual('install_requires = [ "eggs", "spam>=0.7" ],', build_install_dependencies_string(self.project))
    
    def test_should_not_insert_url_dependency_into_install_requires (self):
        self.project.depends_on("spam")
        self.project.depends_on("pyassert", url="https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz")
        
        self.assertEqual('install_requires = [ "spam" ],', build_install_dependencies_string(self.project))

class DependencyLinksTest (unittest.TestCase):
    def setUp(self):
        self.project = Project(".")
        
    def test_should_return_empty_string_when_no_link_dependency_is_given (self):
        self.assertEqual("", build_dependency_links_string(self.project))
    
    def test_should_return_dependency_link (self):
        self.project.depends_on("pyassert", url="https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz")
        self.assertEqual('dependency_links = [ "https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz" ],', \
                         build_dependency_links_string(self.project))
    
    def test_should_return_dependency_links (self):
        self.project.depends_on("pyassert1", url="https://github.com/downloads/halimath/pyassert/pyassert1-0.2.2.tar.gz")
        self.project.depends_on("pyassert2", url="https://github.com/downloads/halimath/pyassert/pyassert2-0.2.2.tar.gz")
        self.assertEqual('dependency_links = [ "https://github.com/downloads/halimath/pyassert/pyassert1-0.2.2.tar.gz", "https://github.com/downloads/halimath/pyassert/pyassert2-0.2.2.tar.gz" ],', \
                         build_dependency_links_string(self.project))
    
class DefaultTest (unittest.TestCase):
    def test_should_return_empty_string_as_default_when_given_value_is_none (self):
        self.assertEqual("", default(None))
        
    def test_should_return_given_default_when_given_value_is_none (self):
        self.assertEqual("default", default(None, default="default"))
        
    def test_should_return_value_string_when_value_given (self):
        self.assertEqual("value", default("value"))
        
    def test_should_return_value_string_when_value_and_default_given (self):
        self.assertEqual("value", default("value", default="default"))


class BuildDataFilesStringTest (unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.project = Project(".")
        
    def test_should_return_empty_data_files_string (self):
        self.assertEqual("", build_data_files_string(self.project))
    
    def test_should_return_data_files_string_including_several_files (self):
        self.project.install_file("bin", "activate")
        self.project.install_file("bin", "command-stub")
        self.project.install_file("bin", "rsync")
        self.project.install_file("bin", "ssh")
        
        self.assertEqual("data_files = [('bin', ['activate', 'command-stub', 'rsync', 'ssh'])],", \
                         build_data_files_string(self.project))

    def test_should_return_data_files_string_with_files_to_be_installed_in_several_destinations (self):
        self.project.install_file("/usr/bin", "pyb")
        self.project.install_file("/etc", "pyb.cfg")
        self.project.install_file("data", "pyb.dat")
        self.project.install_file("data", "howto.txt")
        self.assertEqual("data_files = [('/usr/bin', ['pyb']), ('/etc', ['pyb.cfg'])," \
                         " ('data', ['pyb.dat', 'howto.txt'])],", \
                         build_data_files_string(self.project))

class BuildPackageDataStringTest (unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.project = Project('.')
        
    def test_should_return_empty_package_data_string_when_no_files_to_include_given (self):
        self.assertEqual('', build_package_data_string(self.project))
        
    def test_should_return_package_data_string_when_including_file (self):
        self.project.include_file("spam", "egg")
        
        self.assertEqual("package_data = {'spam': ['egg']},", build_package_data_string(self.project))
        
    def test_should_return_package_data_string_when_including_three_files (self):
        self.project.include_file("spam", "egg")
        self.project.include_file("ham", "eggs")
        self.project.include_file("monty", "python")
        
        self.assertEqual("package_data = {'ham': ['eggs'], 'monty': ['python'], " \
                         "'spam': ['egg']},", build_package_data_string(self.project))
    
    def test_should_return_package_data_string_with_keys_in_alphabetical_order (self):
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
        
        self.assertEqual("package_data = {'a': ['alpha'], 'b': ['beta'], 'd': ['delta'], " \
                         "'e': ['epsilon'], 'i': ['Iota'], 'k': ['Kappa'], 'l': ['lambda'], " \
                         "'m': ['Mu'], 'p': ['psi'], 't': ['theta'], 'x': ['chi'], " \
                         "'z': ['Zeta']},", build_package_data_string(self.project))

class RenderSetupScriptTest (unittest.TestCase):
    def test_should_render_setup_file (self):
        project = create_project()

        actual_setup_script = render_setup_script(project)

        self.assertEqual("""#!/usr/bin/env python

from distutils.core import setup

if __name__ == '__main__':
    setup(
          name = 'Spam and Eggs',
          version = '1.2.3',
          description = 'This is a simple integration-test for distutils plugin.',
          long_description = '''As you might have guessed we have nothing to say here.''',
          author = "Udo Juettner, Michael Gruber",
          author_email = "udo.juettner@gmail.com, aelgru@gmail.com",
          license = 'WTFPL',
          url = 'http://github.com/pybuilder/pybuilder',
          scripts = ['spam', 'eggs'],
          packages = ['spam', 'eggs'],
          classifiers = ['Development Status :: 5 - Beta', 'Environment :: Console'],
          data_files = [('dir', ['file1', 'file2'])],
          package_data = {'spam': ['eggs']},
          install_requires = [ "sometool" ],
          dependency_links = [ "https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz" ],
          zip_safe=True
    )
""", actual_setup_script)

class RenderManifestFileTest (unittest.TestCase):
    def test_should_render_manifest_file (self):
        project = create_project()

        actual_manifest_file = render_manifest_file(project)

        self.assertEqual("""include file1
include file2
include spam/eggs
""", actual_manifest_file)
        
def create_project():
    project = Project("/")
    project.build_depends_on("testingframework")
    project.depends_on("sometool")
    project.depends_on("pyassert", url="https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz")
    project.name = "Spam and Eggs"
    project.version = "1.2.3"
    project.summary = "This is a simple integration-test for distutils plugin."
    project.description = "As you might have guessed we have nothing to say here."
    project.authors = [Author("Udo Juettner", "udo.juettner@gmail.com"), Author("Michael Gruber", "aelgru@gmail.com")]
    project.license = "WTFPL"
    project.url = "http://github.com/pybuilder/pybuilder"
    
    def return_dummy_list ():
        return ["spam", "eggs"]
    
    project.list_scripts = return_dummy_list
    project.list_packages = return_dummy_list
    
    project.set_property("distutils_classifiers", ["Development Status :: 5 - Beta", "Environment :: Console"])
    project.install_file("dir", "file1")
    project.install_file("dir", "file2")
    project.include_file("spam", "eggs")
    
    return project

