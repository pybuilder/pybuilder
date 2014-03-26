import unittest

from pybuilder.pluginhelper.external_command import ExternalCommandBuilder
from pybuilder.core import Project


class ExternalCommandBuilderTests(unittest.TestCase):

    def setUp(self):
        self.project = Project('/base/dir')
        self.command = ExternalCommandBuilder('command-name', self.project)

    def test_should_only_use_command_name_by_default(self):
        self.assertEqual(self.command.as_string, 'command-name')

    def test_should_add_unconditional_argument_to_command(self):
        self.command.has_argument('--foo=bar')

        self.assertEqual(self.command.as_string, 'command-name --foo=bar')

    def test_should_add_conditional_argument_when_property_is_truthy(self):
        self.project.set_property('verbose', True)
        self.command.has_argument('--verbose').only_if_property_is_truthy('verbose')

        self.assertEqual(self.command.as_string, 'command-name --verbose')

    def test_should_not_add_conditional_argument_when_property_is_falsy(self):
        self.project.set_property('verbose', False)
        self.command.has_argument('--verbose').only_if_property_is_truthy('verbose')

        self.assertEqual(self.command.as_string, 'command-name')

    def test_should_add_conditional_argument_when_property_is_truthy_after_unconditional_argument(self):
        self.project.set_property('verbose', True)
        self.command.has_argument('--cool').has_argument('--verbose').only_if_property_is_truthy('verbose')

        self.assertEqual(self.command.as_string, 'command-name --cool --verbose')

    def test_should_not_add_conditional_argument_when_property_is_falsy_after_unconditional_argument(self):
        self.project.set_property('verbose', False)
        self.command.has_argument('--cool').has_argument('--verbose').only_if_property_is_truthy('verbose')

        self.assertEqual(self.command.as_string, 'command-name --cool')

    def test_should_format_unconditional_argument_with_property_when_given(self):
        self.project.set_property('name', 'value')
        self.command.has_argument('--name={0}').formatted_with_property('name')

        self.assertEqual(self.command.as_string, 'command-name --name=value')

    def test_should_include_conditional_argument_with_formatting_when_property_is_falsy(self):
        self.project.set_property('name', 'value')
        self.command.has_argument('--name={0}').formatted_with_property('name').only_if_property_is_truthy('name')

        self.assertEqual(self.command.as_string, 'command-name --name=value')

    def test_should_omit_conditional_argument_with_formatting_when_property_is_falsy(self):
        self.project.set_property('name', 'value')
        self.project.set_property('falsy', None)
        self.command.has_argument('--name={0}').formatted_with_property('name').only_if_property_is_truthy('falsy')

        self.assertEqual(self.command.as_string, 'command-name')

    def test_should_include_conditional_argument_with_truthy_formatting(self):
        self.project.set_property('name', 'value')
        self.command.has_argument('--name={0}').formatted_with_truthy_property('name')

        self.assertEqual(self.command.as_string, 'command-name --name=value')

    def test_should_omit_conditional_argument_with_falsy_formatting(self):
        self.project.set_property('name', None)
        self.command.has_argument('--name={0}').formatted_with_truthy_property('name')

        self.assertEqual(self.command.as_string, 'command-name')
