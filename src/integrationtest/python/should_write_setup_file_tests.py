import unittest

from integrationtest_support import IntegrationTestSupport

class Test (IntegrationTestSupport):
    def test (self):
        self.write_build_file("""
from pythonbuilder.core import use_plugin

use_plugin("python.core")
use_plugin("python.distutils")

name = "integration-test"
default_task = "publish"
""")
        self.create_directory("src/main/python/spam")
        self.write_file("src/main/python/spam/__init__.py", "")
        self.write_file("src/main/python/spam/eggs.py", """
def spam ():
    pass
""")
        
        reactor = self.prepare_reactor()
        reactor.build()
        
        self.assert_directory_exists("target/dist/integration-test-1.0-SNAPSHOT")
        self.assert_directory_exists("target/dist/integration-test-1.0-SNAPSHOT/spam")
        self.assert_file_empty("target/dist/integration-test-1.0-SNAPSHOT/spam/__init__.py")
        self.assert_file_content("target/dist/integration-test-1.0-SNAPSHOT/spam/eggs.py", """
def spam ():
    pass
""")
        self.assert_file_exists("target/dist/integration-test-1.0-SNAPSHOT/spam/eggs.pyc")
        self.assert_file_exists("target/dist/integration-test-1.0-SNAPSHOT/spam/__init__.pyc")
        
        setup_py = 'target/dist/integration-test-1.0-SNAPSHOT/setup.py'
        
        self.assert_file_exists(setup_py)
        self.assert_file_permissions(0755, setup_py)
        self.assert_file_content(setup_py, """#!/usr/bin/env python

from setuptools import setup

if __name__ == '__main__':
    setup(
          name = 'integration-test',
          version = '1.0-SNAPSHOT',
          description = '',
          long_description = '''''',
          author = "",
          author_email = "",
          license = '',
          url = '',
          scripts = [],
          packages = ['spam'],
          classifiers = ['Development Status :: 3 - Alpha', 'Programming Language :: Python'],
          
          
          
          zip_safe=True
    )
""")
        
        
if __name__ == '__main__':
    unittest.main()
