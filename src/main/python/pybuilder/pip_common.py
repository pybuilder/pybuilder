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

from pip._vendor.packaging.specifiers import SpecifierSet, InvalidSpecifier
from pip._vendor.packaging.version import Version, InvalidVersion
from pip._vendor.pkg_resources import _initialize_master_working_set
from pip.commands.show import search_packages_info

pip_working_set_init = _initialize_master_working_set

SpecifierSet = SpecifierSet
InvalidSpecifier = InvalidSpecifier
Version = Version
InvalidVersion = InvalidVersion
search_packages_info = search_packages_info


def _pip_version():
    import pip
    return getattr(pip, "__version__", None)


pip_version = _pip_version()
