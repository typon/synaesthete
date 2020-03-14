hi def synaestheteLocal           ctermfg=209 guifg=#ff875f
hi def synaestheteGlobal          ctermfg=214 guifg=#ffaf00
hi def synaestheteImported        ctermfg=214 guifg=#ffaf00 cterm=bold gui=bold
hi def synaestheteParameter       ctermfg=75  guifg=#5fafff
hi def synaestheteParameterUnused ctermfg=117 guifg=#87d7ff cterm=underline gui=underline
hi def synaestheteFree            ctermfg=218 guifg=#ffafd7
hi def synaestheteBuiltin         ctermfg=207 guifg=#ff5fff
hi def synaestheteAttribute       ctermfg=49  guifg=#00ffaf
hi def synaestheteSelf            ctermfg=249 guifg=#b2b2b2
hi def synaestheteUnresolved      ctermfg=226 guifg=#ffff00 cterm=underline gui=underline
hi def synaestheteSelected        ctermfg=231 guifg=#ffffff ctermbg=161 guibg=#d7005f


" These options can't be initialized in the Python plugin since they must be
" known immediately.
let g:synaesthete#filetypes = get(g:, 'synaesthete#filetypes', ['python'])
let g:synaesthete#simplify_markup = get(g:, 'synaesthete#simplify_markup', v:true)
let g:synaesthete#no_default_builtin_highlight = get(g:, 'synaesthete#no_default_builtin_highlight', v:true)

" function! s:simplify_markup()
"     autocmd FileType python call s:simplify_markup_extra()

"     " For python-syntax plugin
"     let g:python_highlight_operators = 0
" endfunction

" function! s:simplify_markup_extra()
"     hi link pythonConditional pythonStatement
"     hi link pythonImport pythonStatement
"     hi link pythonInclude pythonStatement
"     hi link pythonRaiseFromStatement pythonStatement
"     hi link pythonDecorator pythonStatement
"     hi link pythonException pythonStatement
"     hi link pythonConditional pythonStatement
"     hi link pythonRepeat pythonStatement
" endfunction

" function! s:disable_builtin_highlights()
"     autocmd FileType python call s:remove_builtin_extra()
"     let g:python_no_builtin_highlight = 1
"     hi link pythonBuiltin NONE
"     let g:python_no_exception_highlight = 1
"     hi link pythonExceptions NONE
"     hi link pythonAttribute NONE
"     hi link pythonDecoratorName NONE

"     " For python-syntax plugin
"     let g:python_highlight_class_vars = 0
"     let g:python_highlight_builtins = 0
"     let g:python_highlight_exceptions = 0
"     hi link pythonDottedName NONE
" endfunction

" function! s:remove_builtin_extra()
"     syn keyword pythonKeyword True False None
"     hi link pythonKeyword pythonNumber
" endfunction

function! s:filetype_changed()
    let l:ft = expand('<amatch>')
    if index(g:synaesthete#filetypes, l:ft) != -1
        if !get(b:, 'synaesthete_attached', v:false)
            SynaestheteEnable
        endif
    else
        if get(b:, 'synaesthete_attached', v:false)
            SynaestheteDisable
        endif
    endif
endfunction

function! synaesthete#buffer_attach()
    if get(b:, 'synaesthete_attached', v:false)
        return
    endif
    let b:synaesthete_attached = v:true
    augroup SynaestheteEvents
        " autocmd BufEnter <buffer> call SynaestheteBufEnter(+expand('<abuf>'), line('w0'), line('w$'))
        autocmd CursorMoved <buffer> call SynaestheteCursorMoved(line('w0'), line('w$'))
        autocmd CursorMovedI <buffer> call SynaestheteCursorMoved(line('w0'), line('w$'))
    augroup END
    " call SynaestheteBufEnter(bufnr('%'), line('w0'), line('w$'))
endfunction

function! synaesthete#buffer_detach()
    let b:synaesthete_attached = v:false
    augroup SynaestheteEvents
        autocmd! BufEnter <buffer>
        autocmd! CursorMoved <buffer>
        autocmd! CursorMovedI <buffer>
    augroup END
endfunction

function! synaesthete#init()
    " if g:synaesthete#no_default_builtin_highlight
    "     call s:disable_builtin_highlights()
    " endif
    " if g:synaesthete#simplify_markup
    "     call s:simplify_markup()
    " endif

    autocmd FileType * call s:filetype_changed()
    autocmd BufWipeout * call SynaestheteBufWipeout(+expand('<abuf>'))
endfunction

call synaesthete#init()
