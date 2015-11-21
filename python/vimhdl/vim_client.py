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

import logging
import os
import time
import threading
from multiprocessing.pool import ThreadPool

# pylint: disable=import-error
import vim
# pylint: enable=import-error

import vimhdl.project_builder
from vimhdl.static_check import vhdStaticCheck

__logger__ = logging.getLogger(__name__)
__vimhdl_client__ = None

class VimhdlClient(vimhdl.project_builder.ProjectBuilder):
    """Wrapper around vimhdl.project_builder.ProjectBuilder class to
    make the interface between Vim and vim-hdl"""

    _lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        super(VimhdlClient, self).__init__(*args, **kwargs)
        self.startup()

    def startup(self):
        "Wrapper to setup stuff in background"
        if self._lock.locked():
            _postVimWarning("Thread is running, won't do anything")
            return
        _postVimInfo("Running vim-hdl setup")
        threading.Thread(target=self._startupAsync).start()

    def _startupAsync(self):
        "Read configuration file and build project in background"
        with self._lock:
            __logger__.debug("Reading config file")
            self.readConfigFile()
            __logger__.debug("Building by dependency")
            self.buildByDependency()

    def saveCache(self):
        if self._lock.locked():
            _postVimWarning("Build thread is running, waiting until it "
                            "finishes before saving project cache...")
        with self._lock:
            return super(VimhdlClient, self).saveCache()

    def buildSource(self, path, *args, **kwargs):
        "Wrapper around buildByPath to handle UI threading properly"

        try:
            source = self.sources[os.path.abspath(path)]
        except KeyError:
            msg = {
                'checker'        : 'msim',
                'line_number'    : '',
                'column'         : '',
                'filename'       : '',
                'error_number'   : '',
                'error_type'     : 'W',
                'error_message'  : 'File not found in project file'}
            if self._lock.locked():
                msg['error_message'] += ' (setup it still active, try again ' \
                        'after it finishes)'
            return [msg]

        dependencies = set(["%s.%s" % (x['library'], x['unit']) \
                for x in self._translateSourceDependencies(source)])

        self._logger.debug("Source '%s' depends on %s", str(source), \
                ", ".join(["'%s'" % str(x) for x in dependencies]))

        #  if dependencies.issubset(set(self._units_built)):
        #      self._logger.debug("Dependencies for source '%s' are met", \
        #              str(source))
            #  return super(VimhdlClient, self).buildByPath(path)

        if self._lock.locked():
            _postVimWarning("Project setup is still running...")
            return []

        with self._lock:
            return super(VimhdlClient, self).buildByPath(path, *args, **kwargs)

def _getConfigFile():
    """Searches for a valid vimhdl configuration file in buffer vars
    (i.e., inside b:) then in global vars (i.e., inside g:)
    """
    conf_file = None
    if 'vimhdl_conf_file' in vim.current.buffer.vars.keys():
        conf_file = vim.current.buffer.vars['vimhdl_conf_file']
        if os.path.exists(conf_file):
            __logger__.debug("Using config file from buffer dict")
        else:
            __logger__.warning("Buffer config file '%s' is set but not " \
                    "readable", conf_file)
            conf_file = None

    if conf_file is None:
        if 'vimhdl_conf_file' in vim.vars.keys():
            conf_file = vim.vars['vimhdl_conf_file']
            if os.path.exists(conf_file):
                __logger__.debug("Using config file from global dict")
            else:
                __logger__.warning("Global config file '%s' is set but not " \
                        "readable", conf_file)
                conf_file = None

    if conf_file is None:
        __logger__.warning("Couldn't find a valid config file")
        return

    conf_file_full_path = os.path.abspath(os.path.expanduser(conf_file))

    if os.path.exists(conf_file_full_path):
        return conf_file_full_path
    else:
        __logger__.warning("Config file '%s' doesn't exists", conf_file_full_path)

def _getProjectObject():
    "Try to get a valid configuration file and create the project object"
    global __vimhdl_client__ # pylint: disable=global-statement
    if __vimhdl_client__ is None:
        __logger__.debug("__vimhdl_client__ is None!")
        config_file = _getConfigFile()
        __logger__.debug("Config file is '%s'", config_file)
        if config_file:
            __vimhdl_client__ = VimhdlClient(config_file)
    return __vimhdl_client__

#  pylint: disable=missing-docstring
def onBufRead():
    __logger__.debug("[%d] Running actions for event 'onBufRead'", \
        vim.current.buffer.number)

def onBufWrite():
    __logger__.debug("[%d] Running actions for event 'onBufWrite'", \
        vim.current.buffer.number)

def onBufWritePost():
    __logger__.info("Wrote buffer number %d", vim.current.buffer.number)

def onBufEnter():
    __logger__.debug("[%d] Running actions for event 'onBufEnter'", \
        vim.current.buffer.number)

