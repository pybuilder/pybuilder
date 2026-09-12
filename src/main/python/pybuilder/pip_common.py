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
from __future__ import annotations

import dataclasses
import re
import sys
import types
from collections.abc import Iterable
from importlib.metadata import PathDistribution

from packaging.markers import Marker, InvalidMarker, default_environment
from packaging.requirements import Requirement, InvalidRequirement
from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.utils import canonicalize_name
from packaging.version import Version, InvalidVersion

import importlib.metadata as meta

__all__ = ["SpecifierSet", "InvalidSpecifier"]

SpecifierSet = SpecifierSet
InvalidSpecifier = InvalidSpecifier
Version = Version
InvalidVersion = InvalidVersion
Requirement = Requirement
InvalidRequirement = InvalidRequirement
canonicalize_name = canonicalize_name
Marker = Marker
InvalidMarker = InvalidMarker
default_environment = default_environment


def normalize_markers(markers):
    """Convert a marker expression into its canonical form, so that expressions that differ only
    in whitespace or quoting compare equal. Returns unparseable input unchanged.
    """
    if not markers:
        return None
    try:
        return str(Marker(str(markers)))
    except InvalidMarker:
        return str(markers)


def markers_apply(markers, environment, extra=None):
    """Evaluate a marker expression against the given marker environment.

    `extra` binds the PEP 508 ``extra`` variable, which is how a dependency belonging to an extras
    group is told which group it is being evaluated for. An absent or unparseable marker applies
    unconditionally.
    """
    if not markers:
        return True
    try:
        marker = Marker(str(markers))
    except InvalidMarker:
        return True

    env = dict(environment)
    if extra is not None:
        env["extra"] = extra
    return marker.evaluate(env)


def exact_pin(specifier):
    """The single version a specifier pins to, or None when it constrains anything else."""
    if not specifier:
        return None
    try:
        specifier_set = SpecifierSet(specifier)
    except InvalidSpecifier:
        return None

    pins = [s.version for s in specifier_set if s.operator in ("==", "===") and "*" not in s.version]
    return pins[0] if len(pins) == 1 else None


def specifiers_conflict(left, right):
    """Whether two version specifiers on one distribution provably cannot be satisfied together.

    Only exact pins are decided here, which is exactly the case pip turns into an unattributable
    ResolutionImpossible. Overlapping ranges such as '>=1.0' and '>=2.0' intersect perfectly well,
    and are a normal way for an extra to tighten a base requirement.
    """
    for pinned, other in ((left, right), (right, left)):
        version = exact_pin(pinned)
        if version is None or not other:
            continue
        try:
            if not SpecifierSet(other).contains(version, prereleases=True):
                return True
        except (InvalidSpecifier, InvalidVersion):
            continue

    return False


def safe_extra(extra: str) -> str:
    """Convert an arbitrary string to a standard 'extra' name

    Any runs of non-alphanumeric characters are replaced with a single '_',
    and the result is always lowercased.
    """
    return re.sub('[^A-Za-z0-9.-]+', '_', extra).lower()


class ResolutionError(Exception):
    """Abstract base for dependency resolution errors"""

    def __repr__(self) -> str:
        return self.__class__.__name__ + repr(self.args)


class UnknownExtra(ResolutionError):
    """Distribution doesn't have an "extra feature" of the given name"""


@dataclasses.dataclass
class Distribution:
    project_name: str
    version: str
    location: str
    _path_dist: PathDistribution
    # Marker environment the distribution's own requirements are evaluated against. Defaults to the
    # interpreter running the build, which is wrong whenever the distribution is installed elsewhere.
    marker_env: dict | None = None

    @property
    def _dep_map(self):
        try:
            return self.__dep_map
        except AttributeError:
            self.__dep_map = self._compute_dependencies()
            return self.__dep_map

    def _compute_dependencies(self) -> dict[str | None, list[Requirement]]:
        """Recompute this distribution's dependencies."""
        self.__dep_map: dict[str | None, list[Requirement]] = {None: []}

        reqs: list[Requirement] = list(Requirement(req_str) for req_str in self._path_dist.requires or ())

        def reqs_for_extra(extra):
            environment = dict(self.marker_env) if self.marker_env else {}
            environment['extra'] = extra
            for req in reqs:
                if not req.marker or req.marker.evaluate(environment):
                    yield req

        common = types.MappingProxyType(dict.fromkeys(reqs_for_extra(None)))
        self.__dep_map[None].extend(common)

        for extra in self._path_dist.metadata.get_all('Provides-Extra') or []:
            s_extra = safe_extra(extra.strip())
            self.__dep_map[s_extra] = [
                r for r in reqs_for_extra(extra) if r not in common
            ]

        return self.__dep_map

    @property
    def extras(self) -> list[str]:
        """Names of the extras this distribution provides, normalized with `safe_extra`"""
        return [extra for extra in self._dep_map if extra is not None]

    def extra_requires(self, extra: str) -> list[Requirement]:
        """Requirements an extra adds on top of the unconditional ones"""
        try:
            return list(self._dep_map[safe_extra(extra)])
        except KeyError as e:
            raise UnknownExtra(f"{self} has no such extra feature {extra!r}") from e

    def requires(self, extras: Iterable[str] = ()) -> list[Requirement]:
        """List of Requirements needed for this distro if `extras` are used"""
        dm = self._dep_map
        deps: list[Requirement] = []
        deps.extend(dm.get(None, ()))
        for ext in extras:
            try:
                deps.extend(dm[safe_extra(ext)])
            except KeyError as e:
                raise UnknownExtra(f"{self} has no such extra feature {ext!r}") from e
        return deps


class WorkingSet:
    def __init__(self, paths=None, marker_env=None):
        self.paths = paths if paths is not None else sys.path
        self.marker_env = marker_env
        self._results = None

    def __iter__(self):
        if self._results is None:
            self.refresh()
        return iter(self._results)

    def refresh(self):
        results = []
        for dist in meta.Distribution.discover(path=self.paths):
            results.append(Distribution(dist.metadata.get("Name"),
                                        dist.version,
                                        dist._path.parent,
                                        dist,
                                        self.marker_env))
        results.sort(key=lambda x: x.project_name)
        self._results = results
        return results
