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


from pybuilder.python_utils import patch_mp

patch_mp()

import sys  # noqa: E402
from textwrap import dedent  # noqa: E402

from types import (MethodType,  # noqa: E402
                   FunctionType,
                   BuiltinFunctionType,
                   )

try:
    from types import (WrapperDescriptorType,  # noqa: E402
                       MethodWrapperType,
                       MethodDescriptorType,
                       ClassMethodDescriptorType,
                       )
except ImportError:
    WrapperDescriptorType = type(object.__init__)
    MethodWrapperType = type(object().__str__)
    MethodDescriptorType = type(str.join)
    ClassMethodDescriptorType = type(dict.__dict__['fromkeys'])

from os.path import normcase as nc, sep  # noqa: E402
from io import BytesIO, StringIO  # noqa: E402
from pickle import PickleError, Unpickler, UnpicklingError, HIGHEST_PROTOCOL  # noqa: E402
from pickletools import dis  # noqa: E402

from pybuilder.python_utils import (mp_get_context,  # noqa: E402
                                    mp_ForkingPickler as ForkingPickler,
                                    mp_log_to_stderr as log_to_stderr,
                                    IS_WIN)

PICKLE_PROTOCOL_MIN = 4
PICKLE_PROTOCOL_MAX = HIGHEST_PROTOCOL

CALLABLE_TYPES = (MethodType,
                  FunctionType,
                  BuiltinFunctionType,
                  MethodWrapperType,
                  ClassMethodDescriptorType,
                  WrapperDescriptorType,
                  MethodDescriptorType,
                  )

import _compat_pickle  # noqa: E402

ctx = mp_get_context("spawn")
ctx.allow_connection_pickling()
logger = ctx.get_logger()

__all__ = ["RemoteObjectPipe", "RemoteObjectError",
           "Process", "proxy_members", "PipeShutdownError", "log_to_stderr"]

BUILTIN_MODULES = set(sys.builtin_module_names)


class Process:
    def __init__(self, pyenv, group=None, target=None, name=None, args=None):
        self.pyenv = pyenv
        self.proc = ctx.Process(group=group, target=target, name=name, args=args)

    def start(self):
        pyenv = self.pyenv

        from multiprocessing import spawn as patch_module
        if not IS_WIN:
            try:
                from multiprocessing import semaphore_tracker as tracker
            except ImportError:
                from multiprocessing import resource_tracker as tracker
        else:
            tracker = None

        # This is done to prevent polluting tracker's path with our path magic
        if tracker:
            tracker.getfd()

        old_python_exe = patch_module.get_executable()
        patch_module.set_executable(pyenv.executable[0])  # pyenv's actual sys.executable

        old_get_command_line = patch_module.get_command_line

        def patched_get_command_line(**kwds):
            cmd_line = old_get_command_line(**kwds)
            result = list(pyenv.executable) + cmd_line[1:]
            logger.debug("Starting process with %r", result)
            return result

        patch_module.get_command_line = patched_get_command_line

        old_preparation_data = patch_module.get_preparation_data

        def patched_preparation_data(name):
            d = old_preparation_data(name)
            sys_path = d["sys_path"]

            exec_prefix = nc(sys.exec_prefix) + sep

            trailing_paths = []
            for idx, path in enumerate(sys_path):
                nc_path = nc(path)

                if nc_path.startswith(exec_prefix):
                    sys_path[idx] = pyenv.env_dir + sep + path[len(exec_prefix):]
                    trailing_paths.append(path)

            # Push current exec_prefix paths to the very end
            sys_path.extend(trailing_paths)

            logger.debug("Process sys.path will be: %r", sys_path)
            return d

        patch_module.get_preparation_data = patched_preparation_data
        try:
            return self.proc.start()
        finally:
            patch_module.set_executable(old_python_exe)
            patch_module.get_command_line = old_get_command_line
            patch_module.get_preparation_data = old_preparation_data

    def terminate(self):
        return self.proc.terminate()

    def kill(self):
        return self.proc.kill()

    def join(self, timeout=None):
        return self.proc.join(timeout)

    def is_alive(self):
        return self.proc.is_alive()

    def close(self):
        return self.proc.close()

    @property
    def name(self):
        return self.proc.name

    @name.setter
    def name(self, name):
        self.proc.name = name

    @property
    def daemon(self):
        return self.proc.daemon

    @daemon.setter
    def daemon(self, daemonic):
        self.proc.daemon = daemonic

    @property
    def authkey(self):
        return self.proc.authkey

    @authkey.setter
    def authkey(self, authkey):
        self.proc.authkey = authkey

    @property
    def exitcode(self):
        return self.proc.exitcode

    @property
    def ident(self):
        return self.proc.ident

    pid = ident

    @property
    def sentinel(self):
        return self.proc.sentinel

    def __repr__(self):
        return repr(self.proc)


