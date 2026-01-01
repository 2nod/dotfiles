local wezterm = require("wezterm")
local act = wezterm.action

wezterm.on("toggle-opacity", function(window, _)
  local overrides = window:get_config_overrides() or {}
  if overrides.window_background_opacity then
    overrides.window_background_opacity = nil
  else
    overrides.window_background_opacity = 0.6
  end
  window:set_config_overrides(overrides)
end)

wezterm.on("toggle-blur", function(window, _)
  local overrides = window:get_config_overrides() or {}
  if overrides.macos_window_background_blur then
    overrides.macos_window_background_blur = nil
  else
    overrides.macos_window_background_blur = 0
  end
  window:set_config_overrides(overrides)
end)

wezterm.on("gui-startup", function(cmd)
  local _, _, window = wezterm.mux.spawn_window(cmd or {})
  window:gui_window():maximize()
end)

local keys = {
  { key = "a", mods = "LEADER|CTRL", action = act.SendString("\x01") },
  { key = "d", mods = "CMD", action = act.SplitHorizontal({ domain = "CurrentPaneDomain" }) },
  { key = "d", mods = "CMD|SHIFT", action = act.SplitVertical({ domain = "CurrentPaneDomain" }) },
  { key = "t", mods = "CMD", action = act.SpawnTab("CurrentPaneDomain") },
  { key = "w", mods = "CMD", action = act.CloseCurrentPane({ confirm = true }) },
  { key = "W", mods = "CMD|SHIFT", action = act.CloseCurrentTab({ confirm = true }) },
  { key = "z", mods = "CMD", action = act.TogglePaneZoomState },
  { key = "h", mods = "CMD", action = act.ActivatePaneDirection("Left") },
  { key = "j", mods = "CMD", action = act.ActivatePaneDirection("Down") },
  { key = "k", mods = "CMD", action = act.ActivatePaneDirection("Up") },
  { key = "l", mods = "CMD", action = act.ActivatePaneDirection("Right") },
  { key = "H", mods = "CMD|SHIFT", action = act.AdjustPaneSize({ "Left", 5 }) },
  { key = "J", mods = "CMD|SHIFT", action = act.AdjustPaneSize({ "Down", 5 }) },
  { key = "K", mods = "CMD|SHIFT", action = act.AdjustPaneSize({ "Up", 5 }) },
  { key = "L", mods = "CMD|SHIFT", action = act.AdjustPaneSize({ "Right", 5 }) },
  { key = "(", mods = "CMD|SHIFT", action = act.MoveTabRelative(-1) },
  { key = ")", mods = "CMD|SHIFT", action = act.MoveTabRelative(1) },
  { key = "Space", mods = "LEADER", action = act.QuickSelect },
  { key = "f", mods = "LEADER", action = act.EmitEvent("toggle-blur") },
  { key = "o", mods = "LEADER", action = act.EmitEvent("toggle-opacity") },
  { key = "Enter", mods = "SHIFT", action = act.SendString("\x1b\r") },
}

for i = 1, 9 do
  table.insert(keys, {
    key = tostring(i),
    mods = "LEADER",
    action = act.ActivateTab(i - 1),
  })
end

return {
  font = wezterm.font_with_fallback({ "UDEV Gothic 35LG", "JetBrains Mono", "Menlo" }),
  font_size = 13.0,
  force_reverse_video_cursor = true,
  adjust_window_size_when_changing_font_size = false,

  window_padding = {
    left = 1,
    right = 0,
    top = 0,
    bottom = 0,
  },

  window_background_opacity = 0.75,
  macos_window_background_blur = 20,
  window_decorations = "RESIZE",

  use_ime = true,
  send_composed_key_when_left_alt_is_pressed = false,
  send_composed_key_when_right_alt_is_pressed = false,
  macos_forward_to_ime_modifier_mask = "SHIFT|CTRL",
  audible_bell = "SystemBeep",

  leader = { key = ";", mods = "CTRL" },
  enable_csi_u_key_encoding = true,
  keys = keys,

  tab_bar_at_bottom = false,
  use_fancy_tab_bar = false,
  hide_tab_bar_if_only_one_tab = true,
  show_new_tab_button_in_tab_bar = false,

  colors = {
    foreground = "#c5c9c5",
    background = "#181616",

    cursor_bg = "#C8C093",
    cursor_fg = "#2D4F67",
    cursor_border = "#C8C093",

    selection_fg = "#C8C093",
    selection_bg = "#2D4F67",

    scrollbar_thumb = "#16161D",
    split = "#16161D",

    ansi = { "#0D0C0C", "#C4746E", "#8A9A7B", "#C4B28A", "#8BA4B0", "#A292A3", "#8EA4A2", "#C8C093" },
    brights = { "#A6A69C", "#E46876", "#87A987", "#E6C384", "#7FB4CA", "#938AA9", "#7AA89F", "#C5C9C5" },
    indexed = { [16] = "#B6927B", [17] = "#B98D7B" },

    tab_bar = {
      background = "#1b1f2f",
      inactive_tab_edge = "none",

      active_tab = {
        bg_color = "#444b71",
        fg_color = "#c6c8d1",
        intensity = "Normal",
        underline = "None",
        italic = false,
        strikethrough = false,
      },

      inactive_tab = {
        bg_color = "#282d3e",
        fg_color = "#c6c8d1",
        intensity = "Normal",
        underline = "None",
        italic = false,
        strikethrough = false,
      },

      inactive_tab_hover = {
        bg_color = "#1b1f2f",
        fg_color = "#c6c8d1",
        intensity = "Normal",
        underline = "None",
        italic = true,
        strikethrough = false,
      },

      new_tab = {
        bg_color = "#1b1f2f",
        fg_color = "#c6c8d1",
        italic = false,
      },

      new_tab_hover = {
        bg_color = "#444b71",
        fg_color = "#c6c8d1",
        italic = false,
      },
    },
  },
}
