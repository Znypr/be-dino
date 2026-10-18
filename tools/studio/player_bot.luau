-- tools/studio/player_bot.luau  (BD-1048, docs/187 section C and docs/194)
-- A STUDIO-ONLY test player. NOT shipped, NOT under src/, has no remote of its own. Plain Luau, run through the Studio MCP
-- `execute_luau` with datamodel_type = "Client" while a Play session runs. It is still a script, not a person (see docs/194).
--
-- What it does, like a sensible player:
--   * reads the real Food folder (positions, Points, visible or eaten), every 0.2 s
--   * picks the next food by value per walking time:  score = points / (distance / walkSpeed + eatSeconds)
--   * walks with Humanoid:MoveTo, and uses PathfindingService only when it is stuck (a tree, a rock, water)
--   * skips food that lies near a wild predator, and walks away from a predator that comes close
--   * starts the run with the same remote the EXPLORE button uses, and ends it with the same remote GO HOME uses
--   * writes ONE log line per event (target, eat, flee, stuck, path, run end, card) with time, food kind, points,
--     running food_raw and eggs, as a Lua table the lead can read: shared.PlayerBot.log
--   * has a stop condition: seconds since the run began, or estimated food_raw
-- It makes NO random move. Every move has a logged reason (the "target" lines hold the decision: id and why).
--
-- Install (once per Play session) by pasting the whole file, or with tools/studio/run_player_bot.py install.
-- Then:  shared.PlayerBot.start({stopSeconds = 300})   shared.PlayerBot.status()   shared.PlayerBot.report()   shared.PlayerBot.stop()
--
-- Every loop here waits (task.wait). A loop without a wait freezes Studio (docs/192).

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local PathfindingService = game:GetService("PathfindingService")

local DEFAULTS = {
    stopSeconds = 300,      -- stop this many seconds after the run became Active
    stopFood = nil,         -- or stop when the estimated food_raw reaches this (nil = off)
    autoStartRun = true,    -- fire RequestStartRun while the character is in Sanctuary (the EXPLORE button does the same)
    autoEndRun = true,      -- fire RequestEndRun at the stop condition (the GO HOME button does the same)
    tickSeconds = 0.1,      -- movement tick; the food list is read every second tick
    maxDistance = 170,      -- only look at food this close (flat studs): what the player can see. 170 = sees nearly everything, about 60 = what is on screen
    thinkSeconds = 0,       -- stand still this long before choosing each next food (a person looks around); 0 = no pause
    eatSeconds = 0.25,      -- fixed time added to every walk in the value-per-time score
    predatorAvoid = 34,     -- skip food this close to a wild predator, flee when one is this close to the player (aggro range is 26)
    fleeDistance = 50,      -- how far away from the predator a flee walks
    stuckSeconds = 1.4,     -- no progress for this long = stuck
    blacklistSeconds = 25,  -- a food that failed (no path, no progress, not eaten) is ignored this long
    targetTimeout = 16,     -- give up on one food after this many seconds
    verticalLimit = 5,      -- the server only eats food within 6 studs of height
    pathSpacing = 6,
    casual = false,         -- true = the casual walker of the round-3b pace run (docs/194 s4): next food among the six nearest within 90 studs (not by value), walks 2.5 to 5 s, stops 0.3 to 1.6 s, looks around 2 to 4 s every 25 to 35 s
    cardWaitSeconds = 12,   -- wait this long for the Run Complete card after the run ended
}

local lp = Players.LocalPlayer
local Bot = shared.PlayerBot
if Bot and Bot.running then
    Bot.running = false -- an older copy of the loop stops itself at its next tick
    task.wait(0.3)
end
Bot = {version = 1, running = false, log = {}, opts = nil, phase = "idle", t0 = nil, runT0 = nil, foodRaw = 0, eats = 0, kinds = {}, stats = {}}
shared.PlayerBot = Bot

local function flat(a: Vector3, b: Vector3): number
    local dx, dz = a.X - b.X, a.Z - b.Z
    return math.sqrt(dx * dx + dz * dz)
