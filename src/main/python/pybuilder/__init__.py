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

from pybuilder.errors import BuildFailedException

__version__ = "${dist_version}"


def bootstrap():
    import sys
    import inspect

    try:
        current_frame = inspect.currentframe()
        previous_frame = current_frame.f_back
        name_of_previous_frame = previous_frame.f_globals['__name__']
        if name_of_previous_frame == '__main__':
            import pybuilder.cli

            sys.exit(pybuilder.cli.main(*sys.argv[1:]))
    except BuildFailedException:
        sys.exit(1)
