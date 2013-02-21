#  This file is part of Python Builder
#
#  Copyright 2011-2013 PyBuilder Team
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
from mockito import verify, unstub, any, times, when
import unittest
from test_utils import mock

from pybuilder.errors import MissingTaskDependencyException, CircularTaskDependencyException, NoSuchTaskException,\
    MissingActionDependencyException, InvalidNameException
from pybuilder.core import Logger
from pybuilder.execution import as_task_name_list, Action, Executable, ExecutionManager, Task,\
    DependenciesNotResolvedException, Initializer

class AsTaskNameList(unittest.TestCase):
    def test_should_return_list_of_strings_when_string_given(self):
        self.assertEquals(["spam"], as_task_name_list("spam"))

    def test_should_return_list_of_strings_when_list_of_strings_given(self):
        self.assertEquals(["spam", "eggs"], as_task_name_list(["spam", "eggs"]))

    def test_should_return_list_of_strings_when_function_given(self):
        def spam(): pass

        self.assertEquals(["spam"], as_task_name_list(spam))

    def test_should_return_list_of_strings_when_list_of_functions_given(self):
        def spam(): pass

        def eggs(): pass

        self.assertEquals(["spam", "eggs"], as_task_name_list([spam, eggs]))


class ExecutableTest(unittest.TestCase):
    def test_should_raise_exception_when_passing_non_function_to_constructor(self):
        self.assertRaises(TypeError, Executable, "callable", "spam")

    def test_should_raise_exception_when_executable_name_is_invalid(self):
        def callable(): pass

        self.assertRaises(InvalidNameException, Executable, "a-b", callable)
        self.assertRaises(InvalidNameException, Executable, "88aa", callable)
        self.assertRaises(InvalidNameException, Executable, "l asd ll", callable)
        self.assertRaises(InvalidNameException, Executable, "@", callable)
        self.assertRaises(InvalidNameException, Executable, "$", callable)
        self.assertRaises(InvalidNameException, Executable, "%", callable)

    def test_should_execute_callable_without_arguments(self):
        def callable():
            callable.called = True

        callable.called = False

        Executable("callable", callable).execute({})

        self.assertTrue(callable.called)

    def test_should_execute_callable_with_single_arguments(self):
        def callable(spam):
            callable.called = True
            callable.spam = spam

        callable.called = False

        Executable("callable", callable).execute({"spam": "spam"})

        self.assertTrue(callable.called)
        self.assertEquals("spam", callable.spam)

    def test_should_raise_exception_when_callable_argument_cannot_be_satisfied(self):
        def callable(spam): pass

        executable = Executable("callable", callable)
        self.assertRaises(ValueError, executable.execute, {})


class ActionTest(unittest.TestCase):
    def test_should_initialize_fields(self):
        def callable(): pass

        action = Action("callable", callable, "before", "after", "description")

        self.assertEquals(["before"], action.execute_before)
        self.assertEquals(["after"], action.execute_after)
        self.assertEquals("description", action.description)


class TaskTest(unittest.TestCase):
    def test_should_initialize_fields(self):
        def callable(): pass

        task = Task("callable", callable, "dependency", "description")

        self.assertEquals(["dependency"], task.dependencies)
        self.assertEquals(["description"], task.description)

    def test_should_execute_callable_without_arguments(self):
        def callable():
            callable.called = True

        callable.called = False

        Task("callable", callable).execute(mock(), {})

        self.assertTrue(callable.called)

    def test_should_execute_callable_with_single_arguments(self):
        def callable(spam):
            callable.called = True
            callable.spam = spam

        callable.called = False

        Task("callable", callable).execute(mock(), {"spam": "spam"})

        self.assertTrue(callable.called)
        self.assertEquals("spam", callable.spam)

    def test_should_raise_exception_when_callable_argument_cannot_be_satisfied(self):
        def callable(spam): pass

        executable = Task("callable", callable)
        self.assertRaises(ValueError, executable.execute, mock(), {})


class TaskExtensionTest(unittest.TestCase):
    def test_should_extend_task_with_values_from_other_task(self):
        def callable_one(): pass

        def callable_two(param): pass

        task = Task("task", callable_one, "dependency", "description")
        replacement = Task("replacement", callable_two,
            "another_dependency", "replacement description")

        task.extend(replacement)

        self.assertEquals("task", task.name)
        self.assertEquals(["dependency", "another_dependency"], task.dependencies)
        self.assertEquals(["description", "replacement description"], task.description)

    def test_should_execute_both_callables_when_extending_task(self):
        def callable_one():
            callable_one.called = True

        callable_one.called = False

        def callable_two(param):
            callable_two.called = True

        callable_two.called = False

        task_one = Task("task", callable_one)
        task_two = Task("task", callable_two)
        task_one.extend(task_two)

        task_one.execute(mock(), {"param": "spam"})

        self.assertTrue(callable_one.called)
        self.assertTrue(callable_two.called)


