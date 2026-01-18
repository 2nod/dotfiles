---@type vim.lsp.Config
return {
  cmd = function(dispatchers, config)
    local cmd = "oxfmt"
    local local_cmd = (config or {}).root_dir and config.root_dir .. "/node_modules/.bin/oxfmt"
    if local_cmd and vim.fn.executable(local_cmd) == 1 then
      cmd = local_cmd
    end
    return vim.lsp.rpc.start({ cmd, "--lsp" }, dispatchers)
  end,
  filetypes = {
    "astro",
    "css",
    "graphql",
    "handlebars",
    "html",
    "javascript",
    "javascript.jsx",
    "javascriptreact",
    "json",
    "json5",
    "jsonc",
    "less",
    "markdown",
    "markdown.mdx",
    "mdx",
    "scss",
    "svelte",
    "toml",
    "typescript",
    "typescript.tsx",
    "typescriptreact",
    "vue",
    "yaml",
  },
  root_markers = {
    ".oxfmtrc.jsonc",
    ".oxfmtrc.json",
    "package.json",
    ".git",
  },
}
