-- Offline text-floor smoke (BD-1119 / BD-1117; driven by tools/verify_text_style.py; docs/202 R2 and R4).
-- tools/verify_text_style.py puts the head of tools/menu_layout_smoke.luau in front of this file (the geometry mock, the stubs, the Bootstrap-shaped world,
-- mountShop, showMenu) and swaps in the real modules. So the REAL ModalCompact, PhoneScale, ShopScreens, EggsScreen and TextStyle run here.
-- What is checked at every window size of the small-window check (11 sizes, mouse and touch):
--   1. the window TITLE is at least 22 px on screen and is a title (TextKind attribute set by TextStyle.outlined);
--   2. the red X is at least 48 px on screen in both directions, sits inside the header at the top right and never touches the title;
--   3. every text on a shop page and on the Eggs screen is at least 16 px on screen (text that shrinks to fit is judged at its largest size, like the
--      small-window check), except the entries of tools/text_style_allow.json (each one has a reason).
-- Text is not measured in the mock (no font): this is about the SIZE asked for, not about drawing. NOT Studio evidence.
-- @@PREFIX@@ is already replaced by the head of menu_layout_smoke.
local ALLOW = @@ALLOW@@
local TextStyleReal = requireModule(SharedFolder.TextStyle)
-- what the Eggs screen needs besides the real modules (the same stubs as tools/small_window_smoke.luau)
stubs.EggPicture = {
    add = function(parent, _, size) return inst("ImageLabel", "Egg", parent, {Size = UDim2.fromOffset(size, size), ZIndex = parent.ZIndex + 1}) end,
    stage = function(parent, w, h) return inst("Frame", "Stage", parent, {Size = UDim2.fromOffset(w, h), ZIndex = parent.ZIndex + 1}) end,
}
stubs.ConditionStage = {hero = function() return nil end}
stubs.FxUi = {mount = function() return nil end}
stubs.FusionSelection = {eggSlotLook = function() return "plain" end}
for _, n in {"EggPicture", "ConditionStage", "FxUi", "FusionSelection"} do
    if SharedFolder:FindFirstChild(n) == nil then register(n) end
end
for _, n in {"EggsScreen", "EggPicture", "ConditionStage"} do SharedFolder[n].Parent = ClientFolder end -- the screen finds ModalCompact next to itself
local allowUsed = {}
local TITLE_PX, CARD_PX, CLOSE_PX = 22, 16, 48

local function pxOf(d)
    local size = d.TextSize or 14
    if d.TextScaled then
        local limit = d:FindFirstChildOfClass("UITextSizeConstraint")
        size = if limit then limit.MaxTextSize else size
    end
    local _, _, k = layout(d)
    return size * k
end

local function allowed(tag, d, px)
    for i, entry in ALLOW do
        if string.find(tag, entry.screen, 1, true) == 1 and px >= entry.minPx - .01 then
            local okName = entry.name == nil or d.Name == entry.name
            local okText = entry.text == nil or string.find(d.Text, entry.text, 1, true) ~= nil
            if okName and okText then allowUsed[i] = true return true end
        end
    end
    return false
end

local function chromeChecks(world, tag)
    local heading, x, header = world.heading, world.x, world.header
    local hp = pxOf(heading)
    check(TextStyleReal.onScreenOk("title", hp, ModalCompact.model().mode == "compact"), string.format("%s: the window title is %.1f px on screen (needs %d)", tag, hp, TITLE_PX))
    check(heading:GetAttribute("TextKind") == "title", tag .. ": the window title is not marked as a title (TextStyle.outlined)")
    local xr, hr, tr = rectOf(x), rectOf(header), rectOf(heading)
    check(xr.w >= CLOSE_PX - .5 and xr.h >= CLOSE_PX - .5, string.format("%s: the X is %dx%d px on screen (needs %d)", tag, xr.w + .5, xr.h + .5, CLOSE_PX))
    check(math.abs(xr.w - xr.h) < 1.5, string.format("%s: the X is not a square (%dx%d)", tag, xr.w + .5, xr.h + .5))
    check(inside(xr, hr, 1.5), string.format("%s: the X %s is not inside the header %s", tag, describe(xr), describe(hr)))
    check(xr.x + xr.w >= hr.x + hr.w - 8, string.format("%s: the X is not at the top right (%s in %s)", tag, describe(xr), describe(hr)))
    check(not overlaps(xr, tr), string.format("%s: the title box %s touches the X %s", tag, describe(tr), describe(xr)))
    check(tr.x >= hr.x - .75 and tr.x + tr.w <= xr.x + .75, string.format("%s: the title box %s leaves the header or runs under the X", tag, describe(tr)))
