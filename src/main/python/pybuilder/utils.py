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

"""
    The PyBuilder utils module.
    Provides generic utilities that can be used by plugins.
"""

import collections
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import traceback
from multiprocessing import Process
from subprocess import Popen, PIPE

try:
    from multiprocessing import SimpleQueue
except ImportError:
    from multiprocessing.queues import SimpleQueue

try:
    basestring = basestring
except NameError:
    basestring = str

from pybuilder.errors import MissingPrerequisiteException, PyBuilderException

if sys.version_info[0] < 3:  # if major is less than 3
    from .excp_util_2 import raise_exception, is_string

    is_string = is_string
else:
    from .excp_util_3 import raise_exception, is_string

    is_string = is_string


def get_all_dependencies_for_task(task):
    """
    Returns a list containing all tasks required by the given
    task function (but not the given task itself)
    """
    from pybuilder.reactor import Reactor

    task_name = task.__name__
    execution_manager = Reactor.current_instance().execution_manager
    task_and_all_dependencies = execution_manager.collect_all_transitive_tasks([task_name])
    return [dependency for dependency in task_and_all_dependencies if dependency.name != task_name]


def render_report(report_dict):
    return json.dumps(report_dict, indent=2, sort_keys=True)


def format_timestamp(timestamp):
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def timedelta_in_millis(timedelta):
    return ((timedelta.days * 24 * 60 * 60) + timedelta.seconds) * 1000 + round(timedelta.microseconds / 1000)


def as_list(*whatever):
    """
        Returns a list containing all values given in whatever.
        Each list or tuple will be "unpacked", all other elements
        are added to the resulting list.

        Examples given

        >>> as_list('spam')
        ['spam']

        >>> as_list('spam', 'eggs')
        ['spam', 'eggs']

        >>> as_list(('spam', 'eggs'))
        ['spam', 'eggs']

        >>> as_list(['spam', 'eggs'])
        ['spam', 'eggs']

        >>> as_list(['spam', 'eggs'], ('spam', 'eggs'), 'foo', 'bar')
        ['spam', 'eggs', 'spam', 'eggs', 'foo', 'bar']
    """
    result = []

    for w in whatever:
        if w is None:
            continue
        elif isinstance(w, list):
            result += w
        elif isinstance(w, tuple):
            result += w
        else:
            result.append(w)
    return result


def remove_leading_slash_or_dot_from_path(path):
    if path.startswith('/') or path.startswith('.'):
        return path[1:]
    return path


def remove_python_source_suffix(file_name):
    if file_name.endswith(".py"):
        return file_name[0:-len(".py")]
    return file_name


def discover_modules(source_path, suffix=".py"):
    return discover_modules_matching(source_path, "*{0}".format(suffix))


def discover_modules_matching(source_path, module_glob):
    result = []
    if not module_glob.endswith(".py"):
        module_glob += ".py"
    for module_file_path in discover_files_matching(source_path, module_glob):
        relative_module_file_path = module_file_path.replace(source_path, "")
        relative_module_file_path = relative_module_file_path.replace(os.sep, ".")
        module_file = remove_leading_slash_or_dot_from_path(relative_module_file_path)
        module_name = remove_python_source_suffix(module_file)
        if module_name.endswith(".__init__"):
            module_name = module_name.replace(".__init__", "")
        result.append(module_name)
    return result


def discover_files(start_dir, suffix):
    return discover_files_matching(start_dir, "*{0}".format(suffix))


def discover_files_matching(start_dir, file_glob):
    for root, _, files in os.walk(start_dir):
        for file_name in files:
            if fnmatch.fnmatch(file_name, file_glob):
                yield os.path.join(root, file_name)


def execute_command(command_and_arguments, outfile_name=None, env=None, cwd=None, error_file_name=None, shell=False):
    if error_file_name is None and outfile_name:
        error_file_name = outfile_name + ".err"

    out_file_created = False
    error_file_created = False

    if not hasattr(outfile_name, "write"):
        outfile_name = open(outfile_name, "w") if outfile_name else None
        out_file_created = True

    try:
        if not hasattr(error_file_name, "write"):
            error_file_name = open(error_file_name, "w") if error_file_name else None
            error_file_created = True

        try:
            process = Popen(command_and_arguments,
                            stdout=outfile_name,
                            stderr=error_file_name,
                            env=env,
                            cwd=cwd,
                            shell=shell)
            return process.wait()
        finally:
            if error_file_name and error_file_created:
                error_file_name.close()
    finally:
        if outfile_name and out_file_created:
            outfile_name.close()