class ProxyDef:
    def __init__(self, remote_id, module_name, type_name, is_type, methods, fields, spec_fields):
        self.remote_id = remote_id
        self.module_name = module_name
        self.type_name = type_name
        self.is_type = is_type
        self.methods = methods
        self.fields = fields
        self.spec_fields = spec_fields

    def __repr__(self):
        return "ProxyDef[remote_id=%r, module_name=%r, type_name=%r, is_type=%r," \
               " methods=%r, fields=%r, spec_fields=%r]" % (self.remote_id,
                                                            self.module_name,
                                                            self.type_name,
                                                            self.is_type,
                                                            self.methods,
                                                            self.fields,
                                                            self.spec_fields)

    def make_proxy_type(self):
        """
        Return a proxy type whose methods are given by `exposed`
        """

        remote_id = self.remote_id
        methods = tuple(self.methods)
        fields = tuple(self.fields)
        dic = {}

        body = ""
        for meth in methods:
            body += dedent("""
            def %s(self, *args, **kwargs):
                return self._BaseProxy__rop.call(%r, %r, args, kwargs)""" % (meth, remote_id, meth))

        for field in fields:
            body += dedent("""
            def %s_getter(self):
                return self._BaseProxy__rop.call_getattr(%r, %r)

            def %s_setter(self, value):
                return self._BaseProxy__rop.call_setattr(%r, %r, value)

            %s = property(%s_getter, %s_setter)""" % (field, remote_id, field, field,
                                                      remote_id, field, field, field, field))

        exec(body, dic)
        if self.is_type:
            proxy_type = type(self.type_name, (_BaseProxyType, object), dic)
        else:
            proxy_type = type(self.type_name, (_BaseProxy, object), dic)

        proxy_type.__module__ = self.module_name
        proxy_type.__name__ = self.type_name
        proxy_type.__methods__ = methods
        proxy_type.__fields__ = fields
        return proxy_type


PICKLE_PID_TYPE_REMOTE_OBJ = 0
PICKLE_PID_TYPE_REMOTE_BACKREF = 1
PICKLE_PID_TYPE_REMOTE_EXC_TB = 5


class RemoteObjectUnpickler(Unpickler, object):
    def __init__(self, *args, **kwargs):
        self._rop = kwargs.pop("_rop")  # type: _RemoteObjectPipe
        super(RemoteObjectUnpickler, self).__init__(*args, **kwargs)

    def persistent_load(self, pid):
        if isinstance(pid, tuple):
            remote_type = pid[0]
            if remote_type == PICKLE_PID_TYPE_REMOTE_OBJ:
                remote_id = pid[1]
                proxy_def = self._rop.get_remote_proxy_def(remote_id)
                return self._rop.get_remote_proxy(proxy_def)

            if remote_type == PICKLE_PID_TYPE_REMOTE_BACKREF:
                remote_id = pid[1]
                return self._rop.get_remote_obj_by_id(remote_id)

            if remote_type == PICKLE_PID_TYPE_REMOTE_EXC_TB:
                exc_payload = pid[1]
                return rebuild_exception(*exc_payload)

        raise UnpicklingError("unsupported persistent id encountered: %r" % pid)

    @classmethod
    def loads(cls, buf, _rop, *args, **kwargs):
        f = BytesIO(buf)
        return cls(f, *args, _rop=_rop, **kwargs).load()


