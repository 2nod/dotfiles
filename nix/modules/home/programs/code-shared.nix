{ config, ... }:
let
  nvimBin = "/etc/profiles/per-user/${config.home.username}/bin/nvim";
  nvimInit = "${config.home.homeDirectory}/.config/nvim/init.lua";
in
{
  userSettings = {
    "editor.minimap.enabled" = false;
    "diffEditor.renderSideBySide" = false;
    "editor.colorDecorators" = false;
    "editor.multiCursorModifier" = "ctrlCmd";
    "editor.renderControlCharacters" = true;
    "editor.renderLineHighlight" = "all";
    "editor.renderWhitespace" = "all";
    "editor.snippetSuggestions" = "top";
    "editor.wordWrap" = "on";
    "editor.fontSize" = 13;
    "explorer.confirmDelete" = false;
    "files.insertFinalNewline" = true;
    "files.trimFinalNewlines" = true;
    "files.trimTrailingWhitespace" = true;
    "window.openFoldersInNewWindow" = "off";
    "workbench.colorTheme" = "Kanagawa Dragon";
    "workbench.editor.labelFormat" = "short";
    "workbench.editor.tabSizing" = "shrink";
    "workbench.startupEditor" = "none";
    "terminal.integrated.copyOnSelection" = true;
    "terminal.integrated.defaultProfile.osx" = "fish";
    "terminal.integrated.profiles.osx" = {
      "fish" = {
        "path" = "/run/current-system/sw/bin/fish";
        "args" = [ "-l" ];
      };
    };
    "window.restoreWindows" = "none";
    "terminal.integrated.allowChords" = false;
    "security.workspace.trust.untrustedFiles" = "open";
    "editor.accessibilitySupport" = "off";
    "editor.formatOnSave" = true;
    "editor.formatOnSaveMode" = "file";
    "editor.codeActionsOnSave" = {
      "source.organizeImports" = "explicit";
    };
    "editor.quickSuggestions" = {
      "strings" = "on";
    };
    "editor.unicodeHighlight.ambiguousCharacters" = false;
    "editor.unicodeHighlight.invisibleCharacters" = false;
    "extensions.experimental.affinity" = {
      "asvetliakov.vscode-neovim" = 1;
    };
    "vscode-neovim.neovimExecutablePaths.darwin" = nvimBin;
    "vscode-neovim.neovimInitVimPaths.darwin" = nvimInit;
  };
  keybindings = [
    {
      "key" = "space d";
      "command" = "editor.action.goToDeclaration";
      "when" = "neovim.mode == normal && editorTextFocus";
    }
    {
      "key" = "space b";
      "command" = "workbench.action.navigateBack";
      "when" = "neovim.mode == normal && editorTextFocus";
    }
    {
      "key" = "space h";
      "command" = "editor.action.showHover";
      "when" = "neovim.mode == normal && editorTextFocus";
    }
    {
      "key" = "space r";
      "command" = "editor.action.goToReferences";
      "when" = "neovim.mode == normal && editorTextFocus";
    }
  ];
}
