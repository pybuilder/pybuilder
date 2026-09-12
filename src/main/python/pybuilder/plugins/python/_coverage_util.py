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


import os
import sys
from os.path import relpath, join as jp, exists, normcase as nc, abspath as ap, dirname, isdir, realpath

if sys.platform in {"win32", "cygwin", "msys"}:
    from fnmatch import fnmatch
else:
    from fnmatch import fnmatchcase as fnmatch

files_abs_file = None

# The Coverage the startup bootstrap took responsibility for in this interpreter
adopted_coverage = None

# Coverage's own hand-off of the active configuration to a starting interpreter.
COVERAGE_PROCESS_CONFIG_ENV = "COVERAGE_PROCESS_CONFIG"

# Everything about the hand-off that Coverage does not know about: where to import
# Coverage from, and how to normalize what the subprocess collects.
PYB_COVERAGE_PROCESS_CONFIG_ENV = "PYB_COVERAGE_PROCESS_CONFIG"

BOOTSTRAP_MODULE_NAME = "pybuilder_coverage_bootstrap"
BOOTSTRAP_PTH_NAME = "pybuilder_coverage.pth"
BOOTSTRAP_PTH_CONTENT = "import %(mod)s; %(mod)s.start()\n" % {"mod": BOOTSTRAP_MODULE_NAME}

# From Python 3.15 the `.pth` prepares the interpreter and a PEP 829 entry point does
# the starting. The two deliberately do NOT share a basename: PEP 829 has a `.start`
# supersede the `import` line of the `.pth` it is named after, and that line is the
# only thing that runs early enough to prepare for the entry point.
BOOTSTRAP_PREPARE_PTH_CONTENT = "import %(mod)s; %(mod)s.prepare()\n" % {"mod": BOOTSTRAP_MODULE_NAME}
BOOTSTRAP_START_NAME = "pybuilder_coverage_entrypoint.start"
BOOTSTRAP_START_CONTENT = "%s:start\n" % BOOTSTRAP_MODULE_NAME

# PEP 829 entry points arrived in Python 3.15, and supersede `.pth` import lines,
# which stop being honored in 3.18
BOOTSTRAP_START_MIN_VERSION = (3, 15)

# Where this module and the bootstrap it plants live
MODULE_DIR = dirname(ap(__file__))


def canonical_path(path):
    """Spells `path` the way Coverage spells the files it measures.

    Coverage identifies a file by its `realpath`, which is not always how the build
    reached it: a macOS temp directory is reached through /var and measured as
    /private/var, and a Windows one through an 8.3 short name and measured expanded.
    Anything held up against what Coverage collected has to be spelled Coverage's way,
    or the same file looks like two.

    This has to keep agreeing with `patched_abs_file`, which is what produces the
    spelling of the data itself.
    """
    return nc(ap(realpath(path)))


def patched_abs_file(path):
    global files_abs_file
    return nc(files_abs_file(path))


def patch_coverage():
    from coverage import files
    from coverage import control

    if files.abs_file == patched_abs_file:
        return
    global files_abs_file
    files_abs_file = files.abs_file

    files.abs_file = patched_abs_file
    control.abs_file = patched_abs_file


def save_normalized_coverage(coverage, source_path, omit_patterns, paths=None):
    """This method is NOT a panacea but it's better than nothing
    It will produce bullshit relative path on occasion with complex loading plans
    or when entries are being removed from sys.path so they cannot be observed post-factum
    """
    paths = paths or sys.path
    normalized_paths = []

    processed_paths = set()
    for path in paths:
        # Canonical, because these are held up against what Coverage measured, and it
        # does not necessarily spell a path the way the build that loaded from it did
        path = canonical_path(path)
        if path in processed_paths:
            continue
        processed_paths.add(path)

        normalized_paths.append(path)

    def file_mapper(path):
        path = nc(path)
        best_candidate = None
        for p in normalized_paths:
            if path == p:
                return path

            if path.startswith(p):
                candidate = relpath(path, p)
                if not best_candidate or len(candidate) < len(best_candidate):
                    best_candidate = candidate

        if best_candidate:
            final_candidate = jp(source_path, best_candidate)
            if exists(final_candidate):
                return final_candidate
            return best_candidate
        else:
            return path

    collector = coverage._collector
    collector.file_mapper = file_mapper

    def clean_data(data):
        # Normalize keys/paths on Windows
        # Remove all data for files that is not in source_path
        # Remove all data in omit_patterns

        for k in list(data.keys()):
            delete_key = False
            new_k = collector.cached_mapped_file(k)
            if not new_k.startswith(source_path):
                delete_key = True
            else:
                for omit_pattern in omit_patterns:
                    if fnmatch(new_k, omit_pattern):
                        delete_key = True
                        break

            if delete_key:
                del data[k]
            else:
                v = data[k]
                del data[k]
                data[new_k] = v

    clean_data(collector.data)
    clean_data(collector.file_tracers)

    coverage.save()


