---@type vim.lsp.Config
return {
  cmd = function(dispatchers, config)
    local cmd = "oxlint"
    local local_cmd = (config or {}).root_dir and config.root_dir .. "/node_modules/.bin/oxlint"
    if local_cmd and vim.fn.executable(local_cmd) == 1 then
      cmd = local_cmd
    end
    return vim.lsp.rpc.start({ cmd, "--lsp" }, dispatchers)
  end,
  filetypes = {
    "astro",
    "javascript",
    "javascript.jsx",
    "javascriptreact",
    "svelte",
    "typescript",
    "typescript.tsx",
    "typescriptreact",
    "vue",
  },
  root_markers = {
    ".oxlintrc.json",
    "package.json",
    ".git",
  },
  single_file_support = false,
  workspace_required = true,
}