end

local function textChecks(world, tag)
    local count = 0
    local compact = ModalCompact.model().mode == "compact"
    for _, d in world.body:GetDescendants() do
        if isGuiObject(d) and d.Visible and (d:IsA("TextLabel") or d:IsA("TextButton")) and d.Text ~= "" and d.TextTransparency ~= 1 then
            count += 1
            local px = pxOf(d)
            local kind = d:GetAttribute("TextKind")
            if kind == nil or TextStyleReal.Floors[kind] == nil then kind = "card" end
            if not TextStyleReal.onScreenOk(kind, px, compact) and not allowed(tag, d, px) then
                check(false, string.format("%s: text '%s' (%s) is %.1f px on screen (cards need %d, or 14 in a small window; add it to tools/text_style_allow.json with a reason only if it cannot grow)", tag, string.sub(d.Text, 1, 28), d.Name, px, CARD_PX))
            end
        end
    end
    return count
end

local texts = 0
for _, touch in {false, true} do
    for _, size in SIZES do
        local w, h = size[1], size[2]
        for _, pageName in {"auras", "trails", "eggs", "crystals"} do
            local world = buildWorld(w, h, touch)
            local shop = mountShop(world, {touch = touch})
            showMenu(world)
            shop.open("auras")
            for _, tab in tabsOf(world) do
                if string.lower(tab.Text) == pageName then tab.Activated:Fire() end
            end
            ModalCompact.enforce()
            local tag = string.format("Shop/%s %dx%d%s", pageName, w, h, if touch then " touch" else "")
            chromeChecks(world, tag)
            texts += textChecks(world, tag)
            world.gui:Destroy()
        end
        for _, pageName in {"auraConfirm", "auraInfo", "eggPurchase", "oddsSimple", "eggOdds", "potions", "potionConfirm", "potionReplace"} do -- auraInfo: BD-1144
            local world = buildWorld(w, h, touch)
            local shop = mountShop(world, {touch = touch, potions = {speed_common = 2}})
            showMenu(world)
            shop.open(pageName)
            ModalCompact.enforce()
            local tag = string.format("Shop/%s %dx%d%s", pageName, w, h, if touch then " touch" else "")
            chromeChecks(world, tag)
            texts += textChecks(world, tag)
            world.gui:Destroy()
        end
    end
end

-- ===== the Eggs screen (the real EggsScreen in the same world) =====
local EggsScreen = requireModule(ClientFolder.EggsScreen)
local function eggsCtx(world, scenario)
    local values = {NextChestId = scenario.entry and scenario.entry.id or "", QueuedEggsWaiting = scenario.waiting or 0, NextChestReadyAt = 0, ActiveChestCount = scenario.active or 0}
    return {
        body = world.body, C = Colors, label = uiLabel, box = uiBox, button = uiButton, art = uiArt,
        queue = function() return if scenario.entry then {scenario.entry} else {} end,
        str = function(name) return values[name] or "" end, num = function(name) return values[name] or 0 end,
        nestList = scenario.nests, rarityNames = {"Common", "Uncommon", "Rare", "Epic", "Legendary"}, rarityColors = {Colors.text, Colors.accent, Colors.blue, Colors.purple, Colors.gold},
        scale = function() return ModalCompact.model().scale end,
        notify = function() end, openNest = function() end, openEgg = function() end, openSettings = function() end, explore = function() end,
        autoOpenText = function() return "Auto-open is off" end, collectionCopies = function() return scenario.copies or 9 end,
        bodyH = ModalCompact.bodyHeight(), bodyScale = ModalCompact.bodyScale(),
    }
end
local function nestsOf(states)
    local list = {}
    for i, state in states do list[i] = {id = "n" .. i, state = state, readyAt = 1000 + 9000 * i, genes = nil} end
    return list
