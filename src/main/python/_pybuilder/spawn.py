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
import os
import sys

if sys.version_info[0] == 2:
    def _bootstrap(data):
        from multiprocessing.process import current_process, AuthenticationString
        current_process()._authkey = AuthenticationString(data["authkey"])

        if 'main_path' in data:
            # XXX (ncoghlan): The following code makes several bogus
            # assumptions regarding the relationship between __file__
            # and a module's real name. See PEP 302 and issue #10845
            # The problem is resolved properly in Python 3.4+, as
            # described in issue #19946

            main_path = data['main_path']
            main_name = os.path.splitext(os.path.basename(main_path))[0]
            if main_name == '__init__':
                main_name = os.path.basename(os.path.dirname(main_path))

            if main_name == '__main__':
                # For directory and zipfile execution, we assume an implicit
                # "if __name__ == '__main__':" around the module, and don't
                # rerun the main module code in spawned processes
                main_module = sys.modules['__main__']
                main_module.__file__ = main_path
            elif main_name != 'ipython':
                # Main modules not actually called __main__.py may
                # contain additional code that should still be executed
                import imp

                if main_path is None:
                    dirs = None
                elif os.path.basename(main_path).startswith('__init__.py'):
                    dirs = [os.path.dirname(os.path.dirname(main_path))]
                else:
                    dirs = [os.path.dirname(main_path)]

                assert main_name not in sys.modules, main_name
                file, path_name, etc = imp.find_module(main_name, dirs)
                try:
                    # We would like to do "imp.load_module('__main__', ...)"
                    # here.  However, that would cause 'if __name__ ==
                    # "__main__"' clauses to be executed.
                    main_module = imp.load_module(
                        '__parents_main__', file, path_name, etc
                    )
                finally:
                    if file:
                        file.close()

                sys.modules['__main__'] = main_module
                main_module.__name__ = '__main__'

                # Try to make the potentially picklable objects in
                # sys.modules['__main__'] realize they are in the main
                # module -- somewhat ugly.
                for obj in main_module.__dict__.values():
                    try:
                        if obj.__module__ == '__parents_main__':
                            obj.__module__ = '__main__'
                    except Exception:
                        pass

else:
    def _bootstrap(data):
        from multiprocessing.process import current_process, AuthenticationString
        from multiprocessing.spawn import (_fixup_main_from_name,
                                           _fixup_main_from_path)
        current_process().authkey = AuthenticationString(data["authkey"])

        if "init_main_from_name" in data:
            _fixup_main_from_name(data["init_main_from_name"])
        elif "init_main_from_path" in data:
            _fixup_main_from_path(data["init_main_from_path"])


def spawn_main():
    import sys
    import pickle
    import os
    from contextlib import closing

    devnull_f = open(os.devnull, "r")
    stdin_f = os.fdopen(0, "rb")  # will be closed automatically
    unpickler = pickle.Unpickler(stdin_f)
    _bootstrap(unpickler.load())
    with closing(unpickler.load()):
        try:
            data = unpickler.load()
        finally:
            os.dup2(devnull_f.fileno(), 0)
            sys.__stdin__ = os.fdopen(0, "r")
            sys.stdin = sys.__stdin__

        modules = sys.modules
        modules.pop("pickle", None)
        modules.pop("_pickle", None)
        for name in list(modules):
            if name.startswith("multiprocessing"):
                del modules[name]

        # This is a shim main
        data._main()
