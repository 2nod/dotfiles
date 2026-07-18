local wezterm = require("wezterm")
local mux = wezterm.mux

wezterm.on("update-right-status", function(window, _pane)
	local name = window:active_key_table()
	if name then
		name = "TABLE: " .. name
	end
	window:set_right_status(name or "")
end)

wezterm.on("toggle-opacity", function(window, _)
	local overrides = window:get_config_overrides() or {}
	if not overrides.window_background_opacity then
		overrides.window_background_opacity = 0.6
	else
		overrides.window_background_opacity = nil
	end
	window:set_config_overrides(overrides)
end)

wezterm.on("toggle-blur", function(window, _)
	local overrides = window:get_config_overrides() or {}
	if not overrides.macos_window_background_blur then
		overrides.macos_window_background_blur = 0
	else
		overrides.macos_window_background_blur = nil
	end
	window:set_config_overrides(overrides)
end)

wezterm.on("gui-startup", function(cmd)
	-- 明示的にコマンド付きで起動された場合はレイアウトを組まない
	if cmd then
		local _, _, window = mux.spawn_window(cmd)
		window:gui_window():maximize()
		return
	end

	local cwd = wezterm.home_dir .. "/dotfiles"
	local _, left, window = mux.spawn_window({ cwd = cwd })
	window:gui_window():maximize()

	-- 左: herdr(3/5) / 右: hunk diff + shell(高さ1/5)
	local right = left:split({ direction = "Right", size = 0.4, cwd = cwd })
	local bottom = right:split({ direction = "Bottom", size = 0.2, cwd = cwd })

	-- 先頭スペースで fish の履歴に残さない
	left:send_text(" herdr\n")
	right:send_text(" hunk diff\n")
	bottom:activate()
end)
