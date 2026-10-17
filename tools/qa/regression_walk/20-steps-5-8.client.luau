--!nocheck
-- BD-541 regression walk, CLIENT chunk 2: steps 5 to 8 (weather by the admin remote, go home and Run Complete, Eggs screen / hatch party /
-- auto-open, equip another dino with size and camera). Needs 00-lib.client.luau and a run with eggs from chunk 1. Repeat while CONTINUE.
local W = shared.BDWalk
assert(W and W.lib == 2, "run 00-lib.client.luau first")
local HttpService = game:GetService("HttpService")
local player = W.player
local add = W.add

-- Hatched copies live in e.variants[key].count (base stays 0 for them), so count both; the 2026-10-17 run saw "1 -> 1" without this.
local function ownedCount(e)
    local n = (e.base or 0) + (e.gold or 0) + (e.emerald or 0) + (e.diamond or 0)
    if type(e.variants) == "table" then
        for _, v in e.variants do if type(v) == "table" then n += v.count or 0 end end
    end
    return n
end
local function copiesTotal()
    local total = 0
    for _, e in W.json("CollectionJson") or {} do
        if type(e) == "table" then total += ownedCount(e) end
    end
    return total
end

-- ---- 5. start weather through the admin remote ---------------------------------------------------------------------------------
W.steps[5] = function(ctx)
    local c = {}
    local name = "Start weather (admin remote)"
    if not add(c, W.rs() == "Active", "still in the run (RunState " .. tostring(W.rs()) .. ")") then return name, c end
    local PC = W.mod("Shared.ProgressionConfig")
    local id = "rain"
    local event
    for _, e in PC.Weather do if e.id == id then event = e end end
    if not add(c, event ~= nil, "weather 'rain' exists in ProgressionConfig") then return name, c end
    if player:GetAttribute("IsAdmin") ~= true then
        add(c, nil, "this player is not an admin (published place?): weather cannot be started from here; use F2 or wait for a natural one")
        return name, c
    end
    local ok, msg = W.admin("startWeather", id, 90)
    add(c, ok == true, "AdminAction startWeather answered " .. tostring(ok) .. " / " .. tostring(msg))
    add(c, W.wait(function() return workspace:GetAttribute("WeatherId") == id end, 6) ~= nil, "WeatherId is " .. tostring(workspace:GetAttribute("WeatherId")))
    add(c, (workspace:GetAttribute("WeatherEndsAt") or 0) - workspace:GetServerTimeNow() > 45, "weather ends in " .. string.format("%.0f", (workspace:GetAttribute("WeatherEndsAt") or 0) - workspace:GetServerTimeNow()) .. " s")
    local g = W.gui()
    add(c, W.wait(function() return W.find(g, function(d) return d:IsA("TextLabel") and string.find(d.Text, "^" .. event.name .. " %d") ~= nil end) end, 3) ~= nil, "weather tile counts down '" .. event.name .. " ...'")
    add(c, W.wait(function() return (W.cattr("WeatherLootMultiplier") or 1) > 1 end, 4) ~= nil, "loot multiplier is " .. tostring(W.cattr("WeatherLootMultiplier")) .. " (eggs caught now can carry the weather)")
    local toast = W.wait(function() local t = g:FindFirstChild("Toasts") return t and W.hasMatch(t, "started") end, 3)
    add(c, if toast then true else nil, if toast then "toast: " .. toast else "no 'started' toast seen (it may have been dismissed)")
    return name, c, "look up: darker haze and rain around the dino"
end

