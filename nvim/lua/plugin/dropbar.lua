return {
  "Bekaboo/dropbar.nvim",
  event = "BufReadPost",
  keys = {
    {
      "<leader>;",
      function()
        require("dropbar.api").pick()
      end,
      desc = "Pick breadcrumbs",
    },
  },
  opts = {
    bar = {
      enable = function(buf, win)
        if not (vim.api.nvim_buf_is_valid(buf) and vim.api.nvim_win_is_valid(win)) then
          return false
        end

        if vim.api.nvim_win_get_config(win).zindex then
          return false
        end

        if vim.bo[buf].buftype ~= "" then
          return false
        end

        if vim.api.nvim_buf_get_name(buf) == "" then
          return false
        end

        if vim.bo[buf].filetype == "oil" then
          return false
        end

        if vim.wo[win].diff then
          return false
        end

        return true
      end,
    },
  },
}