class InitializerTest(unittest.TestCase):
    def setUp(self):
        def callable(): pass

        self.callable = callable

    def test_should_return_true_when_invoking_is_applicable_without_environment_and_initializer_does_not_define_environments(
            self):
        initializer = Initializer("initialzer", self.callable)
        self.assertTrue(initializer.is_applicable())

    def test_should_return_true_when_invoking_is_applicable_with_environment_and_initializer_does_not_define_environments(
            self):
        initializer = Initializer("initialzer", self.callable)
        self.assertTrue(initializer.is_applicable("any_environment"))

    def test_should_return_true_when_invoking_is_applicable_with_environment_and_initializer_defines_environment(
            self):
        initializer = Initializer("initialzer", self.callable, "any_environment")
        self.assertTrue(initializer.is_applicable("any_environment"))

    def test_should_return_true_when_invoking_is_applicable_with_environments_and_initializer_defines_environment(
            self):
        initializer = Initializer("initialzer", self.callable, "any_environment")
        self.assertTrue(initializer.is_applicable(["any_environment", "any_other_environment"]))

    def test_should_return_false_when_invoking_is_applicable_with_environment_and_initializer_defines_environment(
            self):
        initializer = Initializer("initialzer", self.callable, "any_environment")
        self.assertFalse(initializer.is_applicable("any_other_environment"))

    def test_should_return_false_when_invoking_is_applicable_without_environment_and_initializer_defines_environment(
            self):
        initializer = Initializer("initialzer", self.callable, "any_environment")
        self.assertFalse(initializer.is_applicable())

    def test_should_return_true_when_invoking_is_applicable_with_environment_and_initializer_defines_multiple_environments(
            self):
        initializer = Initializer("initialzer", self.callable, ["any_environment", "any_other_environment"])
        self.assertTrue(initializer.is_applicable(["any_environment"]))


class ExecutionManagerTestBase(unittest.TestCase):
    def setUp(self):
        self.execution_manager = ExecutionManager(Logger())

    def tearDown(self):
        unstub()


class ExecutionManagerInitializerTest(ExecutionManagerTestBase):
    def test_ensure_that_initializer_is_added_when_calling_register_initializer(self):
        initializer = mock()
        self.execution_manager.register_initializer(initializer)
        self.assertEquals([initializer], self.execution_manager.initializers)

    def test_ensure_that_registered_initializers_are_executed_when_calling_execute_initializers(self):
        initializer_1 = mock()
        when(initializer_1).is_applicable(any()).thenReturn(True)
        self.execution_manager.register_initializer(initializer_1)

        initializer_2 = mock()
        when(initializer_2).is_applicable(any()).thenReturn(True)
        self.execution_manager.register_initializer(initializer_2)

        self.execution_manager.execute_initializers(a=1)

        verify(initializer_1).execute({"a": 1})
        verify(initializer_2).execute({"a": 1})

    def test_ensure_that_registered_initializers_are_not_executed_when_environments_do_not_match (self):
        initializer = mock()
        when(initializer).is_applicable(any()).thenReturn(False)

        self.execution_manager.register_initializer(initializer)

        environments = []
        self.execution_manager.execute_initializers(environments, a=1)

        verify(initializer).is_applicable(environments)
        verify(initializer, 0).execute(any())


