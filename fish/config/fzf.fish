set -gx FZF_DEFAULT_COMMAND 'rg --files --hidden --follow --no-messages --glob "!.git/*"'
set -gx FZF_FIND_FILE_COMMAND $FZF_DEFAULT_COMMAND
set -gx FZF_DEFAULT_OPTS '--extended --cycle --select-1 --height 40% --reverse --border'
set -gx FZF_FIND_FILE_OPTS '--preview "bat --color=always --style=header,grid --line-range :100 {}"'
set -gx FZF_CTRL_R_OPTS "--preview 'echo {}' --preview-window down:3:hidden:wrap --bind '?:toggle-preview'"
set -gx FZF_COMPLETION_TRIGGER '**'