_PICKLE_SKIP_PID_CHECK_TYPES = {type(None), bool, int, float, complex, str, bytes, bytearray, list, tuple, dict, set}


class RemoteObjectPickler(ForkingPickler, object):

    def __init__(self, *args, **kwargs):
        self._rop = kwargs.pop("_rop")  # type: _RemoteObjectPipe
        self._verify_types = set()
        self.exc_persisted = []

        super(RemoteObjectPickler, self).__init__(args[0], self._rop.pickle_version, *args[1:])

    def persistent_id(self, obj):  # Mutable default is intentional here
        t_obj = obj if isinstance(obj, type) else type(obj)
        if t_obj in _PICKLE_SKIP_PID_CHECK_TYPES:
            return None

        exc_persisted = self.exc_persisted
        # This is a weird trick.
        if obj in exc_persisted:
            exc_persisted.remove(obj)
            return None

        if isinstance(obj, _BaseProxy):
            return PICKLE_PID_TYPE_REMOTE_BACKREF, obj._BaseProxy__proxy_def.remote_id

        if issubclass(t_obj, _BaseProxyType):
            return PICKLE_PID_TYPE_REMOTE_BACKREF, t_obj._BaseProxy__proxy_def.remote_id

        rop = self._rop
        remote_obj = rop.get_remote(obj)
        if remote_obj is not None:
            return PICKLE_PID_TYPE_REMOTE_OBJ, remote_obj.remote_id

        if isinstance(obj, BaseException):
            exc_persisted.append(obj)
            return PICKLE_PID_TYPE_REMOTE_EXC_TB, reduce_exception(obj)  # exception with traceback

        if t_obj not in rop._verified_types:
            if t_obj.__module__ not in BUILTIN_MODULES:
                self._verify_types.add((t_obj.__module__, t_obj.__name__))

        return None

    @classmethod
    def dumps(cls, obj, _rop, *args, **kwargs):
        buf = BytesIO()
        pickler = cls(buf, *args, _rop=_rop, **kwargs)
        pickler.dump(obj)
        if logger.getEffectiveLevel() == 1:
            buf.seek(0)
            dis_log = StringIO()
            dis(buf, dis_log)
            logger.debug(dis_log.getvalue())
        return buf.getvalue(), pickler._verify_types


def rebuild_exception(ex, tb):
    if tb:
        setattr(ex, "__traceback__", tb)
    return ex


def reduce_exception(ex):
    return ex, getattr(ex, "__traceback__", None)


def proxy_members(obj, public=True, protected=True, add_callable=True, add_str=True):
    '''
    Return a list of names of methods of `obj` which do not start with '_'
    '''
    methods = []
    fields = []
    spec_fields = {}

    for name in dir(obj):
        is_public = name[0] != '_'
        is_protected = name[0] == '_' and (len(name) == 1 or name[1] != '_')
        is_callable = name == "__call__"
        is_str = name == "__str__"
        if (public and is_public or
                protected and is_protected or
                is_callable and add_callable or
                is_str and add_str):
            member = getattr(obj, name)
            if isinstance(member, CALLABLE_TYPES):
                methods.append(name)
            else:
                fields.append(name)

    if isinstance(obj, BaseException):
        if hasattr(obj, "__cause__"):
            fields.append("__cause__")
        if hasattr(obj, "__traceback__"):
            fields.append("__traceback__")
        if hasattr(obj, "__context__"):
            fields.append("__context__")
        if hasattr(obj, "__suppress_context__"):
            fields.append("__suppress_context__")

    if isinstance(obj, type):
        spec_fields["__qualname__"] = obj.__qualname__

    return methods, fields, spec_fields