class ExecutionManagerTaskTest(ExecutionManagerTestBase):
    def test_ensure_task_is_added_when_calling_register_task(self):
        task = mock()
        self.execution_manager.register_task(task)
        self.assertEquals([task], self.execution_manager.tasks)

    def test_ensure_task_is_replaced_when_registering_two_tasks_with_same_name(self):
        original = mock(name="spam")
        replacement = mock(name="spam")

        self.execution_manager.register_task(original)
        self.execution_manager.register_task(replacement)

        verify(original).extend(replacement)

    def test_should_raise_exception_when_calling_execute_task_before_resolve_dependencies(self):
        self.assertRaises(DependenciesNotResolvedException,
            self.execution_manager.execute_task,
            mock())

    def test_ensure_task_is_executed_when_calling_execute_task(self):
        task = mock(name="spam", dependencies=[])

        self.execution_manager.register_task(task)
        self.execution_manager.resolve_dependencies()

        self.execution_manager.execute_task(task, a=1)

        verify(task).execute(any(), {"a": 1})

    def test_ensure_before_action_is_executed_when_task_is_executed(self):
        task = mock(name="task", dependencies=[])
        action = mock(name="action", execute_before=["task"], execute_after=[])

        self.execution_manager.register_action(action)
        self.execution_manager.register_task(task)
        self.execution_manager.resolve_dependencies()

        self.execution_manager.execute_task(task)

        verify(action).execute({})
        verify(task).execute(any(), {})

    def test_ensure_after_action_is_executed_when_task_is_executed(self):
        task = mock(name="task", dependencies=[])
        action = mock(name="action", execute_before=[], execute_after=["task"])

        self.execution_manager.register_action(action)
        self.execution_manager.register_task(task)
        self.execution_manager.resolve_dependencies()

        self.execution_manager.execute_task(task)

        verify(action).execute({})
        verify(task).execute(any(), {})

    def test_should_return_single_task_name(self):
        self.execution_manager.register_task(mock(name="spam"))
        self.assertEquals(["spam"], self.execution_manager.task_names)

    def test_should_return_all_task_names(self):
        self.execution_manager.register_task(mock(name="spam"), mock(name="eggs"))
        self.assertEquals(["eggs", "spam"], self.execution_manager.task_names)


class ExecutionManagerActionTest(ExecutionManagerTestBase):
    def test_ensure_action_is_registered(self):
        action = mock(name="action")
        self.execution_manager.register_action(action)
        self.assertEquals({"action": action}, self.execution_manager._actions)

    def test_ensure_action_registered_for_two_tasks_is_executed_two_times(self):
        spam = mock(name="spam", dependencies=[])
        eggs = mock(name="eggs", dependencies=[])
        self.execution_manager.register_task(spam, eggs)

        action = mock(name="action",
            execute_before=[],
            execute_after=["spam", "eggs"],
            only_once=False)
        self.execution_manager.register_action(action)

        self.execution_manager.resolve_dependencies()

        self.execution_manager.execute_execution_plan([spam, eggs])

        verify(action, times(2)).execute(any())

    def test_ensure_action_registered_for_two_tasks_is_executed_only_once_if_single_attribute_is_present(self):
        spam = mock(name="spam", dependencies=[])
        eggs = mock(name="eggs", dependencies=[])
        self.execution_manager.register_task(spam, eggs)

        action = mock(name="action",
            execute_before=[],
            execute_after=["spam", "eggs"],
            only_once=True)
        self.execution_manager.register_action(action)

        self.execution_manager.resolve_dependencies()

        self.execution_manager.execute_execution_plan([spam, eggs])

        verify(action, times(1)).execute(any())


class ExecutionManagerResolveDependenciesTest(ExecutionManagerTestBase):
    def test_ensure_that_dependencies_are_resolved_when_no_task_is_given(self):
        self.execution_manager.resolve_dependencies()
        self.assertTrue(self.execution_manager._dependencies_resolved)

    def test_ensure_that_dependencies_are_resolved_when_single_task_is_given(self):
        task = mock(dependencies=[])

        self.execution_manager.register_task(task)

        self.execution_manager.resolve_dependencies()
        self.assertTrue(self.execution_manager._dependencies_resolved)

    def test_should_raise_exception_when_task_depends_on_task_not_found(self):
        task = mock(dependencies=["not_found"])

        self.execution_manager.register_task(task)

        self.assertRaises(MissingTaskDependencyException, self.execution_manager.resolve_dependencies)

    def test_should_raise_exception_when_before_action_depends_on_task_not_found(self):
        action = mock(execute_before=["not_found"], execute_after=[])

        self.execution_manager.register_action(action)

        self.assertRaises(MissingActionDependencyException, self.execution_manager.resolve_dependencies)

    def test_should_raise_exception_when_after_action_depends_on_task_not_found(self):
        action = mock(execute_before=[], execute_after=["not_found"])

        self.execution_manager.register_action(action)

        self.assertRaises(MissingActionDependencyException, self.execution_manager.resolve_dependencies)

    def test_ensure_that_dependencies_are_resolved_when_simple_dependency_is_found(self):
        one = mock(name="one", dependencies=[])
        two = mock(name="two", dependencies=["one"])

        self.execution_manager.register_task(one, two)

        self.execution_manager.resolve_dependencies()

        self.assertEquals([], self.execution_manager._task_dependencies.get("one"))
        self.assertEquals([one], self.execution_manager._task_dependencies.get("two"))

    def test_ensure_that_dependencies_are_resolved_when_task_depends_on_multiple_tasks(self):
        one = mock(name="one", dependencies=[])
        two = mock(name="two", dependencies=["one"])
        three = mock(name="three", dependencies=["one", "two"])

        self.execution_manager.register_task(one, two, three)

        self.execution_manager.resolve_dependencies()

        self.assertEquals([], self.execution_manager._task_dependencies.get("one"))
        self.assertEquals([one], self.execution_manager._task_dependencies.get("two"))
        self.assertEquals([one, two], self.execution_manager._task_dependencies.get("three"))


