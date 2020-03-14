"A minimal vimrc for development

syntax on
set nocompatible
colorscheme zellner

set noswapfile
set hidden
set tabstop=8
set shiftwidth=4
set softtabstop=4
set smarttab
set expandtab
set number

let &runtimepath .= ',' . getcwd()
let $NVIM_RPLUGIN_MANIFEST = './dev/rplugin.vim'

let mapleader = ','

noremap <silent> <S-j> 4j
noremap <silent> <S-k> 4k
noremap <silent> q :q<CR>
noremap <silent> Q :qa!<CR>
noremap <silent><C-tab> :bnext<CR>
noremap <silent><C-S-tab> :bprev<CR>


function! SynStack()
    if !exists('*synstack')
        return
    endif
    echo map(synstack(line('.'), col('.')), "synIDattr(v:val, 'name')")
endfunc
nnoremap <leader>v :call SynStack()<CR>


let $SYNAESTHETE_LOG_FILE = '/tmp/synaesthete.log'
let $SYNAESTHETE_LOG_LEVEL = 'DEBUG'

let g:synaesthete#error_sign_delay = 0.5

" nmap <silent> <leader>rr :Synaesthete rename<CR>
" nmap <silent> <Tab> :Synaesthete goto name next<CR>
" nmap <silent> <S-Tab> :Synaesthete goto name prev<CR>

" nmap <silent> <C-n> :Synaesthete goto class next<CR>
" nmap <silent> <C-p> :Synaesthete goto class prev<CR>

" nmap <silent> <C-a> :Synaesthete goto function next<CR>
" nmap <silent> <C-x> :Synaesthete goto function prev<CR>

" nmap <silent> <leader>ee :Synaesthete error<CR>
" nmap <silent> <leader>ge :Synaesthete goto error<CR>