class RemoteObjectPipe:

    def expose(self, name, obj, methods=None, fields=None, remote=True, error=False):
        """Same as `RemoteObjectManager.expose`"""
        raise NotImplementedError

    def hide(self, name):
        """Same as `RemoteObjectManager.hide`"""
        raise NotImplementedError

    def register_remote(self, obj, methods=None, fields=None):
        """Same as `RemoteObjectManager.register_remote`"""
        raise NotImplementedError

    def register_remote_type(self, t):
        """Same as `RemoteObjectManager.register_remote_type`"""
        raise NotImplementedError

    def receive(self):
        """Listens for incoming remote requests"""
        raise NotImplementedError

    def close(self, exc=None):
        """Closes current pipe.
        You can optionally attach an exception to pass to the other end of the pipe."""
        raise NotImplementedError

    def remote_close_cause(self):
        raise NotImplementedError

    @classmethod
    def new_pipe(cls):
        return _RemoteObjectSession().new_pipe()


def obj_id(obj):
    if isinstance(obj, type):
        return obj, id(obj)
    return type(obj), id(obj)


class id_dict(dict):
    def __getitem__(self, key):
        key = id(key)
        return super(id_dict, self).__getitem__(key)[1]

    def get(self, key, default=None):
        key = id(key)
        val = super(id_dict, self).get(key, default)
        if val is default:
            return val
        return val[1]

    def __setitem__(self, key, value):
        obj = key
        key = id(key)
        return super(id_dict, self).__setitem__(key, (obj, value))

    def __delitem__(self, key):
        key = id(key)
        return super(id_dict, self).__delitem__(key)

    def __contains__(self, key):
        return super(id_dict, self).__contains__(id(key))

    def keys(self):
        for k, v in super(id_dict, self).items():
            yield v[0]

    def values(self):
        for k, v in super(id_dict, self).items():
            yield v[1]

    def items(self):
        for k, v in super(id_dict, self).items():
            yield v[0], v[1]

    def __iter__(self):
        for k, v in super(id_dict, self).items():
            yield v[0]


class _RemoteObjectSession:
    def __init__(self):
        self._remote_id = 0

        # Mapping name (str): object
        self._exposed_objs = dict()

        # Mapping remote ID (int): object
        self._remote_objs_ids = dict()

        # Mapping object: ProxyDef
        self._remote_objs = id_dict()  # instances to be proxied

        # All types to be always proxied
        self._remote_types = set()  # classes to be proxied

    def new_pipe(self):
        # type:(object) -> _RemoteObjectPipe

        return _RemoteObjectPipe(self)

    def expose(self, name, obj, remote=True, methods=None, fields=None, error=False):
        exposed_objs = self._exposed_objs

        if name in exposed_objs:
            raise ValueError("%r is already exposed" % name)

        if error:
            obj = ExposedObjectError(obj)

        exposed_objs[name] = obj

        if not error and remote:
            self.register_remote(obj, methods, fields)

    def hide(self, name):
        self._exposed_objs.pop(name)

    def register_remote(self, obj, methods=None, fields=None, spec_fields=None):
        remote_id = self._remote_id
        self._remote_id = remote_id + 1

        if methods is None or fields is None or spec_fields is None:
            obj_methods, obj_fields, obj_spec_fields = proxy_members(obj)
            if methods is None:
                methods = obj_methods

            if fields is None:
                fields = obj_fields

            if spec_fields is None:
                spec_fields = obj_spec_fields

        if isinstance(obj, type):
            obj_type = obj
        else:
            obj_type = type(obj)

        proxy = ProxyDef(remote_id, obj_type.__module__, obj_type.__name__, obj_type is obj,
                         methods, fields, spec_fields)

        self._remote_objs[obj] = proxy
        self._remote_objs_ids[remote_id] = obj

        logger.debug("registered proxy %r for %r", proxy, obj_id(obj))
        return proxy

    def register_remote_type(self, t):
        self._remote_types.add(t)

    def get_exposed_by_name(self, name):
        return self._exposed_objs.get(name, None)

    def get_proxy_by_name(self, name):
        obj = self._exposed_objs.get(name, None)
        if obj is not None:
            return self._remote_objs[obj]

        return None

    def get_proxy_by_id(self, remote_id):
        obj = self._remote_objs_ids.get(remote_id, None)
        if obj is None:
            return

        return self._remote_objs[obj]

    def get_remote_obj_by_id(self, remote_id):
        return self._remote_objs_ids.get(remote_id, None)

    def get_remote(self, obj):
        try:
            proxy_def = self._remote_objs.get(obj, None)
        except TypeError:
            return None

        if proxy_def:
            return proxy_def

        if not isinstance(obj, type):
            t_obj = type(obj)
            if t_obj in self._remote_types:
                logger.debug("%r is instance of type %r, which will register as remote", obj_id(obj), t_obj)
                return self.register_remote(obj)

            for remote_type in self._remote_types:
                if isinstance(obj, remote_type):
                    logger.debug("%r is instance of type %r, which will register as remote", obj_id(obj), remote_type)
                    return self.register_remote(obj)
        else:
            if obj in self._remote_types:
                logger.debug("%r will register as remote", obj)
                return self.register_remote(obj)

            for remote_type in self._remote_types:
                if issubclass(obj, remote_type):
                    logger.debug("%r is subtype of type %r, which will register as remote", obj_id(obj), remote_type)
                    return self.register_remote(obj)


