-- Offline rare-find banner smoke (BD-1121; driven by tools/verify_rare_find_banner.py; docs/202 R6).
-- tools/verify_rare_find_banner.py puts the head of tools/menu_layout_smoke.luau in front of this file (the geometry mock, the stubs, the Bootstrap-shaped world) and swaps in the
-- real modules. So the REAL RareFindBanner, RareHatch, RarityWord and TextStyle run here, and the mock keeps a clock (frames) for the fades and the hold.
-- What is checked: two lines and NO panel (no background anywhere), a huge outlined title "RARE FIND!", one sentence with the rarity word in its colour, no player name, a secret
-- keeps its name out, a bad payload draws nothing (the caller then shows the old strip), fades only without Reduce Motion, the banner goes away by itself, one at a time.
-- NOT Studio evidence: no font, no drawing.
-- @@PREFIX@@ is already replaced by the head of menu_layout_smoke.
local TextStyleReal = requireModule(SharedFolder.TextStyle)
local RarityWordReal = requireModule(SharedFolder.RarityWord)
local Banner = requireModule(SharedFolder.RareFindBanner)
local Rare = requireModule(SharedFolder.RareHatch)

local tweens = 0
do
    local realCreate = Services.TweenService.Create
    Services.TweenService.Create = function(self, ...) tweens += 1 return realCreate(self, ...) end
end

local function hexOf(tier) return RarityWordReal.hex(tier) end
local function banners(gui)
    local out = {}
    for _, c in gui:GetChildren() do if c.Name == Banner.Name then table.insert(out, c) end end
    return out
end
local function texts(root)
    local out = {}
    for _, d in root:GetDescendants() do if d:IsA("TextLabel") then out[d.Name] = d end end
    return out
end
local function runUntilGone(gui, limit)
    for _ = 1, limit do
        if #banners(gui) == 0 then return true end
        frames(1, 1)
    end
    return #banners(gui) == 0
end

local world = buildWorld(1156, 793, false)
local gui = world.gui
local good = {k = "all", kind = "legendary", tier = 5, species = "Compy", text = "Sam hatched a Legendary Compy!", shiny = false, mutation = false}

