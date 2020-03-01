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

from io import BytesIO, StringIO  # noqa: E402
from pickle import PickleError, Unpickler, UnpicklingError  # noqa: E402
from pickletools import dis  # noqa: E402

from pybuilder.remote._remote_weak import WeakKeyDictionary, WeakSet, WeakValueDictionary  # noqa: E402
from pybuilder.python_utils import (mp_get_context,
                                    mp_ForkingPickler as ForkingPickler,
                                    mp_log_to_stderr as log_to_stderr,
                                    PY2,
                                    IS_WIN)  # noqa: E402

PICKLE_PROTOCOL = 2

if PY2:
    ConnectionError = EnvironmentError

ctx = mp_get_context("spawn")
ctx.allow_connection_pickling()
logger = ctx.get_logger()

__all__ = ["RemoteObjectManager", "RemoteObjectPipe", "RemoteObjectError",
           "get_rom", "ctx", "proxy_members", "PipeShutdownError", "log_to_stderr"]


def get_rom():
    # type: () -> RemoteObjectManager
    cp = ctx.current_process()
    cp_rom = getattr(cp, "_rom", None)
    if not cp_rom:
        cp_rom = _RemoteObjectManager()
        setattr(cp, "_rom", cp_rom)
    return cp_rom


class ProxyDef:
    def __init__(self, remote_id, type_name, methods, fields):
        self.remote_id = remote_id
        self.type_name = type_name
        self.methods = methods
        self.fields = fields

    def __repr__(self):
        return "ProxyDef[remote_id=%r, type_name=%r, methods=%r, fields=%r]" % (self.remote_id, self.type_name,
                                                                                self.methods, self.fields)


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
        file = BytesIO(buf)
        return cls(file, *args, _rop=_rop, **kwargs).load()


_PICKLE_SKIP_PID_CHECK_TYPES = {type(None), bool, int, float, str, bytes, bytearray, list, tuple, dict, set}


class RemoteObjectPickler(ForkingPickler, object):

    def __init__(self, *args, **kwargs):
        self._rop = kwargs.pop("_rop")  # type: _RemoteObjectPipe
        if PY2:
            kwargs["protocol"] = PICKLE_PROTOCOL  # This is for full backwards compatibility with Python 2
            super(RemoteObjectPickler, self).__init__(*args, **kwargs)
        else:
            super(RemoteObjectPickler, self).__init__(args[0], PICKLE_PROTOCOL, *args[1:])

    def persistent_id(self, obj, exc_persisted=[]):  # Mutable default is intentional here
        if type(obj) in _PICKLE_SKIP_PID_CHECK_TYPES:
            return None

        # This is a weird trick. Since we need
        if obj in exc_persisted:
            exc_persisted.remove(obj)
            return None

        if isinstance(obj, _BaseProxy):
            return PICKLE_PID_TYPE_REMOTE_BACKREF, obj._BaseProxy__proxy_def.remote_id

        rop = self._rop
        remote_obj = rop.get_remote(obj)
        if remote_obj is not None:
            return PICKLE_PID_TYPE_REMOTE_OBJ, remote_obj.remote_id

        if isinstance(obj, BaseException):
            exc_persisted.append(obj)
            return PICKLE_PID_TYPE_REMOTE_EXC_TB, reduce_exception(obj)  # exception with traceback

        return None

    @classmethod
    def dumps(cls, obj, _rop, *args, **kwargs):
        buf = BytesIO()
        cls(buf, *args, _rop=_rop, **kwargs).dump(obj)
        if logger.getEffectiveLevel() == 1:
            buf.seek(0)
            dis_log = StringIO()
            dis(buf, dis_log)
            logger.debug(dis_log.getvalue())
        return buf.getvalue()


def rebuild_exception(ex, tb):
    if tb:
        setattr(ex, "__traceback__", tb)
    return ex


def reduce_exception(ex):
    return ex, getattr(ex, "__traceback__", None)


#
# Functions for finding the method names of an object
#

def proxy_members(obj, public=True, protected=True, add_callable=True, add_str=True):
    '''
    Return a list of names of methods of `obj` which do not start with '_'
    '''
    methods = []
    fields = []
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
            if callable(member):
                methods.append(name)
            else:
                fields.append(name)
    return methods, fields


