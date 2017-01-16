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
    The PyBuilder reactor module.
    Operates a build process by instrumenting an ExecutionManager from the
    execution module.
"""

import imp
import os.path

from pybuilder.core import (TASK_ATTRIBUTE, DEPENDS_ATTRIBUTE, DEPENDENTS_ATTRIBUTE,
                            DESCRIPTION_ATTRIBUTE, AFTER_ATTRIBUTE,
                            BEFORE_ATTRIBUTE, INITIALIZER_ATTRIBUTE,
                            ACTION_ATTRIBUTE, ONLY_ONCE_ATTRIBUTE, TEARDOWN_ATTRIBUTE,
                            Project, NAME_ATTRIBUTE, ENVIRONMENTS_ATTRIBUTE, optional)
from pybuilder.errors import PyBuilderException, ProjectValidationFailedException
from pybuilder.execution import Action, Initializer, Task, TaskDependency
from pybuilder.pluginloader import (BuiltinPluginLoader,
                                    DispatchingPluginLoader,
                                    DownloadingPluginLoader)
from pybuilder.utils import as_list, get_dist_version_string, basestring


class BuildSummary(object):
    def __init__(self, project, task_execution_summaries):
        self.project = project
        self.task_summaries = task_execution_summaries


class Reactor(object):
    _current_instance = None

    @staticmethod
    def current_instance():
        return Reactor._current_instance

    @staticmethod
    def _set_current_instance(reactor):
        Reactor._current_instance = reactor

    def __init__(self, logger, execution_manager, plugin_loader=None):
        self.logger = logger
        self.execution_manager = execution_manager
        if not plugin_loader:
            self.plugin_loader = DispatchingPluginLoader(self.logger,
                                                         BuiltinPluginLoader(self.logger),
                                                         DownloadingPluginLoader(self.logger))
        else:
            self.plugin_loader = plugin_loader
        self._plugins = []
        self.project = None

    def require_plugin(self, plugin, version=None, plugin_module_name=None):
        if plugin not in self._plugins:
            try:
                self._plugins.append(plugin)
                self.import_plugin(plugin, version, plugin_module_name)
            except:  # NOQA
                self._plugins.remove(plugin)
                raise

    def get_plugins(self):
        return self._plugins

    def get_tasks(self):
        return self.execution_manager.tasks

    def validate_project(self):
        validation_messages = self.project.validate()
        if len(validation_messages) > 0:
            raise ProjectValidationFailedException(validation_messages)

    def prepare_build(self,
                      property_overrides=None,
                      project_directory=".",
                      project_descriptor="build.py",
                      exclude_optional_tasks=None,
                      exclude_tasks=None,
                      exclude_all_optional=False):
        if not property_overrides:
            property_overrides = {}
        Reactor._set_current_instance(self)

        project_directory, project_descriptor = self.verify_project_directory(
            project_directory, project_descriptor)

        self.logger.debug("Loading project module from %s", project_descriptor)

        self.project = Project(basedir=project_directory)

        self.project_module = self.load_project_module(project_descriptor)

        self.apply_project_attributes()
        self.override_properties(property_overrides)

        self.logger.debug("Have loaded plugins %s", ", ".join(self._plugins))

        self.collect_tasks_and_actions_and_initializers(self.project_module)

        self.execution_manager.resolve_dependencies(exclude_optional_tasks, exclude_tasks, exclude_all_optional)

    def build(self, tasks=None, environments=None):
        if not tasks:
            tasks = []
        else:
            tasks = as_list(tasks)
        if not environments:
            environments = []

        execution_plan = self.create_execution_plan(tasks, environments)
        return self.build_execution_plan(tasks, execution_plan)

    def create_execution_plan(self, tasks, environments):
        Reactor._set_current_instance(self)

        if environments:
            self.logger.info(
                "Activated environments: %s", ", ".join(environments))

        self.execution_manager.execute_initializers(
            environments, logger=self.logger, project=self.project)

        self.log_project_properties()

        self.validate_project()

        tasks = self._prepare_tasks(tasks)

        return self.execution_manager.build_execution_plan(tasks)

    def build_execution_plan(self, tasks, execution_plan):
        self.logger.debug("Execution plan is %s", ", ".join(
            [task.name for task in execution_plan]))

        self.logger.info(
            "Building %s version %s%s", self.project.name, self.project.version, get_dist_version_string(self.project))
        self.logger.info("Executing build in %s", self.project.basedir)

        if len(tasks) == 1:
            self.logger.info("Going to execute task %s", tasks[0])
        else:
            list_of_tasks = ", ".join(tasks)
            self.logger.info("Going to execute tasks: %s", list_of_tasks)

        task_execution_summaries = self.execution_manager.execute_execution_plan(
            execution_plan,
            logger=self.logger,
            project=self.project,
            reactor=self)

        return BuildSummary(self.project, task_execution_summaries)

    def execute_task(self, task_name):
        execution_plan = self.execution_manager.build_execution_plan(task_name)

        self.execution_manager.execute_execution_plan(execution_plan,
                                                      logger=self.logger,
                                                      project=self.project,
                                                      reactor=self)

    def execute_task_shortest_plan(self, task_name):
        execution_plan = self.execution_manager.build_shortest_execution_plan(task_name)

        self.execution_manager.execute_execution_plan(execution_plan,
                                                      logger=self.logger,
                                                      project=self.project,
                                                      reactor=self)

    def override_properties(self, property_overrides):
        for property_override in property_overrides:
            self.project.set_property(
                property_override, property_overrides[property_override])

    def log_project_properties(self):
        formatted = ""
        for key in sorted(self.project.properties):
            formatted += "\n%40s : %s" % (key, self.project.get_property(key))
        self.logger.debug("Project properties: %s", formatted)

    def import_plugin(self, plugin, version=None, plugin_module_name=None):
        self.logger.debug("Loading plugin '%s'%s", plugin, " version %s" % version if version else "")
        plugin_module = self.plugin_loader.load_plugin(self.project, plugin, version, plugin_module_name)
        self.collect_tasks_and_actions_and_initializers(plugin_module)

    def collect_tasks_and_actions_and_initializers(self, project_module):
        injected_task_dependencies = {}

        def normalize_candidate_name(candidate):
            return getattr(candidate, NAME_ATTRIBUTE, candidate.__name__ if hasattr(candidate, "__name__") else None)

        def add_task_dependency(names, depends_on, optional):
            for name in as_list(names):
                if not isinstance(name, basestring):
                    name = normalize_candidate_name(name)
                if name not in injected_task_dependencies:
                    injected_task_dependencies[name] = list()
                injected_task_dependencies[name].append(TaskDependency(depends_on, optional))

        for name in dir(project_module):
            candidate = getattr(project_module, name)
            name = normalize_candidate_name(candidate)

            if getattr(candidate, TASK_ATTRIBUTE, None):
                dependents = getattr(candidate, DEPENDENTS_ATTRIBUTE, None)

                if dependents:
                    dependents = list(as_list(dependents))
                    for d in dependents:
                        if isinstance(d, optional):
                            d = d()
                            add_task_dependency(d, name, True)
                        else:
                            add_task_dependency(d, name, False)

        for name in dir(project_module):
            candidate = getattr(project_module, name)
            name = normalize_candidate_name(candidate)

            description = getattr(candidate, DESCRIPTION_ATTRIBUTE, "")

            if getattr(candidate, TASK_ATTRIBUTE, None):
                dependencies = getattr(candidate, DEPENDS_ATTRIBUTE, None)

                task_dependencies = list()
                if dependencies:
                    dependencies = list(as_list(dependencies))
                    for d in dependencies:
                        if isinstance(d, optional):
                            d = as_list(d())
                            task_dependencies.extend([TaskDependency(item, True) for item in d])
                        else:
                            task_dependencies.append(TaskDependency(d))

                # Add injected
                if name in injected_task_dependencies:
                    task_dependencies.extend(injected_task_dependencies[name])
                    del injected_task_dependencies[name]

                self.logger.debug("Found task '%s' with dependencies %s", name, task_dependencies)
                self.execution_manager.register_task(
                    Task(name, candidate, task_dependencies, description))

            elif getattr(candidate, ACTION_ATTRIBUTE, None):
                before = getattr(candidate, BEFORE_ATTRIBUTE, None)
                after = getattr(candidate, AFTER_ATTRIBUTE, None)

                only_once = getattr(candidate, ONLY_ONCE_ATTRIBUTE, False)
                teardown = getattr(candidate, TEARDOWN_ATTRIBUTE, False)

                self.logger.debug("Found action %s", name)
                self.execution_manager.register_action(
                    Action(name, candidate, before, after, description, only_once, teardown))

            elif getattr(candidate, INITIALIZER_ATTRIBUTE, None):
                environments = getattr(candidate, ENVIRONMENTS_ATTRIBUTE, [])

                self.execution_manager.register_initializer(
                    Initializer(name, candidate, environments, description))

        self.execution_manager.register_late_task_dependencies(injected_task_dependencies)

    def apply_project_attributes(self):
        self.propagate_property("name")
        self.propagate_property("version")
        self.propagate_property("default_task")
        self.propagate_property("summary")
        self.propagate_property("home_page")
        self.propagate_property("description")
        self.propagate_property("authors")
        self.propagate_property("license")
        self.propagate_property("url")
        self.propagate_property("explicit_namespaces")
        self.propagate_property("requires_python")
        self.propagate_property("obsoletes")

    def propagate_property(self, property):
        if hasattr(self.project_module, property):
            value = getattr(self.project_module, property)
            setattr(self.project, property, value)

    def _prepare_tasks(self, tasks):
        if not len(tasks):
            if self.project.default_task:
                tasks += as_list(self.project.default_task)
            else:
                raise PyBuilderException("No default task given.")
        else:
            new_tasks = [task for task in tasks if task[0] not in ("+", "^") or task in ("+", "^")]
            append_tasks = [task[1:] for task in tasks if task[0] == "+" and task != "+"]
            remove_tasks = [task[1:] for task in tasks if task[0] == "^" and task != "^"]

            if len(new_tasks):
                del tasks[:]
                tasks.extend(new_tasks)
                tasks.extend(append_tasks)
                for task in remove_tasks:
                    try:
                        tasks.remove(task)
                    except ValueError:
                        pass
            else:
                del tasks[:]
                if self.project.default_task:
                    tasks += as_list(self.project.default_task)
                tasks += append_tasks
                for task in remove_tasks:
                    try:
                        tasks.remove(task)
                    except ValueError:
                        pass

        return tasks

    @staticmethod
    def load_project_module(project_descriptor):
        try:
            return imp.load_source("build", project_descriptor)
        except ImportError as e:
            raise PyBuilderException(
                "Error importing project descriptor %s: %s" % (project_descriptor, e))

    @staticmethod
    def verify_project_directory(project_directory, project_descriptor):
        project_directory = os.path.abspath(project_directory)

        if not os.path.exists(project_directory):
            raise PyBuilderException(
                "Project directory does not exist: %s", project_directory)

        if not os.path.isdir(project_directory):
            raise PyBuilderException(
                "Project directory is not a directory: %s", project_directory)

        project_descriptor_full_path = os.path.join(
            project_directory, project_descriptor)

        if not os.path.exists(project_descriptor_full_path):
            raise PyBuilderException(
                "Project directory does not contain descriptor file: %s",
                project_descriptor_full_path)

        if not os.path.isfile(project_descriptor_full_path):
            raise PyBuilderException(
                "Project descriptor is not a file: %s", project_descriptor_full_path)

        return project_directory, project_descriptor_full_path
