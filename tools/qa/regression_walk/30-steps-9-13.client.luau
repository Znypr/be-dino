--!nocheck
-- BD-541 regression walk, CLIENT chunk 3: steps 9 to 13 (potion buy and use, Crystal Shop tabs, Fusion menu open without fusing,
-- Settings tabs and Reduce Motion, a second run). Needs 00-lib.client.luau, and the step files of chunks 1 and 2 loaded in the same
-- session (step 13 repeats steps 2, 3 and 6). Repeat while CONTINUE.
local W = shared.BDWalk
assert(W and W.lib == 2, "run 00-lib.client.luau first")
local HttpService = game:GetService("HttpService")
local player = W.player
local add = W.add

-- ---- 9. potion buy and use -----------------------------------------------------------------------------------------------------
local function shopAct(action, id, replace) -- ProgressionAction -> ProgressionResult, exactly as Bootstrap's transact() does
    local remote, result = W.remote("ProgressionAction"), W.remote("ProgressionResult")
    if not remote or not result then return nil end
    local got
    for _ = 1, 3 do -- the server answers "busy" to a second action within 0.4 s (ProgressionService rate limit): a player cannot click that fast, so wait and retry
        local token = HttpService:GenerateGUID(false)
        got = nil
        local conn = result.OnClientEvent:Connect(function(t, ok, status) if t == token then got = {ok = ok, status = status} end end)
        remote:FireServer(action, id, token, replace == true)
        W.wait(function() return got end, 6)
        conn:Disconnect()
        if not got or got.status ~= "busy" then break end
        task.wait(0.6)
    end
    return got
end
W.steps[9] = function(ctx)
    local c = {}
    local name = "Potion buy and use"
    if W.modalOpen() and not W.modalOpen("Potion Shop") then W.closeModal() end -- keep it when a hand click already opened it (NEEDS flow)
    if not add(c, W.rs() == "Sanctuary", "at home (RunState " .. tostring(W.rs()) .. ")") then return name, c end
    local Rules, PC = W.mod("Shared.ProgressionRules"), W.mod("Shared.ProgressionConfig")
    local ok, why = W.ensure(function() return W.modalOpen("Potion Shop") end, function() return W.rail("potions") end, "POTIONS", 7)
    if not add(c, if ok then true else nil, if ok then "Potion Shop opened" else why) then return name, c end
    local s = W.scrim()
    add(c, s:FindFirstChild("PotionScroll", true) ~= nil, "offer list is drawn")
    local window = Rules.shopWindow(workspace:GetServerTimeNow())
    local p = W.json("ProgressionJson") or {}
    local pick
    for _, offer in Rules.shopOffers(window) do
        local item = Rules.item(PC.Potions, offer.id)
        if Rules.shopRemaining(p, window, offer.id) > 0 and (not pick or item.price < pick.price) then pick = item end
    end
    if not add(c, pick ~= nil, "a potion with stock is on offer") then return name, c end
    local owned0 = (p.potions or {})[pick.id] or 0
    local crystals0 = W.num("Crystals")
    local buy = shopAct("buyPotion", pick.id .. "@" .. window, false)
    add(c, buy ~= nil and buy.ok == true, "buy " .. pick.name .. " answered " .. (if buy then tostring(buy.ok) .. "/" .. tostring(buy.status) else "nothing"))
    add(c, W.wait(function() return ((W.json("ProgressionJson") or {}).potions or {})[pick.id] == owned0 + 1 end, 4) ~= nil, "owned " .. pick.id .. " went " .. owned0 .. " -> " .. tostring((((W.json("ProgressionJson") or {}).potions or {})[pick.id])))
    local crystals1 = W.num("Crystals")
    local preview = string.find(tostring(player:GetAttribute("ProfileMode")), "preview", 1, true) ~= nil
    local Config = W.mod("Shared.Config")
    local resetTo = if preview and Config then Config.StudioTestCrystals else nil -- ProfileRepository sets the wallet to StudioTestCrystals on every action in a Studio preview
    add(c, if crystals1 == crystals0 - pick.price then true elseif preview and (crystals1 == crystals0 or crystals1 == resetTo) then nil else false, string.format("crystals %d -> %d (price %d)%s", crystals0, crystals1, pick.price, if preview then " [Studio test wallet resets to a fixed amount]" else ""))
    local active = (((W.json("ProgressionJson") or {}).buffs or {})[pick.kind])
    task.wait(0.5)
    local use = shopAct("usePotion", pick.id, active ~= nil and active.expiresAt > workspace:GetServerTimeNow())
    add(c, use ~= nil and use.ok == true, "use answered " .. (if use then tostring(use.ok) .. "/" .. tostring(use.status) else "nothing"))
    local buff = W.wait(function() local b = ((W.json("ProgressionJson") or {}).buffs or {})[pick.kind] return b and b.expiresAt > workspace:GetServerTimeNow() and b end, 4)
    add(c, buff ~= nil, "a " .. pick.kind .. " buff is running" .. (if buff then string.format(" for %.0f s", buff.expiresAt - workspace:GetServerTimeNow()) else ""))
    local chip = W.wait(function() return W.hasMatch(W.gui(), "[Pp]otion %d") end, 4)
    add(c, chip ~= nil, "the HUD lists the potion timer: " .. tostring(chip))
    W.keep.potionKind = pick.kind
    return name, c, "the Potion Shop and the potion chip on the HUD"
