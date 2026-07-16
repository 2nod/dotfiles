function pi-review --wraps pi --description 'pi in read-only mode (no edits)'
    pi --tools read,grep,find,ls $argv
end
