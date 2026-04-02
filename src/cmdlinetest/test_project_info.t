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

Find the project root (parent of target/dist):

  $ PROJECT_ROOT="$(cd "$(dirname "$(which pyb)")/../../../.."; pwd)"

Project info outputs valid JSON to stdout:

  $ pyb -D "$PROJECT_ROOT" -i 2>/dev/null | python -c "import json, sys; d = json.load(sys.stdin); print(d['project']['name'])"
  pybuilder

Project info JSON contains expected top-level keys:

  $ pyb -D "$PROJECT_ROOT" -i 2>/dev/null | python -c "import json, sys; d = json.load(sys.stdin); keys = sorted(d.keys()); print(' '.join(keys))"
  dependencies environments files_to_install manifest_included_files package_data plugins project properties pybuilder_version tasks

Project info is mutually exclusive with list-tasks:

  $ pyb -i -t 2>&1 | head -1
  Usage error: .* mutually exclusive.* (re)
