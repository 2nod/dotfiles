return {
  "neovim/nvim-lspconfig",
  dependencies = {
    "williamboman/mason.nvim",
    "williamboman/mason-lspconfig.nvim",
    "hrsh7th/cmp-nvim-lsp",
  },
  init = function()
    vim.lsp.enable({ "efm" })
  end,
  config = function()
    require("config.lsp")
  end,
}
