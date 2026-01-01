return {
  "nvim-treesitter/nvim-treesitter",
  lazy = false,
  build = ":TSUpdate",
  config = function()
    local treesitter = require("nvim-treesitter")
    local languages = {
      "bash",
      "json",
      "lua",
      "markdown",
      "markdown_inline",
      "nix",
      "vim",
      "vimdoc",
      "yaml",
    }
    local wanted = {}

    for _, lang in ipairs(languages) do
      wanted[lang] = true
    end

    treesitter.install(languages)

    vim.api.nvim_create_autocmd("FileType", {
      callback = function(args)
        local ft = vim.bo[args.buf].filetype
        local lang = vim.treesitter.language.get_lang(ft)
        if not lang or not wanted[lang] then
          return
        end

        if not pcall(vim.treesitter.start, args.buf) then
          return
        end

        vim.bo[args.buf].indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
      end,
    })
  end,
}
