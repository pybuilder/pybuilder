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

"""
    The PyBuilder execution module.
    Deals with the execution of a PyBuilder process by
    running tasks, actions and initializers in the correct
    order regarding dependencies.
"""

import inspect
import copy
import traceback
import sys

import re
import types

from pybuilder.errors import (CircularTaskDependencyException,
                              DependenciesNotResolvedException,
                              InvalidNameException,
                              MissingTaskDependencyException,
                              RequiredTaskExclusionException,
                              MissingActionDependencyException,
                              NoSuchTaskException)
from pybuilder.utils import as_list, Timer, odict
from pybuilder.graph_utils import Graph, GraphHasCycles

if sys.version_info[0] < 3:  # if major is less than 3
    from .excp_util_2 import raise_exception
else:
    from .excp_util_3 import raise_exception


def as_task_name_list(mixed):
    result = []
    for item in as_list(mixed):
        if isinstance(item, types.FunctionType):
            result.append(item.__name__)
        else:
            result.append(str(item))
    return result


class Executable(object):
    NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]+$")

    def __init__(self, name, callable, description=""):
        if not Executable.NAME_PATTERN.match(name):
            raise InvalidNameException(name)

        self._name = name
        self.description = description
        self.callable = callable
        if hasattr(callable, "__module__"):
            self.source = callable.__module__
        else:
            self.source = "n/a"

        if isinstance(self.callable, types.FunctionType):
            self.parameters = inspect.getargspec(self.callable).args
        else:
            raise TypeError("Don't know how to handle callable %s" % callable)

    @property
    def name(self):
        return self._name

    def execute(self, argument_dict):
        arguments = []
        for parameter in self.parameters:
            if parameter not in argument_dict:
                raise ValueError("Invalid parameter '%s' for %s %s" % (parameter, self.__class__.__name__, self.name))
            arguments.append(argument_dict[parameter])

        self.callable(*arguments)


class Action(Executable):
    def __init__(self, name, callable, before=None, after=None, description="", only_once=False, teardown=False):
        super(Action, self).__init__(name, callable, description)
        self.execute_before = as_task_name_list(before)
        self.execute_after = as_task_name_list(after)
        self.only_once = only_once
        self.teardown = teardown


class Task(object):
    def __init__(self, name, callable, dependencies=None, description="", optional_dependencies=None):
        self.name = name
        self.executables = [Executable(name, callable, description)]
        self.dependencies = as_task_name_list(dependencies)
        self.optional_dependencies = as_task_name_list(optional_dependencies)
        self.description = [description]

    def __eq__(self, other):
        if isinstance(other, Task):
            return self.name == other.name
        return False

    def __hash__(self):
        return 9 * hash(self.name)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other, Task):
            return self.name < other.name
        return self.name < other

    def extend(self, task):
        self.executables += task.executables
        self.dependencies += task.dependencies
        self.description += task.description

    def execute(self, logger, argument_dict):
        for executable in self.executables:
            logger.debug("Executing subtask from %s", executable.source)
            executable.execute(argument_dict)


class Initializer(Executable):
    def __init__(self, name, callable, environments=None, description=""):
        super(Initializer, self).__init__(name, callable, description)
        self.environments = environments

    def is_applicable(self, environments=None):
        if not self.environments:
            return True
        for environment in as_list(environments):
            if environment in self.environments:
                return True


class TaskExecutionSummary(object):
    def __init__(self, task, number_of_actions, execution_time):
        self.task = task
        self.number_of_actions = number_of_actions
        self.execution_time = execution_time


