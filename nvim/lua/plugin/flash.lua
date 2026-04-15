return {
	"folke/flash.nvim",
	event = "BufReadPost",
	---@type Flash.Config
	opts = {
		modes = {
			char = { enabled = false },
			search = { enabled = false },
			treesitter = { enabled = false },
		},
	},
	keys = {
		{
			"<CR>",
			mode = { "n", "x", "o", "v" },
			function()
				require("flash").jump({
					label = { before = true, after = false },
				})
			end,
			desc = "Flash",
		},
	},
}
