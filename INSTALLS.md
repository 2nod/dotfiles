# What This Repo Installs

このリポジトリで `nix run .#switch -- <profile>` を実行したときに入るものを、役割ごとに列挙します。

## 注意

- `link_force` は既存のファイルやディレクトリを削除してから symlink を張ります。
- `homebrew.onActivation.cleanup = "uninstall"` が有効なので、`homebrew.brews` / `homebrew.casks` から外した formula/cask は削除対象になります。
- 初回適用前に、少なくとも次のファイルはバックアップ対象として確認してください。
  - `~/.zshenv`
  - `~/.zshrc`
  - `~/.bash_profile`
  - `~/.bashrc`
  - `~/.config/wezterm`
  - `~/.config/karabiner`
  - `~/.config/efm-langserver`
  - `~/.config/fish`
  - `~/.config/git/hooks/pre-push`
  - `~/.config/claude/settings.json`
  - `~/.config/cmux/settings.json`
  - `~/.config/nvim`
  - `~/Library/Application Support/Code/User/settings.json`
  - `~/Library/Application Support/Code/User/keybindings.json`
  - `~/Library/Application Support/Cursor/User/settings.json`
  - `~/Library/Application Support/Cursor/User/keybindings.json`
  - `~/.codex/AGENTS.md`
- `~/.config/codex` (symlink to `~/.codex`)

## System

`nix-darwin` 側で適用されるもの。

- `brew-nix.enable = true`
- `homebrew.enable = true`
- `homebrew.onActivation.cleanup = "uninstall"`
- `homebrew.onActivation.autoUpdate = true`
- `homebrew.onActivation.extraFlags = [ "--force-cleanup" ]`
- `homebrew.casks`
  - `alt-tab`
  - `anki`
  - `arc`
  - `bitwarden`
  - `claude`
  - `codex-app`
  - `cmux`
  - `cursor`
  - `cursor-cli`
  - `discord`
  - `ghostty`
  - `google-chrome`
  - `jordanbaird-ice`
  - `karabiner-elements`
  - `nani`
  - `notion`
  - `obsidian`
  - `raycast`
  - `slack`
  - `stats`
  - `swiftbar`
  - `visual-studio-code`
  - `zoom`
- `nix.enable = false`
- `nixpkgs.config.allowUnfree = true`
- `users.users.${user}`
  - home: `/Users/${user}`
  - shell: `fish`
  - `ignoreShellProgramCheck = true`
- `system.primaryUser = user`
- `launchd.user.agents`
  - `colima`
  - `karabiner-elements`
  - `bitwarden`
  - `swiftbar`
  - `stats`
  - アプリ自身のログイン登録が無い、または無効なものだけを置く。AltTab /
    Raycast / Ice は自前で登録する（`sfltool dumpbtm` で enabled）ため入れない
  - `open` を使う agent に `KeepAlive` は付けない（監視対象が `open` であって
    アプリ本体ではないため無意味で、アプリ不在時だけ再試行ループになる）
- `fonts.packages`
  - `udev-gothic`
  - `udev-gothic-nf`
- `system.defaults`
  - Dock
  - Finder
  - `NSGlobalDomain`
  - screenshot settings
  - trackpad settings
  - custom symbolic hotkeys / multitouch settings
- `environment.shells = [ pkgs.fish ]`
- login shell change via `chsh -s ... fish` only when current shell is not already fish
- Rosetta 2 install only when enabled by profile and not already installed
- `system.configurationRevision`
- `system.stateVersion = 6`
- `nixpkgs.hostPlatform`
- optional `networking.hostName` / `computerName` / `localHostName` when `hostName` is set in a profile

## Home Manager

`home-manager` 側で適用されるもの。

- `home.stateVersion = "24.11"`
- `programs.home-manager.enable = true`
- `home.packages` (`nix/modules/home/packages.nix`)
  - `bat`
  - `bun`
  - `mise`
  - `deno`
  - `eza`
  - `fzf`
  - `gh`
  - `ghq`
  - `lazygit`
  - `colima`
  - `docker_29`
  - `lazydocker`
  - `google-cloud-sdk`
  - `pnpm`
  - `spotify`
  - `starship`
  - `ripgrep`
  - `roots`
  - `terraform`
  - `pyright`
  - `ruff`
  - `uv`
  - `wezterm`
  - `yazi`
  - `zoxide`
- ツール固有のパッケージは `nix/modules/home/programs/<tool>/` 側で入る
  - `ai-tools.nix`: `cursor-agent` / `opencode` / `pi`
  - `claude-code/`: `claude-code`
  - `codex.nix`: `codex`
  - `neovim.nix`: `efm-langserver` / `hadolint` / `oxfmt` / `oxlint` / `telescope-fzf-native-nvim` / `typescript-go`