def execute_command_and_capture_output(*command_and_arguments):
    process_handle = Popen(command_and_arguments, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process_handle.communicate()
    stdout, stderr = stdout.decode(sys.stdout.encoding or 'utf-8'), stderr.decode(sys.stderr.encoding or 'utf-8')
    process_return_code = process_handle.returncode
    return process_return_code, stdout, stderr


def tail(file_path, lines=20):
    try:
        import tailer
    except ImportError:
        return (l[:len(l)] for l in read_file(file_path))

    with open(file_path) as f:
        return tailer.tail(f, lines)


def tail_log(file_path, lines=20):
    return "\n".join("\t" + l for l in tail(file_path, lines))


def assert_can_execute(command_and_arguments, prerequisite, caller):
    with tempfile.NamedTemporaryFile() as f:
        try:
            process = subprocess.Popen(command_and_arguments, stdout=f, stderr=f, shell=False)
            process.wait()
        except OSError:
            raise MissingPrerequisiteException(prerequisite, caller)


def read_file(file_name):
    if hasattr(file_name, "mode"):
        # This is an open file with mode
        file_name.seek(0)
        return file_name.readlines()
    else:
        with open(file_name, "r") as file_handle:
            return file_handle.readlines()


def write_file(file_name, *lines):
    with open(file_name, "w") as file_handle:
        file_handle.writelines(lines)


class Timer(object):
    @staticmethod
    def start():
        return Timer()

    def __init__(self):
        self.start_time = time.time()
        self.end_time = None

    def stop(self):
        self.end_time = time.time()

    def get_millis(self):
        if self.end_time is None:
            raise PyBuilderException("Timer is running.")
        return int((self.end_time - self.start_time) * 1000)


def apply_on_files(start_directory, closure, globs, *additional_closure_arguments, **keyword_closure_arguments):
    glob_expressions = list(map(lambda g: GlobExpression(g), globs))

    for root, _, file_names in os.walk(start_directory):
        for file_name in file_names:
            absolute_file_name = os.path.join(root, file_name)
            relative_file_name = absolute_file_name.replace(start_directory, "")[1:]

            for glob_expression in glob_expressions:
                if glob_expression.matches(relative_file_name):
                    closure(absolute_file_name,
                            relative_file_name,
                            *additional_closure_arguments,
                            **keyword_closure_arguments)


class GlobExpression(object):
    def __init__(self, expression):
        self.expression = expression
        self.regex = "^" + expression.replace("**", ".+").replace("*", "[^/]*") + "$"
        self.pattern = re.compile(self.regex)

    def matches(self, path):
        if self.pattern.match(path):
            return True
        return False


def mkdir(directory):
    """
    Tries to create the directory denoted by the given name. If it exists and is a directory, nothing will be created
    and no error is raised. If it exists as a file a PyBuilderException is raised. Otherwise the directory incl.
    all parents is created.
    """

    if os.path.exists(directory):
        if os.path.isfile(directory):
            message = "Unable to created directory '%s': A file with that name already exists"
            raise PyBuilderException(message, directory)
        return
    os.makedirs(directory)


def is_windows():
    return any(win_platform in sys.platform for win_platform in ("win32", "cygwin", "msys"))


def fake_windows_fork(group, target, name, args, kwargs):
    return 0, target(*args, **kwargs)


def fork_process(logger, group=None, target=None, name=None, args=(), kwargs={}):
    """
    Forks a child, making sure that all exceptions from the child are safely sent to the parent
    If a target raises an exception, the exception is re-raised in the parent process
    @return tuple consisting of process exit code and target's return value
    """
    if is_windows():
        logger.warn(
            "Not forking for %s due to Windows incompatibilities (see #184). "
            "Measurements (coverage, etc.) might be biased." % target)
        return fake_windows_fork(group, target, name, args, kwargs)
    try:
        sys.modules["tblib.pickling_support"]
    except KeyError:
        import tblib.pickling_support

        tblib.pickling_support.install()

    q = SimpleQueue()

    def instrumented_target(*args, **kwargs):
        ex = tb = None
        try:
            send_value = (target(*args, **kwargs), None, None)
        except:
            _, ex, tb = sys.exc_info()
            send_value = (None, ex, tb)

        try:
            q.put(send_value)
        except:
            _, send_ex, send_tb = sys.exc_info()
            e_out = Exception(str(send_ex), send_tb, None if ex is None else str(ex), tb)
            q.put(e_out)

    p = Process(group=group, target=instrumented_target, name=name, args=args, kwargs=kwargs)
    p.start()
    result = q.get()
    p.join()
    if isinstance(result, tuple):
        if result[1]:
            raise_exception(result[1], result[2])
        return p.exitcode, result[0]
    else:
        msg = "Fatal error occurred in the forked process %s: %s" % (p, result.args[0])
        if result.args[2]:
            chained_message = "This error masked the send error '%s':\n%s" % (
                result.args[2], "".join(traceback.format_tb(result.args[3])))
            msg += "\n" + chained_message
        ex = Exception(msg)
        raise_exception(ex, result.args[1])


if sys.version_info[0] == 2 and sys.version_info[1] == 6:  # if Python is 2.6
    # Backport of OrderedDict() class that runs on Python 2.4, 2.5, 2.6, 2.7 and pypy.
    # Passes Python2.7's test suite and incorporates all the latest updates.

    try:
        from thread import get_ident as _get_ident
    except ImportError:
        from dummy_thread import get_ident as _get_ident

    try:
        from _abcoll import KeysView, ValuesView, ItemsView
    except ImportError:
        pass

    class OrderedDict(dict):
        'Dictionary that remembers insertion order'

        # An inherited dict maps keys to values.
        # The inherited dict provides __getitem__, __len__, __contains__, and get.
        # The remaining methods are order-aware.
        # Big-O running times for all methods are the same as for regular dictionaries.

        # The internal self.__map dictionary maps keys to links in a doubly linked list.
        # The circular doubly linked list starts and ends with a sentinel element.
        # The sentinel element never gets deleted (this simplifies the algorithm).
        # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

        def __init__(self, *args, **kwds):
            '''Initialize an ordered dictionary.  Signature is the same as for
            regular dictionaries, but keyword arguments are not recommended
            because their insertion order is arbitrary.

            '''
            if len(args) > 1:
                raise TypeError('expected at most 1 arguments, got %d' % len(args))
            try:
                self.__root
            except AttributeError:
                self.__root = root = []  # sentinel node
                root[:] = [root, root, None]
                self.__map = {}
            self.__update(*args, **kwds)

        def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
            'od.__setitem__(i, y) <==> od[i]=y'
            # Setting a new item creates a new link which goes at the end of the linked
            # list, and the inherited dictionary is updated with the new key/value pair.
            if key not in self:
                root = self.__root
                last = root[0]
                last[1] = root[0] = self.__map[key] = [last, root, key]
            dict_setitem(self, key, value)

        def __delitem__(self, key, dict_delitem=dict.__delitem__):
            'od.__delitem__(y) <==> del od[y]'
            # Deleting an existing item uses self.__map to find the link which is
            # then removed by updating the links in the predecessor and successor nodes.
            dict_delitem(self, key)
            link_prev, link_next, key = self.__map.pop(key)
            link_prev[1] = link_next
            link_next[0] = link_prev

        def __iter__(self):
            'od.__iter__() <==> iter(od)'
            root = self.__root
            curr = root[1]
            while curr is not root:
                yield curr[2]
                curr = curr[1]

        def __reversed__(self):
            'od.__reversed__() <==> reversed(od)'
            root = self.__root
            curr = root[0]
            while curr is not root:
                yield curr[2]
                curr = curr[0]

        def clear(self):
            'od.clear() -> None.  Remove all items from od.'
            try:
                for node in self.__map.itervalues():
                    del node[:]
                root = self.__root
                root[:] = [root, root, None]
                self.__map.clear()
            except AttributeError:
                pass
            dict.clear(self)

        def popitem(self, last=True):
            '''od.popitem() -> (k, v), return and remove a (key, value) pair.
            Pairs are returned in LIFO order if last is true or FIFO order if false.

            '''
            if not self:
                raise KeyError('dictionary is empty')
            root = self.__root
            if last:
                link = root[0]
                link_prev = link[0]
                link_prev[1] = root
                root[0] = link_prev
            else:
                link = root[1]
                link_next = link[1]
                root[1] = link_next
                link_next[0] = root
            key = link[2]
            del self.__map[key]
            value = dict.pop(self, key)
            return key, value

        # -- the following methods do not depend on the internal structure --

        def keys(self):
            'od.keys() -> list of keys in od'
            return list(self)

        def values(self):
            'od.values() -> list of values in od'
            return [self[key] for key in self]

        def items(self):
            'od.items() -> list of (key, value) pairs in od'
            return [(key, self[key]) for key in self]

        def iterkeys(self):
            'od.iterkeys() -> an iterator over the keys in od'
            return iter(self)

        def itervalues(self):
            'od.itervalues -> an iterator over the values in od'
            for k in self:
                yield self[k]

        def iteritems(self):
            'od.iteritems -> an iterator over the (key, value) items in od'
            for k in self:
                yield (k, self[k])

        def update(*args, **kwds):
            '''od.update(E, **F) -> None.  Update od from dict/iterable E and F.

            If E is a dict instance, does:           for k in E: od[k] = E[k]
            If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
            Or if E is an iterable of items, does:   for k, v in E: od[k] = v
            In either case, this is followed by:     for k, v in F.items(): od[k] = v

            '''
            if len(args) > 2:
                raise TypeError('update() takes at most 2 positional '
                                'arguments (%d given)' % (len(args),))
            elif not args:
                raise TypeError('update() takes at least 1 argument (0 given)')
            self = args[0]
            # Make progressively weaker assumptions about "other"
            other = ()
            if len(args) == 2:
                other = args[1]
            if isinstance(other, dict):
                for key in other:
                    self[key] = other[key]
            elif hasattr(other, 'keys'):
                for key in other.keys():
                    self[key] = other[key]
            else:
                for key, value in other:
                    self[key] = value
            for key, value in kwds.items():
                self[key] = value

        __update = update  # let subclasses override update without breaking __init__

        __marker = object()

        def pop(self, key, default=__marker):
            '''od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
            If key is not found, d is returned if given, otherwise KeyError is raised.

            '''
            if key in self:
                result = self[key]
                del self[key]
                return result
            if default is self.__marker:
                raise KeyError(key)
            return default

        def setdefault(self, key, default=None):
            'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
            if key in self:
                return self[key]
            self[key] = default
            return default

        def __repr__(self, _repr_running={}):
            'od.__repr__() <==> repr(od)'
            call_key = id(self), _get_ident()
            if call_key in _repr_running:
                return '...'
            _repr_running[call_key] = 1
            try:
                if not self:
                    return '%s()' % (self.__class__.__name__,)
                return '%s(%r)' % (self.__class__.__name__, self.items())
            finally:
                del _repr_running[call_key]

        def __reduce__(self):
            'Return state information for pickling'
            items = [[k, self[k]] for k in self]
            inst_dict = vars(self).copy()
            for k in vars(OrderedDict()):
                inst_dict.pop(k, None)
            if inst_dict:
                return (self.__class__, (items,), inst_dict)
            return self.__class__, (items,)

        def copy(self):
            'od.copy() -> a shallow copy of od'
            return self.__class__(self)

        @classmethod
        def fromkeys(cls, iterable, value=None):
            '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
            and values equal to v (which defaults to None).

            '''
            d = cls()
            for key in iterable:
                d[key] = value
            return d

        def __eq__(self, other):
            '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
            while comparison to a regular mapping is order-insensitive.

            '''
            if isinstance(other, OrderedDict):
                return len(self) == len(other) and self.items() == other.items()
            return dict.__eq__(self, other)

        def __ne__(self, other):
            return not self == other

        # -- the following methods are only used in Python 2.7 --

        def viewkeys(self):
            "od.viewkeys() -> a set-like object providing a view on od's keys"
            return KeysView(self)

        def viewvalues(self):
            "od.viewvalues() -> an object providing a view on od's values"
            return ValuesView(self)

        def viewitems(self):
            "od.viewitems() -> a set-like object providing a view on od's items"
            return ItemsView(self)

    odict = OrderedDict
else:
    from collections import OrderedDict

    odict = OrderedDict


def is_notstr_iterable(obj):
    """Checks if obj is iterable, but not a string"""
    return not isinstance(obj, basestring) and isinstance(obj, collections.Iterable)


def get_dist_version_string(project, format=" (%s)"):
    return format % project.dist_version if project.version != project.dist_version else ""


def safe_log_file_name(file_name):
    # per https://support.microsoft.com/en-us/kb/177506
    # per https://msdn.microsoft.com/en-us/library/aa365247
    return re.sub(r'\\|/|:|\*|\?|\"|<|>|\|', '_', file_name)
