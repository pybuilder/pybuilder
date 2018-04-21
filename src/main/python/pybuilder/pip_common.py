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

try:
    from pip.commands.show import search_packages_info
except ImportError:
    from pip._internal.commands.show import search_packages_info

try:
    # This is the path for pip 7.x and beyond
    from pip._vendor.pkg_resources import _initialize_master_working_set

    pip_working_set_init = _initialize_master_working_set
except ImportError:
    # This is the path for pip 6.x
    from imp import reload
    from pip._vendor import pkg_resources

    def pip_working_set_init():
        reload(pkg_resources)

SpecifierSet = SpecifierSet
InvalidSpecifier = InvalidSpecifier
Version = Version
InvalidVersion = InvalidVersion
search_packages_info = search_packages_info


def _pip_disallows_insecure_packages_by_default():
    import pip
    # (2014-01-01) BACKWARD INCOMPATIBLE pip no longer will scrape insecure external urls by default
    # nor will it install externally hosted files by default
    # Also pip v1.1 for example has no __version__
    return hasattr(pip, "__version__") and (pip.__version__ >= '1.5' or pip.__version__ >= '10.0')


def _pip_supports_constraints():
    import pip
    return hasattr(pip, "__version__") and (pip.__version__ >= '7.1' or pip.__version__ >= '10.0')


def _pip_version():
    import pip
    return getattr(pip, "__version__", None)


pip_version = _pip_version()
