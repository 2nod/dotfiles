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

		telescope.setup({
			defaults = {
				layout_strategy = "horizontal",
				layout_config = { prompt_position = "top" },
				sorting_strategy = "ascending",
			},
		})

		pcall(telescope.load_extension, "fzf")
		pcall(telescope.load_extension, "ghq")
		pcall(telescope.load_extension, "zoxide")
	end,
}
