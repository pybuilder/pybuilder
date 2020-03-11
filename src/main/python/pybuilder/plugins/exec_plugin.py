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

import sys
from subprocess import PIPE, Popen

from pybuilder.core import task, use_plugin
from pybuilder.errors import BuildFailedException

use_plugin("core")


@task
def run_unit_tests(project, logger):
    run_command('run_unit_tests', project, logger)


@task
def run_integration_tests(project, logger):
    run_command('run_integration_tests', project, logger)


@task
def analyze(project, logger):
    run_command('analyze', project, logger)


@task
def package(project, logger):
    run_command('package', project, logger)


@task
def publish(project, logger):
    run_command('publish', project, logger)


def _write_command_report(project, stdout, stderr, command_line, phase, process_return_code):
    project.write_report('exec_%s' % phase, stdout)
    project.write_report('exec_%s.err' % phase, stderr)


def _log_quoted_output(logger, output_type, output, phase):
    separator = '-' * 5
    logger.info('{0} verbatim {1} output of {2} {0}'.format(separator, output_type, phase))
    for line in output.split('\n'):
        logger.info(line)
    logger.info('{0} end of verbatim {1} output {0}'.format(separator, output_type))


def run_command(phase, project, logger):
    command_line = project.get_property('%s_command' % phase)

    if not command_line:
        return

    process_handle = Popen(command_line, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = process_handle.communicate()
    stdout, stderr = stdout.decode(sys.stdout.encoding or 'utf-8'), stderr.decode(sys.stderr.encoding or 'utf-8')
    process_return_code = process_handle.returncode

    _write_command_report(project,
                          stdout,
                          stderr,
                          command_line,
                          phase,
                          process_return_code)

    if project.get_property('%s_propagate_stdout' % phase) and stdout:
        _log_quoted_output(logger, '', stdout, phase)

    if project.get_property('%s_propagate_stderr' % phase) and stderr:
        _log_quoted_output(logger, 'error', stderr, phase)

    if process_return_code != 0:
        raise BuildFailedException(
            'exec plugin command {0} for {1} exited with nonzero code {2}'.format(command_line,
                                                                                  phase,
                                                                                  process_return_code))
