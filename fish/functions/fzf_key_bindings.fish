# Key bindings derived from fzf's fish integration, kept local so the bindings
# are stable across package updates.
function fzf_key_bindings
    function fzf-file-widget -d "List files and folders"
        set -l commandline (__fzf_parse_commandline)
        set -l dir $commandline[1]
        set -l fzf_query $commandline[2]

        set -q FZF_CTRL_T_COMMAND; or set -l FZF_CTRL_T_COMMAND "
    command find -L \$dir -mindepth 1 \\( -path \$dir'*/\\.*' -o -fstype 'sysfs' -o -fstype 'devfs' -o -fstype 'devtmpfs' \\) -prune \
    -o -type f -print \
    -o -type d -print \
    -o -type l -print 2> /dev/null | sed 's@^\./@@'"

        set -q FZF_TMUX_HEIGHT; or set FZF_TMUX_HEIGHT 40%
        begin
            set -lx FZF_DEFAULT_OPTS "--height $FZF_TMUX_HEIGHT --reverse $FZF_DEFAULT_OPTS $FZF_CTRL_T_OPTS"
            eval "$FZF_CTRL_T_COMMAND | "(__fzfcmd)' -m --query "'$fzf_query'"' | while read -l r
                set result $result $r
            end
        end

        if test -z "$result"
            commandline -f repaint
            return
        end

        commandline -t ""
        for i in $result
            commandline -it -- (string escape $i)
            commandline -it -- ' '
        end
        commandline -f repaint
    end

    function fzf-history-widget -d "Show command history"
        set -q FZF_TMUX_HEIGHT; or set FZF_TMUX_HEIGHT 40%
        begin
            set -lx FZF_DEFAULT_OPTS "--height $FZF_TMUX_HEIGHT $FZF_DEFAULT_OPTS --tiebreak=index --bind=ctrl-r:toggle-sort $FZF_CTRL_R_OPTS +m"
            history -z | eval (__fzfcmd) --read0 --print0 -q '(commandline)' | read -lz result
            and commandline -- $result
        end
        commandline -f repaint
    end

    function fzf-cd-widget -d "Change directory"
        set -l commandline (__fzf_parse_commandline)
        set -l dir $commandline[1]
        set -l fzf_query $commandline[2]

        set -q FZF_ALT_C_COMMAND; or set -l FZF_ALT_C_COMMAND "
    command find -L \$dir -mindepth 1 \\( -path \$dir'*/\\.*' -o -fstype 'sysfs' -o -fstype 'devfs' -o -fstype 'devtmpfs' \\) -prune \
    -o -type d -print 2> /dev/null | sed 's@^\./@@'"

        set -q FZF_TMUX_HEIGHT; or set FZF_TMUX_HEIGHT 40%
        begin
            set -lx FZF_DEFAULT_OPTS "--height $FZF_TMUX_HEIGHT --reverse $FZF_DEFAULT_OPTS $FZF_ALT_C_OPTS"
            eval "$FZF_ALT_C_COMMAND | "(__fzfcmd)' +m --query "'$fzf_query'"' | read -l result
            if test -n "$result"
                cd $result
                commandline -t ""
            end
        end

        commandline -f repaint
    end

    function __fzfcmd
        set -q FZF_TMUX; or set FZF_TMUX 0
        set -q FZF_TMUX_HEIGHT; or set FZF_TMUX_HEIGHT 40%
        if test "$FZF_TMUX" -eq 1
            echo "fzf-tmux -d$FZF_TMUX_HEIGHT"
        else
            echo fzf
        end
    end

    bind \ct fzf-file-widget
    bind \cr fzf-history-widget
    bind \ec fzf-cd-widget

    if bind -M insert >/dev/null 2>&1
        bind -M insert \ct fzf-file-widget
        bind -M insert \cr fzf-history-widget
        bind -M insert \ec fzf-cd-widget
    end

    function __fzf_parse_commandline -d "Parse current command line token for fzf"
        set -l commandline (eval "printf '%s' "(commandline -t))

        if test -z "$commandline"
            set dir '.'
            set fzf_query ''
        else
            set dir (__fzf_get_dir $commandline)
            if test "$dir" = "."; and test (string sub -l 1 $commandline) != '.'
                set fzf_query $commandline
            else
                set fzf_query (string replace -r "^$dir/?" '' "$commandline")
            end
        end

        echo $dir
        echo $fzf_query
    end

    function __fzf_get_dir -d "Find longest existing filepath from input"
        set dir $argv
        if test (string length $dir) -gt 1
            set dir (string replace -r '/*$' '' $dir)
        end
        while test ! -d "$dir"
            set dir (dirname "$dir")
        end
        echo $dir
    end
end
