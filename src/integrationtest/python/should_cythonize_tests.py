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

import unittest

from itest_support import IntegrationTestSupport


class Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file("""
import os

from pybuilder.core import use_plugin, init

use_plugin("python.core")
use_plugin("python.install_dependencies")
use_plugin("python.distutils")
use_plugin("copy_resources")
use_plugin("filter_resources")

name = "integration-test"
default_task = "publish"

@init
def init (project):
    project.depends_on("pyassert", url="https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz",
        declaration_only = True)

    project.set_property("filter_resources_target", "$dir_dist")
    project.set_property("filter_resources_glob", [
        os.path.join("**", "__init__.py")
    ])
    project.set_property("distutils_cython_ext_modules", [{
            "module_list": ["spam/**/*.py", "eggs/**/*.py"],
            "exclude": ["**/__init__.py"],
            "compiler_directives": {"language_level": "3"}
    }])
    project.set_property("distutils_cython_remove_python_sources", True)
    project.set_property("copy_resources_target", "$dir_dist")
""")
        self.create_directory("src/main/python/spam")
        self.write_file("src/main/python/spam/__init__.py", "")
        self.write_file("src/main/python/spam/eggs.py", """
def spam ():
    pass
""")
        self.create_directory("src/main/python/eggs")
        self.write_file("src/main/python/eggs/__init__.py", "")
        self.write_file("src/main/python/eggs/spam.py", """
def eggs ():
    pass
""")

        reactor = self.prepare_reactor()
        reactor.build()

        self.assert_directory_exists("target/dist/integration-test-1.0.dev0")
        self.assert_directory_exists("target/dist/integration-test-1.0.dev0/spam")
        self.assert_file_empty("target/dist/integration-test-1.0.dev0/spam/__init__.py")
        self.assert_file_exists("target/dist/integration-test-1.0.dev0/spam/eggs.c")

        setup_py = "target/dist/integration-test-1.0.dev0/setup.py"

        self.assert_file_exists(setup_py)
        self.assert_file_permissions(0o755, setup_py)

        self.assert_file_content(setup_py, """#!/usr/bin/env python
#   -*- coding: utf-8 -*-

from setuptools import setup, Extension
from setuptools.command.install import install as _install

from setuptools.command.build_py import build_py as _build_py
import glob

class LazyCythonize(list):
    def __init__(self, ext_modules, cythonize_modules_kwargs):
        self.ext_modules = ext_modules if ext_modules is not None else []
        self.cythonize_modules_kwargs = cythonize_modules_kwargs if cythonize_modules_kwargs is not None else []
        self.cythonized_modules = []

    def _cythonize(self):
        if self.cythonized_modules:
            return

        from Cython.Build import cythonize

        for kwargs in self.cythonize_modules_kwargs:
            self.cythonized_modules.extend(cythonize(**kwargs))
        self.cythonized_modules.extend(self.ext_modules)

    def __iter__(self):
        self._cythonize()
        return iter(self.cythonized_modules)

    def __getitem__(self, key):
        self._cythonize()
        if 0<=key<len(self.cythonized_modules):
            return self.cythonized_modules[key]
        else:
            raise IndexError("Index out of range")

    def __len__(self):
        self._cythonize()
        return len(self.cythonized_modules)


class install(_install):
    def pre_install_script(self):
        pass

    def post_install_script(self):
        pass

    def run(self):
        self.pre_install_script()

        _install.run(self)

        self.post_install_script()


cython_module_list = ['spam/**/*.py', 'eggs/**/*.py']
cython_excludes = ['**/__init__.py']
def not_cythonized(tup):
    (package, module, filepath) = tup
    return any(
        [filepath in glob.iglob(pattern, recursive=True) for pattern in cython_excludes]
    ) or not any(
        [filepath in glob.iglob(pattern, recursive=True) for pattern in cython_module_list]
    )

class build_py(_build_py):
    def find_modules(self):
        modules = super().find_modules()
        return list(filter(not_cythonized, modules))

    def find_package_modules(self, package, package_dir):
        modules = super().find_package_modules(package, package_dir)
        return list(filter(not_cythonized, modules))


if __name__ == '__main__':
    setup(
        name = 'integration-test',
        version = '1.0.dev0',
        description = '',
        long_description = 'integration-test',
        long_description_content_type = None,
        classifiers = [
            'Development Status :: 3 - Alpha',
            'Programming Language :: Python'
        ],
        keywords = '',

        author = '',
        author_email = '',
        maintainer = '',
        maintainer_email = '',

        license = '',

        url = '',
        project_urls = {},

        scripts = [],
        packages = [
            'eggs',
            'spam'
        ],
        namespace_packages = [],
        py_modules = [],
        ext_modules = LazyCythonize([],[{"module_list":['spam/**/*.py', 'eggs/**/*.py'],"exclude":['**/__init__.py'],"compiler_directives":{'language_level': '3'}}]),
        entry_points = {},
        data_files = [],
        package_data = {},
        include_package_data = False,
        install_requires = [],
        dependency_links = ['https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz'],
        zip_safe = True,
        cmdclass = {'install': install,'build_py': build_py},
        python_requires = '',
        obsoletes = [],
        setup_requires = ['cython'],
    )
""")  # noqa: E501


if __name__ == "__main__":
    unittest.main()
