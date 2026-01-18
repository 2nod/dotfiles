local M = {}

local uv = vim.uv or vim.loop

local function debounce(func, wait)
	local timer_id
	return function(...)
		if timer_id ~= nil then
			uv.timer_stop(timer_id)
		end
		local args = { ... }
		timer_id = assert(uv.new_timer())
		uv.timer_start(timer_id, wait, 0, function()
			func(unpack(args))
			timer_id = nil
		end)
	end
end

local function is_image(url)
	local extension = url:match("^.+(%..+)$")
	if not extension then
		return false
	end
	local image_ext = { ".bmp", ".jpg", ".jpeg", ".png", ".gif" }

	for _, ext in ipairs(image_ext) do
		if extension == ext then
			return true
		end
	end
	return false
end

local function get_entry_absolute_path()
	local oil = require("oil")
	local entry = oil.get_cursor_entry()
	local dir = oil.get_current_dir()
	if not entry or not dir then
		return
	end
	return dir .. entry.name, entry, dir
end

M.openWithQuickLook = {
	callback = function()
		local path = assert((get_entry_absolute_path()))
		vim.cmd(("silent !qlmanage -p %s &"):format(vim.fn.shellescape(path)))
	end,
	desc = "Open with QuickLook",
}

local function get_neovim_wezterm_pane()
	local wezterm_pane_id = vim.env.WEZTERM_PANE
	if not wezterm_pane_id then
		vim.notify("Wezterm pane not found", vim.log.levels.ERROR)
		return
	end
	return tonumber(wezterm_pane_id)
end

local active_wezterm_pane = function(wezterm_pane_id)
	vim.system({ "wezterm", "cli", "activate-pane", "--pane-id", wezterm_pane_id })
end

local function open_new_wezterm_pane(opt)
	local _opt = opt or {}
	local percent = _opt.percent or 30
	local direction = _opt.direction or "right"

	local cmd = {
		"wezterm",
		"cli",
		"split-pane",
		("--percent=%d"):format(percent),
		("--%s"):format(direction),
		"--",
		"bash",
	}
	local obj = vim.system(cmd, { text = true }):wait()
	local wezterm_pane_id = assert(tonumber(obj.stdout))

	return wezterm_pane_id
end

local function close_wezterm_pane(wezterm_pane_id)
	if not wezterm_pane_id then
		return
	end
	vim.system({
		"wezterm",
		"cli",
		"kill-pane",
		("--pane-id=%d"):format(wezterm_pane_id),
	})
end

local function send_command_to_wezterm_pane(wezterm_pane_id, command)
	local cmd = {
		"echo",
		("'%s'"):format(command),
		"|",
		"wezterm",
		"cli",
		"send-text",
		"--no-paste",
		("--pane-id=%d"):format(wezterm_pane_id),
	}
	vim.fn.system(table.concat(cmd, " "))
end

local function list_wezterm_panes()
	local cli_result = vim.system({
		"wezterm",
		"cli",
		"list",
		"--format=json",
	}, { text = true }):wait()

	if cli_result.code ~= 0 or not cli_result.stdout or cli_result.stdout == "" then
		return {}
	end

	local ok, json = pcall(vim.json.decode, cli_result.stdout)
	if not ok or type(json) ~= "table" then
		return {}
	end

	local panes = {}
	for _, obj in ipairs(json) do
		panes[#panes + 1] = { pane_id = obj.pane_id, tab_id = obj.tab_id }
	end

	return panes
end

local function get_preview_wezterm_pane_id()
	local panes = list_wezterm_panes()
	local neovim_wezterm_pane_id = get_neovim_wezterm_pane()
	if not neovim_wezterm_pane_id then
		return
	end
	local current_tab_id

	for _, obj in ipairs(panes) do
		if tonumber(obj.pane_id) == neovim_wezterm_pane_id then
			current_tab_id = obj.tab_id
			break
		end
	end
	if not current_tab_id then
		return
	end

	for _, obj in ipairs(panes) do
		if obj.tab_id == current_tab_id and tonumber(obj.pane_id) > neovim_wezterm_pane_id then
			return obj.pane_id
		end
	end
end

local function open_wezterm_preview_pane()
	local preview_pane_id = get_preview_wezterm_pane_id()
	if preview_pane_id == nil then
		preview_pane_id = open_new_wezterm_pane({ percent = 30, direction = "right" })
	end
	return preview_pane_id
end

local function is_wezterm_preview_open()
	return get_preview_wezterm_pane_id() ~= nil
end

M.weztermPreview = {
	callback = function()
		if is_wezterm_preview_open() then
			close_wezterm_pane(get_preview_wezterm_pane_id())
		end
		local oil = require("oil")
		local util = require("oil.util")
		local preview_entry_id = nil
		local prev_cmd = nil

		local neovim_wezterm_pane_id = get_neovim_wezterm_pane()
		if not neovim_wezterm_pane_id then
			return
		end
		local bufnr = vim.api.nvim_get_current_buf()

		local update_wezterm_preview = debounce(
			vim.schedule_wrap(function()
				if vim.api.nvim_get_current_buf() ~= bufnr then
					return
				end
				local entry = oil.get_cursor_entry()
				if entry ~= nil and not util.is_visual_mode() then
					local preview_pane_id = open_wezterm_preview_pane()
					active_wezterm_pane(neovim_wezterm_pane_id)

					if preview_entry_id == entry.id then
						return
					end

					if prev_cmd == "bat" then
						send_command_to_wezterm_pane(preview_pane_id, "q")
						prev_cmd = nil
					end

					local path = assert((get_entry_absolute_path()))
					local command = ""
					if entry.type == "directory" then
						local cmd = "ls -l"
						command = command .. ("%s %s"):format(cmd, path)
						prev_cmd = cmd
					elseif entry.type == "file" and is_image(path) then
						local cmd = "wezterm imgcat"
						command = command .. ("%s %s"):format(cmd, path)
						prev_cmd = cmd
					elseif entry.type == "file" then
						local cmd = "bat"
						command = command .. ("%s %s"):format(cmd, path)
						prev_cmd = cmd
					end

					send_command_to_wezterm_pane(preview_pane_id, command)
				end
			end),
			50
		)

		update_wezterm_preview()

		local config = require("oil.config")
		local preview = config.preview_win or config.preview or {}
		if preview.update_on_cursor_moved then
			vim.api.nvim_create_autocmd("CursorMoved", {
				desc = "Update oil wezterm preview",
				group = "Oil",
				buffer = bufnr,
				callback = function()
					update_wezterm_preview()
				end,
			})
		end

		vim.api.nvim_create_autocmd({ "BufLeave", "BufDelete", "VimLeave" }, {
			desc = "Close oil wezterm preview",
			group = "Oil",
			buffer = bufnr,
			callback = function()
				close_wezterm_pane(get_preview_wezterm_pane_id())
			end,
		})
	end,
	desc = "Preview with Wezterm",
}

return M
