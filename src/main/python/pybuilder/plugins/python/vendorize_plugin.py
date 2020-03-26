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
    Package vendorizer plugin.
    - Unpacks specified packages into specified directory
    - Relativizes all imports of the top-level package names
"""

import ast
import re
from glob import iglob
from itertools import chain
from os import sep, unlink
from os.path import join as jp, exists, relpath, isdir
from shutil import rmtree

from pybuilder.core import task, init, use_plugin, depends, Dependency
from pybuilder.utils import as_list, makedirs

__author__ = "Arcadiy Ivanov"

RE_FROM_IMPORT = re.compile(r"from\s+(\S+)\s+import\s+")

use_plugin("python.core")


@init
def initialize_vendorize_plugin(project):
    project.set_property_if_unset("vendorize_packages", [])
    project.set_property_if_unset("vendorize_target_dir", "$dir_source_main_python/_vendor")
    project.set_property_if_unset("vendorize_clean_target_dir", True)
    project.set_property_if_unset("vendorize_cleanup_globs", [])


@task
@depends("prepare")
def vendorize(project, reactor, logger):
    target_dir = project.expand_path("$vendorize_target_dir")
    packages = [Dependency(p) for p in as_list(project.get_property("vendorize_packages"))]
    clean = project.get_property("vendorize_clean_target_dir")
    logfile = project.expand_path("$dir_logs", "vendorize.log")

    logger.info("Will vendorize packages %r into %r%s", packages, target_dir, " (cleaning)" if clean else "")

    if clean:
        rmtree(target_dir, ignore_errors=False)
    makedirs(target_dir, exist_ok=True)

    reactor.pybuilder_venv.install_dependencies(packages,
                                                install_log_path=logfile,
                                                package_type="vendorized",
                                                target_dir=target_dir,
                                                ignore_installed=True)

    # Vendorize
    _vendorize(target_dir)

    # Cleanup globs
    for g in project.get_property("vendorize_cleanup_globs"):
        for p in iglob(jp(target_dir, g)):
            if isdir(p):
                rmtree(p)
            else:
                unlink(p)

    # Populate names after cleanup
    cleaned_up_packages = _list_top_level_packages(target_dir)
    with open(jp(target_dir, "__init__.py"), "wt") as init_py:
        init_py.write("__names__ = %r\n" % sorted(cleaned_up_packages))

    # Cleanup metadata
    for p in _list_metadata_dirs(target_dir):
        if isdir(p):
            rmtree(p)
        else:
            unlink(p)


def _relpkg_import(pkg_parts):
    return "." * len(pkg_parts)


def _relpkg_from(pkg_parts, import_parts):
    i = 0
    for idx, pkg in enumerate(pkg_parts):
        if idx >= len(import_parts) or pkg != import_parts[idx]:
            break
        i += 1
    return "." * ((len(pkg_parts) - i) or 1) + ".".join(import_parts[i:])


def _path_to_package(path):
    pkg_parts = path.split(sep)
    if pkg_parts and pkg_parts[-1] == "__init__.py":
        del pkg_parts[-1]
    if pkg_parts and pkg_parts[-1].endswith(".py"):
        pkg_parts[-1] = pkg_parts[-1][:-3]
    return pkg_parts


class ImportTransformer(ast.NodeVisitor):
    def __init__(self, source_path, source, vendor_path, vendorized_packages, results):
        super(ImportTransformer, self).__init__()
        self.source_path = source_path
        self.source = source
        self.source_lines = _source_line_offsets(source)
        self.package_path = relpath(source_path, vendor_path)
        self.vendorized_packages = vendorized_packages
        self.pkg_parts = _path_to_package(self.package_path)
        self.results = results

        self.transformed_source = source
        self.offset = 0

    def visit_Import(self, node):
        modify_stmt = False
        for alias in node.names:
            name = alias.name.split(".")
            for p in self.vendorized_packages:
                if name[0] == p:
                    modify_stmt = True
                    break
            if modify_stmt:
                break

        if modify_stmt:
            import_changes = _relpkg_import(self.pkg_parts)
            import_stmt, offset_start, offset_end = self.extract_source(node)

            ts = self.transformed_source
            ts_prefix = ts[:offset_start + self.offset]
            ts_postfix = ts[offset_end + self.offset:]

            inject = "from " + import_changes + " "
            self.offset += len(inject)

            for alias in node.names:
                name = alias.name.split(".")
                if len(name) > 1:
                    import_stmt = import_stmt.replace(alias.name, name[0])
                    self.offset += -len(alias.name) + len(name[0])

            self.transformed_source = ts_prefix + inject + import_stmt + ts_postfix
        return node

    def visit_ImportFrom(self, node):
        if not node.level:
            module = node.module.split(".")
            for p in self.vendorized_packages:
                if module[0] == p:
                    import_changes = _relpkg_from(self.pkg_parts, module)
                    import_stmt, offset_start, offset_end = self.extract_source(node)

                    m = RE_FROM_IMPORT.match(import_stmt)

                    ts = self.transformed_source
                    ts_prefix = ts[:offset_start + m.start(1) + self.offset]
                    ts_postfix = ts[offset_start + self.offset + m.end(1):]
                    inject = import_changes
                    self.transformed_source = ts_prefix + inject + ts_postfix
                    self.offset += len(inject) - len(m[1])
                    break
        return node

    def extract_source(self, node):
        start_off, end_off = _extract_source(self.source_lines, node)
        return self.source[start_off:end_off], start_off, end_off


def _vendorize(vendorized_path):
    vendorized_packages = _list_top_level_packages(vendorized_path)
    for py_path in chain(iglob(jp(vendorized_path, "*.py")),
                         iglob(jp(vendorized_path, "**", "*.py"), recursive=True),
                         ):
        with open(py_path, "rt") as source_file:
            source = source_file.read()
        parsed_ast = ast.parse(source, filename=py_path)
        it = ImportTransformer(py_path, source, vendorized_path, vendorized_packages, [])
        it.visit(parsed_ast)
        with open(py_path, "wt") as source_file:
            source_file.write(it.transformed_source)

    return vendorized_packages


def _list_metadata_dirs(vendorized_path):
    return chain(iglob(jp(vendorized_path, "*.egg-info")), iglob(jp(vendorized_path, "*.dist-info")))


def _list_top_level_packages(vendorized_path):
    vendorized_packages = set()
    for name in _list_metadata_dirs(vendorized_path):
        top_level_path = jp(vendorized_path, name, "top_level.txt")
        if exists(top_level_path):
            with open(top_level_path) as f:
                for p in filter(None, map(lambda line: line.strip(), f)):
                    vendorized_packages.add(p)
    return vendorized_packages


def _source_line_offsets(source):
    idx = 0
    lines = [0]
    started_line = True
    while idx < len(source):
        c = source[idx]
        idx += 1
        started_line = False
        # Keep \r\n together
        if c == '\r' and idx < len(source) and source[idx] == '\n':
            idx += 1
        if c in '\r\n':
            lines.append(idx)
            started_line = True

    if not started_line:
        lines.append(idx)

    return lines


def _extract_source(source_lines, node):
    try:
        lineno = node.lineno - 1
        end_lineno = node.end_lineno - 1
        col_offset = node.col_offset
        end_col_offset = node.end_col_offset
    except AttributeError:
        return None

    start_line_offset = source_lines[lineno]
    end_line_offset = source_lines[end_lineno]

    return start_line_offset + col_offset, end_line_offset + end_col_offset
