--!strict
-- BD-1232 (docs/242 benchmark gap 17, "loading is a clean logo + bar but plain"): the loading scene and the rotating kid tip, used ONLY while
-- Config.LoadingSceneEnabled is on (playtest profile) and the warm loading look (Config.ScreensCohesionEnabled) is on. Pure data and rules:
-- no Roblox services, no Instances (src/loading/Loading.client.luau draws it; tools/verify_loading_scene.py runs this offline).
--   * the scene is REAL art: the owner-approved Blender render egg_stage_jungle (jungle waterfalls over a stone pedestal, docs/77), uploaded
--     2026-11-16 and checked IsLoaded in Studio. Never code-drawn. An empty or malformed id = the plain warm field, as before.
--   * one short tip at a time, a new one every TipSeconds; words follow docs/72 (short, no numbers like "5m 0s" or "1.25x").
--   * a Skip button after SkipSeconds, only once the save has loaded (before that there is nothing to play yet).
local S = {}

S.SceneImage = "rbxassetid://116338780514546" -- egg_stage_jungle (resources/ui/v2/stage/egg-stage-jungle-v1.jpg), docs/77
S.SceneShade = 0.25 -- a light cream veil over the picture so the title and the bar stay readable (R2)
S.TipSeconds = 4
S.SkipSeconds = 6
S.TipMax = 40 -- characters: one line on a phone
S.Tips = table.freeze({
    "Eat food to grow big!",
    "Bigger dinos find more eggs!",
    "Hatch eggs to find new dinos!",
    "Nests make eggs while you rest.",
    "Watch out for big hungry dinos!",
    "Rainbow eggs are extra rare!",
    "Fuse six of one dino for a Gold one!",
    "Crystals buy potions and trails.",
})

-- Is this a usable picture id?
function S.validImage(id: any): boolean
    return typeof(id) == "string" and string.match(id, "^rbxassetid://%d+$") ~= nil
end

-- The tip to show `elapsed` seconds after the start. `seed` (0..n-1) picks the first tip, so two joins do not always start alike.
function S.tipAt(elapsed: number, seed: number): string
    local n = #S.Tips
    local step = math.max(0, math.floor(elapsed / S.TipSeconds))
    return S.Tips[((math.floor(seed) + step) % n) + 1]
end

-- Show the Skip button? loaded = the save is loaded (ProfileState "Loaded").
function S.skipVisible(elapsed: number, loaded: boolean): boolean
    return loaded and elapsed >= S.SkipSeconds
end

return S
