return {
	"iamcco/markdown-preview.nvim",
	ft = { "markdown", "mdx" },
	build = "cd app && npm install",
	init = function()
		vim.g.mkdp_auto_start = 0
		vim.g.mkdp_auto_close = 1
		vim.g.mkdp_refresh_slow = 0
		vim.g.mkdp_command_for_global = 0
		vim.g.mkdp_open_to_the_world = 0
		vim.g.mkdp_browser = ""
		vim.g.mkdp_echo_preview_url = 1
		vim.g.mkdp_page_title = "${name}"

		vim.api.nvim_create_autocmd("FileType", {
			pattern = { "markdown", "mdx" },
			callback = function(args)
				local opts = { buffer = args.buf, silent = true }
				vim.keymap.set("n", "<leader>mp", "<cmd>MarkdownPreviewToggle<CR>", opts)
				vim.keymap.set("n", "<leader>mo", "<cmd>MarkdownPreview<CR>", opts)
				vim.keymap.set("n", "<leader>mc", "<cmd>MarkdownPreviewStop<CR>", opts)
			end,
		})
	end,
}
