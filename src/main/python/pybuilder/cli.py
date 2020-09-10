#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2020 PyBuilder Team
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
    The PyBuilder cli module.
    Contains the PyBuilder command-line entrypoint.
"""

import datetime
import optparse
import re
import sys
import traceback
from os.path import sep, normcase as nc

from pybuilder import __version__
from pybuilder import extern
from pybuilder.core import Logger
from pybuilder.errors import PyBuilderException
from pybuilder.execution import ExecutionManager
from pybuilder.python_utils import IS_WIN
from pybuilder.reactor import Reactor
from pybuilder.scaffolding import start_project, update_project
from pybuilder.terminal import (BOLD, BROWN, RED, GREEN, bold, styled_text,
                                fg, italic, print_text, print_text_line,
                                print_error, print_error_line, draw_line)
from pybuilder.utils import format_timestamp, get_dist_version_string

PROPERTY_OVERRIDE_PATTERN = re.compile(r'^[a-zA-Z0-9_]+=.*')
_extern = extern


class CommandLineUsageException(PyBuilderException):
    def __init__(self, usage, message):
        super(CommandLineUsageException, self).__init__(message)
        self.usage = usage


class StdOutLogger(Logger):
    def _level_to_string(self, level):
        if Logger.DEBUG == level:
            return "[DEBUG]"
        if Logger.INFO == level:
            return "[INFO] "
        if Logger.WARN == level:
            return "[WARN] "
        return "[ERROR]"

    def _do_log(self, level, message, *arguments):
        formatted_message = self._format_message(message, *arguments)
        log_level = self._level_to_string(level)
        print_text_line("{0} {1}".format(log_level, formatted_message))


class ColoredStdOutLogger(StdOutLogger):
    def _level_to_string(self, level):
        if Logger.DEBUG == level:
            return italic("[DEBUG]")
        if Logger.INFO == level:
            return bold("[INFO] ")
        if Logger.WARN == level:
            return styled_text("[WARN] ", BOLD, fg(BROWN))
        return styled_text("[ERROR]", BOLD, fg(RED))


def parse_options(args):
    parser = optparse.OptionParser(usage="%prog [options] [+|^]task1 [[[+|^]task2] ...]",
                                   version="%prog " + __version__)

    def error(msg):
        raise CommandLineUsageException(
            parser.get_usage() + parser.format_option_help(), msg)

    parser.error = error

    list_tasks_option = parser.add_option("-t", "--list-tasks",
                                          action="store_true",
                                          dest="list_tasks",
                                          default=False,
                                          help="List all tasks that can be run in the current build configuration")

    list_plan_tasks_option = parser.add_option("-T", "--list-plan-tasks",
                                               action="store_true",
                                               dest="list_plan_tasks",
                                               default=False,
                                               help="List tasks that will be run with current execution plan")

    start_project_option = parser.add_option("--start-project",
                                             action="store_true",
                                             dest="start_project",
                                             default=False,
                                             help="Initialize build descriptors and Python project structure")

    update_project_option = parser.add_option("--update-project",
                                              action="store_true",
                                              dest="update_project",
                                              default=False,
                                              help="Update build descriptors and Python project structure")

    project_group = optparse.OptionGroup(
        parser, "Project Options", "Customizes the project to build.")

    project_group.add_option("-D", "--project-directory",
                             dest="project_directory",
                             help="Root directory to execute in",
                             metavar="<project directory>",
                             default=".")

    project_group.add_option("-O", "--offline",
                             dest="offline",
                             help="Attempt to execute the build without network connectivity (may cause build failure)",
                             default=False,
                             action="store_true")

    project_group.add_option("-E", "--environment",
                             dest="environments",
                             help="Activate the given environment for this build. Can be used multiple times",
                             metavar="<environment>",
                             action="append",
                             default=[])

    project_group.add_option("-P",
                             action="append",
                             dest="property_overrides",
                             default=[],
                             metavar="<property>=<value>",
                             help="Set/ override a property value")

    project_group.add_option("-x", "--exclude",
                             action="append",
                             dest="exclude_optional_tasks",
                             default=[],
                             metavar="<task>",
                             help="Exclude optional task dependencies")

    project_group.add_option("-o", "--exclude-all-optional",
                             action="store_true",
                             dest="exclude_all_optional",
                             default=False,
                             help="Exclude all optional task dependencies")

    project_group.add_option("--force-exclude",
                             action="append",
                             dest="exclude_tasks",
                             default=[],
                             metavar="<task>",
                             help="Exclude any task dependencies "
                                  "(dangerous, may break the build in unexpected ways)")

    project_group.add_option("--reset-plugins",
                             action="store_true",
                             dest="reset_plugins",
                             default=False,
                             help="Reset plugins directory prior to running the build")

    project_group.add_option("--no-venvs",
                             action="store_true",
                             dest="no_venvs",
                             default=False,
                             help="Disables the use of Python Virtual Environments")

    parser.add_option_group(project_group)

    output_group = optparse.OptionGroup(
        parser, "Output Options", "Modifies the messages printed during a build.")

    output_group.add_option("-X", "--debug",
                            action="store_true",
                            dest="debug",
                            default=False,
                            help="Print debug messages")

    output_group.add_option("-v", "--verbose",
                            action="store_true",
                            dest="verbose",
                            default=False,
                            help="Enable verbose output")

    output_group.add_option("-q", "--quiet",
                            action="store_true",
                            dest="quiet",
                            default=False,
                            help="Quiet mode; print only warnings and errors")

    output_group.add_option("-Q", "--very-quiet",
                            action="store_true",
                            dest="very_quiet",
                            default=False,
                            help="Very quiet mode; print only errors")

    output_group.add_option("-c", "--color",
                            action="store_true",
                            dest="force_color",
                            default=False,
                            help="Force colored output")

    output_group.add_option("-C", "--no-color",
                            action="store_true",
                            dest="no_color",
                            default=False,
                            help="Disable colored output")

    parser.add_option_group(output_group)

    options, arguments = parser.parse_args(args=list(args))

    if options.list_tasks and options.list_plan_tasks:
        parser.error("%s and %s are mutually exclusive" % (list_tasks_option, list_plan_tasks_option))
    if options.start_project and options.update_project:
        parser.error("%s and %s are mutually exclusive" % (start_project_option, update_project_option))

    property_overrides = {}
    for pair in options.property_overrides:
        if not PROPERTY_OVERRIDE_PATTERN.match(pair):
            parser.error("%s is not a property definition." % pair)
        key, val = pair.split("=", 1)
        property_overrides[key] = val

    options.property_overrides = property_overrides

    if options.very_quiet:
        options.quiet = True

    return options, arguments


def init_reactor(logger):
    execution_manager = ExecutionManager(logger)
    reactor = Reactor(logger, execution_manager)
    return reactor


def should_colorize(options):
    return options.force_color or (sys.stdout.isatty() and not options.no_color)


def init_logger(options):
    threshold = Logger.INFO
    if options.debug:
        threshold = Logger.DEBUG
    elif options.quiet:
        threshold = Logger.WARN

    if not should_colorize(options):
        logger = StdOutLogger(threshold)
    else:
        if IS_WIN:
            import colorama
            colorama.init()
        logger = ColoredStdOutLogger(threshold)

    return logger


def print_build_summary(options, summary):
    print_text_line("Build Summary")
    print_text_line("%20s: %s" % ("Project", summary.project.name))
    print_text_line("%20s: %s%s" % ("Version", summary.project.version, get_dist_version_string(summary.project)))
    print_text_line("%20s: %s" % ("Base directory", summary.project.basedir))
    print_text_line("%20s: %s" %
                    ("Environments", ", ".join(options.environments)))

    task_summary = ""
    for task in summary.task_summaries:
        task_summary += " %s [%d ms]" % (task.task, task.execution_time)

    print_text_line("%20s:%s" % ("Tasks", task_summary))


def print_styled_text(text, options, *style_attributes):
    if should_colorize(options):
        add_trailing_nl = False
        if text[-1] == '\n':
            text = text[:-1]
            add_trailing_nl = True
        text = styled_text(text, *style_attributes)
        if add_trailing_nl:
            text += '\n'
    print_text(text)


def print_styled_text_line(text, options, *style_attributes):
    print_styled_text(text + "\n", options, *style_attributes)


def print_build_status(failure_message, options, successful):
    draw_line()
    if successful:
        print_styled_text_line("BUILD SUCCESSFUL", options, BOLD, fg(GREEN))
    else:
        print_styled_text_line(
            "BUILD FAILED - {0}".format(failure_message), options, BOLD, fg(RED))
    draw_line()


def print_elapsed_time_summary(start, end):
    time_needed = end - start
    millis = ((time_needed.days * 24 * 60 * 60) + time_needed.seconds) * 1000 + time_needed.microseconds / 1000
    print_text_line("Build finished at %s" % format_timestamp(end))
    print_text_line("Build took %d seconds (%d ms)" %
                    (time_needed.seconds, millis))


def print_summary(successful, summary, start, end, options, failure_message):
    print_build_status(failure_message, options, successful)

    if successful and summary:
        print_build_summary(options, summary)

    print_elapsed_time_summary(start, end)


def length_of_longest_string(list_of_strings):
    if len(list_of_strings) == 0:
        return 0

    result = 0
    for string in list_of_strings:
        length_of_string = len(string)
        if length_of_string > result:
            result = length_of_string

    return result


def task_description(task):
    return " ".join(task.description) or "<no description available>"


def print_task_list(tasks, quiet=False):
    if quiet:
        print_text_line("\n".join([task.name + ":" + task_description(task)
                                   for task in tasks]))
        return

    column_length = length_of_longest_string(
        list(map(lambda task: task.name, tasks)))
    column_length += 4

    for task in tasks:
        task_name = task.name.rjust(column_length)
        print_text_line("{0} - {1}".format(task_name, task_description(task)))

        if task.dependencies:
            whitespace = (column_length + 3) * " "
            depends_on_message = "depends on tasks: %s" % " ".join(
                [str(dependency) for dependency in task.dependencies])
            print_text_line(whitespace + depends_on_message)


def print_list_of_tasks(reactor, quiet=False):
    tasks = reactor.get_tasks()
    sorted_tasks = sorted(tasks)
    if not quiet:
        print_text_line('Tasks found for project "%s":' % reactor.project.name)
    print_task_list(sorted_tasks, quiet)


def print_plan_list_of_tasks(options, arguments, reactor, quiet=False):
    execution_plan = reactor.create_execution_plan(arguments, options.environments)
    if not quiet:
        print_text_line('Tasks that will be executed for project "%s":' % reactor.project.name)
    print_task_list(execution_plan, quiet)


def get_failure_message():
    exc_type, exc_obj, exc_tb = sys.exc_info()

    filename = None
    lineno = None

    while exc_tb.tb_next:
        exc_tb = exc_tb.tb_next

    frame = exc_tb.tb_frame
    if hasattr(frame, "f_code"):
        code = frame.f_code
        filename = code.co_filename
        lineno = exc_tb.tb_lineno

        filename = nc(filename)
        for path in sys.path:
            path = nc(path)
            if filename.startswith(path) and len(filename) > len(path) and filename[len(path)] == sep:
                filename = filename[len(path) + 1:]
                break

    return "%s%s%s" % ("%s: " % exc_type.__name__ if not isinstance(exc_obj, PyBuilderException) else "",
                       exc_obj,
                       " (%s:%d)" % (filename, lineno) if filename else "")


def main(*args):
    if not args:
        args = sys.argv[1:]
    try:
        options, arguments = parse_options(args)
    except CommandLineUsageException as e:
        print_error_line("Usage error: %s\n" % e)
        print_error(e.usage)
        return 1

    start = datetime.datetime.now()

    logger = init_logger(options)
    reactor = init_reactor(logger)

    if options.start_project:
        return start_project()

    if options.update_project:
        return update_project()

    if options.list_tasks or options.list_plan_tasks:
        try:
            reactor.prepare_build(property_overrides=options.property_overrides,
                                  project_directory=options.project_directory,
                                  exclude_optional_tasks=options.exclude_optional_tasks,
                                  exclude_tasks=options.exclude_tasks,
                                  exclude_all_optional=options.exclude_all_optional,
                                  offline=options.offline,
                                  no_venvs=options.no_venvs
                                  )
            if options.list_tasks:
                print_list_of_tasks(reactor, quiet=options.very_quiet)

            if options.list_plan_tasks:
                print_plan_list_of_tasks(options, arguments, reactor, quiet=options.very_quiet)
            return 0
        except PyBuilderException:
            print_build_status(get_failure_message(), options, successful=False)
            return 1

    if not options.very_quiet:
        print_styled_text_line(
            "PyBuilder version {0}".format(__version__), options, BOLD)
        print_text_line("Build started at %s" % format_timestamp(start))
        draw_line()

    successful = True
    failure_message = None
    summary = None

    try:
        try:
            reactor.prepare_build(property_overrides=options.property_overrides,
                                  project_directory=options.project_directory,
                                  exclude_optional_tasks=options.exclude_optional_tasks,
                                  exclude_tasks=options.exclude_tasks,
                                  exclude_all_optional=options.exclude_all_optional,
                                  reset_plugins=options.reset_plugins,
                                  offline=options.offline,
                                  no_venvs=options.no_venvs
                                  )

            if options.verbose or options.debug:
                logger.debug("Verbose output enabled.\n")
                reactor.project.set_property("verbose", True)

            summary = reactor.build(
                environments=options.environments, tasks=arguments)

        except KeyboardInterrupt:
            raise PyBuilderException("Build aborted")

    except (Exception, SystemExit):
        successful = False
        failure_message = get_failure_message()
        if options.debug:
            traceback.print_exc(file=sys.stderr)

    finally:
        end = datetime.datetime.now()
        if not options.very_quiet:
            print_summary(
                successful, summary, start, end, options, failure_message)

        if not successful:
            return 1

        return 0
