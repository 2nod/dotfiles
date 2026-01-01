{ self, user, pkgs, ... }:
{
  brew-nix.enable = true;

  # brew-nix casks are defined in nix/modules/darwin/packages.nix (home-manager).
  # Homebrew is managed here for casks that are fragile under brew-nix.
  homebrew = {
    enable = true;
    onActivation.cleanup = "uninstall";
    casks = [
      "karabiner-elements"
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

  # Enable alternative shell support in nix-darwin.
  programs.fish.enable = true;
  environment.shells = [ pkgs.fish ];

  system.activationScripts.postActivation.text = ''
    echo "Setting login shell to fish..."
    chsh -s ${pkgs.fish}/bin/fish ${user} || true
  '';

  # Set Git commit hash for darwin-version.
  system.configurationRevision = self.rev or self.dirtyRev or null;

  # Used for backwards compatibility, please read the changelog before changing.
  # $ darwin-rebuild changelog
  system.stateVersion = 6;

  # The platform the configuration will be used on.
  nixpkgs.hostPlatform = "aarch64-darwin";
}
