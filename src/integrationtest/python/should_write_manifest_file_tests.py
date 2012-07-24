import unittest

from integrationtest_support import IntegrationTestSupport

class Test (IntegrationTestSupport):
    def test (self):
        self.write_build_file("""
from pythonbuilder.core import use_plugin, init

use_plugin('python.core')
use_plugin('python.distutils')

name = 'integration-test'
default_task = 'publish'

@init
def init (project):
    project.include_file('spam', 'eggs')
    project.install_file('spam_dir', 'more_spam')
    project.install_file('eggs_dir', 'more_eggs')
""")
        self.create_directory('src/main/python/spam')
        self.write_file('src/main/python/spam/eggs', '')
        self.write_file('src/main/python/more_spam', '')
        self.write_file('src/main/python/more_eggs', '')
        
        reactor = self.prepare_reactor()
        reactor.build()
        
        self.assert_directory_exists('target/dist/integration-test-1.0-SNAPSHOT')
        self.assert_directory_exists('target/dist/integration-test-1.0-SNAPSHOT/spam')
        self.assert_file_empty('target/dist/integration-test-1.0-SNAPSHOT/spam/eggs')
        self.assert_file_empty('target/dist/integration-test-1.0-SNAPSHOT/more_spam')
        self.assert_file_empty('target/dist/integration-test-1.0-SNAPSHOT/more_eggs')
        
        manifest_in = 'target/dist/integration-test-1.0-SNAPSHOT/MANIFEST.in'
        
        self.assert_file_exists(manifest_in)
        self.assert_file_permissions(0664, manifest_in)
        self.assert_file_content(manifest_in, """include spam/eggs
include more_spam
include more_eggs
""")


if __name__ == '__main__':
    unittest.main()