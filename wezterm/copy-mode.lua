local wezterm = require("wezterm")
local act = wezterm.action

local default_key_tables = {}
if wezterm.gui and wezterm.gui.default_key_tables then
	default_key_tables = wezterm.gui.default_key_tables()
end

local blocked = {
	["y:NONE"] = true,
	["Escape:NONE"] = true,
	["q:NONE"] = true,
	["C:CTRL"] = true,
	["G:CTRL"] = true,
}

local copy_mode = {}
for _, entry in ipairs(default_key_tables.copy_mode or {}) do
	local key = entry.key
	local mods = entry.mods or "NONE"
	if not blocked[string.format("%s:%s", key, mods)] then
		table.insert(copy_mode, entry)
	end
end

local close_copy_mode = act.Multiple {
	act.ClearSelection,
	act.CopyMode("Close"),
}

table.insert(copy_mode, {
	key = "y",
	mods = "NONE",
	action = act.Multiple {
		act.CopyTo("ClipboardAndPrimarySelection"),
		act.ClearSelection,
		act.CopyMode("Close"),
	},
})
table.insert(copy_mode, {
	key = "Escape",
	mods = "NONE",
	action = close_copy_mode,
})
table.insert(copy_mode, {
	key = "q",
	mods = "NONE",
	action = close_copy_mode,
})
table.insert(copy_mode, {
	key = "C",
	mods = "CTRL",
	action = close_copy_mode,
})
table.insert(copy_mode, {
	key = "G",
	mods = "CTRL",
	action = close_copy_mode,
})

return copy_mode
