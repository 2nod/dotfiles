function hydro_update_git_on_pwd_change --on-variable PWD
    set --query _hydro_git || return
    set --universal $_hydro_git ""
end
