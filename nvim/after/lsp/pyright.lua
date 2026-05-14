---@type vim.lsp.Config
return {
	cmd = { "pyright-langserver", "--stdio" },
	filetypes = { "python" },
	root_markers = {
		"pyproject.toml",
		"pyrightconfig.json",
		".git",
	},
	settings = {
		python = {
			analysis = {
				typeCheckingMode = "basic",
				diagnosticMode = "openFilesOnly",
			},
		},
	},
}
