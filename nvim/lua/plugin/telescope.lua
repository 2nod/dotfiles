return {
	"nvim-telescope/telescope.nvim",
	dependencies = {
		"nvim-lua/plenary.nvim",
		{
			"nvim-telescope/telescope-fzf-native.nvim",
			dir = vim.env.TELESCOPE_FZF_NATIVE,
			cond = vim.env.TELESCOPE_FZF_NATIVE ~= nil and vim.env.TELESCOPE_FZF_NATIVE ~= "",
		},
		"nvim-telescope/telescope-ghq.nvim",
		"jvgrootveld/telescope-zoxide",
	},
	cmd = "Telescope",
	config = function()
		local telescope = require("telescope")
		local actions = require("telescope.actions")

		telescope.setup({
			defaults = {
				layout_strategy = "horizontal",
				layout_config = { prompt_position = "top" },
				mappings = {
					i = {
						["<CR>"] = function(prompt_bufnr)
							actions.select_default(prompt_bufnr)
							vim.cmd.stopinsert()
						end,
						["<C-q>"] = actions.send_to_qflist + actions.open_qflist,
						["<C-s>"] = actions.send_selected_to_qflist + actions.open_qflist,
					},
					n = {
						["<CR>"] = function(prompt_bufnr)
							actions.select_default(prompt_bufnr)
							vim.cmd.stopinsert()
						end,
						["q"] = actions.close,
						["<C-q>"] = actions.send_to_qflist + actions.open_qflist,
						["<C-s>"] = actions.send_selected_to_qflist + actions.open_qflist,
					},
				},
				sorting_strategy = "ascending",
			},
		})

		pcall(telescope.load_extension, "fzf")
		pcall(telescope.load_extension, "ghq")
		pcall(telescope.load_extension, "zoxide")
	end,
}