end

local function r1(n: number): number return math.floor(n * 10 + 0.5) / 10 end

local function now(): number return os.clock() - (Bot.t0 or os.clock()) end

local function characterParts()
    local ch = lp.Character
    local hum = ch and ch:FindFirstChildOfClass("Humanoid")
    local root = ch and ch:FindFirstChild("HumanoidRootPart")
    return ch, hum, root
end

local function eggsNow(): number
    local ch = lp.Character
    return ch and (ch:GetAttribute("CatchScore") or 0) or 0
end

-- ONE line per event. `text` is for a person, `data` for a script.
local function add(ev: string, text: string, data: {[string]: any}?)
    local entry = {t = r1(now()), ev = ev, text = text, food_raw = Bot.foodRaw, eggs = eggsNow(), data = data}
    table.insert(Bot.log, entry)
    if #Bot.log > 6000 then table.remove(Bot.log, 1) end
    return entry
end

local function line(e): string
    return string.format("%6.1f  %-7s food_raw=%-5d eggs=%-3d  %s", e.t, e.ev, e.food_raw, e.eggs, e.text)
end

function Bot.lines(from: number?, to: number?): string
    local out = {}
    for i = from or 1, math.min(to or #Bot.log, #Bot.log) do out[#out + 1] = line(Bot.log[i]) end
    return table.concat(out, "\n")
end

-- ----------------------------------------------------------------------------------------------- the world
local foodFolder = workspace:FindFirstChild("Food")
local info = {} -- part -> {pts, vis, pos}

local function kindOf(part: Instance): string return part.Name end
local function idOf(part: BasePart): string
    local p = part.Position
    return string.format("%s@(%d,%d)", part.Name, p.X, p.Z)
end

-- Reads every food. Returns the list of visible foods. Counts foods that just vanished next to the player as eaten (food_raw).
local function scan(rootPos: Vector3, count: boolean)
    if not foodFolder or foodFolder.Parent == nil then foodFolder = workspace:FindFirstChild("Food") end
    local list = {}
    if not foodFolder then return list end
    for _, part in foodFolder:GetChildren() do
        if part:IsA("BasePart") then
            local rec = info[part]
            if not rec then
                rec = {pts = part:GetAttribute("Points") or 1, vis = true, pos = part.Position}
                info[part] = rec
            end
            local visible = part.Transparency < 1
            if rec.vis and not visible and count and flat(rec.pos, rootPos) < 10 then
                Bot.foodRaw += rec.pts
                Bot.eats += 1
                Bot.kinds[kindOf(part)] = (Bot.kinds[kindOf(part)] or 0) + 1
                add("eat", string.format("%s +%d", kindOf(part), rec.pts), {kind = kindOf(part), pts = rec.pts, id = idOf(part)})
            end
            rec.vis = visible
            rec.pos = part.Position
            if visible then list[#list + 1] = part end
        end
    end
    return list
end

local function predators(): {Vector3}
    local out = {}
    local folder = workspace:FindFirstChild("BeDinoNpcs")
    if not folder then return out end
    for _, m in folder:GetChildren() do
        if m:IsA("Model") and m:GetAttribute("NpcPredator") and not m:GetAttribute("NpcFading") then
            local ok, cf = pcall(function() return m:GetPivot() end)
            if ok then out[#out + 1] = cf.Position end
        end
    end
    return out
end

local function nearestPredator(pos: Vector3, list: {Vector3}): (number, Vector3?)
    local best, where = math.huge, nil
    for _, p in list do
        local d = flat(pos, p)
        if d < best then best, where = d, p end
    end
    return best, where
end

-- ----------------------------------------------------------------------------------------------- decisions
local blacklist: {[BasePart]: number} = {}

-- Value per walking time. Returns the best two {part, score, dist, pts}.
local function choose(rootPos: Vector3, walkSpeed: number, foods: {BasePart}, preds: {Vector3}, opts)
    local best, second = nil, nil
    local clock = os.clock()
    if opts.casual then
        local near = {}
        for _, part in foods do
            local until_ = blacklist[part]
            if until_ and until_ > clock then continue end
            local rec = info[part]
            local d = flat(rec.pos, rootPos)
            local dy = math.abs(rec.pos.Y - rootPos.Y)
            if d <= 90 and dy <= opts.verticalLimit + 6 then
                local bad = false
                for _, p in preds do if flat(rec.pos, p) < opts.predatorAvoid then bad = true break end end
                if not bad then near[#near + 1] = {part = part, dist = d, pts = rec.pts, score = 0} end
            end
        end
        table.sort(near, function(a, b) return a.dist < b.dist end)
        if #near == 0 then return nil, nil end
        local pick = if math.random() < 0.12 then near[math.random(1, #near)] else near[math.random(1, math.min(6, #near))]
        return pick, nil
    end
    for _, part in foods do
        local until_ = blacklist[part]
        if until_ and until_ > clock then continue end
        local rec = info[part]
        local pos = rec.pos
        local dy = math.abs(pos.Y - rootPos.Y)
        local d = flat(pos, rootPos)
        if d <= opts.maxDistance and dy <= opts.verticalLimit + 6 then
            local nearBad = false
            for _, p in preds do
                if flat(pos, p) < opts.predatorAvoid then nearBad = true break end
            end
            if not nearBad then
                local walk = (d + dy * 2) / walkSpeed + opts.eatSeconds
                local score = rec.pts / walk
                local entry = {part = part, score = score, dist = d, pts = rec.pts}
                if not best or score > best.score then best, second = entry, best
                elseif not second or score > second.score then second = entry end
            end
        end
    end
    return best, second
end

local function describe(e): string
    return string.format("%s %dpt d=%.1f score=%.2f", idOf(e.part), e.pts, e.dist, e.score)
end

-- ----------------------------------------------------------------------------------------------- walking
local function followPath(hum: Humanoid, root: BasePart, target: BasePart, opts): string
    local path = PathfindingService:CreatePath({AgentRadius = 2.2, AgentHeight = 4, AgentCanJump = true, WaypointSpacing = opts.pathSpacing})
    local goal = info[target].pos
    local ok = pcall(function() path:ComputeAsync(root.Position, goal) end)
    if not ok or path.Status ~= Enum.PathStatus.Success then
        return "nopath"
    end
    local waypoints = path:GetWaypoints()
    add("path", string.format("%d waypoints to %s", #waypoints, idOf(target)), {n = #waypoints})
    Bot.stats.paths = (Bot.stats.paths or 0) + 1
    for i = 2, #waypoints do
        if not Bot.running or not info[target].vis then return "done" end
        local wp = waypoints[i]
        if wp.Action == Enum.PathWaypointAction.Jump then hum.Jump = true end
        hum:MoveTo(wp.Position)
        local t0 = os.clock()
        while Bot.running and info[target].vis and flat(root.Position, wp.Position) > 3 and os.clock() - t0 < 3.5 do
            task.wait(opts.tickSeconds)
        end
        if os.clock() - t0 >= 3.5 then return "slow" end
    end
    return "done"
end

local function flee(hum: Humanoid, root: BasePart, from: Vector3, opts)
    local away = root.Position - from
    away = Vector3.new(away.X, 0, away.Z)
    if away.Magnitude < 0.1 then away = Vector3.new(1, 0, 0) end
    local goal = root.Position + away.Unit * opts.fleeDistance
    goal = Vector3.new(math.clamp(goal.X, -400, 400), root.Position.Y, math.clamp(goal.Z, -400, 400))
    add("flee", string.format("predator %.0f studs away, walking to (%d,%d)", flat(root.Position, from), goal.X, goal.Z), {from = from})
    Bot.stats.flees = (Bot.stats.flees or 0) + 1
    hum:MoveTo(goal)
    local t0 = os.clock()
    while Bot.running and os.clock() - t0 < 1.8 and flat(root.Position, goal) > 3 do task.wait(opts.tickSeconds) end
end

-- ----------------------------------------------------------------------------------------------- card
local function readCard(): string?
    local gui = lp:FindFirstChildOfClass("PlayerGui")
    local scrim = gui and gui:FindFirstChild("BeDinoUI") and gui.BeDinoUI:FindFirstChild("ModalScrim")
    if not scrim or not scrim.Visible then return nil end
    local texts = {}
    for _, d in scrim:GetDescendants() do
        if d:IsA("TextLabel") and d.Text ~= "" and d.Visible then texts[#texts + 1] = d.Text:gsub("\n", " / ") end
    end
    return table.concat(texts, " | ")
end

-- Where to click for a button of the open card. Mouse tool coordinates are the centre of AbsolutePosition.
function Bot.buttons(): string
    local gui = lp:FindFirstChildOfClass("PlayerGui")
    local out = {}
    if not gui then return "" end
    for _, d in gui:GetDescendants() do
        if d:IsA("GuiButton") and d.AbsoluteSize.X > 0 then
            local vis, a = true, d
            while a and a:IsA("GuiBase2d") do
                if (a:IsA("GuiObject") and not a.Visible) or (a:IsA("ScreenGui") and not a.Enabled) then vis = false break end
                a = a.Parent
            end
            if vis then
                local label = d:IsA("TextButton") and d.Text or ""
                if label == "" then local tl = d:FindFirstChildWhichIsA("TextLabel", true) label = tl and tl.Text or "" end
                out[#out + 1] = string.format("%s '%s' click at %d,%d", d.Name, label:sub(1, 24), d.AbsolutePosition.X + d.AbsoluteSize.X / 2, d.AbsolutePosition.Y + d.AbsoluteSize.Y / 2)
            end
        end
    end
    return table.concat(out, "\n")
end

-- ----------------------------------------------------------------------------------------------- the loop
local function loop(opts)
    local remotes = ReplicatedStorage:WaitForChild("BeDinoRemotes", 30)
    local startRemote = remotes and remotes:FindFirstChild("RequestStartRun")
    local endRemote = remotes and remotes:FindFirstChild("RequestEndRun")
    local target: BasePart? = nil
    local targetSince = 0
    local lastScanTick = 0
    local tick = 0
    local foods: {BasePart} = {}
    local history: {{t: number, p: Vector3}} = {}
    local lastStartFire = -10
    local endRequested = false
    local endFired = -10
    local stopReason: string? = nil
    local pathTried: {[BasePart]: boolean} = {}
    local casualNextLook, casualWalkUntil = os.clock() + 30, os.clock() + 3

    add("bot", string.format("start: stop after %ss%s, autoStartRun=%s", tostring(opts.stopSeconds), if opts.stopFood then " or food " .. opts.stopFood else "", tostring(opts.autoStartRun)))
    Bot.phase = "waiting"
    while Bot.running do
        task.wait(opts.tickSeconds)
        tick += 1
        local ch, hum, root = characterParts()
        if not ch or not hum or not root or hum.Health <= 0 then
            if Bot.runT0 then stopReason = stopReason or "died" break end
            continue
        end
        local state = ch:GetAttribute("RunState")
        if state ~= "Active" then
            if Bot.runT0 then break end -- the run ended (home, settled, defeated)
            if opts.autoStartRun and state == "Sanctuary" and startRemote and os.clock() - lastStartFire > 3 then
                lastStartFire = os.clock()
                add("start", "firing RequestStartRun (same as the EXPLORE button)")
                startRemote:FireServer()
            end
            continue
        end
        if not Bot.runT0 then
            Bot.runT0 = os.clock()
            Bot.foodRaw, Bot.eats, Bot.kinds = 0, 0, {}
            add("run", "run is Active, run clock starts", {runId = ch:GetAttribute("RunId")})
            Bot.phase = "running"
            scan(root.Position, false) -- baseline, nothing counted
            casualNextLook, casualWalkUntil = os.clock() + 30, os.clock() + 3
        end
        local runSeconds = os.clock() - Bot.runT0

        -- stop condition
        if not endRequested and (runSeconds >= opts.stopSeconds or (opts.stopFood and Bot.foodRaw >= opts.stopFood)) then
            endRequested = true
            stopReason = if runSeconds >= opts.stopSeconds then "time" else "food"
            add("stop", string.format("stop condition reached (%s) at %.0f s, food_raw %d", stopReason, runSeconds, Bot.foodRaw))
            Bot.phase = "ending"
        end
        if endRequested then
            if opts.autoEndRun and endRemote and os.clock() - endFired > 2.5 then
                endFired = os.clock()
                add("end", "firing RequestEndRun (same as GO HOME)")
                endRemote:FireServer()
            end
            if not opts.autoEndRun then break end
            hum:MoveTo(root.Position)
            continue
        end

        -- history for stuck detection
        history[#history + 1] = {t = os.clock(), p = root.Position}
        while #history > 0 and os.clock() - history[1].t > opts.stuckSeconds + 0.3 do table.remove(history, 1) end

        if tick - lastScanTick >= 2 then
            lastScanTick = tick
            foods = scan(root.Position, true)
        end

        local preds = predators()
        local pd, pwhere = nearestPredator(root.Position, preds)
        if pwhere and pd < opts.predatorAvoid then
            target = nil
            flee(hum, root, pwhere, opts)
            continue
        end

        -- keep the target while it is still there, otherwise decide
        if target and (not info[target] or not info[target].vis) then target = nil end
        if target then
            local rec = info[target]
            local near = nearestPredator(rec.pos, preds)
            if near < opts.predatorAvoid then
                add("skip", idOf(target) .. " lies near a predator, dropped")
                target = nil
            elseif os.clock() - targetSince > opts.targetTimeout then
                blacklist[target] = os.clock() + opts.blacklistSeconds
                add("skip", idOf(target) .. " not eaten after " .. opts.targetTimeout .. " s, ignored for " .. opts.blacklistSeconds .. " s")
                Bot.stats.timeouts = (Bot.stats.timeouts or 0) + 1
                target = nil
            end
        end
        if not target then
            if opts.thinkSeconds > 0 then
                hum:MoveTo(root.Position)
                task.wait(opts.thinkSeconds)
                foods = scan(root.Position, true)
            end
            local best, second = choose(root.Position, hum.WalkSpeed, foods, preds, opts)
            if not best then
                add("idle", "no food within reach, waiting")
                hum:MoveTo(root.Position)
                task.wait(0.5)
                continue
            end
            target = best.part
            targetSince = os.clock()
            history = {}
            pathTried[target] = nil
            add("target", describe(best) .. (if second then "  (2nd: " .. describe(second) .. ")" else "") .. string.format("  walkSpeed %.0f", hum.WalkSpeed),
                {id = idOf(best.part), pts = best.pts, dist = best.dist, score = best.score})
        end

        if opts.casual then -- the casual rhythm: short walks, short stops, a look around now and then
            local c = os.clock()
            if c >= casualNextLook then
                hum:MoveTo(root.Position)
                task.wait(2 + 2 * math.random())
                casualNextLook = os.clock() + 25 + 10 * math.random()
                casualWalkUntil = os.clock() + 2.5 + 2.5 * math.random()
            elseif c >= casualWalkUntil then
                hum:MoveTo(root.Position)
                task.wait(0.3 + 1.3 * math.random())
                casualWalkUntil = os.clock() + 2.5 + 2.5 * math.random()
            end
            if not info[target] or not info[target].vis then target = nil continue end
        end
        -- walk
        local rec = info[target]
        hum:MoveTo(rec.pos)
        local d = flat(root.Position, rec.pos)
        -- stuck: moved less than a third of what the walk speed allows over stuckSeconds
        local first = history[1]
        if first and os.clock() - first.t >= opts.stuckSeconds and d > 3 then
            local moved = flat(root.Position, first.p)
            if moved < hum.WalkSpeed * opts.stuckSeconds * 0.33 then
                Bot.stats.stuck = (Bot.stats.stuck or 0) + 1
                add("stuck", string.format("moved %.1f studs in %.1f s on the way to %s", moved, opts.stuckSeconds, idOf(target)))
                history = {}
                if pathTried[target] then
                    -- trapped (a pocket in a rock, the arena edge): every food within 15 studs of this one is ignored for a while, so the
                    -- bot does not spend 5 seconds on each of them one by one (round 1 lost about 45 seconds this way)
                    local pos = info[target].pos
                    local n = 0
                    for part, rec in info do
                        if flat(rec.pos, pos) < 15 then blacklist[part] = os.clock() + opts.blacklistSeconds * 4 n += 1 end
                    end
                    add("skip", idOf(target) .. " stuck again after a path, " .. n .. " foods within 15 studs ignored for " .. opts.blacklistSeconds * 4 .. " s")
                    target = nil
                else
                    pathTried[target] = true
                    hum.Jump = true -- a player would jump first
                    local result = followPath(hum, root, target, opts)
                    if result == "nopath" then
                        blacklist[target] = os.clock() + opts.blacklistSeconds
                        add("skip", idOf(target) .. " has no path, ignored")
                        Bot.stats.nopath = (Bot.stats.nopath or 0) + 1
                        target = nil
                    end
                    history = {}
                end
            end
        elseif d < 1.2 and os.clock() - targetSince > 1.5 then
            blacklist[target] = os.clock() + opts.blacklistSeconds
            add("skip", idOf(target) .. " reached but not eaten, ignored")
            target = nil
        end
    end

    -- run is over: wait for the Run Complete card and write the summary
    local ch = lp.Character
    local deadline = os.clock() + opts.cardWaitSeconds
    local state = ch and ch:GetAttribute("RunState")
    while Bot.running and state == "Active" and os.clock() < deadline do
        if opts.autoEndRun and endRemote and os.clock() - endFired > 2.5 then endFired = os.clock() endRemote:FireServer() end
        task.wait(0.5)
        ch = lp.Character
        state = ch and ch:GetAttribute("RunState")
    end
    local runSeconds = if Bot.runT0 then os.clock() - Bot.runT0 else 0
    Bot.phase = "card"
    local card = nil
    local cardDeadline = os.clock() + opts.cardWaitSeconds
    while Bot.running and os.clock() < cardDeadline do
        card = readCard()
        if card and card:find("Run Complete") or (card and card:find("Good try")) then break end
        card = nil
        task.wait(0.5)
    end
    if card then task.wait(1.5) card = readCard() or card end -- the crystal line fills in a moment after the card opens
    add("card", card or "no Run Complete card seen", {card = card})
    local player = lp
    add("done", string.format("reason=%s run=%.0fs food_raw(est)=%d eats=%d eggs(CatchScore)=%d LastRunCatchScore=%s growth=%s",
        tostring(stopReason or "ended"), runSeconds, Bot.foodRaw, Bot.eats, eggsNow(), tostring(player:GetAttribute("LastRunCatchScore")), tostring(ch and ch:GetAttribute("GrowthScore"))))
    Bot.phase = "done"
    Bot.running = false
end

-- ----------------------------------------------------------------------------------------------- public
function Bot.start(options)
    if Bot.running then return "already running" end
    local opts = {}
    for k, v in DEFAULTS do opts[k] = v end
    for k, v in (options or shared.PlayerBotOptions or {}) do opts[k] = v end
    Bot.opts = opts
    Bot.log, Bot.foodRaw, Bot.eats, Bot.kinds, Bot.stats = {}, 0, 0, {}, {}
    Bot.t0, Bot.runT0, Bot.phase = os.clock(), nil, "waiting"
    Bot.running = true
    task.spawn(function()
        local ok, err = pcall(loop, opts)
        if not ok then
            add("error", tostring(err))
            Bot.running, Bot.phase = false, "error"
        end
    end)
    return "started"
end

function Bot.stop()
    Bot.running = false
    add("stop", "stopped by the operator")
    return "stopped"
end

function Bot.status(): string
    local ch = lp.Character
    local runS = if Bot.runT0 then os.clock() - Bot.runT0 else 0
    local last = Bot.log[#Bot.log]
    return string.format("phase=%s running=%s run_s=%.0f food_raw(est)=%d eats=%d eggs=%d growth=%s runState=%s log=%d lines\nlast: %s",
        Bot.phase, tostring(Bot.running), runS, Bot.foodRaw, Bot.eats, eggsNow(), tostring(ch and ch:GetAttribute("GrowthScore")),
        tostring(ch and ch:GetAttribute("RunState")), #Bot.log, last and line(last) or "-")
end

-- A readable report: totals, a table per 30 s (food, eggs), the event counts, then every non-eat line.
function Bot.report(maxLines: number?): string
    local out = {}
    local counts = {}
    local buckets = {}
    for _, e in Bot.log do
        counts[e.ev] = (counts[e.ev] or 0) + 1
        local b = math.floor(e.t / 30)
        local rec = buckets[b] or {food = 0, eats = 0, eggs = 0}
        buckets[b] = rec
        if e.ev == "eat" then rec.food += e.data.pts rec.eats += 1 end
        rec.eggs = math.max(rec.eggs, e.eggs)
    end
    local keys = {}
    for k in counts do keys[#keys + 1] = k end
    table.sort(keys)
    local parts = {}
    for _, k in keys do parts[#parts + 1] = k .. "=" .. counts[k] end
    out[#out + 1] = "events: " .. table.concat(parts, " ")
    local kinds = {}
    for k, v in Bot.kinds do kinds[#kinds + 1] = k .. "=" .. v end
    table.sort(kinds)
    out[#out + 1] = "eaten: " .. table.concat(kinds, " ") .. string.format("  food_raw(est)=%d eats=%d", Bot.foodRaw, Bot.eats)
    local bk = {}
    for b in buckets do bk[#bk + 1] = b end
    table.sort(bk)
    out[#out + 1] = "per 30 s (bot clock): window  food  eats  eggs_at_end"
    for _, b in bk do out[#out + 1] = string.format("  %3d-%3d s  %4d  %3d  %3d", b * 30, b * 30 + 30, buckets[b].food, buckets[b].eats, buckets[b].eggs) end
    local shown = 0
    for _, e in Bot.log do
        if e.ev ~= "eat" then
            shown += 1
            if shown <= (maxLines or 400) then out[#out + 1] = line(e) end
        end
    end
    return table.concat(out, "\n")
end

-- Share of points by kind, the share of amber + golden drumstick, and points from a food eaten a SECOND time in the run (the "loop"
-- that BD-1081 slowed down). Needs the eat lines, so call it before the log is trimmed (6,000 lines) or the next start.
function Bot.summary(): string
    local pts, cnt, tot, perId, repeatPts = {}, {}, 0, {}, 0
    local byMinute = {}
    for _, e in Bot.log do
        if e.ev == "eat" then
            local k = e.data.kind
            pts[k] = (pts[k] or 0) + e.data.pts
            cnt[k] = (cnt[k] or 0) + 1
            tot += e.data.pts
            if perId[e.data.id] then repeatPts += e.data.pts end
            perId[e.data.id] = true
            local m = math.floor(e.t / 60)
            byMinute[m] = (byMinute[m] or 0) + e.data.pts
        end
    end
    local out = {}
    for k, v in pts do out[#out + 1] = string.format("%s: %d eaten, %d pts (%.0f%%)", k, cnt[k], v, 100 * v / math.max(tot, 1)) end
    table.sort(out)
    local rich = (pts.amber or 0) + (pts.golden_drumstick or 0)
    local minutes = {}
    for m = 0, 6 do if byMinute[m] then minutes[#minutes + 1] = string.format("min%d=%d", m + 1, byMinute[m]) end end
    return string.format("total %d pts (est). amber + golden drumstick %d = %.0f%%. points from a food eaten a second time: %d (%.1f%%)\n%s\n%s",
        tot, rich, 100 * rich / math.max(tot, 1), repeatPts, 100 * repeatPts / math.max(tot, 1), table.concat(out, "\n"), table.concat(minutes, " "))
end

return Bot
