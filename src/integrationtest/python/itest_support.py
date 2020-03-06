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

from base_itest_support import BaseIntegrationTestSupport
from pybuilder.cli import StdOutLogger
from pybuilder.core import Logger
from pybuilder.execution import ExecutionManager
from pybuilder.reactor import Reactor


class IntegrationTestSupport(BaseIntegrationTestSupport):
    def prepare_reactor(self):
        logger = StdOutLogger(level=Logger.DEBUG)
        execution_manager = ExecutionManager(logger)
        reactor = Reactor(logger, execution_manager)
        reactor.prepare_build(project_directory=self.tmp_directory)
        return reactor
