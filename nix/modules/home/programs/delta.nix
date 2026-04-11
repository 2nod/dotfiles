{
  ...
}:
{
  programs.delta = {
    enable = true;
    enableGitIntegration = true;
    options = {
      dark = true;
      syntax-theme = "GitHub";
      diff-so-fancy = true;
      keep-plus-minus-markers = true;
      side-by-side = true;
      hunk-header-style = "omit";
      line-numbers = true;
    };
  };
}
