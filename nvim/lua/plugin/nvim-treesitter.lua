return {
  "nvim-treesitter/nvim-treesitter",
  branch = "master",
  event = { "BufReadPost", "VeryLazy" },
  config = function()
    require("nvim-treesitter.configs").setup({
      auto_install = false, -- Grammars provided by Nix.
      sync_install = false,
      highlight = {
        enable = true,
        additional_vim_regex_highlighting = false,
      },
      indent = { enable = true },
    })
  end,
}
