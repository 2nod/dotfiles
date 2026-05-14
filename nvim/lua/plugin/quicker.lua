return {
	"stevearc/quicker.nvim",
	ft = "qf",
	keys = {
		{
			"<leader>R",
			function()
				require("quicker").refresh()
			end,
			desc = "Refresh quickfix",
		},
	},
	opts = {},
}