-- ---- 6. go home and Run Complete -----------------------------------------------------------------------------------------------
W.steps[6] = function(ctx)
    local m = ctx.mem
    local c = m.c or {}
    m.c = c
    local name = "Go home and Run Complete"
    local g = W.gui()
    if m.eggs == nil then
        if not add(c, W.rs() == "Active", "in a run before going home") then return name, c end
        m.eggs = math.floor(W.cattr("CatchScore") or 0)
        m.runBefore = player:GetAttribute("LastRunId")
        W.keep.eggsRun, W.keep.lastRun = m.eggs, m.runBefore
        W.keep.copiesBefore = copiesTotal()
    end
    if W.rs() == "Active" then
        local function ended() return W.rs() ~= "Active" end
        local ok, why = W.ensure(function() return ended() or W.modalOpen("Go home?") end, function() return g:FindFirstChild("HomeButton") end, "HOME")
        if ok and not ended() then
            ok, why = W.ensure(ended, function() return W.btn(W.scrim(), "GO HOME") end, "GO HOME")
        end
        if not ended() then
            add(c, nil, tostring(why) .. "; fired RequestEndRun instead (the remote GO HOME fires)")
            local r = W.remote("RequestEndRun")
            if r then r:FireServer() end
        end
    end
    local home = W.wait(function() return W.rs() == "Sanctuary" and player:GetAttribute("ProfileState") == "Loaded" end, math.min(40, math.max(2, W.left() - 2)))
    if not home then
        if W.left() <= 3 then return name, c, nil, "CONTINUE", "settling the run" end
        add(c, false, "never got back home (RunState " .. tostring(W.rs()) .. ", ProfileState " .. tostring(player:GetAttribute("ProfileState")) .. ", exit status " .. tostring(player:GetAttribute("LastExitStatus")) .. ")")
        return name, c
    end
    add(c, true, "settled and back at home")
    if W.num("LastRunCrystalBox") > 0 then -- the Run Crystal Box card shows for about 3 s before Run Complete
        W.wait(function() local sc = W.scrim() return sc ~= nil and W.visible(sc) and W.hasExact(sc, "Run Crystal Box") end, 4)
    end
    local function complete()
        local s = W.scrim()
        return s and W.visible(s) and (W.hasExact(s, "Run Complete!") or W.hasExact(s, "Oops! Good try!")) and not W.hasExact(s, "Run Crystal Box")
    end
    if not W.wait(complete, math.min(25, math.max(2, W.left() - 1))) then
        if W.left() <= 2 then return name, c, nil, "CONTINUE", "waiting for the Run Complete card" end
        add(c, false, "no Run Complete card (crystal box and results never showed)")
        return name, c
    end
    task.wait(0.5)
    local s = W.scrim()
    local score = player:GetAttribute("LastRunCatchScore") or -1
    add(c, player:GetAttribute("LastRunEndReason") == "ManualExit", "end reason " .. tostring(player:GetAttribute("LastRunEndReason")))
    add(c, score >= m.eggs and score <= m.eggs + 3, string.format("server run score %s for the %d eggs seen before HOME", tostring(score), m.eggs))
    add(c, W.hasMatch(s, "%f[%d]" .. string.format("%.0f", score) .. "%f[%D]") ~= nil, "Run Complete shows the egg count " .. string.format("%.0f", score))
    add(c, W.num("LastRunEggCount") == math.min(math.floor(score), 150), "banked run eggs " .. W.num("LastRunEggCount") .. " equal the catches")
    add(c, player:GetAttribute("LastRunId") ~= m.runBefore, "a new run id was recorded")
    add(c, W.btn(s, "BACK TO SANCTUARY") ~= nil, "BACK TO SANCTUARY button")
    add(c, if score > 0 then W.btn(s, "OPEN EGGS") ~= nil else nil, if score > 0 then "OPEN EGGS button" else "no eggs this run, so no OPEN EGGS button")
    local rows = W.hasMatch(s, "Crystals")
    add(c, rows ~= nil, "crystal row: " .. tostring(rows))
    return name, c, "the Run Complete card"
end

