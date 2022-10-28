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
import sys
from itertools import chain
from os import sep, unlink, walk
from os.path import exists, relpath, isdir, splitext, basename, dirname
from shutil import rmtree

from pybuilder.core import task, init, use_plugin, depends, Dependency
from pybuilder.python_utils import iglob
from pybuilder.utils import as_list, makedirs, jp, np

__author__ = "Arcadiy Ivanov"

_RE_FROM_IMPORT = re.compile(r"from\s+(\S+)\s+import\s+")
_RE_DECODE_PY = re.compile(rb'^[ \t\f]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)')

use_plugin("python.core")


@init
def initialize_vendorize_plugin(project):
    project.set_property_if_unset("vendorize_packages", [])
    project.set_property_if_unset("vendorize_target_dir", "$dir_source_main_python/_vendor")
    project.set_property_if_unset("vendorize_clean_target_dir", True)
    project.set_property_if_unset("vendorize_cleanup_globs", [])
    project.set_property_if_unset("vendorize_preserve_metadata", [])
    project.set_property_if_unset("vendorize_collect_licenses", True)
    project.set_property_if_unset("vendorize_licenses", "$vendorize_target_dir/LICENSES")


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
    _vendorize(target_dir, logger)

    if project.get_property("vendorize_collect_licenses"):
        licenses_content = ""
        for p in _list_metadata_dirs(target_dir):
            package_name, _ = splitext(basename(p))
            lic_file = None
            for f in ("LICENSE", "LICENSE.txt"):
                f = jp(p, f)
                if exists(f):
                    lic_file = f
                    break

            if not lic_file:
                logger.warn("No license file found in package %r", package_name)
                continue

            with open(lic_file, "rt") as f:
                licenses_content += "%s\n==========\n%s\n\n" % (package_name, f.read())

            logger.debug("Collected license file for package %r", package_name)

        with open(project.expand_path("$vendorize_licenses"), "wt") as f:
            f.write(licenses_content)

    def delete(p):
        if isdir(p):
            rmtree(p)
        else:
            unlink(p)

    # Cleanup globs
    for g in project.get_property("vendorize_cleanup_globs"):
        for p in iglob(jp(target_dir, g), recursive=True):
            delete(p)

    # Cleanup metadata exclusions
    preserve_metadata = []
    for g in project.get_property("vendorize_preserve_metadata"):
        for p in iglob(jp(target_dir, g), recursive=True):
            preserve_metadata.append(p)

    # Cleanup metadata
    for p in _list_metadata_dirs(target_dir):
        if p not in preserve_metadata:
            if isdir(p):
                rmtree(p)
            else:
                unlink(p)
        else:
            logger.debug("Preserving metadata %s", p)

    # Populate names after cleanup
    cleaned_up_packages = list(chain((basename(dirname(f)) for f in iglob(jp(target_dir, "*", "__init__.py"))),
                                     (basename(f)[:-3] for f in iglob(jp(target_dir, "*.py")))))
    with open(jp(target_dir, "__init__.py"), "wt") as init_py:
        init_py.write("__names__ = %r\n" % sorted(cleaned_up_packages))


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
        pkg_parts[-1] = ""
    if pkg_parts and pkg_parts[-1].endswith(".py"):
        pkg_parts[-1] = pkg_parts[-1][:-3]
    return pkg_parts


if sys.version_info[:2] < (3, 8):
    class NodeVisitor(object):
        def __init__(self):
            self._count = 0
            self._q = []
            self.source_lines = None

        def _visit(self, node):
            if hasattr(node, "lineno") and hasattr(node, "col_offset"):
                self._q.append(node)

            for field, value in ast.iter_fields(node):
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, ast.AST):
                            self._visit(item)
                elif isinstance(value, ast.AST):
                    self._visit(value)

        def visit(self, node):
            """Visit a node."""
            self._visit(node)

            q = self._q
            len_q = len(self._q)
            sl = self.source_lines

            for idx, node in enumerate(q):
                method = 'visit_' + node.__class__.__name__
                visitor = getattr(self, method, None)
                if visitor:
                    next_idx = idx + 1
                    if next_idx < len_q:
                        next_node = q[next_idx]
                        if node.lineno == next_node.lineno:
                            node.end_lineno = next_node.lineno
                            node.end_col_offset = next_node.col_offset - 1
                        else:
                            node.end_lineno = next_node.lineno - 1
                            node.end_col_offset = sl[node.end_lineno] - sl[node.end_lineno - 1]
                    else:
                        node.end_lineno = len(sl) - 1
                        node.end_col_offset = sl[node.end_lineno] - sl[node.end_lineno - 1]

                    visitor(node)
else:
    NodeVisitor = ast.NodeVisitor


class ImportTransformer(NodeVisitor):
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

    def visit_ImportFrom(self, node):
        if not node.level:
            module = node.module.split(".")
            for p in self.vendorized_packages:
                if module[0] == p:
                    import_changes = _relpkg_from(self.pkg_parts, module)
                    import_stmt, offset_start, offset_end = self.extract_source(node)

                    m = _RE_FROM_IMPORT.match(import_stmt)

                    ts = self.transformed_source
                    ts_prefix = ts[:offset_start + m.start(1) + self.offset]
                    ts_postfix = ts[offset_start + self.offset + m.end(1):]
                    inject = import_changes
                    self.transformed_source = ts_prefix + inject + ts_postfix
                    self.offset += len(inject) - len(m.group(1))
                    break

    def extract_source(self, node):
        start_off, end_off = _extract_source(self.source_lines, node)
        return self.source[start_off:end_off], start_off, end_off


def _vendorize(vendorized_path, logger):
    vendorized_packages = _list_top_level_packages(vendorized_path)
    for root, dirs, files in walk(vendorized_path):
        for py_path in files:
            if not py_path.endswith(".py"):
                continue

            py_path = np(jp(root, py_path))
            with open(py_path, "rb") as source_file:
                source_b = source_file.read()
            source_encoding, source = _decode_py(source_b)

            parsed_ast = ast.parse(source, filename=py_path)
            it = ImportTransformer(py_path, source, vendorized_path, vendorized_packages, [])
            it.visit(parsed_ast)

            if source != it.transformed_source:
                logger.debug("Vendorized %r", py_path)
                with open(py_path, "wt", encoding=source_encoding) as source_file:
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


def _decode_py(source_b):
    encoding = "utf-8"
    if source_b.startswith(b'\xef\xbb\xbf'):
        encoding = "utf-8"
    else:
        source_b_lines = source_b.splitlines()
        for idx, line in enumerate(source_b_lines):
            if idx > 1:
                break
            match = _RE_DECODE_PY.match(line)
            if match:
                encoding = match.group(1).decode("utf-8")
                break

    return encoding, source_b.decode(encoding, errors='strict')
