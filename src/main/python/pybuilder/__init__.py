#  This file is part of PyBuilder
#
#  Copyright 2011-2014 PyBuilder Team
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

__version__ = "${version}"


def bootstrap():
    import inspect
    try:
        _, filename, _, _, _, _ = inspect.getouterframes(inspect.currentframe())[1]
        if filename == 'build.py':  # a relative path means we ran build.py directly
            import pybuilder.cli
            import sys
            sys.exit(pybuilder.cli.main(*sys.argv[1:]))

    except:
        pass
