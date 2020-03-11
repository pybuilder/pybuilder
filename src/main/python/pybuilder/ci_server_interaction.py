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

from pybuilder.terminal import print_text
import os


def _is_running_on_teamcity(environment):
    return "TEAMCITY_VERSION" in environment


def test_proxy_for(project):
    running_coverage = project.get_property('__running_coverage')
    running_on_teamcity = _is_running_on_teamcity(os.environ) or project.get_property('teamcity_output')
    if running_on_teamcity and not running_coverage:
        return TeamCityTestProxy()
    else:
        return TestProxy()


def flush_text_line(text_line):
    print_text(text_line + '\n', flush=True)


class TestProxy(object):

    def __init__(self, test_name='not set'):
        self.test_name = test_name

    def and_test_name(self, test_name):
        self.test_name = test_name
        return self

    def test_starts(self):
        pass

    def test_finishes(self):
        pass

    def fails(self, reason):
        pass

    def __enter__(self, *args, **kwargs):
        self.test_starts()
        return self

    def __exit__(self, *args, **kwargs):
        self.test_finishes()


class TeamCityTestProxy(TestProxy):

    def test_starts(self):
        flush_text_line("##teamcity[testStarted name='{0}']".format(self.test_name))

    def test_finishes(self):
        flush_text_line("##teamcity[testFinished name='{0}']".format(self.test_name))

    def fails(self, reason):
        flush_text_line("##teamcity[testFailed name='{0}' message='See details' details='{1}']".format(
                        self.test_name,
                        reason
                        ))
