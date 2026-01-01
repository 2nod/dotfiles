local lspconfig = require("lspconfig")
local mason = require("mason")
local mason_lspconfig = require("mason-lspconfig")
local cmp_nvim_lsp = require("cmp_nvim_lsp")

local capabilities = cmp_nvim_lsp.default_capabilities()

local function on_attach(_, bufnr)
  local map = function(mode, lhs, rhs, desc)
    vim.keymap.set(mode, lhs, rhs, { buffer = bufnr, desc = desc })
  end

  map("n", "gd", vim.lsp.buf.definition, "Go to definition")
  map("n", "gr", vim.lsp.buf.references, "References")
  map("n", "K", vim.lsp.buf.hover, "Hover")
  map("n", "<leader>rn", vim.lsp.buf.rename, "Rename")
  map("n", "<leader>ca", vim.lsp.buf.code_action, "Code action")
  map("n", "<leader>f", function()
    vim.lsp.buf.format({ async = true })
  end, "Format")
end

mason.setup()

mason_lspconfig.setup()

mason_lspconfig.setup_handlers({
  function(server_name)
    lspconfig[server_name].setup({
      capabilities = capabilities,
      on_attach = on_attach,
    })
  end,
  ["lua_ls"] = function()
    lspconfig.lua_ls.setup({
      capabilities = capabilities,
      on_attach = on_attach,
      settings = {
        Lua = {
          runtime = { version = "LuaJIT" },
          diagnostics = { globals = { "vim" } },
          workspace = { checkThirdParty = false },
          telemetry = { enable = false },
        },
      },
    })
  end,
})
