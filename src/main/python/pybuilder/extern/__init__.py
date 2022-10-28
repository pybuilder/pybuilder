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
from importlib import import_module
from importlib.abc import Loader

import pybuilder._vendor


class VendorImporter(Loader):
    """
    A PEP 302 meta path importer for finding optionally-vendored
    or otherwise naturally-installed packages from root_name.
    """

    def __init__(self, root_name, vendored_names, vendor_pkg):
        self.root_name = root_name
        self.vendored_names = set(vendored_names)
        self.vendor_pkg = vendor_pkg
        self._in_flight_imports = set()

    @property
    def search_path(self):
        """
        Search first the vendor package then as a natural package.
        """
        yield self.vendor_pkg + "."

    #        yield ""

    def find_module(self, fullname, path=None):
        """
        Return self when fullname starts with root_name and the
        target module is one vendored through this importer.
        """
        root, base, target = fullname.partition(self.root_name + ".")
        if root == fullname and not base and not target:
            root = None
            target = fullname
        if root:
            return
        if not any(map(target.startswith, self.vendored_names)):
            return
        return self

    def load_module(self, fullname):
        """
        Iterate over the search path to locate and load fullname.
        """
        root, base, target = fullname.partition(self.root_name + ".")
        if root == fullname and not base and not target:
            root = None
            target = fullname
        for prefix in self.search_path:
            extant = prefix + target
            if extant not in self._in_flight_imports:
                self._in_flight_imports.add(extant)
                try:
                    mod = import_module(extant)
                finally:
                    self._in_flight_imports.remove(extant)
            if extant in sys.modules:
                mod = sys.modules[extant]
                sys.modules[fullname] = mod
                return mod
        else:
            raise ImportError(
                "The '{target}' package is required; "
                "normally this is bundled with this package so if you get "
                "this warning, consult the packager of your "
                "distribution.".format(**locals())
            )

    def _find_distributions(self, context):
        context.path.insert(0, pybuilder._vendor.__file__[:-len("__init__.py") - 1])
        return []

    # https://github.com/pybuilder/pybuilder/issues/807
    if sys.version_info[:2] == (3, 8):
        def find_distributions(self, context):
            return iter(self._find_distributions(context))
    else:
        find_distributions = _find_distributions

    def install(self):
        """
        Install this importer into sys.meta_path if not already present.
        """
        if self not in sys.meta_path:
            sys.meta_path.insert(0, self)

        for pkg in self.vendored_names:
            for p in list(sys.modules):
                if p == pkg or p.startswith(pkg + "."):
                    sys.modules.pop(p, None)


# Don't run if we're actually in PDoc
# if not (sys.version_info[0] == 2 and basename(sys.argv[0]) == "pdoc"):
VendorImporter(__name__, pybuilder._vendor.__names__, pybuilder._vendor.__package__).install()