class RemoteObjectError(Exception):
    pass


class PipeShutdownError(RemoteObjectError):
    def __init__(self, cause=None):
        self.cause = cause


class ExposedObjectError(RemoteObjectError):
    def __init__(self, cause=None):
        self.cause = cause


class _BaseProxy:
    def __init__(self, __rop, __proxy_def):
        self.__rop = __rop
        self.__proxy_def = __proxy_def


class _BaseProxyType:
    pass


ROP_CLOSE = 0
ROP_CLOSE_CLOSED = 1

ROP_PICKLE_VERSION = 2

ROP_GET_EXPOSED = 5
ROP_GET_EXPOSED_RESULT = 6
ROP_GET_EXPOSED_ERROR = 7

ROP_GET_PROXY_DEF = 10
ROP_GET_PROXY_DEF_RESULT = 11

ROP_VERIFY_TYPES = 14
ROP_VERIFY_TYPES_RESULT = 15

ROP_REMOTE_ACTION = 20
ROP_REMOTE_ACTION_CALL = 21
ROP_REMOTE_ACTION_GETATTR = 22
ROP_REMOTE_ACTION_SETATTR = 23
ROP_REMOTE_ACTION_REMOTE_ERROR = 24
ROP_REMOTE_ACTION_RETURN = 25
ROP_REMOTE_ACTION_EXCEPTION = 26