def combine_subprocess_coverage(coverage, source_path):
    """Combines what the subprocesses of a covered task measured into `coverage`.

    Not every subprocess had anything of PyBuilder's in it to spell what it measured
    PyBuilder's way: under `--no-venvs` the only thing measuring one is Coverage's own
    startup hook, so `patch_coverage` never ran there and the data is spelled the way
    the file system spells it, where everything here is normcased. On Windows that is
    two strings for one file.

    An alias of the source path to itself reconciles them as the data is read: Coverage
    matches aliases case-insensitively, and canonicalizes what it rewrites through the
    patched `abs_file` - which is what produces the spelling used everywhere else.

    The alias is only in force for the reading. Left set, Coverage applies it a second
    time when a report asks for the data, onto a copy it keeps in memory and never
    writes - which is not the data this was combined into.
    """
    old_paths = coverage.config.paths
    coverage.config.paths = {"pybuilder_source_path": [source_path, source_path]}
    try:
        coverage.combine()
    finally:
        coverage.config.paths = old_paths


def coverage_parent_dir():
    """The directory Coverage can be imported from, wherever PyBuilder installed it."""
    import coverage as cov_module

    return nc(ap(jp(dirname(cov_module.__file__), "..")))


def subprocess_coverage_env(coverage, source_path, omit_patterns):
    """Returns the environment variables that make Python subprocesses measure themselves.

    A subprocess only starts measuring if something runs at its interpreter startup,
    and that startup hook needs to know what `coverage` alone cannot tell it: where
    Coverage can be imported from, since the VEnvs PyBuilder builds into do not have
    it installed, and how to map the collected paths back onto the sources.
    """
    config = {"cov_parent_dir": coverage_parent_dir(),
              "cov_util_dir": MODULE_DIR,
              "cov_source_path": source_path,
              "cov_omit_patterns": list(omit_patterns),
              }

    return {COVERAGE_PROCESS_CONFIG_ENV: coverage.config.serialize(),
            PYB_COVERAGE_PROCESS_CONFIG_ENV: repr(config),
            }


def subprocess_coverage_env_from_environ(environ=None):
    """Returns the subprocess coverage variables present in `environ`, if any.

    Used to pass the hand-off along to subprocesses that are given an environment
    built from scratch rather than an inherited one.
    """
    if environ is None:
        environ = os.environ

    return {name: environ[name] for name in (COVERAGE_PROCESS_CONFIG_ENV, PYB_COVERAGE_PROCESS_CONFIG_ENV)
            if name in environ}


def install_coverage_bootstrap(site_path, version):
    """Plants the startup hook that makes subprocesses started from `site_path` measure themselves.

    Before Python 3.15 the hook is an `import` line in a `.pth` file. From 3.15 the
    starting moves to a PEP 829 entry point, which is what `site` will still honor once
    it stops running `import` lines in 3.18, and the `import` line is left to prepare
    the interpreter for it.

    Returns whether the hook was planted.
    """
    from shutil import copyfile

    if not isdir(site_path):
        return False

    copyfile(jp(MODULE_DIR, "_coverage_bootstrap.py"), jp(site_path, BOOTSTRAP_MODULE_NAME + ".py"))

    has_entrypoints = tuple(version[:2]) >= BOOTSTRAP_START_MIN_VERSION

    with open(jp(site_path, BOOTSTRAP_PTH_NAME), "wt") as pth_file:
        pth_file.write(BOOTSTRAP_PREPARE_PTH_CONTENT if has_entrypoints else BOOTSTRAP_PTH_CONTENT)

    if has_entrypoints:
        with open(jp(site_path, BOOTSTRAP_START_NAME), "wt") as start_file:
            start_file.write(BOOTSTRAP_START_CONTENT)

    return True


def adopt_subprocess_coverage(source_path, omit_patterns):
    """Takes responsibility for a Coverage that a startup hook already began here.

    Coverage saves the raw paths on its own, which are only usable when the measured
    files happen to already sit under the source path. Adopting means taking over the
    save so it goes through normalization instead.

    Returns the Coverage that is measuring this interpreter with normalization
    arranged - whether this call arranged it or an earlier one did - and None when
    nothing has started measuring, in which case the caller has to start its own.
    """
    import atexit

    global adopted_coverage

    if adopted_coverage is not None:
        return adopted_coverage

    import coverage

    cov = getattr(coverage.process_startup, "coverage", None)
    if cov is None:
        return None

    adopted_coverage = cov
    cov._auto_save = False

    def save_on_exit():
        cov.stop()
        save_normalized_coverage(cov, source_path, omit_patterns)

    atexit.register(save_on_exit)

    return cov


def start_subprocess_coverage(config):
    """Starts Coverage in a subprocess spawned by a covered task.

    Called from the planted bootstrap at interpreter startup, which is early enough
    to measure imports and module-level code - the part that both the in-process
    tool and the command line shim necessarily miss.

    Returns the Coverage measuring this interpreter, or None when there is nothing
    to start.
    """
    if adopted_coverage is not None or not os.environ.get(COVERAGE_PROCESS_CONFIG_ENV):
        return None

    sys.path.insert(0, config["cov_parent_dir"])
    try:
        import coverage
    except ImportError:
        return None
    finally:
        del sys.path[0]

    patch_coverage()

    # Returns None when it has already run in this interpreter, which happens when a
    # site directory is visible twice, or when Coverage's own startup hook is
    # installed alongside ours and sorted ahead of it. Either way it leaves what it
    # started behind for us to adopt.
    coverage.process_startup()

    return adopt_subprocess_coverage(config["cov_source_path"], config["cov_omit_patterns"])
