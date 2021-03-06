# This file is part of vim-hdl.
#
# vim-hdl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# vim-hdl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with vim-hdl.  If not, see <http://www.gnu.org/licenses/>.
"Wrapper for vim-hdl usage within Vim's Python interpreter"

import os.path as p
import logging
import subprocess as subp
import time
import os
from multiprocessing import Queue

import vim # pylint: disable=import-error
import vimhdl
import vimhdl.vim_helpers as vim_helpers
from vimhdl.base_requests import (RequestMessagesByPath, RequestQueuedMessages,
                                  RequestHdlccInfo, RequestProjectRebuild)

_logger = logging.getLogger(__name__)

def _sortBuildMessages(records):
    "Sorts the build messages using Vim's terminology"
    for record in records:
        for key in ('lnum', 'nr', 'col'):
            try:
                record[key] = int(record[key])
            except ValueError:
                pass
    records.sort(key=lambda x: (x['type'], x['lnum'], x['col'], x['nr']))
    return records

class VimhdlClient(object):
    "Point of entry of Vim commands"

    def __init__(self, **options):
        self._logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self._logger.info("Creating vimhdl client object...")

        self._server = None
        self._host = options.get('host', 'localhost')
        self._port = options.get('port', vim_helpers.getUnusedLocalhostPort())
        self._server_args = [
            '--log-level', str(options.get('log_level', 'DEBUG')),
            '--log-stream', options.get('log_target', '/tmp/hdlcc.log')
        ]

        self._posted_notifications = []

        self._ui_queue = Queue()

        self._setup()
        self._waitForServerSetup()

        import atexit
        atexit.register(self.shutdown)

    def _postError(self, msg):
        "Post errors to the user once"
        if ('error', msg) not in self._posted_notifications:
            self._posted_notifications += [('error', msg)]
            vim_helpers.postVimWarning(msg)

    def _postWarning(self, msg):
        "Post warnings to the user once"
        if ('warn', msg) not in self._posted_notifications:
            self._posted_notifications += [('warn', msg)]
            vim_helpers.postVimWarning(msg)

    def _isServerAlive(self):
        "Checks if the the server is alive"
        sts = self._server.poll() is None
        if not sts:
            self._postWarning("hdlcc server is not running")
        return sts

    def _setup(self):
        "Launches the hdlcc server"
        self._logger.info("Running vim_hdl client setup")

        vimhdl_path = p.abspath(p.join(p.dirname(__file__), '..', '..'))

        hdlcc_server = p.join(vimhdl_path, 'dependencies', 'hdlcc', 'hdlcc',
                              'code_checker_server.py')

        cmd = [hdlcc_server,
               '--host', self._host,
               '--port', str(self._port),
               '--stdout', '/tmp/hdlcc-stdout.log',
               '--stderr', '/tmp/hdlcc-stderr.log',
               '--attach-to-pid', str(os.getpid())] + \
                self._server_args

        self._logger.info("Starting hdlcc server with '%s'", " ".join(cmd))

        try:
            self._server = subp.Popen(cmd, stdout=subp.PIPE, stderr=subp.PIPE)
            if not self._isServerAlive():
                vim_helpers.postVimError("Failed to launch hdlcc server")
        except subp.CalledProcessError:
            self._logger.exception("Error calling '%s'", " ".join(cmd))

    def _waitForServerSetup(self):
        "Wait for ~10s until the server is actually responding"
        for _ in range(10):
            time.sleep(0.1)
            request = RequestHdlccInfo(self._host, self._port)
            reply = request.sendRequest()
            self._logger.debug(reply)
            if reply:
                self._logger.info("Ok, server is really up")
                return
            else:
                self._logger.info("Server is not responding yet")

        self._postError("Unable to talk to server")

    def shutdown(self):
        "Kills the hdlcc server"
        if not self._isServerAlive():
            self._logger.warning("Server is not running")
            return
        self._logger.debug("Sending shutdown signal")
        self._server.terminate()
        self._logger.debug("Done")

    def _handleAsyncRequest(self, response):
        "Callback passed to asynchronous requests"
        if response is not None:
            self._ui_queue.put(response)

    def _postQueuedMessages(self):
        "Empty our queue in a single message"
        while not self._ui_queue.empty():
            messages = self._ui_queue.get()
            for severity, message in messages.json().get('ui_messages', []):
                if severity == 'info':
                    vim_helpers.postVimInfo(message)
                elif severity == 'warning':
                    vim_helpers.postVimWarning(message)
                elif severity == 'error':
                    vim_helpers.postVimError(message)
                else:
                    vim_helpers.postVimError(
                        "Unknown severity '%s' for message '%s'" %
                        (severity, message))

    def getMessages(self, vim_buffer=None):
        """Returns a list (vim.List) of messages (vim.Dictionary) to
        populate the quickfix list. For more info, check :help getqflist()"""
        if not self._isServerAlive():
            return

        if vim_buffer is None:
            vim_buffer = vim.current.buffer

        project_file = vim_helpers.getProjectFile()
        path = p.abspath(vim_buffer.name)

        request = RequestMessagesByPath(host=self._host, port=self._port,
                                        project_file=project_file, path=path)

        response = request.sendRequest()
        if response is None:
            return

        messages = []
        for message in response.json().get('messages', []):
            vim_fmt_dict = {
                'lnum'     : message['line_number'] or '-1',
                'bufnr'    : vim_buffer.number,
                'filename' : message['filename'] or vim_buffer.name,
                'valid'    : '1',
                'text'     : message['error_message'] or '<none>',
                'nr'       : message['error_number'] or '0',
                'type'     : message['error_type'] or 'E',
                'col'      : message['column'] or '0'
            }
            try:
                vim_fmt_dict['subtype'] = message['error_subtype']
            except KeyError:
                pass

            _logger.info(vim_fmt_dict)

            messages.append(vim_helpers.dict(vim_fmt_dict))

        self.requestUiMessages('getMessages')

        return vim_helpers.list(_sortBuildMessages(messages))

    def requestUiMessages(self, event):
        """Retrieves UI messages from the server and post them with the
        appropriate severity level"""
        self._logger.info("Handling event '%s'. Filetype is %s",
                          event, vim.eval('&filetype'))
        self._postQueuedMessages()

        if not self._isServerAlive():
            return

        project_file = vim_helpers.getProjectFile()

        request = RequestQueuedMessages(self._host, self._port,
                                        project_file=project_file)

        request.sendRequestAsync(self._handleAsyncRequest)

    def getVimhdlInfo(self):
        "Gets info about the current project and hdlcc server"
        project_file = vim_helpers.getProjectFile()
        request = RequestHdlccInfo(host=self._host, port=self._port,
                                   project_file=project_file)

        response = request.sendRequest()

        if response is None:
            return "hdlcc server is not running"

        return "\n".join(["vimhdl version: " + vimhdl.__version__] +
                         ["%s: %s" % (k, v)
                          for k, v in response.json().items()])

    def rebuildProject(self):
        "Rebuilds the current project"
        vim_helpers.postVimInfo("Rebuilding project...")
        project_file = vim_helpers.getProjectFile()
        request = RequestProjectRebuild(host=self._host, port=self._port,
                                        project_file=project_file)

        response = request.sendRequest()

        if response is None:
            return "hdlcc server is not running"

        self._logger.info("Response: %s", repr(response))


