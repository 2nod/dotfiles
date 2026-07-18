function hks --description "Switch the live hunk session's source (wt/staged/ref/range), or clean zombies"
    if test "$argv[1]" = clean
        set -l zombies
        for pid in (hunk session list --json | jq -r '.sessions[].pid')
            if test "$(ps -o tty= -p $pid | string trim)" = "??"
                set -a zombies $pid
            end
        end
        if test (count $zombies) -eq 0
            echo "no zombie hunk sessions"
        else
            kill $zombies
            echo "killed zombie hunk session(s): $zombies"
        end
        return
    end

    set -l cmd diff
    switch "$argv[1]"
        case '' wt
            set cmd diff
        case staged s
            set cmd diff --staged
        case '*..*'
            set cmd diff $argv[1]
        case '*'
            if git show-ref --verify --quiet refs/heads/$argv[1]; or git show-ref --verify --quiet refs/remotes/$argv[1]
                set cmd diff $argv[1]...HEAD
            else
                set cmd show $argv[1]
            end
    end

    set -l repo (git rev-parse --show-toplevel) || return
    set -l ids (hunk session list --json | jq -r --arg repo $repo \
        '[.sessions[] | select(.repoRoot == $repo)] | sort_by(.launchedAt) | reverse | .[] | [.sessionId, .terminal.locations[0].tty // "?", .title] | @tsv')

    switch (count $ids)
        case 0
            echo "hks: no live hunk session for $repo" >&2
            return 1
        case 1
            hunk session reload --repo $repo -- $cmd
        case '*'
            set -l picked (printf '%s\n' $ids | fzf --with-nth 2.. --prompt "hunk session> ") || return
            hunk session reload (string split \t $picked)[1] -- $cmd
    end
end
