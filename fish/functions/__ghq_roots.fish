function __ghq_roots --description "Navigate to a ghq-managed repository with fzf"
    set selected (ghq list --full-path | roots | fzf --height 40% --reverse)

    if test -n "$selected"
        cd -- "$selected"
        commandline -f repaint
    end
end