-- ---- 7. Eggs screen OPEN, hatch party, auto-open ------------------------------------------------------------------------------
local function hatchUp() -- the hatch screen (title, or its full-screen tap catcher)
    local g = W.gui()
    return W.modalOpen("An egg is hatching...") or (g ~= nil and W.find(g, function(d) return d.Name == "HatchTapCatcher" and W.visible(d) end) ~= nil)
end
W.steps[7] = function(ctx)
    local m = ctx.mem
    local c = m.c or {}
    m.c = c
    local name = "Eggs screen, OPEN, hatch party, auto-open"
    local g = W.gui()
    m.ph = m.ph or "open"
    if m.ph == "open" then
        if not add(c, W.rs() == "Sanctuary", "at home (RunState " .. tostring(W.rs()) .. ")") then return name, c end
        local ok, why = W.ensure(function() return W.modalOpen("Eggs") end, function() return W.btn(W.scrim() or g, "OPEN EGGS") or W.rail("eggs") end, "OPEN EGGS / EGGS", 7)
        if not add(c, if ok then true else nil, if ok then "Eggs screen opened" else why) then return name, c end
        local s = W.scrim()
        local slots = 0
        local Config = W.mod("Shared.Config")
        local cap = if Config then Config.NestStorageCapacity or 5 else 5
        for i = 1, cap do if s:FindFirstChild("NestSlot" .. i, true) then slots += 1 end end
        add(c, slots == cap, slots .. " of " .. cap .. " nest slots drawn")
        local open = s:FindFirstChild("OpenEggButton", true)
        add(c, open ~= nil and W.visible(open), "OPEN button says " .. (open and open.Text or "(missing)"))
        m.queue0 = W.num("ActiveChestCount") + W.num("QueuedEggsWaiting") -- "Eggs waiting: N" counts every unopened egg, the card egg too
        m.copies0 = copiesTotal()
        if not add(c, if m.queue0 > 0 then true else nil, m.queue0 .. " eggs waiting") then return name, c end
        local waiting = s:FindFirstChild("EggsWaiting", true)
        add(c, if waiting then string.find(waiting.Text, tostring(m.queue0), 1, true) ~= nil else nil, "Eggs waiting line: " .. (waiting and waiting.Text or "(not drawn)"))
        m.ph = "hatch"
    end
    if m.ph == "hatch" then
        W.wait(function() return workspace:GetServerTimeNow() >= W.num("NextChestReadyAt") end, 8)
        local s = W.scrim()
        local ok, why = W.ensure(hatchUp, function() return s and s:FindFirstChild("OpenEggButton", true) end, "OPEN egg", 4)
        if not add(c, if ok then true else nil, if ok then "OPEN starts the hatch screen" else why) then return name, c end
        m.claims = m.claims or 0
        while W.left() > 3 and m.claims < 3 do
            local id = W.priv("LastClaimedChestId")
            if id ~= nil and id ~= m.lastId then m.lastId = id m.claims += 1 end
            local catcher = g and W.find(g, function(d) return d.Name == "HatchTapCatcher" and W.visible(d) end)
            local hint = g and g:FindFirstChild("TapHint", true)
            if m.claims >= 3 and hint and W.visible(hint) then break end
            if catcher and hint and W.visible(hint) and time() - (m.lastTap or 0) > 1.3 then
                m.lastTap = time()
                if W.tap(catcher) ~= "ok" then
                    add(c, nil, "cannot tap the hatch screen by script: click it by hand (viewport center), re-run")
                    return name, c
                end
            end
            task.wait(0.3)
        end
        if m.claims < 3 then
            if W.left() <= 3 then return name, c, nil, "CONTINUE", "hatch party: " .. m.claims .. " eggs so far" end
        end
        add(c, m.claims >= math.min(3, m.queue0), string.format("hatch party: %d eggs claimed one at a time", m.claims))
        local skip = g and g:FindFirstChild("SkipAll", true)
        add(c, if m.queue0 > 3 then (skip ~= nil and W.visible(skip)) else nil, if skip then "'Skip the rest' button is there" else "no 'Skip the rest' button while eggs remain")
        add(c, copiesTotal() > m.copies0, string.format("dino copies went %d -> %d", m.copies0, copiesTotal()))
        W.closeModal() -- leaves the rest of the party unopened, so the auto-open check below has eggs
        m.ph = "auto"
    end
    if m.ph == "auto" then
        local RevealSkip = W.mod("Shared.RevealSkip")
        local left = W.num("ActiveChestCount")
        if not add(c, if left > 0 then true else nil, left .. " eggs left for the auto-open check") then return name, c end
        local function common() local list = W.json("RevealSkipJson") or {} return table.find(list, 1) ~= nil end
        if not common() then
            local ok, why = W.ensure(function() return W.modalOpen("Eggs") end, function() return W.rail("eggs") end, "EGGS rail button", 7)
            if ok then ok, why = W.ensure(function() return W.modalOpen("Settings") end, function() return W.btn(W.scrim(), "AUTO") end, "AUTO") end
            if ok then ok, why = W.ensure(function() return W.btn(W.scrim(), "Common", true) ~= nil end, function() return W.btn(W.scrim(), "HELP") end, "HELP tab") end
            if ok then ok, why = W.ensure(common, function() return W.btn(W.scrim(), "Common", true) end, "Common AUTO button") end
            if not add(c, if ok then true else nil, if ok then "Common set to AUTO in Settings > Help" else why) then return name, c end
        else
            add(c, true, "Common already on AUTO")
        end
        W.closeModal()
        local before = W.num("ActiveChestCount") + W.num("QueuedEggsWaiting")
        local ok, why = W.ensure(function() return W.modalOpen("Eggs") end, function() return W.rail("eggs") end, "EGGS rail button", 7)
        if ok then
            ok, why = W.ensure(function() return hatchUp() or W.modalOpen("Auto-opened eggs") or W.num("ActiveChestCount") + W.num("QueuedEggsWaiting") < before end,
                function() return W.scrim() and W.scrim():FindFirstChild("OpenEggButton", true) end, "OPEN egg", 6)
        end
        add(c, if ok then true else nil, if ok then "OPEN with Common on AUTO" else why)
        local done = W.wait(function() return W.modalOpen("Auto-opened eggs") or (hatchUp() and W.find(g, function(d) return d.Name == "TapHint" and W.visible(d) end)) end, math.min(25, math.max(2, W.left() - 2)))
        add(c, done ~= nil, if W.modalOpen("Auto-opened eggs") then "the 'Auto-opened eggs' summary appeared" elseif done then "auto-open stopped at an egg that must be shown (not Common or notable)" else "neither the summary nor a reveal appeared")
        W.closeModal()
        if RevealSkip and common() then
            local r = W.remote("SetRevealSkip")
            if r then r:FireServer(RevealSkip.toggle(W.json("RevealSkipJson") or {}, 1)) end -- put Common back to SHOW with the same remote and rule the button uses
            add(c, W.wait(function() return not common() end, 4) ~= nil, "Common restored to SHOW")
        end
    end
    return name, c, "the Eggs screen; run Reduce Motion later to repeat"