end

-- ---- 10. Crystal Shop tabs -----------------------------------------------------------------------------------------------------
W.steps[10] = function(ctx)
    local c = {}
    local name = "Crystal Shop tabs"
    if W.modalOpen() and not W.modalOpen("Crystal Shops") then W.closeModal() end -- keep it when a hand click already opened it (NEEDS flow)
    if not add(c, W.rs() == "Sanctuary", "at home (RunState " .. tostring(W.rs()) .. ")") then return name, c end
    local Ftue, Theme = W.mod("Shared.FtueP1"), W.mod("Shared.UITheme")
    local ok, why = W.ensure(function() return W.modalOpen("Crystal Shops") end, function() return W.rail("auras") end, "SHOP", 7)
    if not add(c, if ok then true else nil, if ok then "Crystal Shops opened" else why) then return name, c end
    local s = W.scrim()
    local tile = W.find(s, function(d) return d.Name == "ShopTile_auras" and W.visible(d) end) -- the landing page shows once its pictures exist
    if tile then
        W.tap(tile, function() return W.btn(s, "AURAS") ~= nil end, 3)
        add(c, W.btn(s, "AURAS") ~= nil, "landing tile opens the tabs")
    end
    local level = player:GetAttribute("AccountLevel") or 1
    local tabs = Ftue.shopTabs(level)
    add(c, (W.btn(s, "CONDITIONS") ~= nil) == (level >= Ftue.ConditionsTabLevel), string.format("CONDITIONS tab %s at level %d", if W.btn(s, "CONDITIONS") then "shown" else "hidden", level))
    -- W.keep.shop survives a hand-click re-run (a NEEDS stop returns the step, which clears its own memory): tabs already checked are
    -- skipped, so clicking the printed tab and re-running walks one tab further each time. A finished walk clears it.
    W.keep.shop = W.keep.shop or {seen = {}, done = {}}
    local seen, done = W.keep.shop.seen, W.keep.shop.done
    for _, tab in tabs do
        local label = string.upper(tab)
        if not done[tab] then
            local function onTab() local b = W.btn(s, label) return b ~= nil and b.BackgroundColor3 == Theme.Colors.blue end
            local ok2, why2 = W.ensure(onTab, function() return W.btn(s, label) end, label .. " tab")
            if not add(c, if ok2 then true else nil, if ok2 then label .. " tab opens" else why2) then return name, c end
            task.wait(0.3)
            local snap = table.concat(W.texts(s), "\n")
            add(c, seen[snap] == nil, label .. " page differs from the others")
            seen[snap] = tab
            if tab == "eggs" then add(c, W.hasMatch(s, "Random Egg") ~= nil and (W.btn(s, "BUY EGG") ~= nil or W.btn(s, "NEED", true) ~= nil or W.btn(s, "COMING SOON") ~= nil), "Eggs tab: Random Egg and a buy button (or COMING SOON, BD-532 / EG1)") end
            if tab == "crystals" then add(c, W.hasMatch(s, "You have") ~= nil, "Crystals tab: balance line") end
            if tab == "conditions" then add(c, W.hasMatch(s, "never Cracked") ~= nil or W.hasMatch(s, "%%") ~= nil, "Conditions tab: percentages") end
            done[tab] = true
        end
    end
    W.keep.shop = nil
    return name, c, "the Crystal Shops page on its last tab; repeat on the others if a tab looked odd"
