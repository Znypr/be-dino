--!nocheck
-- BD-541 regression walk, CLIENT chunk 1: steps 1 to 4 (welcome and first screen, leave through the gate, eat until eggs, leap).
-- Needs 00-lib.client.luau run first. Repeat the snippet while it prints CONTINUE. Re-run one step: prefix `shared.BDWalkOnly = 3;`.
local W = shared.BDWalk
assert(W and W.lib == 2, "run 00-lib.client.luau first")
local RunService = game:GetService("RunService")
local player = W.player
local add = W.add

-- ---- 1. welcome and first screen --------------------------------------------------------------------------------------------
W.steps[1] = function(ctx)
    local c = {}
    local cam = workspace.CurrentCamera
    local vp = if cam then cam.ViewportSize else Vector2.new(0, 0)
    add(c, vp.X > 100 and vp.Y > 100, string.format("viewport %.0fx%.0f (1x1 means Studio is not rendering)", vp.X, vp.Y))
    add(c, if game.GameId == 0 then true else nil, if game.GameId == 0 then "unpublished Studio copy: nothing here is saved" else "PUBLISHED place (GameId " .. game.GameId .. "): the walk buys a potion and hatches eggs; stop unless this is a throwaway account")
    if vp.X < 800 or vp.Y < 400 then add(c, nil, "small window: the phone-size HUD checks (BD-531) apply, desktop expectations may not") end
    local ready = W.wait(function() return player:GetAttribute("ProfileState") == "Loaded" and W.rs() == "Sanctuary" and W.gui() end, 45)
    if not add(c, ready ~= nil, "profile loaded and the dino is at home (Sanctuary)") then return "Welcome and first screen", c end
    local frames = 0
    local conn = RunService.RenderStepped:Connect(function() frames += 1 end)
    task.wait(0.5)
    conn:Disconnect()
    add(c, frames >= 5, string.format("%d frames rendered in 0.5 s", frames))
    local Config = W.mod("Shared.Config")
    local g = W.gui()
    local badge = g:FindFirstChild("BuildBadge")
    add(c, badge ~= nil and Config ~= nil and string.find(badge.Text, Config.Build, 1, true) ~= nil, "build badge reads " .. (badge and badge.Text or "(missing)"))
    if W.wait(function() return W.modalOpen("Welcome to Be Dino!") end, 8) then
        add(c, true, "welcome card opened by itself")
        local ok, why = W.ensure(function() return W.modalOpen("Sanctuary") end, function() return W.btn(W.scrim(), "LET'S PLAY") end, "LET'S PLAY")
        if not add(c, if ok then true else nil, if ok then "LET'S PLAY opens the Sanctuary card" else why) then return "Welcome and first screen", c end
    else
        add(c, nil, "no welcome card (already dismissed in this session?)")
    end
    if W.modalOpen() then add(c, W.closeModal() ~= nil, "menu closes") end
    add(c, W.wait(function() return player:GetAttribute("MenuOpen") ~= true end, 2) ~= nil, "MenuOpen is false after closing")
    local home = g:FindFirstChild("HomeButton")
    add(c, home ~= nil and W.visible(home) and home.Text ~= "SAVING...", "home button says " .. (home and home.Text or "(missing)"))
    local rects = W.hudRects()
    add(c, rects.rail ~= nil and rects.crystals ~= nil, "rail and crystal plate are on screen")
    local bad = W.overlaps(rects)
    add(c, #bad == 0, if #bad == 0 then "no HUD rectangles overlap or leave the screen" else "HUD problems: " .. table.concat(bad, ", "))
    return "Welcome and first screen", c, "the hub first screen with the HUD"
end

-- ---- 2. leave through the gate ----------------------------------------------------------------------------------------------
W.steps[2] = function(ctx)
    local c = ctx.mem.c or {}
    ctx.mem.c = c
    local name = "Leave through the gate"
    local Config = W.mod("Shared.Config")
    if W.rs() ~= "Active" then
        if not add(c, W.rs() == "Sanctuary", "at home before leaving (RunState " .. tostring(W.rs()) .. ")") then return name, c end
        if Config.CaveHub == true then
            local Gate = W.mod("Shared.CaveGateRules")
            local z = Gate.zone()
            local target = Vector3.new(z.sx + z.ux * 4, z.floorY + 3, z.sz + z.uz * 4)
            ctx.mem.t0 = ctx.mem.t0 or time()
            local lastMove = -9
            while W.rs() == "Sanctuary" and W.left() > 2 do
                local r = W.root()
                if r and Gate.inZone(r.Position.X, r.Position.Z, r.Position.Y) then
                    ctx.mem.inZoneAt = ctx.mem.inZoneAt or time()
                    if time() - ctx.mem.inZoneAt > 12 then break end -- 1.5 s dwell plus the island load: 12 s is far too long
                else
                    ctx.mem.inZoneAt = nil
                    if time() - lastMove > 2.5 then
                        local h = W.hum()
                        if h then h:MoveTo(target) end
                        lastMove = time()
                    end
                    if time() - ctx.mem.t0 > 35 and not ctx.mem.teleported and player.Character then
                        ctx.mem.teleported = true
                        player.Character:PivotTo(CFrame.new(target)) -- the walk was blocked: stand in the arch instead (the gate still has to fire by itself)
                        add(c, nil, "walk to the gate blocked for 35 s; moved the dino into the arch instead")
                    end
                end
                task.wait(0.2)
            end
        else
            local g = W.gui()
            local ok, why = W.ensure(function() return W.rs() == "Active" end, function() return g:FindFirstChild("HomeButton") end, "EXPLORE button")
            if not ok then
                add(c, nil, why .. "; firing RequestStartRun (the remote that button fires)")
                local r = W.remote("RequestStartRun")
                if r then r:FireServer() end
            end
        end
        if W.rs() ~= "Active" then
            local active = W.wait(function() return W.rs() == "Active" end, math.min(15, math.max(1, W.left() - 1)))
            if not active then
                if W.left() <= 2 then return name, c, nil, "CONTINUE", "walking to the gate" end
                add(c, false, "no run started after standing in the gate (RunState " .. tostring(W.rs()) .. ", start status " .. tostring(player:GetAttribute("LastRunStartStatus")) .. ")")
                return name, c
            end
        end
    end
    add(c, true, "gate started the run (RunState Active)")
    local r = W.root()
    local SpawnGeometry = W.mod("Shared.SpawnGeometry")
    add(c, player:GetAttribute("Location") == "Island", "Location is " .. tostring(player:GetAttribute("Location")))
    add(c, r ~= nil and SpawnGeometry ~= nil and not SpawnGeometry.inHub(Config, r.Position.X, r.Position.Z), "the dino is on the island, not in the hub")
    local home = W.gui():FindFirstChild("HomeButton")
    -- the label flips to HOME a moment (about 0.15 s in a 2026-10-17 run) after RunState turns Active: wait for it, do not read it at once
    W.wait(function() return home ~= nil and home.Text == "HOME" end, 3)
    add(c, home ~= nil and home.Text == "HOME", "home button now says " .. (home and home.Text or "(missing)"))
    local bar = W.gui():FindFirstChild("SizeBar")
    add(c, W.wait(function() return bar and W.visible(bar) end, 3) ~= nil, "SIZE bar shows during the run")
    local bad = W.overlaps(W.hudRects())
    add(c, #bad == 0, if #bad == 0 then "no HUD overlaps in the run" else "HUD problems: " .. table.concat(bad, ", "))
    return name, c, "the island spawn: the dino, the HUD and the SIZE bar"
end

-- ---- 3. eat until eggs are caught --------------------------------------------------------------------------------------------
local function foodVisible(f)
    if f.Transparency < 1 then return true end
    local p = f:FindFirstChildWhichIsA("BasePart", true)
    return p ~= nil and p.Transparency < 1
end
W.steps[3] = function(ctx)
    local m = ctx.mem
    local c = m.c or {}
    m.c = c
    local name = "Eat until eggs are caught"
    local target = ctx.target or 6
    if not add(c, W.rs() == "Active", "in a run (RunState " .. tostring(W.rs()) .. ")") then return name, c end
    if not m.adminAsked then
        m.adminAsked = true
        local ok, msg = W.admin("set", "foodMultiplier", 10) -- the admin panel's "Food worth" slider; shortens the walk, changes no code path
        add(c, if ok == true then true else nil, if ok == true then "Food worth x10 through the admin remote" else "admin food x10 not available (" .. tostring(msg) .. "): this will take longer")
    end
    local food = workspace:FindFirstChild("Food")
    if not add(c, food ~= nil, "workspace.Food exists") then return name, c end
    m.blocked = m.blocked or {}
    local function eggs() return W.cattr("CatchScore") or 0 end
    local function pick()
        local r = W.root()
        if not r then return nil end
        local best, score = nil, -1
        for _, f in food:GetChildren() do
            if f:IsA("BasePart") and not m.blocked[f] and f:GetAttribute("Points") and foodVisible(f) then
                local d = (f.Position - r.Position).Magnitude + 10
                local s = f:GetAttribute("Points") / (d * d) -- prefer rich food, but near beats far (an amber 400 studs away is not worth the walk)
                if s > score then best, score = f, s end
            end
        end
        return best
    end
    m.start = m.start or time()
    while eggs() < target and W.left() > 2 and W.rs() == "Active" do
        local f = pick()
        if not f then
            add(c, false, "no visible food found")
            return name, c
        end
        local h = W.hum()
        if not h then break end
        h:MoveTo(f.Position)
        local t0, got = time(), false
        while time() - t0 < 6 and W.left() > 1 do
            task.wait(0.15)
            local r = W.root()
            if not r then break end
            local flat = Vector3.new(r.Position.X - f.Position.X, 0, r.Position.Z - f.Position.Z).Magnitude
            if flat < 3 or not foodVisible(f) then got = true break end
        end
        if not got then
            m.blocked[f] = true
            local hh = W.hum()
            if hh then hh.Jump = true end
        end
    end
    if eggs() < target then
        if W.rs() ~= "Active" then add(c, false, "the run ended while eating (RunState " .. tostring(W.rs()) .. ")") return name, c end
        return name, c, nil, "CONTINUE", string.format("eggs %d of %d after %.0f s", eggs(), target, time() - m.start)
    end
    add(c, true, string.format("%d eggs caught in %.0f s", eggs(), time() - m.start))
    local g = W.gui()
    local text = g:FindFirstChild("EggsText", true)
    local shown = W.wait(function() return text and tonumber(string.match(text.Text, "%d+")) == eggs() end, 2)
    add(c, shown ~= nil, "EGGS plate reads " .. (text and text.Text or "(missing)") .. " for " .. eggs() .. " eggs")
    add(c, (W.cattr("GrowthScore") or 0) > 0, "growth went up (" .. string.format("%.0f", W.cattr("GrowthScore") or 0) .. ")")
    m.eggs = eggs()
    W.keep.eggsStep3 = eggs()
    return name, c, "the island with the EGGS plate and the SIZE bar after eating"
end

-- ---- 4. leap -------------------------------------------------------------------------------------------------------------------
W.steps[4] = function(ctx)
    local m = ctx.mem
    local c = m.c or {}
    m.c = c
    local name = "Leap"
    if not add(c, W.rs() == "Active", "in a run (RunState " .. tostring(W.rs()) .. ")") then return name, c end
    local PC = W.mod("Shared.ProgressionConfig")
    local function ready() return workspace:GetServerTimeNow() >= (player:GetAttribute("LeapReadyAt") or 0) end
    if not ready() and not W.wait(ready, math.max(1, W.left() - 6)) then return name, c, nil, "CONTINUE", "waiting for the leap cooldown" end
    W.wait(function() local h = W.hum() return h and h.FloorMaterial ~= Enum.Material.Air end, 4)
    local r0 = W.root()
    local y0, p0 = r0.Position.Y, r0.Position
    local status0, reject0, ready0 = player:GetAttribute("LastLeapStatus"), player:GetAttribute("LeapRejectCount") or 0, player:GetAttribute("LeapReadyAt") or 0
    local maxY = y0
    local conn = RunService.Heartbeat:Connect(function()
        local r = W.root()
        if r and r.Position.Y > maxY then maxY = r.Position.Y end
    end)
    local function started() return (player:GetAttribute("LeapReadyAt") or 0) > ready0 end
    local label = W.leapLabel()
    local via = "button"
    local res = if label and label.Parent:IsA("TextButton") then W.tap(label.Parent, started) else "novim"
    if res ~= "ok" then
        via = "key E"
        if not (W.key(Enum.KeyCode.E) and W.wait(started, 1.5)) then
            via = "remote only"
            local remote = W.remote("RequestLeap")
            if remote then remote:FireServer() end -- the very remote requestLeap() fires first; without a tap the dino is not launched locally
            W.wait(started, 1.5)
        end
    end
    task.wait(1.4)
    conn:Disconnect()
    local r1 = W.root()
    add(c, started(), "leap accepted by the server (cooldown started), via " .. via)
    add(c, player:GetAttribute("LastLeapStatus") == "leaping", "LastLeapStatus is " .. tostring(player:GetAttribute("LastLeapStatus")) .. " (was " .. tostring(status0) .. ")")
    add(c, (player:GetAttribute("LeapRejectCount") or 0) == reject0, "the server did not reject the leap")
    local apex = maxY - y0
    local flat = if r1 then Vector3.new(r1.Position.X - p0.X, 0, r1.Position.Z - p0.Z).Magnitude else 0
    local launched = via ~= "remote only"
    add(c, if launched then apex >= 3 else nil, string.format("apex +%.1f studs", apex) .. (if launched then " (needs 3)" else " (not launched: only the remote was fired)"))
    add(c, if launched then flat >= 8 else nil, string.format("moved %.0f studs forward", flat) .. (if launched then " (needs 8)" else ""))
    local label2 = W.leapLabel()
    add(c, label2 ~= nil and string.find(label2.Text, "%d") ~= nil, "leap button shows the cooldown: " .. (label2 and label2.Text or "(missing)"))
    if PC then add(c, (player:GetAttribute("LeapReadyAt") or 0) - workspace:GetServerTimeNow() > 1, "cooldown is running (LeapCooldown " .. tostring(PC.LeapCooldown) .. ")") end
    return name, c, "look at the dino in the air or on landing, trail visible"
end

return W.run({1, 2, 3, 4})
