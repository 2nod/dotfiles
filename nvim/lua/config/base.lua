vim.g.loaded_netrw = 1
vim.g.loaded_netrwPlugin = 1

local treesitter_grammars = vim.env.TREESITTER_GRAMMARS
if treesitter_grammars and treesitter_grammars ~= "" then
  vim.opt.runtimepath:append(treesitter_grammars)
end