end

-- ---- 11. fusion menu opens (no fusing) -------------------------------------------------------------------------------------------
W.steps[11] = function(ctx)
    local c = {}
    local name = "Fusion menu (open only)"
    if W.modalOpen() then W.closeModal() end
    if not add(c, W.rs() == "Sanctuary", "at home (RunState " .. tostring(W.rs()) .. ")") then return name, c end
    local function fusion() local pg = player:FindFirstChild("PlayerGui") return pg and pg:FindFirstChild("BeDinoFusionUI") end
    local function up() local f = fusion() return f ~= nil and f.Enabled end
    local function legacy() return W.gui() ~= nil and W.hasMatch(W.gui(), "coming soon") ~= nil end -- BD-617: the old Dinosaur Fusion card is gone
    local ok, why = W.ensure(function() return up() or legacy() end, function() return W.rail("fusion") end, "FUSION", 7)
    if not add(c, if ok then true else nil, if ok then "FUSION answered" else why) then return name, c end
    if not up() then
        add(c, nil, "FUSION said 'coming soon': the pattern Fusion Menu is switched off in this build, nothing more to check")
        return name, c, "the coming-soon notice"
    end
    task.wait(0.5)
    local f = fusion()
    local panel = f:FindFirstChild("FusionPanel", true)
    add(c, panel ~= nil and W.visible(panel), "FusionPanel is on screen")
    local unavailable = W.hasMatch(f, "unavailable") ~= nil
    if unavailable then
        add(c, nil, "the menu says Fusion is unavailable here (flag off): nothing more to check")
    else
        local columns = 0
        for _, n in {"Browse", "Ingredients", "ResultColumn"} do if f:FindFirstChild(n, true) then columns += 1 end end
        add(c, columns == 3, columns .. " of 3 columns (Browse, Ingredients, Result)")
        local rail = W.hudRects().rail
        local cam = workspace.CurrentCamera
        if rail and panel and W.visible(rail) and W.visible(panel) then
            local compact = cam ~= nil and cam.ViewportSize.Y < 500 -- BD-334: on a short phone canvas the panel may cover the rail by design
            local clear = panel.AbsolutePosition.X >= rail.AbsolutePosition.X + rail.AbsoluteSize.X - 2
            add(c, if compact then nil else clear, string.format("panel starts at x=%.0f, rail ends at x=%.0f%s", panel.AbsolutePosition.X, rail.AbsolutePosition.X + rail.AbsoluteSize.X, if compact then " (phone-size window: not judged)" else ""))
        end
    end
    -- Close with the menu's own X button. NOT through require(Client.FusionMenu).close(): this script runs in its own Lua VM, so that module is a
    -- second instance whose "open" state is not the game's (2026-10-17 run: close() did nothing and the check failed).
    local okc, whyc = W.ensure(function() return not up() end, function() return W.btn(fusion(), "X") end, "Fusion menu X")
    add(c, if okc then true else nil, if okc then "the menu closes again (its own X button)" else whyc)
    if okc then W.ensure(up, function() return W.rail("fusion") end, "FUSION", 7) end -- left open for the capture; step 12 closes it
    return name, c, "the Fusion menu is OPEN: capture now (nothing was fused)"
end

