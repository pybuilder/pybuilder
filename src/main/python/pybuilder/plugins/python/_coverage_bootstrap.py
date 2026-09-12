#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2026 PyBuilder Team
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

"""Startup hook planted into the site directories of the VEnvs PyBuilder builds into.

This module is copied into a VEnv's site directory and run from a `.pth` (or, on
Python 3.15 and later, a PEP 829 `.start`) file of the same name, so it is imported
by every interpreter that starts from that VEnv. It does nothing at all unless the
covered task that spawned the process asked for subprocess measurement.

PyBuilder itself is not importable here, so everything this module needs is carried
in the environment. It stays a stub on purpose: the work belongs in `_coverage_util`,
which is where it can be tested.
"""

import os
import sys

CONFIG_ENV = "PYB_COVERAGE_PROCESS_CONFIG"
COVERAGE_CONFIG_ENV = "COVERAGE_PROCESS_CONFIG"


def prepare():
    """Makes this interpreter able to reach the entry point that starts measurement.

    `site` resolves a PEP 829 `.start` entry point with `pkgutil`, and reports any
    failure resolving it with `traceback`. It imports both lazily, and pip empties
    `sys.path` for the duration of the site processing its build isolation does, so
    there both imports fail - the second one while reporting the first - and the
    exception aborts interpreter startup outright. Having them in `sys.modules` is
    enough for `site` to get through it, and `.pth` import lines run before any entry
    point does, which is early enough to put them there.

    Nothing here may escape, for the same reason nothing in `start` may.
    """
    try:
        stdlib_dir = os.path.dirname(os.__file__)
        if stdlib_dir in sys.path:
            return None

        sys.path.append(stdlib_dir)
        try:
            import pkgutil  # noqa: F401 - `site` resolves entry points with it
            import traceback  # noqa: F401 - and reports a failure to resolve one with it
        finally:
            # `sys.path` has to be left exactly as it was found: pip takes what site
            # processing added to it as the set of paths to drop from the real one
            sys.path.remove(stdlib_dir)
    except BaseException:
        return None


def start():
    """Starts measuring this interpreter, if a covered task asked for it and we can.

    `site` cannot recover from a `.pth` that raises: it reports the failure by
    importing `traceback`, which is no better off than we are when the import system
    is what is unavailable, and the exception goes on to abort interpreter startup.
    Measurement is best effort, so nothing here may ever escape.
    """
    try:
        return _start()
    except BaseException:
        return None


def _start():
    # This runs at the start of every interpreter the VEnv ever runs, long after the
    # build that planted it is over, so the way out when there is nothing to measure
    # comes before anything `site` has not already imported for us.
    config = os.environ.get(CONFIG_ENV)
    if not config or not os.environ.get(COVERAGE_CONFIG_ENV):
        return None

    # Not every interpreter that gets here can import at all: pip empties `sys.path`
    # for the duration of the site processing that its build isolation does, so even
    # the standard library is out of reach until that is over.
    import ast

    config = ast.literal_eval(config)

    sys.path.insert(0, config["cov_util_dir"])
    try:
        from _coverage_util import start_subprocess_coverage
    except ImportError:
        return None
    finally:
        del sys.path[0]

    return start_subprocess_coverage(config)
