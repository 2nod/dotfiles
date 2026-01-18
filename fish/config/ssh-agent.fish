if status is-interactive
    ssh-add -l >/dev/null 2>&1; or ssh-add --apple-use-keychain "$HOME/.ssh/github" >/dev/null 2>&1
end