-- ---- 12. Settings tabs and Reduce Motion --------------------------------------------------------------------------------------
W.steps[12] = function(ctx)
    local c = {}
    local name = "Settings tabs and Reduce Motion"
    -- NOTE: require(Client.SettingsMenu / Shared.SettingsModel / Shared.UITheme) from this script gives a SECOND module instance (own Lua VM), whose
    -- tab(), calm() and MotionEnabled are not the game's. So everything here is read from what the player sees (page markers, the toggle's text)
    -- and from the saved SettingsJson, which is the server's truth.
    local fgui = player:FindFirstChild("PlayerGui") and player.PlayerGui:FindFirstChild("BeDinoFusionUI") -- close the Fusion menu by its own X (see step 11)
    if fgui and fgui.Enabled then W.ensure(function() return not fgui.Enabled end, function() return W.btn(fgui, "X") end, "Fusion menu X") end
    if W.modalOpen() and not W.modalOpen("Settings") then W.closeModal() end -- keep it when a hand click already opened it (NEEDS flow)
    if not add(c, W.rs() == "Sanctuary", "at home (RunState " .. tostring(W.rs()) .. ")") then return name, c end
    local ok, why = W.ensure(function() return W.modalOpen("Settings") end, function() return W.rail("settings") end, "SETTINGS", 7)
    if not add(c, if ok then true else nil, if ok then "Settings opened" else why) then return name, c end
    -- W.keep.settings survives a hand-click re-run (a NEEDS stop returns the step): tabs already checked are skipped, their lines are kept.
    local keep = W.keep.settings or {done = {}, lines = {}}
    W.keep.settings = keep
    for _, l in keep.lines do table.insert(c, l) end
    local marker = {sound = "Hatch sound", look = "Calm motion", controls = "Camera", help = "HOW TO PLAY"}
    for _, id in {"sound", "look", "controls", "help"} do
        if not keep.done[id] then
            local s = W.scrim()
            local ok2, why2 = W.ensure(function() return W.hasExact(W.scrim(), marker[id]) end, function() return s:FindFirstChild("Tab_" .. id, true) end, id .. " tab")
            if not add(c, if ok2 then true else nil, if ok2 then id .. " tab shows '" .. marker[id] .. "'" else why2) then return name, c end
            keep.done[id] = true
            table.insert(keep.lines, {true, id .. " tab shows '" .. marker[id] .. "'"})
        end
    end
    local function calmOn() local j = W.json("SettingsJson") return j ~= nil and j.calm == true end
    local function toggle() return W.scrim() and W.scrim():FindFirstChild("Toggle_Calm motion", true) end
    ok, why = W.ensure(function() return W.hasExact(W.scrim(), "Calm motion") end, function() return W.scrim():FindFirstChild("Tab_look", true) end, "look tab")
    ok, why = W.ensure(function() local t = toggle() return t ~= nil and t.Text == "ON" end, toggle, "Calm motion toggle")
    if not add(c, if ok then true else nil, if ok then "Calm motion (Reduce Motion) switched ON" else why) then return name, c end
    local Theme = W.mod("Shared.UITheme") -- in Studio this is the script's own copy and still says true: ODD, not a verdict on the game
    add(c, if Theme and Theme.MotionEnabled == false then true else nil, if Theme and Theme.MotionEnabled == false then "UITheme.MotionEnabled is false" else "UITheme.MotionEnabled cannot be read from this script (its own module copy); the saved setting below is the check")
    add(c, toggle() ~= nil and toggle().Text == "ON", "the toggle reads " .. (toggle() and toggle().Text or "(missing)"))
    add(c, W.wait(calmOn, 6) ~= nil, "the server saved calm=true (SettingsJson)")
    W.keep.calmOn = true
    W.keep.settings = nil
    return name, c, "Reduce Motion is ON now (left on for this capture; step 13 turns it off first)"
end

