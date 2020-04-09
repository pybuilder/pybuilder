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


from pybuilder.remote import Process, PipeShutdownError, RemoteObjectPipe, logger, log_to_stderr

__all__ = ["RemoteObjectPipe", "start_tool", "Tool", "PipeShutdownError", "logger"]


class Tool:
    def start(self, pipe):
        """Starts the tool in the tool process"""
        pass

    def stop(self, pipe):
        """Stops the tool in the tool process"""
        pass


def start_tool(pyenv, tools, group=None, name=None, logging=None):
    """
    Starts a tool process
    """

    if logging:
        log_to_stderr()
        logger.setLevel(int(logging))

    pipe = RemoteObjectPipe.new_pipe()
    proc = Process(pyenv, group=group, target=_instrumented_tool, name=name, args=(tools, pipe))

    try:
        proc.start()
    finally:
        pipe.close_client_side()

    pipe.receive()  # Pickle protocol selection
    return proc, pipe


def _instrumented_tool(tools, pipe):
    try:
        for tool in tools:
            tool.start(pipe)

        while True:
            pipe.receive()

    except PipeShutdownError:
        for tool in reversed(tools):
            tool.stop(pipe)
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception as e:
        pipe.close(e)
    finally:
        pipe.close()
