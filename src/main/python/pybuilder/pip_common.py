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


import pkg_resources

from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.version import Version, InvalidVersion
from packaging.requirements import Requirement, InvalidRequirement
from packaging.utils import canonicalize_name

__all__ = ["SpecifierSet", "InvalidSpecifier"]

SpecifierSet = SpecifierSet
InvalidSpecifier = InvalidSpecifier
Version = Version
InvalidVersion = InvalidVersion
Requirement = Requirement
InvalidRequirement = InvalidRequirement
canonicalize_name = canonicalize_name

WorkingSet = pkg_resources.WorkingSet
