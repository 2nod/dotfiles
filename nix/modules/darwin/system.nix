{
  self,
  lib,
  user,
  hostSystem,
  pkgs,
  profile ? { },
  ...
}:
let
  profileColima = profile.colima or { };
  colima = {
    vmType = (profileColima.vmType or "vz");
    rosetta = (profileColima.rosetta or false);
  };
  installRosetta = colima.vmType == "vz" && colima.rosetta;
in
{
  brew-nix.enable = true;

  # brew-nix casks are defined in nix/modules/darwin/packages.nix (home-manager).
  # Homebrew is managed here for casks that are fragile under brew-nix.
  homebrew = {
    enable = true;
    taps = [
      "modem-dev/tap"
    ];
    onActivation = {
      cleanup = "uninstall";
      autoUpdate = true;
      upgrade = true;
      extraFlags = [ "--force-cleanup" ];
    };
    brews = [
      "pkg-config"
      "cairo"
      "pango"
      "libomp"
      "libpng"
      "jpeg"
      "giflib"
      "librsvg"
      "pixman"
      "python-setuptools"
      "yarn"
      # CLI tools not installable from nixpkgs
      # (hunk: not packaged; herdr: 0.7.1 fails to build on darwin, DarwinSdkNotFound)
      "hunk"
      "herdr"
    ];
    # 自己更新する cask (slack, google-chrome など auto_updates true) は
    # アプリ自身が更新する。最近の Homebrew は auto_updates cask も upgrade
    # しようとするが、これらは root 所有で /Applications への上書きに sudo が
    # 要り、非対話の activation では失敗して中断・ステージング残骸を生む。
    # HOMEBREW_NO_UPGRADE_AUTO_UPDATES_CASKS=1 で upgrade 対象から外す
    # (下の system.activationScripts で brew.env に書き込む)。formulae と
    # 非自己更新 cask は従来どおり onActivation.upgrade で更新される。
    casks = [
      "alt-tab"
      "anki"
      "arc"
      "bitwarden"
      "claude"
      "codex-app"
      "cmux"
      "cursor"
      "cursor-cli"
      "discord"
      "ghostty"
      "google-chrome"
      # menu bar manager。stats / swiftbar でアイコンが増える分をここで畳む。
      "jordanbaird-ice"
      "karabiner-elements"
      "nani"
      "notion"
      "obsidian"
      "raycast"
      "slack"
      "stats"
      "swiftbar"
      "visual-studio-code"
      "zoom"
    ];
  };

  # 自己更新 cask を activation の brew upgrade 対象から外す (homebrew.casks の
  # コメント参照)。activation の brew bundle は
  #   sudo --preserve-env=PATH --user=... --set-home env brew ...
  # で起動され PATH 以外の環境変数を捨てるため environment.variables では届かない。
  # 代わりに Homebrew が必ず読むグローバル設定 brew.env に書き込む。
  system.activationScripts.extraActivation.text = lib.mkAfter ''
    if [ -x /opt/homebrew/bin/brew ]; then
      mkdir -p /opt/homebrew/etc/homebrew
      printf '%s\n' \
        '# Managed by nix-darwin (dotfiles). 自己更新 cask を brew upgrade 対象から外す。' \
        'HOMEBREW_NO_UPGRADE_AUTO_UPDATES_CASKS=1' \
        > /opt/homebrew/etc/homebrew/brew.env
    fi
  '';

  # Determinate Nix manages the daemon; disable nix-darwin's Nix management.
  nix.enable = false;

  nixpkgs.config = {
    allowUnfree = true;
    permittedInsecurePackages = [
      "lima-full-1.2.2"
      "lima-additional-guestagents-1.2.2"
    ];
  };

  users.users.${user} = {
    home = "/Users/${user}";
    shell = pkgs.fish;
    ignoreShellProgramCheck = true;
  };

  # Apply user-scoped defaults for the primary login user.
  system.primaryUser = user;

  # Launch apps at login for the primary user.
  #
  # ここに置くのは「アプリ自身のログイン登録が無い、または無効なもの」だけ。
  # 自前で確実に登録するアプリは二重管理になるので入れない。判定は
  # `sfltool dumpbtm` の Disposition を見る。
  #   - AltTab: 自前の ~/Library/LaunchAgents/com.lwouis.alt-tab-macos.plist が
  #     enabled なので不要
  #   - Raycast: app login item が enabled なので不要（Raycast が自動登録する）
  #   - Stats: app login item が disabled なので、ここで起動する必要がある
  launchd.user.agents = {
    colima = {
      serviceConfig = {
        EnvironmentVariables = {
          COLIMA_HOME = "/Users/${user}/.config/colima";
        };
        ProgramArguments = [
          "${pkgs.colima}/bin/colima"
          "start"
          "--foreground"
          "--vm-type"
          colima.vmType
        ]
        ++ lib.optionals colima.rosetta [ "--vz-rosetta" ];
        RunAtLoad = true;
        KeepAlive = {
          SuccessfulExit = false;
        };
      };
    };
    karabiner-elements = {
      serviceConfig = {
        ProgramArguments = [
          "/usr/bin/open"
          "-g"
          "-a"
          "Karabiner-Elements"
        ];
        LimitLoadToSessionType = [ "Aqua" ];
        RunAtLoad = true;
      };
    };
    bitwarden = {
      serviceConfig = {
        ProgramArguments = [
          "/usr/bin/open"
          "-g"
          "/Applications/Bitwarden.app"
        ];
        LimitLoadToSessionType = [ "Aqua" ];
        RunAtLoad = true;
      };
    };
    # menu bar 系。ice は他のアイコンを畳む側なので常駐していないと意味がない。
    ice = {
      serviceConfig = {
        ProgramArguments = [
          "/usr/bin/open"
          "-g"
          "/Applications/Ice.app"
        ];
        LimitLoadToSessionType = [ "Aqua" ];
        RunAtLoad = true;
        KeepAlive = {
          SuccessfulExit = false;
        };
      };
    };
    swiftbar = {
      serviceConfig = {
        ProgramArguments = [
          "/usr/bin/open"
          "-g"
          "/Applications/SwiftBar.app"
        ];
        LimitLoadToSessionType = [ "Aqua" ];
        RunAtLoad = true;
        KeepAlive = {
          SuccessfulExit = false;
        };
      };
    };
    stats = {
      serviceConfig = {
        ProgramArguments = [
          "/usr/bin/open"
          "-g"
          "/Applications/Stats.app"
        ];
        LimitLoadToSessionType = [ "Aqua" ];
        RunAtLoad = true;
        KeepAlive = {
          SuccessfulExit = false;
        };
      };
    };
  };

  fonts.packages = with pkgs; [
    udev-gothic
    udev-gothic-nf
  ];

  # macOS defaults (based on ryoppippi/dotfiles)
  system.defaults = {
    dock = {
      autohide = true; # Auto-hide Dock to save screen space.
      tilesize = 45; # Dock icon size.
      "persistent-apps" = [ ]; # Remove pinned apps.
      "show-recents" = false; # Hide recent apps in Dock.
      mineffect = "genie"; # Minimize animation style.
      orientation = "bottom"; # Dock position.
    };

    finder = {
      AppleShowAllExtensions = true; # Always show file extensions.
      AppleShowAllFiles = true; # Show hidden files.
      ShowPathbar = true; # Show path bar.
      ShowStatusBar = true; # Show status bar.
      FXEnableExtensionChangeWarning = false; # Disable extension change warning.
      FXPreferredViewStyle = "Nlsv"; # Default to list view.
    };

    NSGlobalDomain = {
      AppleInterfaceStyle = "Dark"; # Use Dark Mode.
      ApplePressAndHoldEnabled = false; # Disable accent popup on key hold.
      AppleShowAllExtensions = true; # Also set at global domain.
      KeyRepeat = 2; # Faster key repeat.
      InitialKeyRepeat = 25; # Shorter delay before repeating.
      "com.apple.trackpad.scaling" = 1.3; # Trackpad speed.
      NSAutomaticCapitalizationEnabled = false; # Disable auto-capitalization.
      NSAutomaticDashSubstitutionEnabled = false; # Disable smart dashes.
      NSAutomaticPeriodSubstitutionEnabled = false; # Disable double-space period.
      NSAutomaticQuoteSubstitutionEnabled = false; # Disable smart quotes.
      NSAutomaticSpellingCorrectionEnabled = false; # Disable auto-correct.
      # NSStatusItemSpacing / NSStatusItemSelectionPadding は指定しない。
      # 以前はアイコンが入りきらず 2px まで詰めていたが、Ice (menu bar manager)
      # が畳むようになったので macOS 既定の間隔に任せる。
    };

    screencapture = {
      location = "~/Pictures/Screenshots"; # Screenshot save location.
      type = "png"; # Screenshot file format.
    };

    trackpad = {
      Clicking = false; # Disable tap-to-click.
      TrackpadRightClick = true; # Enable two-finger right click.
      TrackpadThreeFingerDrag = false; # Disable three-finger drag.
    };

    CustomUserPreferences = {
      # Activity Monitor can garble localized virtual machine service names in
      # Japanese environments, so prefer English just for that app.
      "com.apple.ActivityMonitor" = {
        AppleLanguages = [ "en" ];
      };

      # Mission Control / Spaces shortcuts
      "com.apple.symbolichotkeys" = {
        AppleSymbolicHotKeys = {
          # Mission Control (Ctrl + Up)
          "32" = {
            enabled = true;
            value = {
              type = "standard";
              parameters = [
                65535
                126
                2359296
              ];
            };
          };
          # Application windows (Ctrl + Down)
          "33" = {
            enabled = true;
            value = {
              type = "standard";
              parameters = [
                65535
                125
                2359296
              ];
            };
          };
          # Move left a Space (Ctrl + Left)
          "79" = {
            enabled = true;
            value = {
              type = "standard";
              parameters = [
                65535
                123
                2359296
              ];
            };
          };
          # Move right a Space (Ctrl + Right)
          "81" = {
            enabled = true;
            value = {
              type = "standard";
              parameters = [
                65535
                124
                2359296
              ];
            };
          };
        };
      };
      # Detailed trackpad settings not covered by system.defaults.trackpad.
      "com.apple.AppleMultitouchTrackpad" = {
        FirstClickThreshold = 0; # Light click.
        SecondClickThreshold = 0; # Light force click.
        ActuateDetents = 1; # Enable haptic feedback.
        ForceSuppressed = 0; # Allow force click.
        TrackpadThreeFingerTapGesture = 0; # Disable lookup gesture.
      };
      # Same tuning for Bluetooth trackpad.
      "com.apple.driver.AppleBluetoothMultitouch.trackpad" = {
        FirstClickThreshold = 0;
        SecondClickThreshold = 0;
        ActuateDetents = 1;
        ForceSuppressed = 0;
      };
    };
  };

  # With nix.enable = false, configure Nix settings in /etc/nix/nix.conf.

  # Add fish to system shells; fish config lives in dotfiles.
  environment.shells = [ pkgs.fish ];

  system.activationScripts.postActivation.text = ''
    ${lib.optionalString installRosetta ''
      if [ "$(uname -m)" = "arm64" ]; then
        if /usr/sbin/pkgutil --pkg-info com.apple.pkg.RosettaUpdateAuto >/dev/null 2>&1; then
          echo "Rosetta 2 already installed; skipping."
        else
          echo "Installing Rosetta 2..."
          if ! /usr/sbin/softwareupdate --install-rosetta --agree-to-license; then
            echo "Rosetta 2 installation failed" >&2
            exit 1
          fi
        fi
      fi
    ''}

    current_shell="$(/usr/bin/dscl . -read /Users/${user} UserShell 2>/dev/null | /usr/bin/awk '{print $2}')"
    if [ "$current_shell" = "${pkgs.fish}/bin/fish" ]; then
      echo "Login shell already set to fish; skipping."
    else
      echo "Setting login shell to fish..."
      if ! chsh -s ${pkgs.fish}/bin/fish ${user}; then
        echo "Failed to change login shell for ${user}" >&2
        exit 1
      fi
    fi
  '';

  # Set Git commit hash for darwin-version.
  system.configurationRevision = self.rev or self.dirtyRev or null;

  # Used for backwards compatibility, please read the changelog before changing.
  # $ darwin-rebuild changelog
  system.stateVersion = 6;

  # The platform the configuration will be used on.
  nixpkgs.hostPlatform = hostSystem;
}
