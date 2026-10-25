{ pkgs }:
let
  source = pkgs.fetchFromGitHub {
    owner = "cursor";
    repo = "plugins";
    rev = "df581122cde17e6e27686b5a448bde23e4ad4318";
    hash = "sha256-5ekIT7JbftDl0kBCtT1LKXy/oFl7AeebihQ/JCKf9s4=";
  };
in
"${source}/pstack"
