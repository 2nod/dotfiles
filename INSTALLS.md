# What This Repo Installs

このリポジトリで `nix run .#switch -- <profile>` を実行したときに入るものを、役割ごとに列挙します。

## 注意

- `link_force` は既存のファイルやディレクトリを削除してから symlink を張ります。
- `homebrew.onActivation.cleanup = "uninstall"` が有効なので、`homebrew.casks` から外した GUI アプリは削除対象になります。
- 初回適用前に、少なくとも次のファイルはバックアップ対象として確認してください。
  - `~/.zshenv`
  - `~/.zshrc`
  - `~/.bash_profile`
  - `~/.bashrc`
  - `~/.config/wezterm`
  - `~/.config/karabiner`
  - `~/.config/efm-langserver`
  - `~/.config/fish`
  - `~/.claude/settings.json`
  - `~/.config/nvim`
  - `~/Library/Application Support/Code/User/settings.json`
  - `~/Library/Application Support/Code/User/keybindings.json`
  - `~/Library/Application Support/Cursor/User/settings.json`
  - `~/Library/Application Support/Cursor/User/keybindings.json`
  - `~/.config/codex/config.toml`
  - `~/.config/codex/AGENTS.md`
  - `~/.docker/config.json`

## System

`nix-darwin` 側で適用されるもの。

- `brew-nix.enable = true`
- `homebrew.enable = true`
- `homebrew.onActivation.cleanup = "uninstall"`
- `homebrew.onActivation.autoUpdate = true`
- `homebrew.casks`
  - `aqua-voice`
  - `anki`
  - `arc`
  - `bitwarden`
  - `codex-app`
  - `cursor`
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
- login shell change via `chsh -s ... fish`
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
  - `mise`
  - `claude-code`
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
  - `uv`
  - `wezterm`
  - `yazi`
- `programs.git`
- `programs.direnv`
- `programs.neovim`
- `programs.fish`
- `programs.vscode`
- `programs.cursor`
- `programs.codex`

## Generated Files

Home Manager の activation で生成・差し替えされるもの。

- `~/.config/wezterm`
- `~/.config/karabiner`
- `~/.config/efm-langserver`
- `~/.config/fish`
- `~/.zshenv`
- `~/.zshrc`
- `~/.bash_profile`
- `~/.bashrc`
- `~/.claude/settings.json`
- `~/.config/git/config` and other Home Manager managed files
- `~/Library/Application Support/Code/User/settings.json`
- `~/Library/Application Support/Code/User/keybindings.json`
- `~/Library/Application Support/Cursor/User/settings.json`
- `~/Library/Application Support/Cursor/User/keybindings.json`
- `~/.config/codex/config.toml`
- `~/.config/codex/AGENTS.md`
- `~/.docker/config.json`

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

- casks は `homebrew.casks` に列挙した GUI アプリ
- `homebrew` 自体の挙動は `cleanup = "uninstall"` と `autoUpdate = true`

## どこを見るか

- システム設定: `nix/modules/darwin/system.nix`
- Home Manager のパッケージ: `nix/modules/home/packages.nix`
- Home Manager の各プログラム: `nix/modules/home/programs/`
- dotfiles の symlink: `nix/modules/home/dotfiles.nix`
- profile 切り替え: `nix/modules/profiles/local.nix`
