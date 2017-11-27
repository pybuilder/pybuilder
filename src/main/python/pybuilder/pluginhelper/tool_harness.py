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
Used to abstract logic related to using tightly coupled tools like unittest, pytest, coverage, integration tests etc

This module has very specific restrictions on its use and contents:
* The dependencies must be the most minimal and most universal Python stack only.
* Must not depend on anything PyB so as to not drag it into the executor"s tree.
"""

from __future__ import unicode_literals

import os
import sys
from collections import deque
from contextlib import closing
from multiprocessing.connection import Pipe as _Pipe
from multiprocessing.process import ORIGINAL_DIR, current_process
from multiprocessing.reduction import ForkingPickler
from subprocess import Popen, PIPE
from threading import Event
from threading import Thread
from time import time

try:
    from multiprocessing.connection import wait
    from multiprocessing.spawn import (WINEXE,
                                       WINSERVICE)
except ImportError:
    #
    # Wait
    #
    if sys.platform == 'win32':
        from multiprocessing.forking import (WINEXE,
                                             WINSERVICE)

        try:
            import _winapi
            from _winapi import WAIT_OBJECT_0, WAIT_ABANDONED_0, WAIT_TIMEOUT, INFINITE
        except ImportError:
            if sys.platform == 'win32':
                raise
            _winapi = None


        def _exhaustive_wait(handles, timeout):
            # Return ALL handles which are currently signalled.  (Only
            # returning the first signalled might create starvation issues.)
            L = list(handles)
            ready = []
            while L:
                res = _winapi.WaitForMultipleObjects(L, False, timeout)
                if res == WAIT_TIMEOUT:
                    break
                elif WAIT_OBJECT_0 <= res < WAIT_OBJECT_0 + len(L):
                    res -= WAIT_OBJECT_0
                elif WAIT_ABANDONED_0 <= res < WAIT_ABANDONED_0 + len(L):
                    res -= WAIT_ABANDONED_0
                else:
                    raise RuntimeError('Should not get here')
                ready.append(L[res])
                L = L[res + 1:]
                timeout = 0
            return ready


        _ready_errors = {_winapi.ERROR_BROKEN_PIPE, _winapi.ERROR_NETNAME_DELETED}


        def wait(object_list, timeout=None):
            '''
            Wait till an object in object_list is ready/readable.

            Returns list of those objects in object_list which are ready/readable.
            '''
            if timeout is None:
                timeout = INFINITE
            elif timeout < 0:
                timeout = 0
            else:
                timeout = int(timeout * 1000 + 0.5)

            object_list = list(object_list)
            waithandle_to_obj = {}
            ov_list = []
            ready_objects = set()
            ready_handles = set()

            try:
                for o in object_list:
                    try:
                        fileno = getattr(o, 'fileno')
                    except AttributeError:
                        waithandle_to_obj[o.__index__()] = o
                    else:
                        # start an overlapped read of length zero
                        try:
                            ov, err = _winapi.ReadFile(fileno(), 0, True)
                        except OSError as e:
                            ov, err = None, e.winerror
                            if err not in _ready_errors:
                                raise
                        if err == _winapi.ERROR_IO_PENDING:
                            ov_list.append(ov)
                            waithandle_to_obj[ov.event] = o
                        else:
                            # If o.fileno() is an overlapped pipe handle and
                            # err == 0 then there is a zero length message
                            # in the pipe, but it HAS NOT been consumed...
                            if ov and sys.getwindowsversion()[:2] >= (6, 2):
                                # ... except on Windows 8 and later, where
                                # the message HAS been consumed.
                                try:
                                    _, err = ov.GetOverlappedResult(False)
                                except OSError as e:
                                    err = e.winerror
                                if not err and hasattr(o, '_got_empty_message'):
                                    o._got_empty_message = True
                            ready_objects.add(o)
                            timeout = 0

                ready_handles = _exhaustive_wait(waithandle_to_obj.keys(), timeout)
            finally:
                # request that overlapped reads stop
                for ov in ov_list:
                    ov.cancel()

                # wait for all overlapped reads to stop
                for ov in ov_list:
                    try:
                        _, err = ov.GetOverlappedResult(True)
                    except OSError as e:
                        err = e.winerror
                        if err not in _ready_errors:
                            raise
                    if err != _winapi.ERROR_OPERATION_ABORTED:
                        o = waithandle_to_obj[ov.event]
                        ready_objects.add(o)
                        if err == 0:
                            # If o.fileno() is an overlapped pipe handle then
                            # a zero length message HAS been consumed.
                            if hasattr(o, '_got_empty_message'):
                                o._got_empty_message = True

            ready_objects.update(waithandle_to_obj[h] for h in ready_handles)
            return [o for o in object_list if o in ready_objects]

    else:
        WINEXE = False
        WINSERVICE = False

        import selectors34 as selectors

        # poll/select have the advantage of not requiring any extra file
        # descriptor, contrarily to epoll/kqueue (also, they require a single
        # syscall).
        if hasattr(selectors, 'PollSelector'):
            _WaitSelector = selectors.PollSelector
        else:
            _WaitSelector = selectors.SelectSelector


        def wait(object_list, timeout=None):
            '''
            Wait till an object in object_list is ready/readable.

            Returns list of those objects in object_list which are ready/readable.
            '''
            with _WaitSelector() as selector:
                for obj in object_list:
                    selector.register(obj, selectors.EVENT_READ)

                if timeout is not None:
                    deadline = time.time() + timeout

                while True:
                    ready = selector.select(timeout)
                    if ready:
                        return [key.fileobj for (key, events) in ready]
                    else:
                        if timeout is not None:
                            timeout = deadline - time.time()
                            if timeout < 0:
                                return ready

from _pybuilder import ToolShim

LAUNCH_CODE = """from _pybuilder.spawn import spawn_main
spawn_main()
"""

# Reverse compatiblity with Python 2
_DEFAULT_PICKLE_PROTOCOL = 2

__all__ = ["ToolProc", "ToolRunner", "ToolShim", "DEFAULT_TERMINATE_WAIT", "DEFAULT_MAX_CONCURRENCY"]

DEFAULT_TERMINATE_WAIT = 5
DEFAULT_MAX_CONCURRENCY = 1


class _DataHandler():
    def __init__(self, stream, handler):
        self.stream = stream
        self.handler = handler

    def handle(self, ts, data):
        return self.handler(ts, data)

    def fileno(self):
        return self.stream.fileno()

    def close(self):
        return self.stream.close()


class _IoHandler():
    def __init__(self, stream, fd, handler):
        self.stream = stream
        self.fd = fd
        self.handler = handler

    def handle(self, ts, data):
        return self.handler(self.fd, ts, data)

    def fileno(self):
        return self.stream.fileno()

    def close(self):
        return self.stream.close()


class ToolProc:
    def __init__(self, shim, handle_io, handle_data, cwd, env):
        self.proc = None  # type: Popen
        self.shim = shim  # type: ToolShim
        self.handle_io = handle_io
        self.handle_data = handle_data
        self.cwd = cwd
        self.env = env

        self.alive_r = None
        self.data_r = None
        self._exc = None
        self._set = Event()

    def started(self):
        return self.pid() is not None

    def error(self):
        if not self._set.is_set():
            return None
        if self._exc is not None:
            return self._exc

    @property
    def pid(self):
        if not self._set.is_set():
            return None
        return self.proc.pid

    def fileno(self):
        self._check_proc_set()
        return self.alive_r.fileno()

    def poll(self):
        self._check_proc_set()
        return self.proc.poll()

    def terminate(self):
        self._check_proc_set()
        return self.proc.terminate()

    def kill(self):
        self._check_proc_set()
        return self.proc.terminate()

    def wait(self, timeout=None):
        self._set.wait(timeout)
        self._check_proc_set()

    if sys.version_info[0] == 2:
        def _proc_wait(self, timeout=None):
            self.proc.wait()
    else:
        def _proc_wait(self, timeout=None):
            self.proc.wait(timeout)

    def _get_handlers(self):
        self._check_proc_set()
        return (_IoHandler(self.proc.stdout, 1, self.handle_io),
                _IoHandler(self.proc.stderr, 2, self.handle_io),
                _DataHandler(self.data_r, self.handle_data))

    def _set_proc(self, proc, alive_r, data_r):
        self.proc = proc
        self.alive_r = alive_r
        self.data_r = data_r
        self._set.set()

    def _set_exc(self, exc):
        self._exc = exc
        self._set.set()

    def _check_proc_set(self):
        if not self._set.is_set():
            raise RuntimeError("process not started")
        if self._exc is not None:
            raise self._exc

    def __del__(self):
        if self._set.is_set():
            if self.alive_r:
                try:
                    self.alive_r.close()
                except Exception:
                    sys.excepthook(*sys.exc_info())

            if self.data_r:
                try:
                    self.data_r.close()
                except Exception:
                    sys.excepthook(*sys.exc_info())


class ToolRunner:
    def __init__(self, sys_exec=sys.executable,
                 max_concurrency=DEFAULT_MAX_CONCURRENCY,
                 terminate_wait=DEFAULT_TERMINATE_WAIT):
        self.sys_exec = sys_exec
        self.max_concurrency = max_concurrency
        self.terminate_wait = terminate_wait

        self.closed = False

        self.taskq = deque()
        self._taskq_guard = Event()
        self.launcher_r, self.launcher_w = pipe()

        self.ioq = deque()
        self._ioq_guard = Event()
        self.io_proc_r, self.io_proc_w = pipe()

        self.launcher_thread = Thread(target=self._launcher, name="Process Launcher %s" % id(self))
        self.io_thread = Thread(target=self._io_processor, name="IO Processor %s" % id(self))
        self.io_thread.start()
        self.launcher_thread.start()

    def task(self, shim, handle_io, handle_data, cwd=None, env=None):
        if self.closed:
            raise RuntimeError("closed")
        proc = ToolProc(shim, handle_io, handle_data, cwd, env)
        self.taskq.append(proc)
        self._taskq_guard.set()
        self.launcher_w.write(b"1")
        return proc

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        self.wait()

    def __del__(self):
        self.close()

    def terminate(self):
        if self.closed:
            return
        self.closed = True
        self.launcher_w.write(b"2")
        self.launcher_w.close()

    def close(self):
        """Will wait for all tools to finish what they are doing and """
        if self.closed:
            return
        self.closed = True
        self.launcher_w.close()

    def wait(self, timeout=None):
        self.launcher_thread.join(timeout)

    def _launcher(self):
        taskq = self.taskq
        task_guard = self._taskq_guard
        waiters = set()
        current_procs = 0
        should_exit = False
        terminate = False
        launcher_r = self.launcher_r
        waiters.add(launcher_r)

        with launcher_r:
            while True:
                ready_list = wait(waiters)
                for ready in ready_list:
                    if ready is launcher_r:
                        # We have a new task or shutting down
                        wake_val = launcher_r.read(1)
                        if wake_val == b"":
                            # Writer has been closed, which means get out
                            should_exit = True
                        elif wake_val == b"1":
                            pass
                        elif wake_val == b"2":
                            should_exit = True
                            terminate = True
                            break
                        else:
                            raise AssertionError("unknown launcher wake value %r!" % wake_val)
                    else:
                        # Process died
                        waiters.remove(ready)
                        current_procs -= 1

                no_more_tasks = False
                while current_procs <= self.max_concurrency:
                    try:
                        task_guard.is_set()
                        tool_proc = taskq.pop()  # type: ToolProc

                        self._start(tool_proc)
                        if tool_proc.error():
                            continue
                        waiters.add(tool_proc)
                        self.ioq.append(tool_proc)
                        self._ioq_guard.set()
                        self.io_proc_w.write(b"1")
                        current_procs += 1
                    except IndexError:
                        no_more_tasks = True
                        break

                if should_exit and no_more_tasks:
                    break

            # If terminating this will flush existing tasks
            # If closing gracefully this will be empty already
            taskq.clear()
            for waiter in waiters:
                if waiter is not launcher_r:
                    if terminate:
                        waiter.terminate()
                        waiter.wait(self.terminate_wait)
                        if waiter.poll() is not None:
                            waiter.kill()
                    else:
                        waiter.wait()

        self.io_proc_w.close()
        self.io_thread.join()

    def _start(self, task_proc):
        data_r, data_w = Pipe(False)
        alive_r, alive_w = Pipe(False)
        with closing(data_w), closing(alive_w):
            task_proc.shim.data_w = data_w
            r_bootstrap, w_bootstrap = pipe()
            with r_bootstrap, w_bootstrap:
                try:
                    proc = Popen([sys.executable, "-c", LAUNCH_CODE],
                                 stdin=r_bootstrap, stdout=PIPE, stderr=PIPE, bufsize=0)

                    pickler = ForkingPickler(w_bootstrap, _DEFAULT_PICKLE_PROTOCOL)
                    pickler.dump(self._bootstrap_config())
                    pickler.dump(alive_w)
                    pickler.dump(task_proc.shim)
                    w_bootstrap.flush()
                    task_proc._set_proc(proc, alive_r, data_r)
                except Exception as e:
                    with closing(alive_r), closing(data_r):
                        task_proc._set_exc(e)

    def _bootstrap_config(self, *args):
        return _bootstrap_config(*args)

    def _io_processor(self):
        ioq = self.ioq
        ioq_guard = self._ioq_guard
        io_proc_r = self.io_proc_r
        waiters = set()
        waiters.add(io_proc_r)

        with io_proc_r:
            while waiters:
                add_procs = False
                ready_list = wait(waiters)
                ts = time()
                for ready in ready_list:
                    if ready is io_proc_r:
                        wake_val = io_proc_r.read(1)
                        if wake_val == b"":
                            # We're closed but we'll keep draining the swamp
                            waiters.remove(io_proc_r)
                        elif wake_val == b"1":
                            add_procs = True
                        else:  # pragma: no cover
                            raise AssertionError("unknown IO wake value %r!" % wake_val)
                    else:
                        if isinstance(ready, _IoHandler):
                            data = None
                            try:
                                data = ready.stream.read()
                            except EOFError:
                                pass

                            if not data:
                                waiters.remove(ready)
                                try:
                                    ready.close()
                                except Exception:
                                    sys.excepthook(*sys.exc_info())
                        elif isinstance(ready, _DataHandler):
                            data = None
                            try:
                                data = ready.stream.recv()
                            except EOFError:
                                pass

                            if not data:
                                waiters.remove(ready)
                                try:
                                    ready.close()
                                except Exception:
                                    sys.excepthook(*sys.exc_info())
                        else:  # pragma: no cover
                            raise AssertionError("unknown handler type %s!" % type(ready))
                        try:
                            ready.handle(ts, data)
                        except Exception:
                            sys.excepthook(*sys.exc_info())

                if add_procs:
                    try:
                        ioq_guard.is_set()
                        while True:
                            proc = ioq.pop()
                            for handler in proc._get_handlers():
                                waiters.add(handler)
                    except IndexError:
                        pass


def read_pipe(f, prefix):
    while True:
        l = f.readline()
        if not l:
            break
        sys.stdout.write(prefix + l)


def pipe(r_mode="rb", r_buf=0, w_mode="wb", w_buf=0):
    r_pipe, w_pipe = os.pipe()
    return os.fdopen(r_pipe, r_mode, r_buf), os.fdopen(w_pipe, w_mode, w_buf)


def _conn_send(self, obj):
    """Send a (picklable) object"""
    self._check_closed()
    self._check_writable()
    self._send_bytes(ForkingPickler.dumps(obj, protocol=_DEFAULT_PICKLE_PROTOCOL))


if sys.version_info[0] == 2:
    def _patch_connection(conn):
        return conn


    def _bootstrap_config():
        d = {"authkey": bytes(current_process().authkey)}

        if not WINEXE and not WINSERVICE and \
                not sys.argv[0].lower().endswith('pythonservice.exe'):
            main_path = getattr(sys.modules['__main__'], '__file__', None)
            if not main_path and sys.argv[0] not in ('', '-c'):
                main_path = sys.argv[0]
            if main_path is not None:
                if not os.path.isabs(main_path) and \
                                ORIGINAL_DIR is not None:
                    main_path = os.path.join(ORIGINAL_DIR, main_path)
                d['main_path'] = os.path.normpath(main_path)
        return d
else:
    def _patch_connection(conn):
        conn.send = _conn_send
        return conn


    def _bootstrap_config():
        d = {"authkey": bytes(current_process().authkey)}

        # Figure out whether to initialise main in the subprocess as a module
        # or through direct execution (or to leave it alone entirely)
        main_module = sys.modules["__main__"]
        main_mod_name = getattr(main_module.__spec__, "name", None)
        if main_mod_name is not None:
            d["init_main_from_name"] = main_mod_name
        elif sys.platform != "win32" or (not WINEXE and not WINSERVICE):
            main_path = getattr(main_module, "__file__", None)
            if main_path is not None:
                if not os.path.isabs(main_path) and ORIGINAL_DIR is not None:
                    main_path = os.path.join(ORIGINAL_DIR, main_path)
                d["init_main_from_path"] = os.path.normpath(main_path)

        return d


def Pipe(duplex=True):
    r_pc, w_pc = _Pipe(duplex)
    return _patch_connection(r_pc), _patch_connection(w_pc)
