{ config }:
let
  username = config.home.username;
  githubId = "42732270";
  email = "${githubId}+${username}@users.noreply.github.com";
in
{
  inherit username githubId email;
}
