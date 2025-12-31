{ self, user, ... }:
{
  brew-nix.enable = true;

  # brew-nix casks are defined in nix/modules/darwin/packages.nix (home-manager).

  # Determinate Nix manages the daemon; disable nix-darwin's Nix management.
  nix.enable = false;

  users.users.${user} = {
    home = "/Users/${user}";
  };

  # With nix.enable = false, configure Nix settings in /etc/nix/nix.conf.

  # Enable alternative shell support in nix-darwin.
  # programs.fish.enable = true;

  # Set Git commit hash for darwin-version.
  system.configurationRevision = self.rev or self.dirtyRev or null;

  # Used for backwards compatibility, please read the changelog before changing.
  # $ darwin-rebuild changelog
  system.stateVersion = 6;

  # The platform the configuration will be used on.
  nixpkgs.hostPlatform = "aarch64-darwin";
}
