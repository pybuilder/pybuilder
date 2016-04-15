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

import unittest
from types import ModuleType

from pybuilder.core import (ENVIRONMENTS_ATTRIBUTE,
                            INITIALIZER_ATTRIBUTE,
                            NAME_ATTRIBUTE,
                            TASK_ATTRIBUTE,
                            Project,
                            task,
                            depends,
                            dependents,
                            optional,
                            after,
                            before)
from pybuilder.errors import MissingPluginException, PyBuilderException, ProjectValidationFailedException
from pybuilder.execution import Task, TaskDependency, Action, ExecutionManager, Initializer
from pybuilder.pluginloader import PluginLoader
from pybuilder.reactor import Reactor
from test_utils import Mock, ANY, call, patch


class ReactorTest(unittest.TestCase):
    def setUp(self):
        self.old_reactor = Reactor.current_instance()
        self.plugin_loader_mock = Mock(PluginLoader)
        self.logger = Mock()
        self.execution_manager = Mock(ExecutionManager)
        self.reactor = Reactor(
            self.logger, self.execution_manager, self.plugin_loader_mock)

    def tearDown(self):
        Reactor._set_current_instance(self.old_reactor)

    def test_should_return_tasks_from_execution_manager_when_calling_get_tasks(self):
        self.execution_manager.tasks = ["spam"]
        self.assertEquals(["spam"], self.reactor.get_tasks())

    def test_should_raise_exception_when_importing_plugin_and_plugin_not_found(self):
        self.plugin_loader_mock.load_plugin.side_effect = MissingPluginException("not_found")

        self.assertRaises(
            MissingPluginException, self.reactor.import_plugin, "not_found")

        self.plugin_loader_mock.load_plugin.assert_called_with(ANY, "not_found", None, None)

    def test_should_collect_single_task(self):
        def task():
            pass

        setattr(task, TASK_ATTRIBUTE, True)

        module = ModuleType("mock_module")
        module.task = task

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        self.assertEquals(len(self.execution_manager.register_task.call_args_list), 1)
        self.assertTrue(isinstance(self.execution_manager.register_task.call_args[0][0], Task) and len(
            self.execution_manager.register_task.call_args[0]) == 1)
        self.assertEquals(self.execution_manager.register_task.call_args[0][0].name, "task")

    def test_should_collect_single_task_with_overridden_name(self):
        def task():
            pass

        setattr(task, TASK_ATTRIBUTE, True)
        setattr(task, NAME_ATTRIBUTE, "overridden_name")

        module = ModuleType("mock_module")
        module.task = task

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        self.assertEquals(len(self.execution_manager.register_task.call_args_list), 1)
        self.assertTrue(isinstance(self.execution_manager.register_task.call_args[0][0], Task) and len(
            self.execution_manager.register_task.call_args[0]) == 1)
        self.assertEquals(self.execution_manager.register_task.call_args[0][0].name, "overridden_name")

    def test_should_collect_multiple_tasks(self):
        def task():
            pass

        setattr(task, TASK_ATTRIBUTE, True)

        def task2():
            pass

        setattr(task2, TASK_ATTRIBUTE, True)

        module = ModuleType("mock_module")
        module.task = task
        module.task2 = task2

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        self.assertEquals(len(self.execution_manager.register_task.call_args_list), 2)
        for call_args in self.execution_manager.register_task.call_args_list:
            self.assertTrue(isinstance(call_args[0][0], Task) and len(call_args[0]) == 1)

    def test_task_dependencies(self):
        import pybuilder.reactor

        with patch("pybuilder.reactor.Task"):
            @task
            def task1():
                pass

            @task
            @depends(task1)
            def task2():
                pass

            @task
            def task3():
                pass

            @task
            @depends(optional(task3))
            @dependents("task6")
            def task4():
                pass

            @task
            @dependents("task6", optional(task3))
            def task5():
                pass

            @task
            @depends(task1, optional(task2))
            def task6():
                pass

            module = ModuleType("mock_module")
            module.task1 = task1
            module.task2 = task2
            module.task3 = task3
            module.task4 = task4
            module.task5 = task5
            module.task6 = task6

            self.reactor.collect_tasks_and_actions_and_initializers(module)

            pybuilder.reactor.Task.assert_has_calls([call("task1", task1, [], ''),
                                                     call("task2", task2, [TaskDependency(task1)], ''),
                                                     call("task3", task3, [TaskDependency(task5, True)], ''),
                                                     call("task4", task4, [TaskDependency(task3, True)], ''),
                                                     call("task5", task5, [], ''),
                                                     call("task6", task6,
                                                          [TaskDependency(task1), TaskDependency(task2, True),
                                                           TaskDependency(task4), TaskDependency(task5)], '')])

    def test_task_dependencies_with_post_definition_injections(self):
        import pybuilder.reactor

        with patch("pybuilder.reactor.Task"):
            @task
            def task1():
                pass

            @task
            @depends(task1)
            def task2():
                pass

            @task
            @depends(task1)
            @dependents(task2)
            def task3():
                pass

            module1 = ModuleType("mock_module_one")
            module1.task1 = task1
            module1.task2 = task2

            module2 = ModuleType("mock_module_two")
            module2.task3 = task3

            self.reactor.collect_tasks_and_actions_and_initializers(module1)
            pybuilder.reactor.Task.assert_has_calls([call("task1", task1, [], ''),
                                                     call("task2", task2, [TaskDependency(task1)], '')])

            self.reactor.collect_tasks_and_actions_and_initializers(module2)
            pybuilder.reactor.Task.assert_has_calls([call("task3", task3, [TaskDependency(task1)], '')])
            self.execution_manager.register_late_task_dependencies.assert_has_calls(
                [call({}), call({"task2": [TaskDependency(task3)]})])

    def test_task_dependencies_with_post_definition_injections_custom_names(self):
        import pybuilder.reactor

        with patch("pybuilder.reactor.Task"):
            @task
            def task1():
                pass

            @task
            @depends(task1)
            def task2():
                pass

            @task("task_3")
            @depends(task1)
            @dependents(task2)
            def task3():
                pass

            module1 = ModuleType("mock_module_one")
            module1.task1 = task1
            module1.task2 = task2

            module2 = ModuleType("mock_module_two")
            module2.task3 = task3

            self.reactor.collect_tasks_and_actions_and_initializers(module1)
            pybuilder.reactor.Task.assert_has_calls([call("task1", task1, [], ''),
                                                     call("task2", task2, [TaskDependency(task1)], '')])

            self.reactor.collect_tasks_and_actions_and_initializers(module2)
            pybuilder.reactor.Task.assert_has_calls([call("task_3", task3, [TaskDependency(task1)], '')])
            self.execution_manager.register_late_task_dependencies.assert_has_calls(
                [call({}), call({"task2": [TaskDependency("task_3")]})])

    def test_should_collect_single_before_action(self):
        @before("spam")
        def action():
            pass

        module = ModuleType("mock_module")
        module.task = action

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        self.assertEquals(self.execution_manager.register_action.call_count, 1)
        self.assertTrue(isinstance(self.execution_manager.register_action.call_args[0][0], Action) and
                        len(self.execution_manager.register_action.call_args[0]) == 1)

    def test_should_collect_single_after_action(self):
        @after("spam")
        def action():
            pass

        module = ModuleType("mock_module")
        module.task = action

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        self.assertEquals(self.execution_manager.register_action.call_count, 1)
        self.assertTrue(isinstance(self.execution_manager.register_action.call_args[0][0], Action) and
                        len(self.execution_manager.register_action.call_args[0]) == 1)

    def test_should_collect_single_after_action_with_only_once_flag(self):
        @after("spam", only_once=True)
        def action():
            pass

        module = ModuleType("mock_module")
        module.task = action

        def register_action(action):
            if not action.only_once:
                raise AssertionError("Action is not marked as only_once")

        self.execution_manager.register_action = register_action

        self.reactor.collect_tasks_and_actions_and_initializers(module)

    def test_should_collect_single_after_action_with_teardown_flag(self):
        @after("spam", teardown=True)
        def action():
            pass

        module = ModuleType("mock_module")
        module.task = action

        self.reactor.collect_tasks_and_actions_and_initializers(module)

    def test_should_collect_single_initializer(self):
        def init():
            pass

        setattr(init, INITIALIZER_ATTRIBUTE, True)

        module = ModuleType("mock_module")
        module.task = init

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        self.assertEquals(self.execution_manager.register_initializer.call_count, 1)
        self.assertTrue(isinstance(self.execution_manager.register_initializer.call_args[0][0], Initializer) and
                        len(self.execution_manager.register_initializer.call_args[0]) == 1)

    def test_should_collect_single_initializer_with_environments(self):
        def init():
            pass

        setattr(init, INITIALIZER_ATTRIBUTE, True)
        setattr(init, ENVIRONMENTS_ATTRIBUTE, ["any_environment"])

        module = ModuleType("mock_module")
        module.task = init

        class ExecutionManagerMock(object):
            def register_initializer(self, initializer):
                self.initializer = initializer

            def register_late_task_dependencies(self, dependencies):
                pass

        execution_manager_mock = ExecutionManagerMock()
        self.reactor.execution_manager = execution_manager_mock

        self.reactor.collect_tasks_and_actions_and_initializers(module)

        self.assertEquals(
            execution_manager_mock.initializer.environments, ["any_environment"])

    @patch("pybuilder.reactor.os.path.exists", return_value=False)
    @patch("pybuilder.reactor.os.path.abspath", return_value="spam")
    def test_should_raise_when_verifying_project_directory_and_directory_does_not_exist(self,
                                                                                        os_path_abspath,
                                                                                        os_path_exists):
        self.assertRaises(
            PyBuilderException, self.reactor.verify_project_directory, "spam", "eggs")

        os_path_abspath.assert_called_with("spam")
        os_path_exists.assert_called_with("spam")

    @patch("pybuilder.reactor.os.path.isdir", return_value=False)
    @patch("pybuilder.reactor.os.path.exists", return_value=True)
    @patch("pybuilder.reactor.os.path.abspath", return_value="spam")
    def test_should_raise_when_verifying_project_directory_and_directory_is_not_a_directory(self,
                                                                                            os_path_abspath,
                                                                                            os_path_exists,
                                                                                            os_path_isdir):
        self.assertRaises(
            PyBuilderException, self.reactor.verify_project_directory, "spam", "eggs")

        os_path_abspath.assert_called_with("spam")
        os_path_exists.assert_called_with("spam")
        os_path_isdir.assert_called_with("spam")

    @patch("pybuilder.reactor.os.path.join", side_effect=lambda *x: "/".join(x))
    @patch("pybuilder.reactor.os.path.isdir", return_value=True)
    @patch("pybuilder.reactor.os.path.exists", side_effect=lambda x: True if x == "spam" else False)
    @patch("pybuilder.reactor.os.path.abspath", return_value="spam")
    def test_should_raise_when_verifying_project_directory_and_build_descriptor_does_not_exist(self,
                                                                                               os_path_abspath,
                                                                                               os_path_exists,
                                                                                               os_path_isdir,
                                                                                               os_path_join):
        self.assertRaises(
            PyBuilderException, self.reactor.verify_project_directory, "spam", "eggs")

        os_path_abspath.assert_called_with("spam")
        os_path_exists.assert_has_calls([call("spam"), call("spam/eggs")])
        os_path_isdir.assert_called_with("spam")
        os_path_join.assert_called_with("spam", "eggs")

    @patch("pybuilder.reactor.os.path.isfile", return_value=False)
    @patch("pybuilder.reactor.os.path.join", side_effect=lambda *x: "/".join(x))
    @patch("pybuilder.reactor.os.path.isdir", return_value=True)
    @patch("pybuilder.reactor.os.path.exists", return_value=True)
    @patch("pybuilder.reactor.os.path.abspath", return_value="spam")
    def test_should_raise_when_verifying_project_directory_and_build_descriptor_is_not_a_file(self,
                                                                                              os_path_abspath,
                                                                                              os_path_exists,
                                                                                              os_path_isdir,
                                                                                              os_path_join,
                                                                                              os_path_isfile):
        self.assertRaises(
            PyBuilderException, self.reactor.verify_project_directory, "spam", "eggs")

        os_path_abspath.assert_called_with("spam")
        os_path_exists.assert_has_calls([call("spam"), call("spam/eggs")])
        os_path_isdir.assert_called_with("spam")
        os_path_join.assert_called_with("spam", "eggs")
        os_path_isfile.assert_called_with("spam/eggs")

    @patch("pybuilder.reactor.os.path.isfile", return_value=True)
    @patch("pybuilder.reactor.os.path.join", side_effect=lambda *x: "/".join(x))
    @patch("pybuilder.reactor.os.path.isdir", return_value=True)
    @patch("pybuilder.reactor.os.path.exists", return_value=True)
    @patch("pybuilder.reactor.os.path.abspath", return_value="/spam")
    def test_should_return_directory_and_full_path_of_descriptor_when_verifying_project_directory(self,
                                                                                                  os_path_abspath,
                                                                                                  os_path_exists,
                                                                                                  os_path_isdir,
                                                                                                  os_path_join,
                                                                                                  os_path_isfile):
        self.assertEquals(
            ("/spam", "/spam/eggs"), self.reactor.verify_project_directory("spam", "eggs"))

        os_path_abspath.assert_called_with("spam")
        os_path_exists.assert_has_calls([call("/spam"), call("/spam/eggs")])
        os_path_isdir.assert_called_with("/spam")
        os_path_join.assert_called_with("/spam", "eggs")
        os_path_isfile.assert_called_with("/spam/eggs")

    @patch("pybuilder.reactor.imp.load_source", side_effect=ImportError("spam"))
    def test_should_raise_when_loading_project_module_and_import_raises_exception(self, imp_load_source):
        self.assertRaises(
            PyBuilderException, self.reactor.load_project_module, "spam")

        imp_load_source.assert_called_with("build", "spam")

    @patch("pybuilder.reactor.imp.load_source", return_value=Mock())
    def test_should_return_module_when_loading_project_module_and_import_raises_exception(self, imp_load_source):
        self.assertTrue(imp_load_source.return_value is self.reactor.load_project_module("spam"))

        imp_load_source.assert_called_with("build", "spam")

    def test_ensure_project_attributes_are_set_when_instantiating_project(self):
        module = ModuleType("mock_module")

        module.version = "version"
        module.default_task = "default_task"
        module.summary = "summary"
        module.home_page = "home_page"
        module.description = "description"
        module.authors = "authors"
        module.license = "license"
        module.url = "url"

        self.reactor.project = Mock()
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
        module = ModuleType("mock_module")
        module.name = "mock_module"

        self.reactor.project = Mock()
        self.reactor.project_module = module
        self.reactor.apply_project_attributes()

        self.assertEquals("mock_module", self.reactor.project.name)

    def test_should_import_plugin_only_once(self):
        plugin_module = ModuleType("mock_module")
        self.plugin_loader_mock.load_plugin.return_value = plugin_module

        self.reactor.require_plugin("spam")
        self.reactor.require_plugin("spam")

        self.assertEquals(["spam"], self.reactor.get_plugins())

        self.plugin_loader_mock.load_plugin.assert_called_with(ANY, "spam", None, None)

    def test_ensure_project_properties_are_logged_when_calling_log_project_properties(self):
        project = Project("spam")
        project.set_property("spam", "spam")
        project.set_property("eggs", "eggs")

        self.reactor.project = project
        self.reactor.log_project_properties()

        call_args = self.logger.debug.call_args
        self.assertEquals(call_args[0][0], "Project properties: %s")
        self.assertTrue("basedir : spam" in call_args[0][1])
        self.assertTrue("eggs : eggs" in call_args[0][1])
        self.assertTrue("spam : spam" in call_args[0][1])

    def test_should_raise_exception_when_project_is_not_valid(self):
        self.reactor.project = Mock(properties={})
        self.reactor.project.validate.return_value = ["spam"]

        self.assertRaises(ProjectValidationFailedException, self.reactor.build)
