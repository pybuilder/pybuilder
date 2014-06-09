"""#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
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

from fnmatch import filter
from os import walk
from os.path import join

EXPECTED_LICENSE = __doc__

affected_files = 0


def check_file(file_name):

    with open(file_name, 'r') as source_file:
        line_number = 0
        for line in EXPECTED_LICENSE.split('\n'):
            line_number += 1
            source_line = source_file.readline()[:-1]
            if line != source_line:
                prefix = file_name + ":" + str(line_number) + " "
                print(prefix + source_line)
                print(" " * len(prefix) + line)
                return True
    return False


def find_matching_files(source_directory):
    matching_files = []
    for root, directory_names, file_names in walk(source_directory):
        for filename in filter(file_names, '*.py'):
            path = join(root, filename)
            matching_files.append(path)

    return matching_files


def search_in_directory(source_directory):
    global affected_files

    matching_files = find_matching_files(source_directory)

    for file_name in matching_files:
        found_something = check_file(file_name)

        if found_something:
            affected_files += 1


def main():
    global affected_files

    source_directory = join('src', 'main', 'python')
    search_in_directory(source_directory)

    test_directory = join('src', 'unittest', 'python')
    search_in_directory(test_directory)

    if affected_files > 0:
        print("%d python files contain strange licenses." % affected_files)
        exit(1)


if __name__ == '__main__':
    main()