class RemoteObjectManager:
    def new_pipe(self):
        """Creates new remote object pipe that can expose remote objects"""
        raise NotImplementedError

    def expose(self, name, obj, methods=None, fields=None, remote=True):
        """Exposes the object as a remote under the specified name
        If `remote` is False, the object will be pickled but will not be a remote.
        """
        raise NotImplementedError

    def hide(self, name):
        """Stops exposing remote object"""
        raise NotImplementedError

    def register_remote(self, obj, methods=None, fields=None):
        """Registers an object as a remote but doesn't expose it"""
        raise NotImplementedError

    def register_remote_type(self, t):
        """Registers all objects of this type (isinstance) as remote"""
        raise NotImplementedError


class RemoteObjectPipe:
    def expose(self, name, obj, methods=None, fields=None, remote=True):
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


def obj_id(obj):
    return type(obj), id(obj)


class _RemoteObjectManager(RemoteObjectManager):
    def __init__(self):
        self._remote_id = 0

        # Mapping name (str): object
        self._exposed_objs = dict()

        # Mapping remote ID (int): object
        self._remote_objs_ids = WeakValueDictionary()

        # Mapping object: ProxyDef
        self._remote_objs = WeakKeyDictionary()  # instances to be proxied

        # All types to be always proxied
        self._remote_types = WeakSet()  # classes to be proxied

    def new_pipe(self):
        # type:(object) -> _RemoteObjectPipe

        return _RemoteObjectPipe(self)

    def expose(self, name, obj, remote=True, methods=None, fields=None):
        exposed_objs = self._exposed_objs

        if name in exposed_objs:
            raise ValueError("%r is already exposed" % name)
        exposed_objs[name] = obj
        if remote:
            self.register_remote(obj, methods, fields)

    def hide(self, name):
        self._exposed_objs.pop(name)

    def register_remote(self, obj, methods=None, fields=None):
        remote_id = self._remote_id
        self._remote_id = remote_id + 1

        if methods is None or fields is None:
            obj_methods, obj_fields = proxy_members(obj)
            if methods is None:
                methods = obj_methods

            if fields is None:
                fields = obj_fields

        obj_type = type(obj)
        proxy = ProxyDef(remote_id, obj_type.__module__ + "." + obj_type.__name__, methods, fields)

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

        t_obj = type(obj)
        if t_obj in self._remote_types:
            logger.debug("%r is type %r, which will register as remote", obj_id(obj), t_obj)
            return self.register_remote(obj)

        for remote_type in self._remote_types:
            if isinstance(obj, remote_type):
                logger.debug("%r is instance of type %r, which will register as remote", obj_id(obj), t_obj)
                return self.register_remote(obj)


class RemoteObjectError(Exception):
    pass


class PipeShutdownError(RemoteObjectError):
    def __init__(self, cause=None):
        self.cause = cause


class _BaseProxy:
    def __init__(self, __rom, __rop, __proxy_def):
        self.__rom = __rom
        self.__rop = __rop
        self.__proxy_def = __proxy_def


def _make_proxy_type(proxy_def):
    '''
    Return a proxy type whose methods are given by `exposed`
    '''
    remote_id = proxy_def.remote_id
    methods = tuple(proxy_def.methods)
    fields = tuple(proxy_def.fields)
    dic = {}

    for meth in methods:
        exec('''def %s(self, *args, **kwargs):
        return self._BaseProxy__rop.call(%r, %r, args, kwargs)''' % (meth, remote_id, meth), dic)

    for field in fields:
        exec("""
def %s_getter(self):
    return self._BaseProxy__rop.call_getattr(%r, %r)

def %s_setter(self, value):
    return self._BaseProxy__rop.call_setattr(%r, %r, value)

%s = property(%s_getter, %s_setter)""" % (field, remote_id, field, field, remote_id, field, field, field, field), dic)

    proxy_type = type(proxy_def.type_name, (_BaseProxy, object), dic)
    proxy_type.__methods__ = methods
    proxy_type.__fields__ = fields
    return proxy_type


ROP_CLOSE = 0
ROP_CLOSE_CLOSED = 1

ROP_GET_EXPOSED = 5
ROP_GET_EXPOSED_RESULT = 6

ROP_GET_PROXY_DEF = 7
ROP_GET_PROXY_DEF_RESULT = 8

ROP_REMOTE_ACTION = 10
ROP_REMOTE_ACTION_CALL = 11
ROP_REMOTE_ACTION_GETATTR = 12
ROP_REMOTE_ACTION_SETATTR = 13
ROP_REMOTE_ACTION_REMOTE_ERROR = 14
ROP_REMOTE_ACTION_RETURN = 15
ROP_REMOTE_ACTION_EXCEPTION = 16


