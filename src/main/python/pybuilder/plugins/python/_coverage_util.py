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
from os.path import relpath, join as jp, exists, normcase as nc

if sys.platform in {"win32", "cygwin", "msys"}:
    from fnmatch import fnmatch
else:
    from fnmatch import fnmatchcase as fnmatch

files_abs_file = None


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
        if path in processed_paths:
            continue
        processed_paths.add(path)

        normalized_paths.append(nc(path))

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
