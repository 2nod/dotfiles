function fish_user_key_bindings
    bind \cx\ck fkill
    bind \cb git_switch_branch
    bind \cg __ghq_roots

    if bind -M insert >/dev/null 2>&1
        bind -M insert \cg __ghq_roots
    end

    fzf_key_bindings
end
