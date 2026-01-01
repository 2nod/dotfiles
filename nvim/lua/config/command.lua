vim.api.nvim_create_user_command("QuickLook", function()
  local path = vim.fn.expand("%:p")
  if path == "" then
    return
  end
  vim.cmd(("silent !qlmanage -p %s &"):format(vim.fn.shellescape(path)))
end, { nargs = 0 })
