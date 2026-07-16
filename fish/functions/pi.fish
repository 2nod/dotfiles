function pi --wraps pi --description 'pi with global system-prompt append'
    set -l append "$HOME/.pi/agent/system-append.md"
    switch "$argv[1]"
        case install remove uninstall update list config
            command pi $argv
        case '*'
            if test -f "$append"
                command pi --append-system-prompt "$append" $argv
            else
                command pi $argv
            end
    end
end