class ExecutionManagerBuildExecutionPlanTest(ExecutionManagerTestBase):
    def test_should_raise_exception_when_building_execution_plan_and_dependencies_are_not_resolved(self):
        self.assertRaises(DependenciesNotResolvedException, self.execution_manager.build_execution_plan, ("boom",))

    def test_should_raise_exception_when_building_execution_plan_for_task_not_found(self):
        self.execution_manager.resolve_dependencies()
        self.assertRaises(NoSuchTaskException, self.execution_manager.build_execution_plan, ("boom",))

    def test_should_return_execution_plan_with_single_task_when_single_task_is_to_be_executed(self):
        one = mock(name="one", dependencies=[])

        self.execution_manager.register_task(one)
        self.execution_manager.resolve_dependencies()

        self.assertEqual([one], self.execution_manager.build_execution_plan(["one"]))

    def test_should_return_execution_plan_with_two_tasks_when_two_tasks_are_to_be_executed(self):
        one = mock(name="one", dependencies=[])
        two = mock(name="two", dependencies=[])

        self.execution_manager.register_task(one, two)
        self.execution_manager.resolve_dependencies()

        self.assertEqual([one, two], self.execution_manager.build_execution_plan(["one", "two"]))

    def test_ensure_that_dependencies_are_executed_before_root_task(self):
        one = mock(name="one", dependencies=[])
        two = mock(name="two", dependencies=["one"])

        self.execution_manager.register_task(one, two)
        self.execution_manager.resolve_dependencies()

        self.assertEqual([one, two], self.execution_manager.build_execution_plan(["two"]))


    def test_ensure_that_tasks_are_not_executed_multiple_times(self):
        one = mock(name="one", dependencies=[])

        self.execution_manager.register_task(one)
        self.execution_manager.resolve_dependencies()

        self.assertEqual([one], self.execution_manager.build_execution_plan(["one", "one"]))

    def test_ensure_that_tasks_are_not_executed_multiple_times_when_being_dependencies(self):
        one = mock(name="one", dependencies=[])
        two = mock(name="two", dependencies=["one"])

        self.execution_manager.register_task(one, two)
        self.execution_manager.resolve_dependencies()

        self.assertEqual([one, two], self.execution_manager.build_execution_plan(["one", "two"]))

    def test_should_raise_exception_when_circular_reference_is_detected_on_single_task(self):
        one = mock(name="one", dependencies=["one"])

        self.execution_manager.register_task(one)
        self.execution_manager.resolve_dependencies()

        self.assertRaises(CircularTaskDependencyException, self.execution_manager.build_execution_plan, ["one"])

    def test_should_raise_exception_when_circular_reference_is_detected_on_two_tasks(self):
        one = mock(name="one", dependencies=["two"])
        two = mock(name="two", dependencies=["one"])

        self.execution_manager.register_task(one, two)

        self.execution_manager.resolve_dependencies()

        self.assertRaises(CircularTaskDependencyException, self.execution_manager.build_execution_plan, ["one"])

    def test_should_raise_exception_when_circular_reference_is_detected_on_three_tasks(self):
        one = mock(name="one", dependencies=["three"])
        two = mock(name="two", dependencies=["one"])
        three = mock(name="three", dependencies=["one", "two"])

        self.execution_manager.register_task(one, two, three)

        self.execution_manager.resolve_dependencies()

        self.assertRaises(CircularTaskDependencyException, self.execution_manager.build_execution_plan, ["one"])


class ExecutionManagerExecuteExecutionPlanTest(ExecutionManagerTestBase):
    def test_should_raise_exception_when_dependencies_are_not_resolved(self):
        self.assertRaises(DependenciesNotResolvedException, self.execution_manager.execute_execution_plan, ["boom"])

    def test_ensure_tasks_are_executed(self):
        one = mock(name="one", dependencies=[])
        two = mock(name="two", dependencies=[])

        self.execution_manager.register_task(one, two)
        self.execution_manager.resolve_dependencies()

        self.execution_manager.execute_execution_plan([one, two])

        verify(one).execute(any(), {})
        verify(two).execute(any(), {})