end
local EGG_PLAIN = {id = "e1", rarity = 2, readyAt = 0}
local EGG_CRACKED = {id = "e2", rarity = 4, readyAt = 0, genes = {patternId = "01_plain", primaryColorId = "green", secondaryColorId = "blue", blend = 20, conditionId = "cracked"}, mutationId = "frost"}
local EGG_SCENARIOS = {
    {name = "plain egg", entry = EGG_PLAIN, waiting = 13, active = 1, nests = nestsOf({"incubating", "queued", "queued", "queued", "queued"})},
    {name = "cracked egg", entry = EGG_CRACKED, waiting = 40, active = 1, nests = nestsOf({"ready", "incubating", "queued", "queued", "queued"})},
    {name = "nothing waiting", entry = nil, waiting = 0, active = 0, nests = {}},
}
for _, scenario in EGG_SCENARIOS do
    for _, size in SIZES do
        local w, h = size[1], size[2]
        local world = buildWorld(w, h, false)
        showMenu(world)
        local refresh = EggsScreen.render(eggsCtx(world, scenario))
        ModalCompact.enforce()
        refresh()
        local tag = string.format("Eggs %dx%d (%s)", w, h, scenario.name)
        chromeChecks(world, tag)
        texts += textChecks(world, tag)
        world.gui:Destroy()
    end
end

-- ===== BD-1120: rarity words are coloured where they are shown (the REAL Toasts, EggsScreen and RarityWord) =====
local RarityWordReal = requireModule(SharedFolder.RarityWord)
local function hexOf(tier) return RarityWordReal.hex(tier) end
do
    local world = buildWorld(1156, 793, false)
    loaded.Toasts = nil
    local Toasts = requireModule(ClientFolder.Toasts)
    Toasts.attach({gui = world.gui, shade = world.shade, box = uiBox, label = uiLabel, art = uiArt, motion = function() return false end})
    Toasts.notify("Legendary hatch!", Colors.red, {key = "rw1", body = "Best: Epic Compy"})
    Toasts.notify("Follow the glow", Colors.red, {key = "rw2", body = "Rarer potions show up less often."})
    frames(4)
    local seen = {}
    for _, d in Toasts.layer:GetDescendants() do
        if d:IsA("TextLabel") and d.Visible and d.Text ~= "" then seen[d.Text] = d end
    end
    local legendary = '<font color="' .. hexOf(5) .. '">Legendary</font> hatch!'
    local epic = 'Best: <font color="' .. hexOf(4) .. '">Epic</font> Compy'
    check(seen[legendary] ~= nil and seen[legendary].RichText == true, "a toast title that names Legendary shows the word in the Legendary colour (" .. hexOf(5) .. ")")
    check(seen[epic] ~= nil and seen[epic].RichText == true, "a toast line that names Epic shows the word in the Epic colour (" .. hexOf(4) .. ")")
    check(seen["Follow the glow"] ~= nil and seen["Follow the glow"].RichText ~= true, "a toast without a tier word stays plain text")
    check(seen["Rarer potions show up less often."] ~= nil and seen["Rarer potions show up less often."].RichText ~= true, "'Rarer' is not the word Rare: the line stays plain")
    world.gui:Destroy()
end
do
    local world = buildWorld(1156, 793, false)
    showMenu(world)
    local scenario = {name = "tier words", entry = EGG_PLAIN, waiting = 3, active = 1, nests = nestsOf({"incubating", "queued", "queued", "queued", "queued"})}
    local ctx = eggsCtx(world, scenario)
    ctx.autoOpenText = function() return "Auto-open: Common, Uncommon" end
    EggsScreen.render(ctx)
    ModalCompact.enforce()
    local auto = nil
    for _, d in world.body:GetDescendants() do
        if d:IsA("TextLabel") and string.sub(d.Text, 1, 10) == "Auto-open:" then auto = d end
    end
    local want = 'Auto-open: <font color="' .. hexOf(1) .. '">Common</font>, <font color="' .. hexOf(2) .. '">Uncommon</font>'
    check(auto ~= nil and auto.RichText == true and auto.Text == want, "the Eggs screen paints the tier words of the auto-open line (" .. (if auto then auto.Text else "no label") .. ")")
    world.gui:Destroy()
end
print("Rarity words ok")

for i, entry in ALLOW do
    if not allowUsed[i] then print("ALLOWSTALE " .. i) end
end
if failures > 0 then error(failures .. " text-floor check(s) failed") end
print("Text floor smoke passed: " .. texts .. " texts judged at " .. #SIZES .. " sizes")
