#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2019 PyBuilder Team
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

from pybuilder._vendor import tailer, pkg_resources
from pybuilder._vendor.pkg_resources._vendor import packaging
from pybuilder._vendor.pkg_resources._vendor.packaging import specifiers, version, utils

packaging.specifiers = specifiers
packaging.version = version
packaging.utils = utils

__all__ = ["tailer", "pkg_resources", "packaging"]
