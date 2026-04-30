function fkill --description "Kill a process selected with fzf"
    ps ax -o pid,time,command | fzf --query "$LBUFFER" | awk '{print $1}' | xargs kill
end
