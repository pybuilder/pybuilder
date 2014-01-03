#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
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
import imp
import os
import unittest

from mockito import when, verify, unstub, any, times, contains
from mockito.matchers import Matcher
from test_utils import mock

from pybuilder.core import (ACTION_ATTRIBUTE,
                            AFTER_ATTRIBUTE,
                            BEFORE_ATTRIBUTE,
                            ENVIRONMENTS_ATTRIBUTE,
                            INITIALIZER_ATTRIBUTE,
                            NAME_ATTRIBUTE,
                            ONLY_ONCE_ATTRIBUTE,
                            TASK_ATTRIBUTE,
                            Project)
from pybuilder.errors import MissingPluginException, PyBuilderException, ProjectValidationFailedException
from pybuilder.reactor import Reactor
from pybuilder.execution import Task, Action, Initializer, ExecutionManager
from pybuilder.pluginloader import PluginLoader


class TaskNameMatcher (Matcher):

    def __init__(self, task_name):
        self.task_name = task_name

    def matches(self, arg):
        if not isinstance(arg, Task):
            return False
        return arg.name == self.task_name

    def repr(self):
        return "Task with name %s" % self.task_name


class ReactorTest (unittest.TestCase):

    def setUp(self):
        self.plugin_loader_mock = mock(PluginLoader)
        self.logger = mock()
        self.execution_manager = mock(ExecutionManager)
        self.reactor = Reactor(
            self.logger, self.execution_manager, self.plugin_loader_mock)

    def tearDown(self):
        unstub()

    def test_should_return_tasks_from_execution_manager_when_calling_get_tasks(self):
        self.execution_manager.tasks = ["spam"]
        self.assertEquals(["spam"], self.reactor.get_tasks())

    def test_should_raise_exception_when_importing_plugin_and_plugin_not_found(self):
        when(self.plugin_loader_mock).load_plugin(
            any(), "not_found").thenRaise(MissingPluginException("not_found"))

        self.assertRaises(
            MissingPluginException, self.reactor.import_plugin, "not_found")

        verify(self.plugin_loader_mock).load_plugin(any(), "not_found")

    def test_should_collect_single_task(self):
        def task():
            pass
        setattr(task, TASK_ATTRIBUTE, True)

        module = mock()
        module.task = task

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        verify(self.execution_manager).register_task(TaskNameMatcher("task"))

    def test_should_collect_single_task_with_overridden_name(self):
        def task():
            pass
        setattr(task, TASK_ATTRIBUTE, True)
        setattr(task, NAME_ATTRIBUTE, "overridden_name")

        module = mock()
        module.task = task

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        verify(self.execution_manager).register_task(
            TaskNameMatcher("overridden_name"))

    def test_should_collect_multiple_tasks(self):
        def task():
            pass
        setattr(task, TASK_ATTRIBUTE, True)

        def task2():
            pass
        setattr(task2, TASK_ATTRIBUTE, True)

        module = mock()
        module.task = task
        module.task2 = task2

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        verify(self.execution_manager, times(2)).register_task(any(Task))

    def test_should_collect_single_before_action(self):
        def action():
            pass
        setattr(action, ACTION_ATTRIBUTE, True)
        setattr(action, BEFORE_ATTRIBUTE, "spam")

        module = mock()
        module.task = action

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        verify(self.execution_manager).register_action(any(Action))

    def test_should_collect_single_after_action(self):
        def action():
            pass
        setattr(action, ACTION_ATTRIBUTE, True)
        setattr(action, AFTER_ATTRIBUTE, "spam")

        module = mock()
        module.task = action

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        verify(self.execution_manager).register_action(any(Action))

    def test_should_collect_single_after_action_with_only_once_flag(self):
        def action():
            pass
        setattr(action, ACTION_ATTRIBUTE, True)
        setattr(action, AFTER_ATTRIBUTE, "spam")
        setattr(action, ONLY_ONCE_ATTRIBUTE, True)

        module = mock()
        module.task = action

        def register_action(action):
            if not action.only_once:
                raise AssertionError("Action is not marked as only_once")

        self.execution_manager.register_action = register_action

        self.reactor.collect_tasks_and_actions_and_initializers(module)

    def test_should_collect_single_initializer(self):
        def init():
            pass
        setattr(init, INITIALIZER_ATTRIBUTE, True)

        module = mock()
        module.task = init

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        verify(self.execution_manager).register_initializer(any(Initializer))

    def test_should_collect_single_initializer_with_environments(self):
        def init():
            pass
        setattr(init, INITIALIZER_ATTRIBUTE, True)
        setattr(init, ENVIRONMENTS_ATTRIBUTE, ["any_environment"])

        module = mock()
        module.task = init

        class ExecutionManagerMock (object):

            def register_initializer(self, initializer):
                self.initializer = initializer

        execution_manager_mock = ExecutionManagerMock()
        self.reactor.execution_manager = execution_manager_mock

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        self.assertEquals(
            execution_manager_mock.initializer.environments, ["any_environment"])

    def test_should_raise_exception_when_verifying_project_directory_and_directory_does_not_exist(self):
        when(os.path).abspath("spam").thenReturn("spam")
        when(os.path).exists("spam").thenReturn(False)

        self.assertRaises(
            PyBuilderException, self.reactor.verify_project_directory, "spam", "eggs")

        verify(os.path).abspath("spam")
        verify(os.path).exists("spam")

    def test_should_raise_exception_when_verifying_project_directory_and_directory_is_not_a_directory(self):
        when(os.path).abspath("spam").thenReturn("spam")
        when(os.path).exists("spam").thenReturn(True)
        when(os.path).isdir("spam").thenReturn(False)

        self.assertRaises(
            PyBuilderException, self.reactor.verify_project_directory, "spam", "eggs")

        verify(os.path).abspath("spam")
        verify(os.path).exists("spam")
        verify(os.path).isdir("spam")

    def test_should_raise_exception_when_verifying_project_directory_and_build_descriptor_does_not_exist(self):
        when(os.path).abspath("spam").thenReturn("spam")
        when(os.path).exists("spam").thenReturn(True)
        when(os.path).isdir("spam").thenReturn(True)
        when(os.path).join("spam", "eggs").thenReturn("spam/eggs")
        when(os.path).exists("spam/eggs").thenReturn(False)

        self.assertRaises(
            PyBuilderException, self.reactor.verify_project_directory, "spam", "eggs")

        verify(os.path).abspath("spam")
        verify(os.path).exists("spam")
        verify(os.path).isdir("spam")
        verify(os.path).join("spam", "eggs")
        verify(os.path).exists("spam/eggs")

    def test_should_raise_exception_when_verifying_project_directory_and_build_descriptor_is_not_a_file(self):
        when(os.path).abspath("spam").thenReturn("spam")
        when(os.path).exists("spam").thenReturn(True)
        when(os.path).isdir("spam").thenReturn(True)
        when(os.path).join("spam", "eggs").thenReturn("spam/eggs")
        when(os.path).exists("spam/eggs").thenReturn(True)
        when(os.path).isfile("spam/eggs").thenReturn(False)

        self.assertRaises(
            PyBuilderException, self.reactor.verify_project_directory, "spam", "eggs")

        verify(os.path).abspath("spam")
        verify(os.path).exists("spam")
        verify(os.path).isdir("spam")
        verify(os.path).join("spam", "eggs")
        verify(os.path).exists("spam/eggs")
        verify(os.path).isfile("spam/eggs")

    def test_should_return_directory_and_full_path_of_descriptor_when_verifying_project_directory(self):
        when(os.path).abspath("spam").thenReturn("/spam")
        when(os.path).exists("/spam").thenReturn(True)
        when(os.path).isdir("/spam").thenReturn(True)
        when(os.path).join("/spam", "eggs").thenReturn("/spam/eggs")
        when(os.path).exists("/spam/eggs").thenReturn(True)
        when(os.path).isfile("/spam/eggs").thenReturn(True)

        self.assertEquals(
            ("/spam", "/spam/eggs"), self.reactor.verify_project_directory("spam", "eggs"))

        verify(os.path).abspath("spam")
        verify(os.path).exists("/spam")
        verify(os.path).isdir("/spam")
        verify(os.path).join("/spam", "eggs")
        verify(os.path).exists("/spam/eggs")
        verify(os.path).isfile("/spam/eggs")

    def test_should_raise_exception_when_loading_project_module_and_import_raises_exception(self):
        when(imp).load_source("build", "spam").thenRaise(ImportError("spam"))

        self.assertRaises(
            PyBuilderException, self.reactor.load_project_module, "spam")

        verify(imp).load_source("build", "spam")

    def test_should_return_module_when_loading_project_module_and_import_raises_exception(self):
        module = mock()
        when(imp).load_source("build", "spam").thenReturn(module)

        self.assertEquals(module, self.reactor.load_project_module("spam"))

        verify(imp).load_source("build", "spam")

    def test_ensure_project_attributes_are_set_when_instantiating_project(self):
        module = mock(version="version",
                      default_task="default_task",
                      summary="summary",
                      home_page="home_page",
                      description="description",
                      authors="authors",
                      license="license",
                      url="url")

        self.reactor.project = mock()
        self.reactor.project_module = module

        self.reactor.apply_project_attributes()

        self.assertEquals("version", self.reactor.project.version)
        self.assertEquals("default_task", self.reactor.project.default_task)
        self.assertEquals("summary", self.reactor.project.summary)
        self.assertEquals("home_page", self.reactor.project.home_page)
        self.assertEquals("description", self.reactor.project.description)
        self.assertEquals("authors", self.reactor.project.authors)
        self.assertEquals("license", self.reactor.project.license)
        self.assertEquals("url", self.reactor.project.url)

    def test_ensure_project_name_is_set_from_attribute_when_instantiating_project(self):
        module = mock(name="name")

        self.reactor.project = mock()
        self.reactor.project_module = module
        self.reactor.apply_project_attributes()

        self.assertEquals("name", self.reactor.project.name)

    def test_should_import_plugin_only_once(self):
        plugin_module = mock()
        when(self.plugin_loader_mock).load_plugin(
            any(), "spam").thenReturn(plugin_module)

        self.reactor.require_plugin("spam")
        self.reactor.require_plugin("spam")

        self.assertEquals(["spam"], self.reactor.get_plugins())

        verify(self.plugin_loader_mock).load_plugin(any(), "spam")

    def test_ensure_project_properties_are_logged_when_calling_log_project_properties(self):
        project = Project("spam")
        project.set_property("spam", "spam")
        project.set_property("eggs", "eggs")

        self.reactor.project = project
        self.reactor.log_project_properties()

        verify(self.logger).debug(
            "Project properties: %s", contains("basedir : spam"))
        verify(self.logger).debug(
            "Project properties: %s", contains("eggs : eggs"))
        verify(self.logger).debug(
            "Project properties: %s", contains("spam : spam"))

    def test_should_raise_exception_when_project_is_not_valid(self):
        self.reactor.project = mock(properties={})
        when(self.reactor.project).validate().thenReturn(["spam"])

        self.assertRaises(ProjectValidationFailedException, self.reactor.build)