-- 1. a legendary find, with motion
tweens = 0
check(Banner.show(gui, good, false) == true, "a good payload draws the banner")
local list = banners(gui)
check(#list == 1, "exactly one banner is on screen (" .. #list .. ")")
local root = list[1]
local t = if root then texts(root) else {}
check(t.Title ~= nil and t.Line ~= nil, "the banner has a title line and a sentence")
if t.Title and t.Line then
    check(t.Title.Text == "RARE FIND!", "the title says RARE FIND! (" .. t.Title.Text .. ")")
    check(t.Line.RichText == true and t.Line.Text == 'A <font color="' .. hexOf(5) .. '">Legendary</font> Compy was found!', "the sentence paints Legendary in its colour (" .. t.Line.Text .. ")")
    -- NO panel: nothing in the banner has a background, and it is only the two labels (plus size rules)
    for _, d in root:GetDescendants() do
        if d:IsA("GuiObject") then check(d.BackgroundTransparency == 1, "no panel: " .. d.Name .. " has a background") end
    end
    check(root.BackgroundTransparency == 1, "no panel: the banner root has no background")
    local labelsN, otherGui = 0, 0
    for _, d in root:GetDescendants() do
        if d:IsA("TextLabel") then labelsN += 1 elseif d:IsA("GuiObject") then otherGui += 1 end
    end
    check(labelsN == 2 and otherGui == 0, "only two text lines and nothing else drawn (" .. labelsN .. " labels, " .. otherGui .. " other)")
    -- huge, white, outlined
    check(t.Title:GetAttribute("TextKind") == "title" and t.Line:GetAttribute("TextKind") == "card", "title and sentence use the outlined text style")
    local ts, ls = t.Title:FindFirstChildOfClass("UIStroke"), t.Line:FindFirstChildOfClass("UIStroke")
    check(ts ~= nil and ts.Thickness >= 3 and ts.Transparency == 0, "the title has a thick dark outline")
    check(ls ~= nil and ls.Thickness >= 2, "the sentence has an outline")
    local tl, ll = t.Title:FindFirstChildOfClass("UITextSizeConstraint"), t.Line:FindFirstChildOfClass("UITextSizeConstraint")
    check(tl ~= nil and tl.MaxTextSize >= 48 and tl.MinTextSize >= TextStyleReal.Floors.title, "the title is huge (up to " .. tostring(tl and tl.MaxTextSize) .. " px) and never under 22 px")
    check(ll ~= nil and ll.MaxTextSize >= 26 and ll.MinTextSize >= TextStyleReal.Floors.card, "the sentence is big (up to " .. tostring(ll and ll.MaxTextSize) .. " px) and never under 16 px")
    check(t.Title.TextColor3.R == 1 and t.Title.TextColor3.G == 1 and t.Title.TextColor3.B == 1, "the title is white")
    -- no player name, anywhere
    for _, d in root:GetDescendants() do
        if d:IsA("TextLabel") then check(not string.find(d.Text, "Sam"), "no player name on the banner (" .. d.Text .. ")") end
    end
    check(root.Active == false and t.Title.Active == false and t.Line.Active == false, "the banner never takes a tap")
end
check(tweens >= 4, "with motion the two lines fade in (" .. tweens .. " tweens)")
local before = tweens
check(runUntilGone(gui, 12), "the banner goes away by itself")
check(tweens > before, "with motion it fades out before it goes")

-- 2. Reduce Motion: no fades at all, the same hold
tweens = 0
check(Banner.show(gui, good, true) == true, "Reduce Motion still shows the banner")
check(tweens == 0, "Reduce Motion: no fade (" .. tweens .. " tweens)")
list = banners(gui)
local calmT = if list[1] then texts(list[1]) else {}
check(calmT.Title ~= nil and (calmT.Title.TextTransparency or 0) == 0 and (calmT.Line.TextTransparency or 0) == 0, "Reduce Motion: shown at full strength at once")
frames(3, 1)
check(#banners(gui) == 1, "Reduce Motion: still on screen after 3 s (the hold is " .. Rare.FindFade.hold .. " s)")
check(runUntilGone(gui, 12) and tweens == 0, "Reduce Motion: it goes away without a fade")

-- 3. other finds
local function line(payload, calm)
    local ok = Banner.show(gui, payload, calm)
    local l = banners(gui)[1]
    local tx = if l then texts(l) else {}
    local result = {ok = ok, title = tx.Title and tx.Title.Text, line = tx.Line and tx.Line.Text}
    for _, b in banners(gui) do b:Destroy() end
    return result
end
local r = line({kind = "shiny", tier = 4, species = "Raptor", shiny = true, mutation = true, text = "x"}, true)
check(r.ok and r.line == 'An <font color="' .. hexOf(4) .. '">Epic</font> Shiny Mutant Raptor was found!', "Epic shiny mutant: " .. tostring(r.line))
r = line({kind = "secret", species = "Hidden Name", text = "x"}, true)
check(r.ok and r.title == "SECRET FIND!" and r.line == "A secret dino was found!", "a secret find: " .. tostring(r.title) .. " / " .. tostring(r.line))
check(not string.find(tostring(r.line), "Hidden"), "a secret keeps its species name out of the banner")
r = line({kind = "mutation", tier = 1, species = "Compy", mutation = true, text = "x"}, true)
check(r.ok and r.line == 'A <font color="' .. hexOf(1) .. '">Common</font> Mutant Compy was found!', "Common mutant: " .. tostring(r.line))

-- 4. a payload that fails the checks draws nothing (RareHatchClient then shows the old strip)
for i, bad in {
    {k = "all", kind = "legendary", text = "Sam hatched a Legendary Compy!"}, -- the old payload: no tier, no species
    {k = "all", kind = "legendary", tier = 9, species = "Compy", text = "x"},
    {k = "all", kind = "legendary", tier = 5, species = "<b>Compy</b>", text = "x"},
    {k = "all", kind = "legendary", tier = 5, species = string.rep("x", 30), text = "x"},
    {k = "all", kind = "nonsense", tier = 5, species = "Compy", text = "x"},
} do
    local result = line(bad, false)
    check(result.ok == false and #banners(gui) == 0, "bad payload " .. i .. " draws nothing")
end

-- 5. one at a time
Banner.show(gui, good, true)
Banner.show(gui, {kind = "shiny", tier = 3, species = "Compy", shiny = true, text = "x"}, true)
check(#banners(gui) == 1, "a new find replaces the one still on screen (" .. #banners(gui) .. ")")
local only = banners(gui)[1]
check(only ~= nil and string.find(texts(only).Line.Text, "Shiny") ~= nil, "the newest find is the one shown")

if failures > 0 then error(failures .. " rare-find banner check(s) failed") end
print("Rare find banner smoke passed: two lines, no panel, huge outlined title, coloured rarity word, no name, secret hidden, bad payloads refused, fades only with motion")
