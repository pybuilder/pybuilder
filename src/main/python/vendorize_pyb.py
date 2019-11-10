#!/usr/bin/env python3
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

from glob import glob
from os import makedirs, environ, chdir, unlink
from os.path import dirname, realpath, join, isdir
from shutil import rmtree
from subprocess import check_call as call

CLEANUP_GLOBS = ["bin", "setuptools*", "*.dist-info", "easy_install.py"]


def vendorize():
    script_dir = realpath(dirname(__file__))
    vendor_dir = join(script_dir, "pybuilder/_vendor")
    chdir(script_dir)
    call(["pip", "install", "-U", "vendorize"], env=environ)
    rmtree(vendor_dir, ignore_errors=True)
    makedirs(vendor_dir, exist_ok=True)
    call("python-vendorize")

    for g in CLEANUP_GLOBS:
        for p in glob(join(vendor_dir, g)):
            if isdir(p):
                rmtree(p)
            else:
                unlink(p)

#     patch_billiard(vendor_dir)
#
#
# def patch_file(path, old, new):
#     with open(path, "rt") as f:
#         txt = f.read()
#
#     with open(path, "wt") as f:
#         patched_txt = txt.replace(old, new)
#         f.write(patched_txt)
#
#
# def patch_billiard(vendor_dir):
#     patch_file(join(vendor_dir, "billiard", "semaphore_tracker.py"),
#                'from billiard.semaphore_tracker import main;',
#                'from pybuilder._vendor.billiard.semaphore_tracker import main;')
#
#     patch_file(join(vendor_dir, "billiard", "spawn.py"),
#                'from billiard.spawn import spawn_main;',
#                'from pybuilder._vendor.billiard.spawn import spawn_main;')


if __name__ == "__main__":
    vendorize()
