" This file is part of vim-hdl.
"
" vim-hdl is free software: you can redistribute it and/or modify
" it under the terms of the GNU General Public License as published by
" the Free Software Foundation, either version 3 of the License, or
" (at your option) any later version.
"
" vim-hdl is distributed in the hope that it will be useful,
" but WITHOUT ANY WARRANTY; without even the implied warranty of
" MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
" GNU General Public License for more details.
"
" You should have received a copy of the GNU General Public License
" along with vim-hdl.  If not, see <http://www.gnu.org/licenses/>.
"
"============================================================================
" For Syntastic license, check http://sam.zoy.org/wtfpl/COPYING
"============================================================================

" FIXME: Commands aren't working for a while!
" " { Vimhdl commands
" command! VimhdlRebuildProject                  call vimhdl#rebuildProject()
" command! VimhdlListLibraries                   call vimhdl#listLibraries()
" command! VimhdlListLibrariesAndSources         call vimhdl#listLibrariesAndSources()
" command! VimhdlViewLog                         call vimhdl#viewLog()
" command! VimhdlCleanProjectCache               call vimhdl#cleanProjectCache()

" command! -nargs=? VimhdlAddSourceToLibrary call vimhdl#addSourceToLibrary(<f-args>)
" command! -nargs=? VimhdlRemoveSourceFromLibrary call vimhdl#removeSourceFromLibrary(<f-args>)
" " }
"
call vimhdl#setup()

" { Autocommands
autocmd! BufWritePost *.vhd :py vimhdl_client.requestUiMessages()
autocmd! BufEnter     *.vhd :py vimhdl_client.requestUiMessages()
autocmd! BufLeave     *.vhd :py vimhdl_client.requestUiMessages()
autocmd! FocusGained  *.vhd :py vimhdl_client.requestUiMessages()
autocmd! CursorMoved  *.vhd :py vimhdl_client.requestUiMessages()
autocmd! CursorMovedI *.vhd :py vimhdl_client.requestUiMessages()
autocmd! CursorHold   *.vhd :py vimhdl_client.requestUiMessages()
autocmd! CursorHoldI  *.vhd :py vimhdl_client.requestUiMessages()
autocmd! InsertLeave  *.vhd :py vimhdl_client.requestUiMessages()


" }

" vim: set foldmarker={,} foldlevel=0 foldmethod=marker :