class ExecutionManager(object):
    def __init__(self, logger):
        self.logger = logger

        self._tasks = odict()
        self._task_dependencies = odict()

        self._actions = odict()
        self._execute_before = odict()
        self._execute_after = odict()

        self._initializers = []

        self._dependencies_resolved = False
        self._actions_executed = []
        self._tasks_executed = []
        self._current_task = None

        self._exclude_optional_tasks = []
        self._exclude_tasks = []

    @property
    def initializers(self):
        return self._initializers

    @property
    def tasks(self):
        return list(self._tasks.values())

    @property
    def task_names(self):
        return sorted(self._tasks.keys())

    def register_initializer(self, initializer):
        self.logger.debug("Registering initializer '%s'", initializer.name)
        self._initializers.append(initializer)

    def register_action(self, action):
        self.logger.debug("Registering action '%s'", action.name)
        self._actions[action.name] = action

    def register_task(self, *tasks):
        for task in tasks:
            self.logger.debug("Registering task '%s'", task.name)
            if task.name in self._tasks:
                self._tasks[task.name].extend(task)
            else:
                self._tasks[task.name] = task

    def execute_initializers(self, environments=None, **keyword_arguments):
        for initializer in self._initializers:
            if not initializer.is_applicable(environments):
                message = "Not going to execute initializer '%s' from '%s' as environments do not match."
                self.logger.debug(message, initializer.name, initializer.source)

            else:
                self.logger.debug("Executing initializer '%s' from '%s'",
                                  initializer.name, initializer.source)
                initializer.execute(keyword_arguments)

    def assert_dependencies_resolved(self):
        if not self._dependencies_resolved:
            raise DependenciesNotResolvedException()

    def execute_task(self, task, **keyword_arguments):
        self.assert_dependencies_resolved()

        self.logger.debug("Executing task '%s'",
                          task.name)

        timer = Timer.start()
        number_of_actions = 0

        self._current_task = task

        suppressed_errors = []
        task_error = None

        has_teardown_tasks = False
        after_actions = self._execute_after[task.name]
        for action in after_actions:
            if action.teardown:
                has_teardown_tasks = True
                break

        try:
            for action in self._execute_before[task.name]:
                if self.execute_action(action, keyword_arguments):
                    number_of_actions += 1

            task.execute(self.logger, keyword_arguments)
        except:
            if not has_teardown_tasks:
                raise
            else:
                task_error = sys.exc_info()

        for action in after_actions:
            try:
                if not task_error or action.teardown:
                    if self.execute_action(action, keyword_arguments):
                        number_of_actions += 1
            except:
                if not has_teardown_tasks:
                    raise
                elif task_error:
                    suppressed_errors.append((action, sys.exc_info()))
                else:
                    task_error = sys.exc_info()

        for suppressed_error in suppressed_errors:
            action = suppressed_error[0]
            action_error = suppressed_error[1]
            self.logger.error("Executing action '%s' from '%s' resulted in an error that was suppressed:\n%s",
                              action.name, action.source,
                              "".join(traceback.format_exception(action_error[0], action_error[1], action_error[2])))
        if task_error:
            raise_exception(task_error[1], task_error[2])
        self._current_task = None
        if task not in self._tasks_executed:
            self._tasks_executed.append(task)

        timer.stop()
        return TaskExecutionSummary(task.name, number_of_actions, timer.get_millis())

    def execute_action(self, action, arguments):
        if action.only_once and action in self._actions_executed:
            message = "Action %s has been executed before and is marked as only_once, so will not be executed again"
            self.logger.debug(message, action.name)
            return False

        self.logger.debug("Executing action '%s' from '%s' before task", action.name, action.source)
        action.execute(arguments)
        self._actions_executed.append(action)
        return True

    def execute_execution_plan(self, execution_plan, **keyword_arguments):
        self.assert_dependencies_resolved()

        summaries = []

        for task in execution_plan:
            summaries.append(self.execute_task(task, **keyword_arguments))

        return summaries

    def get_task(self, name):
        if not self.has_task(name):
            raise NoSuchTaskException(name)
        return self._tasks[name]

    def has_task(self, name):
        return name in self._tasks

    def _collect_transitive_tasks(self, task, visited=None):
        if not visited:
            visited = set()
        if task in visited:
            return visited
        visited.add(task)
        dependencies = [self.get_task(dependency_name) for dependency_name in task.dependencies]
        for dependency in dependencies:
            self._collect_transitive_tasks(dependency, visited)
        return visited

    def collect_all_transitive_tasks(self, task_names):
        all_tasks = set()
        for task_name in task_names:
            all_tasks.update(self._collect_transitive_tasks(self.get_task(task_name)))
        return all_tasks

    def build_execution_plan(self, task_names):
        self.assert_dependencies_resolved()

        execution_plan = []

        dependency_edges = {}
        for task in self.collect_all_transitive_tasks(as_list(task_names)):
            dependency_edges[task.name] = task.dependencies
        try:
            Graph(dependency_edges).assert_no_cycles_present()
        except GraphHasCycles as cycles:
            raise CircularTaskDependencyException(str(cycles))

        for task_name in as_list(task_names):
            self.enqueue_task(execution_plan, task_name)
        return execution_plan

    def build_shortest_execution_plan(self, task_names):
        """
        Finds the shortest execution plan taking into the account tasks already executed
        This is useful when you want to execute tasks dynamically without repeating pre-requisite
        tasks you've already executed
        """
        execution_plan = self.build_execution_plan(task_names)
        shortest_plan = copy.copy(execution_plan)
        for executed_task in self._tasks_executed:
            candidate_task = shortest_plan[0]
            if candidate_task.name not in task_names and candidate_task == executed_task:
                shortest_plan.pop(0)
            else:
                break

        if self._current_task and self._current_task in shortest_plan:
            raise CircularTaskDependencyException("Task '%s' attempted to invoke tasks %s, "
                                                  "resulting in plan %s, creating circular dependency" %
                                                  (self._current_task, task_names, shortest_plan))
        return shortest_plan

    def enqueue_task(self, execution_plan, task_name):
        task = self.get_task(task_name)

        if task in execution_plan:
            return

        for dependency in self._task_dependencies[task.name]:
            self.enqueue_task(execution_plan, dependency.name)

        execution_plan.append(task)

    def resolve_dependencies(self, exclude_optional_tasks=None, exclude_tasks=None):
        self._exclude_optional_tasks = as_task_name_list(exclude_optional_tasks or [])
        self._exclude_tasks = as_task_name_list(exclude_tasks or [])

        for task in self._tasks.values():
            self._execute_before[task.name] = []
            self._execute_after[task.name] = []
            self._task_dependencies[task.name] = []
            if self.is_task_excluded(task.name) or self.is_optional_task_excluded(task.name):
                self.logger.debug("Skipping resolution for excluded task '%s'", task.name)
                continue
            for d in task.dependencies:
                if not self.has_task(d):
                    raise MissingTaskDependencyException(task.name, d)
                if self.is_optional_task_excluded(d):
                    raise RequiredTaskExclusionException(task.name, d)
                if not self.is_task_excluded(d):
                    self._task_dependencies[task.name].append(self.get_task(d))
                    self.logger.debug("Adding '%s' as a required dependency of task '%s'", d, task.name)

            for d in task.optional_dependencies:
                if not self.has_task(d):
                    raise MissingTaskDependencyException(task.name, d)
                if not (self.is_task_excluded(d) or self.is_optional_task_excluded(d)):
                    self._task_dependencies[task.name].append(self.get_task(d))
                    self.logger.debug("Adding '%s' as an optional dependency of task '%s'", d, task.name)

        for action in self._actions.values():
            for task in action.execute_before:
                if not self.has_task(task):
                    raise MissingActionDependencyException(action.name, task)
                self._execute_before[task].append(action)
                self.logger.debug("Adding before action '%s' for task '%s'", action.name, task)

            for task in action.execute_after:
                if not self.has_task(task):
                    raise MissingActionDependencyException(action.name, task)
                self._execute_after[task].append(action)
                self.logger.debug("Adding after action '%s' for task '%s'", action.name, task)

        self._dependencies_resolved = True

    def is_task_excluded(self, task):
        return task in self._exclude_tasks

    def is_optional_task_excluded(self, task):
        return task in self._exclude_optional_tasks
