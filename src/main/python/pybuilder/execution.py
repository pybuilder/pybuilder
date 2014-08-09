#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
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
import re
import types

from pybuilder.errors import (CircularTaskDependencyException,
                              DependenciesNotResolvedException,
                              InvalidNameException,
                              MissingTaskDependencyException,
                              MissingActionDependencyException,
                              NoSuchTaskException)
from pybuilder.utils import as_list, Timer


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
    def __init__(self, name, callable, before=None, after=None, description="", only_once=False):
        super(Action, self).__init__(name, callable, description)
        self.execute_before = as_task_name_list(before)
        self.execute_after = as_task_name_list(after)
        self.only_once = only_once


class Task(object):
    def __init__(self, name, callable, dependencies=None, description=""):
        self.name = name
        self.executables = [Executable(name, callable, description)]
        self.dependencies = as_task_name_list(dependencies)
        self.description = [description]

    def __eq__(self, other):
        if isinstance(other, Task):
            return self.name == other.name
        return False

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

        self._tasks = {}
        self._task_dependencies = {}

        self._actions = {}
        self._execute_before = {}
        self._execute_after = {}

        self._initializers = []

        self._dependencies_resolved = False
        self._actions_executed = []

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

        for action in self._execute_before[task.name]:
            if self.execute_action(action, keyword_arguments):
                number_of_actions += 1

        task.execute(self.logger, keyword_arguments)

        for action in self._execute_after[task.name]:
            if self.execute_action(action, keyword_arguments):
                number_of_actions += 1

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
        return self._tasks[name]

    def has_task(self, name):
        return name in self._tasks

    def build_execution_plan(self, task_names):
        self.assert_dependencies_resolved()

        execution_plan = []
        for name in as_list(task_names):
            self.enqueue_task(execution_plan, name)
        return execution_plan

    def enqueue_task(self, execution_plan, task_name, circular_check=None):
        if not self.has_task(task_name):
            raise NoSuchTaskException(task_name)

        task = self.get_task(task_name)

        if task == circular_check:
            raise CircularTaskDependencyException(task.name)

        if task in execution_plan:
            return

        try:
            for dependency in self._task_dependencies[task.name]:
                self.enqueue_task(execution_plan, dependency.name,
                                  circular_check=circular_check if circular_check else task)
        except CircularTaskDependencyException as e:
            if e.second:
                raise
            raise CircularTaskDependencyException(e.first, task.name)

        execution_plan.append(task)

    def resolve_dependencies(self):
        for task in self._tasks.values():
            self._execute_before[task.name] = []
            self._execute_after[task.name] = []
            self._task_dependencies[task.name] = []
            for d in task.dependencies:
                if not self.has_task(d):
                    raise MissingTaskDependencyException(task.name, d)
                self._task_dependencies[task.name].append(self.get_task(d))

        for action in self._actions.values():
            for task in action.execute_before:
                if not self.has_task(task):
                    raise MissingActionDependencyException(action.name, task)
                self._execute_before[task].append(action)

            for task in action.execute_after:
                if not self.has_task(task):
                    raise MissingActionDependencyException(action.name, task)
                self._execute_after[task].append(action)

        self._dependencies_resolved = True
