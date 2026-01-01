{ lib }:
{
  activation = import ./activation.nix { inherit lib; };
  mkUser = config: import ./user.nix { inherit config; };
}