class _RemoteObjectPipe(RemoteObjectPipe):
    def __init__(self, rom):
        self._returns_pending = 0
        self._remote_close_cause = None

        self._rom = rom  # type: _RemoteObjectManager

        self._conn_c = self._conn_p = None
        self._remote_proxy_defs = {}
        self._remote_proxies = {}

        self.id = None
        self.conn = None  # type: ctx.Connection

    def __del__(self):  # noqa
        # DO NOT REMOVE
        # This is required on Python 2.7 to ensure that the object is properly GC'ed
        # and that there isn't an attempt to close an FD with a stale object
        pass

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
            remote_proxy_type = _make_proxy_type(proxy_def)
            remote_proxy = remote_proxy_type(self._rom, self, proxy_def)
            remote_proxies[remote_id] = remote_proxy
            logger.debug("registered local proxy for remote ID %d: %r", remote_id, remote_proxy)
        return remote_proxy

    def get_remote(self, obj):
        return self._rom.get_remote(obj)

    def get_remote_obj_by_id(self, remote_id):
        return self._rom.get_remote_obj_by_id(remote_id)

    def expose(self, name, obj, remote=True, methods=None, fields=None):
        return self._rom.expose(name, obj, remote, methods, fields)

    def hide(self, name):
        self._rom.hide(name)

    def register_remote(self, obj, methods=None, fields=None):
        return self._rom.register_remote(obj, methods, fields)

    def register_remote_type(self, t):
        return self._rom.register_remote_type(t)

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

        return ("r", pipe_id), conn_c

    def __setstate__(self, state):
        self.id = state[0]

        conn = state[1]
        self._conn_c = conn
        self._conn_p = None

        self.conn = conn

        self._rom = get_rom()

        self._remote_proxy_defs = {}
        self._remote_proxies = {}
        self._remote_close_cause = None

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
                obj = self._rom.get_remote_obj_by_id(remote_id)
                if obj is None:
                    self._send_obj(
                        (ROP_REMOTE_ACTION_REMOTE_ERROR, remote_id, "Remote object %r is gone", (remote_id,)))
                remote_name = data[2]
                remote_name_action = data[3]
                if remote_name_action == ROP_REMOTE_ACTION_CALL:
                    func = getattr(obj, remote_name, None)
                    if not callable(func):
                        self._send_obj((ROP_REMOTE_ACTION_REMOTE_ERROR, remote_id,
                                        "%r is not a callable",
                                        (remote_name,)))
                    call_args = data[4]
                    call_kwargs = data[5]

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
                exposed = self._rom.get_exposed_by_name(exposed_name)
                self._send_obj((ROP_GET_EXPOSED_RESULT, exposed))
                continue

            if action_type == ROP_GET_EXPOSED_RESULT:
                return data[1]

            if action_type == ROP_GET_PROXY_DEF:
                remote_id = data[1]
                proxy_def = self._rom.get_proxy_by_id(remote_id)  # type: ProxyDef
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

    if PY2 and IS_WIN:
        # Python 2 on Windows uses Python multiprocessing

        def _send_obj(self, obj):
            """Send a (picklable) object"""
            logger.debug("sending %r", obj)
            if self.conn.closed:
                raise OSError("handle is closed")
            try:
                self.conn.send_bytes(RemoteObjectPickler.dumps(obj, self))
            except (ConnectionError, EOFError) as e:
                logger.debug("failed to send %r", obj, exc_info=e)
                try:
                    self._set_remote_close_cause(e)
                    raise PipeShutdownError()
                finally:
                    self._close()

        def _recv_obj(self, suppress_error=False):
            """Receive a (picklable) object"""
            if self.conn.closed:
                raise OSError("handle is closed")
            try:
                buf = self.conn.recv_bytes()
            except (ConnectionError, EOFError) as e:
                if suppress_error:
                    return

                logger.debug("receive has failed", exc_info=e)
                try:
                    self._set_remote_close_cause(e)
                    raise PipeShutdownError()
                finally:
                    self._close()
            obj = RemoteObjectUnpickler.loads(buf, self)
            logger.debug("received %r", obj)
            return obj
    else:
        # Python 2 on Linux uses Billiard that is API-compatible with Python 3
        def _send_obj(self, obj):
            """Send a (picklable) object"""
            logger.debug("sending %r", obj)
            self.conn._check_closed()
            try:
                self.conn._send_bytes(RemoteObjectPickler.dumps(obj, self))
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