- `programs.git`
- `programs.git.settings.core.hooksPath`
- `programs.git` の pre-push hook で allowlist 以外の `main` / `master` への直接 push を拒否
- `programs.direnv`
- `programs.neovim`
- `programs.fish`
- `programs.delta`
- `programs.lazygit`
- `programs.vscode`
- `programs.cursor` / `cursor-ide.nix`
- `programs.codex`
- `programs.cmux`
- `claude-code/`
- `ghostty.nix`
- `colima.nix`
- `herdr.nix`
- `pi.nix`
- `starship.nix`
- `ai-tools.nix`
- `swiftbar.nix`
  - `targets.darwin.defaults."com.ameba.SwiftBar".PluginDirectory` を `~/dotfiles/swiftbar/plugins` に固定
  - plugin 本体は `swiftbar/plugins/` にコミットした実ファイル（`colima.30s.sh`）
- `ice.nix`
  - `targets.darwin.defaults."com.jordanbaird.Ice"` に Ice の挙動スカラ値を宣言
  - アイコンの仕分けは各アプリの `NSStatusItem Preferred Position` に入るため宣言対象外
- `stats.nix`
  - `targets.darwin.defaults."eu.exelban.Stats".CombinedModules` のみ宣言
  - ウィジェット構成は Stats 自身が同じドメインに書くため、意図的に広げていない

## Generated Files

Home Manager の activation で生成・差し替えされるもの。

- `~/.config/wezterm`
- `~/.config/karabiner`
- `~/.config/efm-langserver`
- `~/.config/fish`
- `~/.config/git/hooks/pre-push`
- `~/.config/git/hooks/pre-push.allowlist`
- `~/.zshenv`
- `~/.zshrc`
- `~/.bash_profile`
- `~/.bashrc`
- `~/.config/claude/settings.json`
- `~/.config/cmux/settings.json`
- `~/.config/git/config` and other Home Manager managed files
- `~/Library/Application Support/Code/User/settings.json`
- `~/Library/Application Support/Code/User/keybindings.json`
- `~/Library/Application Support/Cursor/User/settings.json`
- `~/Library/Application Support/Cursor/User/keybindings.json`
- `~/.config/lazygit/config.yml`
- `~/.codex/AGENTS.md`
- `~/.config/codex` (symlink to `~/.codex`)
- `~/.config/claude/CLAUDE.md`
- `~/.config/ghostty/config` と `~/Library/Application Support/com.mitchellh.ghostty/config`
- `~/.config/herdr/config.toml`
- `~/.config/starship.toml`
- `~/.pi/agent/system-append.md` / `~/.pi/agent/model-router.json`
- agent skills (`nix/modules/home/agent-skills.nix`)
  - `~/.agents/skills`
  - `~/.cursor/skills`
  - `~/.config/claude/skills/dotfiles-shared-skills`

## link_force

`link_force` は既存ファイルを消してから symlink を張ります。

- `nix/modules/home/dotfiles.nix`
  - `wezterm`
  - `karabiner`
  - `efm-langserver`
  - `fish`
  - `zsh/zshenv`
  - `zsh/zshrc`
  - `bash/.bash_profile`
  - `bash/.bashrc`
- `nix/modules/home/programs/neovim.nix`
  - `~/.config/nvim`
- `nix/modules/home/programs/vscode.nix`
  - `~/Library/Application Support/Code/User/settings.json`
  - `~/Library/Application Support/Code/User/keybindings.json`
- `nix/modules/home/programs/cursor-ide.nix`
  - `~/Library/Application Support/Cursor/User/settings.json`
  - `~/Library/Application Support/Cursor/User/keybindings.json`
- `nix/modules/home/programs/ghostty.nix`
  - `~/Library/Application Support/com.mitchellh.ghostty/config`

## Homebrew

`nix-darwin` の `homebrew` 管理で入るもの。
Brewfile は nix-darwin が生成するため、手元で `brew bundle install` / `brew bundle cleanup` は実行しない。

- taps
  - `modem-dev/tap`
- brews
  - `pkg-config`
  - `cairo`
  - `pango`
  - `libomp`
  - `libpng`
  - `jpeg`
  - `giflib`
  - `librsvg`
  - `pixman`
  - `python-setuptools`
  - `yarn`
  - `hunk`
  - `herdr`
- casks は `homebrew.casks` に列挙した GUI アプリ
- `homebrew` 自体の挙動は `cleanup = "uninstall"`、`autoUpdate = true`、`extraFlags = [ "--force-cleanup" ]`

## どこを見るか

- システム設定: `nix/modules/darwin/system.nix`
- Home Manager のパッケージ: `nix/modules/home/packages.nix`
- Home Manager の各プログラム: `nix/modules/home/programs/`
- dotfiles の symlink: `nix/modules/home/dotfiles.nix`
- profile 切り替え: `nix/modules/profiles/local.nix`