def onBufLeave():
    __logger__.debug("[%d] Running actions for event 'onBufLeave'", \
        vim.current.buffer.number)

def onBufWinEnter():
    global __vimhdl_client__ # pylint: disable=global-statement
    __vimhdl_client__ = _getProjectObject()
    __logger__.debug("[%d] Running actions for event 'onBufWinEnter'", \
        vim.current.buffer.number)

def onBufWinLeave():
    __logger__.debug("[%d] Running actions for event 'onBufWinLeave'", \
        vim.current.buffer.number)

def onFocusGained():
    __logger__.debug("[%d] Running actions for event 'onFocusGained'", \
        vim.current.buffer.number)

def onFocusLost():
    __logger__.debug("[%d] Running actions for event 'onFocusLost'", \
        vim.current.buffer.number)

def onCursorHold():
    __logger__.debug("[%d] Running actions for event 'onCursorHold'", \
        vim.current.buffer.number)

def onCursorHoldI():
    __logger__.debug("[%d] Running actions for event 'onCursorHoldI'", \
        vim.current.buffer.number)

def onWinEnter():
    __logger__.debug("[%d] Running actions for event 'onWinEnter'", \
        vim.current.buffer.number)

def onWinLeave():
    __logger__.debug("[%d] Running actions for event 'onWinLeave'", \
        vim.current.buffer.number)

def onTabEnter():
    __logger__.debug("[%d] Running actions for event 'onTabEnter'", \
        vim.current.buffer.number)

def onTabLeave():
    __logger__.debug("[%d] Running actions for event 'onTabLeave'", \
        vim.current.buffer.number)

def onVimLeave():
    __logger__.debug("[%d] Running actions for event 'onVimLeave'", \
        vim.current.buffer.number)
    if __vimhdl_client__ is not None:
        __vimhdl_client__.saveCache()

def _sortBuildMessages(records):
    return sorted(records, key=lambda x: \
            (x['type'], x['lnum'], x['nr']))

def getMessages(vbuffer):
    start = time.time()

    pool = ThreadPool()
    result = []
    __logger__.info("Getting messages for %s", vbuffer.name)
    static_r = pool.apply_async(runStaticCheck, args=(vbuffer, ))
    build_r = pool.apply_async(buildBuffer, args=(vbuffer, ))

    result += static_r.get()
    result += build_r.get()

    pool.terminate()
    pool.join()

    end = time.time()

    _postVimInfo("Building took %.2fs" % (end - start))
    vim.vars['vimhdl_latest_build_messages'] = vim.List(_sortBuildMessages(result))

# More info on :help getqflist()
def buildBuffer(vbuffer):
    if __vimhdl_client__ is None:
        return vim.List([])
    result = []
    for message in __vimhdl_client__.buildSource(vbuffer.name):
        try:
            vim_fmt_dict = {
                'lnum'     : message['line_number'] or '-1',
                'bufnr'    : vbuffer.number,
                'filename' : message['filename'] or vbuffer.name,
                'valid'    : '1',
                'text'     : message['error_message'] or '<none>',
                'nr'       : message['error_number'] or '0',
                'type'     : message['error_type'] or 'E',
                'col'      : message['column'] or '0'
            }
            __logger__.debug("Vim qf dict: %s", repr(vim_fmt_dict))
            result.append(vim.Dictionary(vim_fmt_dict))
        except: # pylint: disable=bare-except
            __logger__.exception("Error processing message '%s'", str(message))
            _postVimWarning("Error processing message '%s'" % str(message))

    return vim.List(result)

def runStaticCheck(vbuffer):
    result = []
    for message in vhdStaticCheck(vbuffer):
        try:
            vim_fmt_dict = {
                'lnum'     : message['line_number'] or '-1',
                'bufnr'    : vbuffer.number,
                'filename' : message['filename'] or vbuffer.name,
                'valid'    : '1',
                'text'     : message['error_message'] or '<none>',
                'nr'       : message['error_number'] or '-1',
                'type'     : message['error_type'] or 'E',
                'subtype'  : message['error_subtype'] or '',
                'col'      : message['column'] or '-1'
            }
            __logger__.debug("Vim qf dict: %s", repr(vim_fmt_dict))
            result.append(vim.Dictionary(vim_fmt_dict))
        except BaseException:
            __logger__.exception("Error processing message '%s'", str(message))
            _postVimWarning("Error processing message '%s'" % str(message))

    return vim.List(result)

# Vim message functions were "Borrowed" from YCM.
# See https://github.com/Valloric/YouCompleteMe
def _escapeForVim(text):
    return text.replace("'", "''")

def _postVimWarning(message):
    vim.command("redraw | echohl WarningMsg | echom '{0}' | echohl None" \
        .format(_escapeForVim(str(message))))

def _postVimInfo(message):
    vim.command("redraw | echom '{0}' | echohl None" \
        .format(_escapeForVim(str(message))))


