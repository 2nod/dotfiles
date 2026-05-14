vim.api.nvim_create_autocmd("TextYankPost", {
	callback = function()
		vim.highlight.on_yank({ timeout = 150 })
	end,
})

vim.api.nvim_create_autocmd("FileType", {
	pattern = "qf",
	callback = function(event)
		vim.keymap.set("n", "<CR>", function()
			vim.cmd([[execute "normal! \<CR>"]])
		end, { buffer = event.buf, desc = "Open quickfix item" })
	end,
})
