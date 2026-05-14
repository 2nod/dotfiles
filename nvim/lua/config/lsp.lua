local mason = require("mason")
local mason_lspconfig = require("mason-lspconfig")
local cmp_nvim_lsp = require("cmp_nvim_lsp")

local capabilities = cmp_nvim_lsp.default_capabilities()

for _, key in ipairs({ "gra", "gri", "grn", "grr", "grt" }) do
	pcall(vim.keymap.del, "n", key)
end

local function on_attach(_, bufnr)
	local map = function(mode, lhs, rhs, desc)
		vim.keymap.set(mode, lhs, rhs, { buffer = bufnr, desc = desc, silent = true })
	end

	local lsp_picker = function(picker, fallback)
		local ok, telescope = pcall(require, "telescope.builtin")
		if ok and telescope[picker] then
			telescope[picker]()
			return
		end

		fallback()
	end

	map("n", "gd", function()
		lsp_picker("lsp_definitions", vim.lsp.buf.definition)
	end, "Go to definition")
	map("n", "gt", function()
		lsp_picker("lsp_type_definitions", vim.lsp.buf.type_definition)
	end, "Go to type definition")
	map("n", "gI", function()
		lsp_picker("lsp_implementations", vim.lsp.buf.implementation)
	end, "Go to implementation")
	map("n", "gr", function()
		lsp_picker("lsp_references", vim.lsp.buf.references)
	end, "References")
	map("n", "K", vim.lsp.buf.hover, "Hover")
	map("n", "<leader>rn", vim.lsp.buf.rename, "Rename")
	map("n", "<leader>ca", vim.lsp.buf.code_action, "Code action")
	map("n", "<leader>f", function()
		local clients = vim.lsp.get_clients({ bufnr = bufnr })
		for _, client in ipairs(clients) do
			if client.name == "oxfmt" then
				vim.lsp.buf.format({ async = true, name = "oxfmt" })
				return
			end
		end
		vim.lsp.buf.format({ async = true })
	end, "Format")
end

vim.lsp.config("*", {
	capabilities = capabilities,
	on_attach = on_attach,
})

vim.lsp.config("lua_ls", {
	settings = {
		Lua = {
			runtime = { version = "LuaJIT" },
			diagnostics = { globals = { "vim" } },
			workspace = { checkThirdParty = false },
			telemetry = { enable = false },
		},
	},
})

mason.setup()
mason_lspconfig.setup()
