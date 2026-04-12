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
    rosetta = (profileColima.rosetta or true);
  };
  installRosetta = colima.vmType == "vz" && colima.rosetta;
in
{
  brew-nix.enable = true;

  # brew-nix casks are defined in nix/modules/darwin/packages.nix (home-manager).
  # Homebrew is managed here for casks that are fragile under brew-nix.
  homebrew = {
    enable = true;
    onActivation = {
      cleanup = "uninstall";
      autoUpdate = true;
    };
    brews = [
      "pkg-config"
      "cairo"
      "pango"
      "libpng"
      "jpeg"
      "giflib"
      "librsvg"
      "pixman"
      "python-setuptools"
      "yarn"
    ];
    casks = [
      "aqua-voice"
      "anki"
      "arc"
      "bitwarden"
      "claude"
      "codex-app"
      "cmux"
      "cursor"
      "cursor-cli"
      "discord"
      "google-chrome"
      "karabiner-elements"
      "nani"
      "notion"
      "obsidian"
      "raycast"
      "slack"
      "typeless"
      "visual-studio-code"
      "zoom"
    ];
  };

  # Determinate Nix manages the daemon; disable nix-darwin's Nix management.
  nix.enable = false;

  nixpkgs.config.allowUnfree = true;

  users.users.${user} = {
    home = "/Users/${user}";
    shell = pkgs.fish;
    ignoreShellProgramCheck = true;
  };

  # Apply user-scoped defaults for the primary login user.
  system.primaryUser = user;

  # Launch apps at login for the primary user.
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
    raycast = {
      serviceConfig = {
        ProgramArguments = [
          "/usr/bin/open"
          "-g"
          "/Applications/Raycast.app"
        ];
        LimitLoadToSessionType = [ "Aqua" ];
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
      NSStatusItemSpacing = 2; # Menu bar spacing.
      NSStatusItemSelectionPadding = 2; # Menu bar item padding.
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
