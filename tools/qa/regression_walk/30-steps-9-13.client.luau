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
    local token, got = HttpService:GenerateGUID(false), nil
    local conn = result.OnClientEvent:Connect(function(t, ok, status) if t == token then got = {ok = ok, status = status} end end)
    remote:FireServer(action, id, token, replace == true)
    W.wait(function() return got end, 6)
    conn:Disconnect()
    return got
end
W.steps[9] = function(ctx)
    local c = {}
    local name = "Potion buy and use"
    if W.modalOpen() then W.closeModal() end
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
    add(c, if crystals1 == crystals0 - pick.price then true elseif preview and crystals1 == crystals0 then nil else false, string.format("crystals %d -> %d (price %d)%s", crystals0, crystals1, pick.price, if preview then " [Studio test wallet resets to a fixed amount]" else ""))
    local active = (((W.json("ProgressionJson") or {}).buffs or {})[pick.kind])
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
    if W.modalOpen() then W.closeModal() end
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
    local seen = {}
    for _, tab in tabs do
        local label = string.upper(tab)
        local function onTab() local b = W.btn(s, label) return b ~= nil and b.BackgroundColor3 == Theme.Colors.blue end
        local ok2, why2 = W.ensure(onTab, function() return W.btn(s, label) end, label .. " tab")
        if not add(c, if ok2 then true else nil, if ok2 then label .. " tab opens" else why2) then return name, c end
        task.wait(0.3)
        local snap = table.concat(W.texts(s), "\n")
        add(c, seen[snap] == nil, label .. " page differs from the others")
        seen[snap] = tab
        if tab == "eggs" then add(c, W.hasMatch(s, "Random Egg") ~= nil and (W.btn(s, "BUY EGG") ~= nil or W.btn(s, "NEED", true) ~= nil), "Eggs tab: Random Egg and a buy button") end
        if tab == "crystals" then add(c, W.hasMatch(s, "You have") ~= nil, "Crystals tab: balance line") end
        if tab == "conditions" then add(c, W.hasMatch(s, "never Cracked") ~= nil or W.hasMatch(s, "%%") ~= nil, "Conditions tab: percentages") end
    end
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
    local function legacy() return W.modalOpen("Dinosaur Fusion") or (W.gui() ~= nil and W.hasMatch(W.gui(), "coming soon") ~= nil) end
    local ok, why = W.ensure(function() return up() or legacy() end, function() return W.rail("fusion") end, "FUSION", 7)
    if not add(c, if ok then true else nil, if ok then "FUSION answered" else why) then return name, c end
    if not up() then
        add(c, nil, "FUSION opened the old Dinosaur Fusion card or said 'coming soon': the pattern Fusion Menu is switched off in this build, nothing more to check")
        return name, c, "the old Fusion card"
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
    local Fusion = W.mod("Client.FusionMenu")
    if Fusion then Fusion.close() end -- the menu's own X button calls exactly this
    add(c, W.wait(function() return not up() end, 2) ~= nil, "the menu closes again")
    W.ensure(up, function() return W.rail("fusion") end, "FUSION", 7) -- left open for the capture; step 12 closes it
    return name, c, "the Fusion menu is OPEN: capture now (nothing was fused)"
end

-- ---- 12. Settings tabs and Reduce Motion --------------------------------------------------------------------------------------
W.steps[12] = function(ctx)
    local c = {}
    local name = "Settings tabs and Reduce Motion"
    local Fusion = W.mod("Client.FusionMenu")
    if Fusion and Fusion.isOpen() then Fusion.close() end
    if W.modalOpen() then W.closeModal() end
    if not add(c, W.rs() == "Sanctuary", "at home (RunState " .. tostring(W.rs()) .. ")") then return name, c end
    local Menu, Model, Theme = W.mod("Client.SettingsMenu"), W.mod("Shared.SettingsModel"), W.mod("Shared.UITheme")
    local ok, why = W.ensure(function() return W.modalOpen("Settings") end, function() return W.rail("settings") end, "SETTINGS", 7)
    if not add(c, if ok then true else nil, if ok then "Settings opened" else why) then return name, c end
    local marker = {sound = "Hatch sound", look = "Calm motion", controls = "Camera", help = "HOW TO PLAY"}
    for _, id in {"sound", "look", "controls", "help"} do
        local s = W.scrim()
        local ok2, why2 = W.ensure(function() return Menu ~= nil and Menu.tab() == id and W.hasExact(W.scrim(), marker[id]) end, function() return s:FindFirstChild("Tab_" .. id, true) end, id .. " tab")
        if not add(c, if ok2 then true else nil, if ok2 then id .. " tab shows '" .. marker[id] .. "'" else why2) then return name, c end
    end
    ok, why = W.ensure(function() return Menu.tab() == "look" and W.hasExact(W.scrim(), "Calm motion") end, function() return W.scrim():FindFirstChild("Tab_look", true) end, "look tab")
    ok, why = W.ensure(function() return Model.calm() end, function() return W.scrim():FindFirstChild("Toggle_Calm motion", true) end, "Calm motion toggle")
    if not add(c, if ok then true else nil, if ok then "Calm motion (Reduce Motion) switched ON" else why) then return name, c end
    add(c, Theme.MotionEnabled == false, "UITheme.MotionEnabled is " .. tostring(Theme.MotionEnabled))
    local toggle = W.scrim() and W.scrim():FindFirstChild("Toggle_Calm motion", true)
    add(c, toggle ~= nil and toggle.Text == "ON", "the toggle reads " .. (toggle and toggle.Text or "(missing)"))
    add(c, W.wait(function() local j = W.json("SettingsJson") return j and j.calm == true end, 6) ~= nil, "the server saved calm=true (SettingsJson)")
    W.keep.calmOn = true
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
        local Model = W.mod("Shared.SettingsModel")
        if Model and Model.calm() then
            if W.modalOpen() then W.closeModal() end
            local ok = W.ensure(function() return W.modalOpen("Settings") end, function() return W.rail("settings") end, "SETTINGS", 7)
            if ok then ok = W.ensure(function() return W.hasExact(W.scrim(), "Calm motion") end, function() return W.scrim():FindFirstChild("Tab_look", true) end, "look tab") end
            if ok then ok = W.ensure(function() return not Model.calm() end, function() return W.scrim():FindFirstChild("Toggle_Calm motion", true) end, "Calm motion toggle") end
            if not ok then Model.set("calm", false) add(c, nil, "could not tap Reduce Motion off; set it off through SettingsModel (what the toggle calls)") end
        end
        if W.modalOpen() then W.closeModal() end
        add(c, Model == nil or not Model.calm(), "Reduce Motion is off again")
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
