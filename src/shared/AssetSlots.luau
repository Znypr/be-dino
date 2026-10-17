--!strict
-- Owner-upload slots that had no config home (docs/120). Every id is "" until tools/bind_assets.py writes a real
-- "rbxassetid://N" (never invent ids). Images are merged into Theme.ImageIds (UITheme.luau); an empty id means the reader
-- keeps its native fallback. Meshes are read with AssetSlots.mesh(name) by the feature that owns them (nil while empty).
local Slots = {}
Slots.Images = {
    -- bind:begin Images (one line per name; tools/bind_assets.py edits the value only)
    aura_meadow = "",
    aura_tidal = "",
    aura_royal = "",
    mutation_dewdrop = "",
    mutation_charged = "",
    mutation_frost = "",
    mutation_seismic = "",
    mutation_ember = "",
    mutation_aurora = "",
    mutation_bloodmoon = "",
    paint_bucket = "",
    rarity_common = "",
    rarity_uncommon = "",
    rarity_rare = "",
    rarity_epic = "",
    rarity_legendary = "",
    rarity_mythic = "",
    tier_gold = "",
    tier_emerald = "",
    tier_diamond = "",
    notify_crystal = "",
    notify_level = "",
    notify_star = "",
    notify_mutation_egg = "",
    notify_warning = "",
    toast_body = "",
    frame_common = "",
    frame_uncommon = "",
    frame_rare = "",
    frame_epic = "",
    frame_legendary = "",
    hud_heart = "",
    hud_class_1 = "",
    hud_class_2 = "",
    hud_class_3 = "",
    class_ground = "",
    class_flyer = "",
    class_water = "",
    class_armored = "",
    hud_bite = "",
    hud_hit_bubble = "",
    crystals_s = "",
    crystals_m = "",
    crystals_l = "",
    crystals_xl = "",
    station_nests = "",
    station_potions = "",
    station_fusion = "",
    station_style = "",
    station_index = "",
    station_settings = "",
    fame_plaque = "",
    golden_drumstick_icon = "",
    potion_icon_speed_common = "rbxassetid://82050795396595",
    potion_icon_growth_common = "rbxassetid://128211480010242",
    potion_icon_loot_common = "rbxassetid://83330672989081",
    potion_icon_speed_uncommon = "rbxassetid://135451701316768",
    potion_icon_growth_uncommon = "rbxassetid://94136880505512",
    potion_icon_speed_rare = "rbxassetid://74980985405918",
    potion_icon_growth_rare = "rbxassetid://87451572767074",
    potion_icon_loot_rare = "rbxassetid://113928284582871",
    potion_icon_growth_epic = "rbxassetid://122890057142150",
    potion_icon_loot_epic = "rbxassetid://94780850187438",
    potion_icon_speed_legendary = "rbxassetid://71253957039051",
    potion_icon_growth_legendary = "rbxassetid://94190575742218",
    -- bind:end Images
}
Slots.Meshes = {
    -- bind:begin Meshes
    hatch_bucket_mesh = "",
    golden_drumstick_mesh = "",
    shock_dome_mesh = "",
    shaft_cone_mesh = "",
    aura_shell_mesh = "",
    -- bind:end Meshes
}
local function valid(id: any): boolean return type(id) == "string" and string.match(id, "^rbxassetid://%d+$") ~= nil end
Slots.isValid = valid
-- "rbxassetid://N" or nil while unbound or malformed.
function Slots.image(name: string): string? local id = Slots.Images[name] return if valid(id) then id else nil end
function Slots.mesh(name: string): string? local id = Slots.Meshes[name] return if valid(id) then id else nil end
return Slots
