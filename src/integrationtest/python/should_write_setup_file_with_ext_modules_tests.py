#  This file is part of PyBuilder
#
#  Copyright 2011 The PyBuilder Team
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

from itest_support import IntegrationTestSupport


class Test(IntegrationTestSupport):
    def test(self):
        self.write_build_file("""
from pybuilder.core import use_plugin, init

use_plugin("python.core")
use_plugin("python.distutils")

name = "integration-test"
default_task = "publish"

@init
def init (project):
    project.depends_on("spam", declaration_only=True)
    project.depends_on("pyassert", url="https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz",
        declaration_only=True)
    project.depends_on("eggs", "==0.2.3", declaration_only=True)
    project.build_depends_on("eggy", declaration_only=True)
    project.set_property("distutils_ext_modules", [{
        "name": "'ext_module'",
        "sources": ["ext_module.c"],
        "depends": ["ext_module.h"],
        "include_dirs": ["ext_module/include"],
        "optional": False,
    }])
""")
        self.create_directory("src/main/python/spam")
        self.write_file("requirements.txt", """
awesome>=1.3.37
foo==42""")
        self.write_file("src/main/python/standalone_module.py")
        self.write_file("src/main/python/spam/__init__.py")
        self.write_file("src/main/python/spam/eggs.py", """
def spam ():
    pass
""")

        self.create_directory("src/main/python/ext_module")
        self.create_directory("src/main/python/ext_module/include")
        self.write_file("src/main/python/ext_module.c", r"""
#include <Python.h>
// Function 1: A simple 'hello world' function
static PyObject* helloworld(PyObject* self, PyObject* args)
{
    printf("Hello World\n");
    return Py_None;
}

// Our Module's Function Definition struct
// We require this `NULL` to signal the end of our method
// definition
static PyMethodDef myMethods[] = {
    { "helloworld", helloworld, METH_NOARGS, "Prints Hello World" },
    { NULL, NULL, 0, NULL }
};

// Our Module Definition struct
static struct PyModuleDef ext_module = {
    PyModuleDef_HEAD_INIT,
    "ext_module",
    "Test Module",
    -1,
    myMethods
};

// Initializes our module using our above struct
PyMODINIT_FUNC PyInit_ext_module(void)
{
    return PyModule_Create(&ext_module);
}
""")
        self.write_file("src/main/python/ext_module.h", """
""")

        reactor = self.prepare_reactor()
        reactor.build()

        self.assert_directory_exists("target/dist/integration-test-1.0.dev0")
        self.assert_directory_exists("target/dist/integration-test-1.0.dev0/spam")
        self.assert_file_exists("target/dist/integration-test-1.0.dev0/standalone_module.py")
        self.assert_file_empty("target/dist/integration-test-1.0.dev0/spam/__init__.py")
        self.assert_file_content("target/dist/integration-test-1.0.dev0/spam/eggs.py", """
def spam ():
    pass
""")

        setup_py = "target/dist/integration-test-1.0.dev0/setup.py"

        self.assert_file_exists(setup_py)
        self.assert_file_permissions(0o755, setup_py)
        self.assert_file_content(setup_py, """#!/usr/bin/env python
#   -*- coding: utf-8 -*-

from setuptools import setup, Extension
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
        packages = ['spam'],
        namespace_packages = [],
        py_modules = ['standalone_module'],
        ext_modules = [Extension(name='ext_module',sources=['ext_module.c'],depends=['ext_module.h'],include_dirs=['ext_module/include'],optional=False)],
        entry_points = {},
        data_files = [],
        package_data = {},
        include_package_data = False,
        install_requires = [
            'eggs==0.2.3',
            'spam'
        ],
        dependency_links = ['https://github.com/downloads/halimath/pyassert/pyassert-0.2.2.tar.gz'],
        zip_safe = True,
        cmdclass = {'install': install},
        python_requires = '',
        obsoletes = [],
        setup_requires = [],
    )
""")  # noqa: E501


if __name__ == "__main__":
    unittest.main()