end

-- ---- 8. equip a different species: size and camera -----------------------------------------------------------------------------
W.steps[8] = function(ctx)
    local m = ctx.mem
    local c = m.c or {}
    m.c = c
    local name = "Equip another dino, size and camera"
    if W.modalOpen() then W.closeModal() end
    if not add(c, W.rs() == "Sanctuary", "at home (RunState " .. tostring(W.rs()) .. ")") then return name, c end
    local Config = W.mod("Shared.Config")
    local Fit = W.mod("Client.CameraFit")
    local cur = player:GetAttribute("EquippedSpeciesId") or "compy"
    local ids = {}
    for id, e in W.json("CollectionJson") or {} do
        if id ~= cur and type(e) == "table" and ownedCount(e) > 0 then table.insert(ids, id) end
    end
    table.sort(ids)
    if not add(c, if #ids > 0 then true else nil, if #ids > 0 then "another species is owned: " .. ids[1] else "only " .. cur .. " is owned: hatch more eggs (step 7) and re-run") then return name, c end
    local pick = ids[1]
    local char = player.Character
    local h0, l0 = nil, nil
    if Fit and char then h0, l0 = Fit.box(char) end
    local remote = W.remote("EquipSpecies")
    if not add(c, remote ~= nil, "EquipSpecies remote exists") then return name, c end
    remote:FireServer(pick, HttpService:GenerateGUID(false)) -- the Equip button fires exactly this
    add(c, W.wait(function() return player:GetAttribute("EquippedSpeciesId") == pick end, 6) ~= nil, "EquippedSpeciesId is " .. tostring(player:GetAttribute("EquippedSpeciesId")))
    add(c, player:GetAttribute("LastEquipStatus") == "equipped", "LastEquipStatus " .. tostring(player:GetAttribute("LastEquipStatus")))
    W.keep.species = pick
    local function visual() local ch = player.Character return ch and ch:FindFirstChild("LocalMeshVisual") end
    local rendered = W.wait(function() local v = visual() return v and v:GetAttribute("SpeciesId") == pick end, 8)
    add(c, if rendered then true else nil, if rendered then "the new dino model is built (" .. pick .. ")" else "no LocalMeshVisual for " .. pick .. " (legacy visual?): framing checks skipped")
    if workspace.CurrentCamera then workspace.CurrentCamera.CameraType = Enum.CameraType.Custom end -- execute_luau leaves it on Fixed after every call (the box test then saw the dino 82 studs away)
    task.wait(1.5) -- the zoom limits and the camera settle
    char = player.Character
    if not char then add(c, false, "no character after the equip") return name, c end
    add(c, math.abs((char:GetAttribute("VisualScale") or 1) - 1) < 0.01, "hub size is 1x (VisualScale " .. tostring(char:GetAttribute("VisualScale")) .. ")")
    local h1, l1
    if Fit then h1, l1 = Fit.box(char) end
    if h0 and h1 then add(c, if (math.abs(h0 - h1) > 0.05 or math.abs(l0 - l1) > 0.05) then true else nil, string.format("model box %.1fx%.1f -> %.1fx%.1f studs", h0, l0, h1, l1)) end
    local cam = workspace.CurrentCamera
    local root = W.root()
    if Fit and Config and h1 then
        local want = Fit.minZoom(Config.CameraMinZoom, char)
        add(c, math.abs(player.CameraMinZoomDistance - want) < 0.6, string.format("minimum zoom %.1f (expected %.1f)", player.CameraMinZoomDistance, want))
    end
    if cam and root then
        local d = (cam.CFrame.Position - root.Position).Magnitude
        add(c, d >= player.CameraMinZoomDistance - 0.6 and d <= player.CameraMaxZoomDistance + 0.6, string.format("camera is %.1f studs away (limits %.1f to %.1f)", d, player.CameraMinZoomDistance, player.CameraMaxZoomDistance))
        local v = visual()
        if v and v:IsA("Model") then
            local cf, size = v:GetBoundingBox()
            local inside, total = 0, 0
            for _, sx in {-1, 1} do for _, sy in {-1, 1} do for _, sz in {-1, 1} do
                total += 1
                local p, onScreen = cam:WorldToViewportPoint(cf:PointToWorldSpace(Vector3.new(size.X / 2 * sx, size.Y / 2 * sy, size.Z / 2 * sz)))
                if onScreen and p.Z > 0 then inside += 1 end
            end end end
            add(c, inside == total, string.format("%d of %d corners of the dino box are on screen", inside, total))
        end
    end
    return name, c, "the new dino at home: compare its size to the first one and check the camera frames all of it"
end

return W.run({5, 6, 7, 8})
