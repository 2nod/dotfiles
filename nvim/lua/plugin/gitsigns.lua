return {
  "lewis6991/gitsigns.nvim",
  event = { "BufReadPost" },
  cmd = { "Gitsigns" },
  keys = {
    { "ms", "Gitsigns", mode = "ca" },
    { "mS", "<cmd>Gitsigns stage_buffer<CR>", mode = "n" },
    { "mh", "<cmd>Gitsigns preview_hunk<CR>", mode = "n" },
    { "ms", "<cmd>Gitsigns stage_hunk<CR>", mode = "n" },
    { "mu", "<cmd>Gitsigns undo_stage_hunk<CR>", mode = "n" },
    { "mr", "<cmd>Gitsigns reset_hunk<CR>", mode = "n" },
    { "mp", "<cmd>Gitsigns preview_hunk<CR>", mode = "n" },
    { "mR", "<cmd>Gitsigns reset_buffer<CR>", mode = "n" },
    { "md", "<cmd>Gitsigns diffthis split=rightbelow<CR>", mode = "n" },
    { "mB", "<cmd>Gitsigns blame<CR>", mode = "n" },
    { "mb", "<cmd>Gitsigns blame_line<CR>", mode = "n" },
  },
  dependencies = {
    "tpope/vim-repeat",
  },
  opts = {
    signs = {
      add = { text = "+" },
      change = { text = "~" },
      delete = { text = "_" },
      topdelete = { text = "^" },
      changedelete = { text = "~_" },
    },
    current_line_blame = true,
  },
  config = true,
}
