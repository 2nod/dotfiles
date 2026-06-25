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
  - `~/.claude/settings.json`
  - `~/.config/cmux/settings.json`
  - `~/.config/nvim`
  - `~/Library/Application Support/Code/User/settings.json`
  - `~/Library/Application Support/Code/User/keybindings.json`
  - `~/Library/Application Support/Cursor/User/settings.json`
  - `~/Library/Application Support/Cursor/User/keybindings.json`
  - `~/.config/codex/AGENTS.md`

## System

`nix-darwin` 側で適用されるもの。

- `brew-nix.enable = true`
- `homebrew.enable = true`
- `homebrew.onActivation.cleanup = "uninstall"`
- `homebrew.onActivation.autoUpdate = true`
- `homebrew.onActivation.extraFlags = [ "--force-cleanup" ]`
- `homebrew.casks`
  - `alt-tab`
  - `aqua-voice`
  - `anki`
  - `arc`
  - `bitwarden`
  - `claude`
  - `codex-app`
  - `cmux`
  - `cursor`
  - `cursor-cli`
  - `discord`
  - `google-chrome`
  - `karabiner-elements`
  - `nani`
  - `notion`
  - `obsidian`
  - `orbstack`
  - `raycast`
  - `slack`
  - `typeless`
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
  - `alt-tab`
  - `raycast`
  - `karabiner-elements`
  - `bitwarden`
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
- `home.packages`
  - `bat`
  - `bun`
  - `claude-code`
  - `mise`
  - `codex`
  - `deno`
  - `eza`
  - `gh`
  - `git`
  - `lazygit`
  - `lazydocker`
  - `pnpm`
  - `spotify`
  - `ripgrep`
  - `terraform`
  - `uv`
  - `wezterm`
  - `yazi`
- `programs.git`
- `programs.git.settings.core.hooksPath`
- `programs.git` の pre-push hook で allowlist 以外の `main` / `master` への直接 push を拒否
- `programs.direnv`
- `programs.neovim`
- `programs.fish`
- `programs.delta`
- `programs.lazygit`
- `programs.vscode`
- `programs.cursor`
- `programs.codex`
- `programs.cmux`

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
- `~/.claude/settings.json`
- `~/.config/cmux/settings.json`
- `~/.config/git/config` and other Home Manager managed files
- `~/Library/Application Support/Code/User/settings.json`
- `~/Library/Application Support/Code/User/keybindings.json`
- `~/Library/Application Support/Cursor/User/settings.json`
- `~/Library/Application Support/Cursor/User/keybindings.json`
- `~/.config/lazygit/config.yml`
- `~/.config/codex/AGENTS.md`

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
  - `claude/settings.json`
- `nix/modules/home/programs/neovim/default.nix`
  - `~/.config/nvim`
- `nix/modules/home/programs/vscode/default.nix`
  - `~/Library/Application Support/Code/User/settings.json`
  - `~/Library/Application Support/Code/User/keybindings.json`
- `nix/modules/home/programs/cursor/default.nix`
  - `~/Library/Application Support/Cursor/User/settings.json`
  - `~/Library/Application Support/Cursor/User/keybindings.json`

## Homebrew

`nix-darwin` の `homebrew` 管理で入るもの。
Brewfile は nix-darwin が生成するため、手元で `brew bundle install` / `brew bundle cleanup` は実行しない。

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
- casks は `homebrew.casks` に列挙した GUI アプリ
- `homebrew` 自体の挙動は `cleanup = "uninstall"`、`autoUpdate = true`、`extraFlags = [ "--force-cleanup" ]`

## どこを見るか

- システム設定: `nix/modules/darwin/system.nix`
- Home Manager のパッケージ: `nix/modules/home/packages.nix`
- Home Manager の各プログラム: `nix/modules/home/programs/`
- dotfiles の symlink: `nix/modules/home/dotfiles.nix`
- profile 切り替え: `nix/modules/profiles/local.nix`