class _RemoteObjectPipe(RemoteObjectPipe):
    def __init__(self, ros):
        self._returns_pending = 0
        self._remote_close_cause = None

        self._ros = ros  # type: _RemoteObjectSession

        self._conn_c = self._conn_p = None
        self._remote_proxy_defs = {}
        self._remote_proxies = {}
        self._verified_types = set()

        self.id = None
        self.conn = None  # type: ctx.Connection
        self.pickle_version = PICKLE_PROTOCOL_MIN

    def get_exposed(self, exposed_name):
        self._send_obj((ROP_GET_EXPOSED, exposed_name))
        return self._recv()  # type: _BaseProxy

    def get_remote_proxy_def(self, remote_id):
        remote_proxy_defs = self._remote_proxy_defs
        proxy_def = remote_proxy_defs.get(remote_id, None)
        if proxy_def is None:
            proxy_def = self.request_remote_proxy_def(remote_id)
            remote_proxy_defs[remote_id] = proxy_def
        return proxy_def

    def get_remote_proxy(self, proxy_def):
        remote_id = proxy_def.remote_id
        remote_proxies = self._remote_proxies
        remote_proxy = remote_proxies.get(remote_id, None)
        if remote_proxy is None:
            remote_proxy_type = proxy_def.make_proxy_type()

            if proxy_def.is_type:
                remote_proxy = remote_proxy_type
                remote_proxy._BaseProxy__rop = self
                remote_proxy._BaseProxy__proxy_def = proxy_def
            else:
                remote_proxy = remote_proxy_type(self, proxy_def)

            for k, v in proxy_def.spec_fields.items():
                setattr(remote_proxy, k, v)

            remote_proxies[remote_id] = remote_proxy
            logger.debug("registered local proxy for remote ID %d: %r", remote_id, remote_proxy)
        return remote_proxy

    def get_remote(self, obj):
        return self._ros.get_remote(obj)

    def get_remote_obj_by_id(self, remote_id):
        return self._ros.get_remote_obj_by_id(remote_id)

    def expose(self, name, obj, remote=True, methods=None, fields=None, error=False):
        return self._ros.expose(name, obj, remote, methods, fields, error)

    def hide(self, name):
        self._ros.hide(name)

    def register_remote(self, obj, methods=None, fields=None):
        return self._ros.register_remote(obj, methods, fields)

    def register_remote_type(self, t):
        return self._ros.register_remote_type(t)

    def close_client_side(self):
        """Ensures that after the child process is spawned the parent relinquishes FD of the child's side pipe"""
        if self._conn_p and self._conn_c:
            self._conn_c.close()
            self._conn_c = None
            self._conn_p = None

    def close(self, exc=None):
        if not self.conn.closed:
            try:
                self._send_obj((ROP_CLOSE, exc))
                self._recv_obj()
            except PipeShutdownError:
                pass
            finally:
                self._close()

    def _close(self):
        try:
            self.conn.close()
        except OSError:
            pass

    def remote_close_cause(self):
        return self._remote_close_cause

    def __getstate__(self):
        if self.conn:
            raise PickleError("already has been pickled once")

        conn_p, conn_c = ctx.Pipe(True)

        self._conn_p = conn_p
        self._conn_c = conn_c

        self.conn = conn_p
        pipe_id = id(conn_p)
        self.id = ("s", pipe_id)

        return ("r", pipe_id), conn_c, PICKLE_PROTOCOL_MAX

    def __setstate__(self, state):
        self.id = state[0]

        conn = state[1]

        pickle_max = max(PICKLE_PROTOCOL_MAX, state[2])

        self._conn_c = conn
        self._conn_p = None

        self.conn = conn

        self._ros = _RemoteObjectSession()

        self._remote_proxy_defs = {}
        self._remote_proxies = {}
        self._verified_types = set()
        self._remote_close_cause = None

        # Not an error. We HAVE to make sure the first send uses minimally-supported Pickle version

        self.pickle_version = PICKLE_PROTOCOL_MIN
        self._send_obj((ROP_PICKLE_VERSION, pickle_max))
        self.pickle_version = pickle_max

        logger.debug("selected pickle protocol v%r", pickle_max)

    def __repr__(self):
        return "RemoteObjectPipe [id=%r, type=%r, conn=%r, conn_fd=%r]" % (
            self.id,
            "pending" if not self.conn else "parent" if self._conn_p else "client",
            self.conn, self.conn._handle if self.conn and hasattr(self.conn, "_handle") else None)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _recv(self):
        """Returns True if shutdown received, False otherwise"""
        while True:
            data = self._recv_obj()
            action_type = data[0]
            if action_type == ROP_REMOTE_ACTION:
                remote_id = data[1]
                obj = self._ros.get_remote_obj_by_id(remote_id)
                if obj is None:
                    self._send_obj(
                        (ROP_REMOTE_ACTION_REMOTE_ERROR, remote_id, "Remote object %r is gone", (remote_id,)))
                remote_name = data[2]
                remote_name_action = data[3]
                if remote_name_action == ROP_REMOTE_ACTION_CALL:
                    call_args = data[4]
                    call_kwargs = data[5]

                    if isinstance(obj, type) and remote_name.startswith("__"):
                        func = getattr(type(obj), remote_name, None)
                        call_args = [obj] + list(call_args)
                    else:
                        func = getattr(obj, remote_name, None)
                    if not callable(func):
                        self._send_obj((ROP_REMOTE_ACTION_REMOTE_ERROR, remote_id,
                                        "%r is not a callable",
                                        (remote_name,)))

                    logger.debug("calling %r.%r (remote ID %d) with args=%r, kwargs=%r",
                                 remote_name,
                                 obj,
                                 remote_id,
                                 call_args, call_kwargs)

                    return_val = return_exc = None
                    try:
                        return_val = func(*call_args, **call_kwargs)
                    except SystemExit as e:
                        raise e
                    except KeyboardInterrupt as e:
                        raise e
                    except Exception as e:
                        return_exc = e

                    if return_exc is not None:
                        self._send_obj((ROP_REMOTE_ACTION_EXCEPTION, return_exc))
                    else:
                        self._send_obj((ROP_REMOTE_ACTION_RETURN, return_val))
                    continue

                if remote_name_action == ROP_REMOTE_ACTION_GETATTR:
                    return_val = return_exc = None
                    try:
                        return_val = getattr(obj, remote_name, None)
                    except SystemExit as e:
                        raise e
                    except KeyboardInterrupt as e:
                        raise e
                    except Exception as e:
                        return_exc = e

                    if return_exc is not None:
                        self._send_obj((ROP_REMOTE_ACTION_EXCEPTION, return_exc))
                    else:
                        self._send_obj((ROP_REMOTE_ACTION_RETURN, return_val))
                    continue

                if remote_name_action == ROP_REMOTE_ACTION_SETATTR:
                    return_val = return_exc = None
                    try:
                        setattr(obj, remote_name, data[4])
                    except SystemExit as e:
                        raise e
                    except KeyboardInterrupt as e:
                        raise e
                    except Exception as e:
                        return_exc = e

                    if return_exc is not None:
                        self._send_obj((ROP_REMOTE_ACTION_EXCEPTION, return_exc))
                    else:
                        self._send_obj((ROP_REMOTE_ACTION_RETURN, return_val))
                    continue

            if action_type == ROP_VERIFY_TYPES_RESULT:
                new_verified = data[1]
                proxy_types = data[2]
                verified_types = self._verified_types
                pickle_version = self.pickle_version

                for module, name in new_verified:
                    cls = find_class(module, name, pickle_version)
                    verified_types.add(cls)

                for module, name in proxy_types:
                    cls = find_class(module, name, pickle_version)
                    self.register_remote_type(cls)

                return

            if action_type == ROP_VERIFY_TYPES:
                verify_types = data[1]
                need_proxy = []
                new_verified = []
                if verify_types:
                    verified_types = self._verified_types
                    pickle_version = self.pickle_version

                    for module_name in verify_types:
                        module, name = module_name
                        try:
                            cls = find_class(module, name, pickle_version)
                            verified_types.add(cls)
                            new_verified.append(module_name)
                        except Exception:
                            need_proxy.append(module_name)

                self._send_obj((ROP_VERIFY_TYPES_RESULT, new_verified, need_proxy))
                continue

            if action_type == ROP_REMOTE_ACTION_REMOTE_ERROR:
                remote_id = data[1]
                msg = data[2]
                args = data[3]
                raise RemoteObjectError(msg % args)

            if action_type == ROP_REMOTE_ACTION_RETURN:
                return_val = data[1]
                return return_val

            if action_type == ROP_REMOTE_ACTION_EXCEPTION:
                return_exc = data[1]
                raise return_exc

            if action_type == ROP_GET_EXPOSED:
                exposed_name = data[1]
                exposed = self._ros.get_exposed_by_name(exposed_name)
                if isinstance(exposed, ExposedObjectError):
                    self._send_obj((ROP_GET_EXPOSED_ERROR, exposed.cause))
                else:
                    self._send_obj((ROP_GET_EXPOSED_RESULT, exposed))
                continue

            if action_type == ROP_GET_EXPOSED_RESULT:
                return data[1]

            if action_type == ROP_GET_EXPOSED_ERROR:
                raise data[1]

            if action_type == ROP_GET_PROXY_DEF:
                remote_id = data[1]
                proxy_def = self._ros.get_proxy_by_id(remote_id)  # type: ProxyDef
                logger.debug("request for proxy with remote ID %d is returning %r", remote_id, proxy_def)
                self._send_obj((ROP_GET_PROXY_DEF_RESULT, proxy_def))
                continue

            if action_type == ROP_GET_PROXY_DEF_RESULT:
                return data[1]

            if action_type == ROP_CLOSE:
                self._set_remote_close_cause(data[1])
                self._send_obj((ROP_CLOSE_CLOSED, None))

                try:
                    self._recv_obj(suppress_error=True)
                finally:
                    try:
                        self._close()
                    finally:
                        raise PipeShutdownError()

            if action_type == ROP_PICKLE_VERSION:
                self.pickle_version = data[1]
                logger.debug("selected pickle protocol v%r", self.pickle_version)
                return

            raise RuntimeError("received data I can't understand: %r" % (data,))

    receive = _recv

    def request_remote_proxy_def(self, remote_id):
        self._send_obj((ROP_GET_PROXY_DEF, remote_id))
        return self._recv()

    def call(self, remote_id, remote_name, call_args, call_kwargs):
        try:
            self._send_obj((ROP_REMOTE_ACTION, remote_id, remote_name, ROP_REMOTE_ACTION_CALL, call_args, call_kwargs))
            return self._recv()
        except ConnectionError as e:
            raise RemoteObjectError(e)

    def call_getattr(self, remote_id, remote_name):
        try:
            self._send_obj((ROP_REMOTE_ACTION, remote_id, remote_name, ROP_REMOTE_ACTION_GETATTR))
            return self._recv()
        except ConnectionError as e:
            raise RemoteObjectError(e)

    def call_setattr(self, remote_id, remote_name, value):
        try:
            self._send_obj((ROP_REMOTE_ACTION, remote_id, remote_name, ROP_REMOTE_ACTION_SETATTR, value))
            return self._recv()
        except ConnectionError as e:
            raise RemoteObjectError(e)

    def _set_remote_close_cause(self, e):
        if self._remote_close_cause is None:
            self._remote_close_cause = e

    def _dump(self, obj):
        while True:
            buf, verify_types = RemoteObjectPickler.dumps(obj, self)
            if verify_types:
                self._send_obj((ROP_VERIFY_TYPES, verify_types))
                self._recv()
            else:
                return buf

    def _send_obj(self, obj):
        """Send a (picklable) object"""
        self.conn._check_closed()

        buf = self._dump(obj)
        logger.debug("sending %r", obj)
        try:
            self.conn._send_bytes(buf)
        except (ConnectionError, EOFError) as e:
            logger.debug("failed to send %r", obj, exc_info=e)
            try:
                self._set_remote_close_cause(e)
                raise PipeShutdownError()
            finally:
                self._close()

    def _recv_obj(self, suppress_error=False):
        """Receive a (picklable) object"""
        self.conn._check_closed()
        try:
            buf = self.conn._recv_bytes()
        except (ConnectionError, EOFError) as e:
            if suppress_error:
                return

            logger.debug("receive has failed", exc_info=e)
            try:
                self._set_remote_close_cause(e)
                raise PipeShutdownError()
            finally:
                self._close()
        obj = RemoteObjectUnpickler.loads(buf.getvalue(), self)
        logger.debug("received %r", obj)
        return obj


def find_class(module, name, proto):
    if proto < 3 and _compat_pickle:
        if (module, name) in _compat_pickle.NAME_MAPPING:
            module, name = _compat_pickle.NAME_MAPPING[(module, name)]
        elif module in _compat_pickle.IMPORT_MAPPING:
            module = _compat_pickle.IMPORT_MAPPING[module]
    __import__(module, level=0)
    if proto >= 4:
        return _getattribute(sys.modules[module], name)[0]
    else:
        return getattr(sys.modules[module], name)


def _getattribute(obj, name):
    for subpath in name.split('.'):
        if subpath == '<locals>':
            raise AttributeError("Can't get local attribute {!r} on {!r}"
                                 .format(name, obj))
        try:
            parent = obj
            obj = getattr(obj, subpath)
        except AttributeError:
            raise AttributeError("Can't get attribute {!r} on {!r}"
                                 .format(name, obj))
    return obj, parent