-- ---- 13. a second run -----------------------------------------------------------------------------------------------------------
W.steps[13] = function(ctx)
    local m = ctx.mem
    local c = m.c or {}
    m.c = c
    local name = "Second run"
    m.ph = m.ph or "calm"
    local function sub(key, step, target) -- run a step of an earlier chunk on its own scratch memory and fold its checks in
        m[key] = m[key] or {mem = {since = m.since or os.time() - 1}, target = target}
        if not W.steps[step] then add(c, nil, "step " .. step .. " is not loaded: run its chunk first") return "ODD" end
        local ok, first, checks, _note, status, progress = pcall(W.steps[step], m[key])
        if not ok then add(c, false, "step " .. step .. " crashed: " .. string.sub(tostring(first), 1, 120)) return "FAIL" end
        if status == "CONTINUE" then return "CONTINUE", progress end
        for _, ck in checks do add(c, ck[1], "run 2 / " .. ck[2]) end
        return "DONE"
    end
    if m.ph == "calm" then
        -- read and set Reduce Motion through what the player sees (the toggle) and the saved SettingsJson, not through a module copy (see step 12)
        local function calmOn() local j = W.json("SettingsJson") return j ~= nil and j.calm == true end
        if calmOn() then
            if W.modalOpen() and not W.modalOpen("Settings") then W.closeModal() end
            local function toggle() return W.scrim() and W.scrim():FindFirstChild("Toggle_Calm motion", true) end
            local ok, why = W.ensure(function() return W.modalOpen("Settings") end, function() return W.rail("settings") end, "SETTINGS", 7)
            if ok then ok, why = W.ensure(function() return W.hasExact(W.scrim(), "Calm motion") end, function() return W.scrim():FindFirstChild("Tab_look", true) end, "look tab") end
            if ok then ok, why = W.ensure(function() local t = toggle() return t ~= nil and t.Text == "OFF" end, toggle, "Calm motion toggle") end
            if not ok then add(c, nil, tostring(why)) return name, c end
        end
        if W.modalOpen() then W.closeModal() end
        add(c, W.wait(function() return not calmOn() end, 6) ~= nil, "Reduce Motion is off again (saved SettingsJson)")
        m.queue0 = W.num("ActiveChestCount") + W.num("QueuedEggsWaiting")
        m.run1 = player:GetAttribute("LastRunId")
        m.ph = "gate"
    end
    if m.ph == "gate" then
        local state, progress = sub("s2", 2)
        if state == "CONTINUE" then return name, c, nil, "CONTINUE", progress end
        add(c, (W.cattr("CatchScore") or -1) == 0, "the new run starts at 0 eggs (CatchScore " .. tostring(W.cattr("CatchScore")) .. ")")
        local text = W.gui():FindFirstChild("EggsText", true)
        add(c, text ~= nil and tonumber(string.match(text.Text, "%d+")) == 0, "the EGGS plate resets to " .. (text and text.Text or "(missing)"))
        add(c, (W.cattr("GrowthScore") or 0) < 5, "growth starts over (" .. string.format("%.0f", W.cattr("GrowthScore") or 0) .. ")")
        m.ph = "eat"
    end
    if m.ph == "eat" then
        local state, progress = sub("s3", 3, 3)
        if state == "CONTINUE" then return name, c, nil, "CONTINUE", progress end
        m.eggs2 = W.keep.eggsStep3
        m.ph = "home"
    end
    if m.ph == "home" then
        local state, progress = sub("s6", 6)
        if state == "CONTINUE" then return name, c, nil, "CONTINUE", progress end
        local score = player:GetAttribute("LastRunCatchScore") or -1
        add(c, player:GetAttribute("LastRunId") ~= m.run1, "run 2 has its own run id")
        add(c, score >= 3 and score <= (m.eggs2 or 3) + 3, "run summary counts only run 2 (" .. tostring(score) .. " eggs, not the sum with run 1)")
        add(c, W.num("ActiveChestCount") + W.num("QueuedEggsWaiting") > m.queue0, "the egg queue grew: " .. m.queue0 .. " -> " .. (W.num("ActiveChestCount") + W.num("QueuedEggsWaiting")))
        local ok = W.admin("reset")
        add(c, if ok == true then true else nil, "admin values reset")
        W.admin("stopWeather")
        add(c, W.wait(function() return workspace:GetAttribute("WeatherId") == "clear" end, 5) ~= nil, "weather is clear again (" .. tostring(workspace:GetAttribute("WeatherId")) .. ")")
        add(c, workspace:GetAttribute("Admin_foodMultiplier") == 1, "Food worth is back to x1")
    end
    return name, c, "the second Run Complete card"
end

return W.run({9, 10, 11, 12, 13})
