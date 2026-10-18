-- BD-632 (docs/152 s9): scenarios for tools/verify_predation_tick.py. They run after the remote fuzz harness head (tools/remote_fuzz.luau: virtual clock,
-- mocked Players / workspace / DataStore, the REAL RunLifecycle, ProfileRepository and MouthReach) and run the REAL src/server/PredationService loop:
-- its task.spawn tick, the plausibility skip, the spawn protection, the size rule, the nearest-mouth winner, the kill egg bonus and the repeat-victim
-- cooldown. Only the engine is a mock (no physics: a character is a root part at a position, workspace:Raycast finds nothing).
--
-- Geometry (growth scale 1, radius 5.5): the attacker stands at (X, 6, 0) looking down -Z; the species with the longest head offset h is used so the
-- head point (0, 6, -h) and the root are far apart. A victim "at the mouth" is h + r - 0.3 ahead (inside the head circle, outside the root circle),
-- "at the root" is r - 0.5 behind the attacker (inside the root circle, outside the head circle).

do
local CELLS = 0
local function stepsUntil(seconds, cond)
    local t0 = now
    while now - t0 < seconds do
        if cond() then return true end
        sleep(0.02)
    end
    return cond()
end

local function startRun(server, p)
    fireNow(server, "ClientWorldReady", p)
    fireNow(server, "RequestStartRun", p)
end

-- Places a player's root and gives the character the attributes the tick reads.
local function place(character, x, y, z, attrs)
    local root = character:FindFirstChild("HumanoidRootPart")
    root.Position = v3(x, y, z)
    root.CFrame = cf(v3(x, y, z), v3(0, 0, -1))
    for k, v in attrs or {} do character:SetAttribute(k, v) end
end

local function takeErrors()
    local mine = {}
    for _, e in errors do table.insert(mine, e.remote .. "(" .. e.args .. "): " .. e.message) end
    table.clear(errors)
    return mine
end
local function reportErrors(name, list)
    check(name .. ": no error escaped from any handler", #list == 0, if #list > 0 then (#list .. " errors, first: " .. string.sub(list[1], 1, 500)) else "")
end

local function describeKills(cells)
    local parts = {}
    for name, c in cells do parts[#parts + 1] = name .. "=" .. (if c.killedAt then string.format("%.2f", c.killedAt) else "-") end
    table.sort(parts)
    return table.concat(parts, " ")
end

-- expect = {mouth = bool, root = bool}: which of the two victims the rule must reach. extra = also run the multi-player cells.
local function predationScenario(name, overrides, expect, extra)
    runScenario(name, overrides, function(server)
        startServices(server)
        -- LowPolyDinos is read through pcall(require) by PredationService; its generated art table is not embedded here, so make the module the
        -- real file would be for this question: LowPoly.enabled() is exactly `Config.LowPolyDinos == true`.
        local okLow, low = pcall(function() return loadMod(server, "src/shared/LowPolyDinos") end)
        if not (okLow and type(low) == "table" and type(low.enabled) == "function") then
            server.cache["src/shared/LowPolyDinos"] = {enabled = function() return server.Config.LowPolyDinos == true end}
            report(name .. ": LowPolyDinos stand-in (the real module needs the generated art tables)")
        end
        local Config = server.Config
        local MR = loadMod(server, "src/shared/MouthReach")
        local Ladder = loadMod(server, "src/shared/ScaleLadder")
        local species, h = nil, -1
        local ids = {}
        for id in Ladder.Dino.species do ids[#ids + 1] = id end
        table.sort(ids)
        for _, id in ids do
            local o = MR.headOffset(id, 1)
            if o > h then species, h = id, o end
        end
        local r = math.min(Config.PredationMaxRadius, Config.PredationBaseRadius)
        local limit = Config.PredationVerticalLimit
        check(name .. ": the test species has its head far from its root (head offset " .. string.format("%.2f", h) .. " > 1, radius " .. r .. ")", h > 1 and MR.radius(species, 1) > 0, species)

        local growth = {}
        server.dino.addGrowth = function(character, points) table.insert(growth, {character = character, points = points}) end
        local Predation = loadMod(server, "src/server/PredationService")
        local tickStart = now
        Predation.start(server.RL, server.dino) -- its tick loop first runs Config.PredationTickSeconds after this, then every PredationTickSeconds

        local reachZ = if expect.mouth then -h else 0 -- where the rule measures from (the head point or the root)
        local function growthOf(character) local n = 0 for _, g in growth do if g.character == character then n += 1 end end return n end

        -- one attacker (or several) and one victim per cell, 1000 studs apart so cells cannot touch
        local function cell(label, spec)
            CELLS += 1
            local X = 1000 * CELLS
            local c = {label = label, X = X, attackers = {}}
            for i, a in spec.attackers or {{id = 5000 + 10 * CELLS, dx = 0}} do
                local p = connect(server, a.id)
                startRun(server, p)
                c.attackers[i] = {player = p, character = p.Character, spec = a}
            end
            c.victim = connect(server, spec.victimId or (5001 + 10 * CELLS))
            c.victimStart = spec.victimStartDelay or 0
            c.spec = spec
            return c
        end
        local function stage(c)
            local spec = c.spec
            for _, a in c.attackers do
                place(a.character, c.X + (a.spec.dx or 0), 6, 0, {GrowthScore = a.spec.score or 100, VisualScale = 1, SpeciesId = species, MovementSpeedLimit = 16})
            end
            local function putVictim()
                startRun(server, c.victim)
                c.victimChar = c.victim.Character
                place(c.victimChar, c.X + (spec.vdx or 0), 6 + (spec.vdy or 0), spec.vz, {GrowthScore = spec.victimScore or 10, VisualScale = 1, MovementSpeedLimit = 16})
                c.startedAt = now
            end
            if (spec.victimStartDelay or 0) > 0 then
                task.spawn(function() sleep(spec.victimStartDelay) putVictim() end)
            else
                putVictim()
            end
        end
        local function watch(cells, seconds)
            stepsUntil(seconds, function()
                local all = true
                for _, c in cells do
                    if c.victimChar and not c.killedAt and c.victimChar:GetAttribute("RunState") ~= "Active" then c.killedAt = now end
                    if not c.killedAt then all = false end
                end
                return false
            end)
        end

        local cells = {}
        local function add(label, spec) cells[label] = cell(label, spec) end
        local ahead = h + r - 0.3
        add("mouth", {vz = -ahead})
        add("root", {vz = r - 0.5})
        add("outside", {vz = -(h + r + 0.5)})
        add("high", {vz = -h, vdy = limit + 1})
        add("equal", {vz = -ahead, victimScore = 100})
        add("bigger", {vz = -ahead, victimScore = 200})
        local killZ = reachZ - 1 -- one stud beyond the point the rule measures from: inside the circle of whichever rule is on
        if extra then
            add("protected", {vz = killZ, victimStartDelay = 6})
            add("nearest", {attackers = {{id = 5200, dx = 3}, {id = 5201, dx = 0.5}}, victimId = 5202, vz = killZ})
            add("tie", {attackers = {{id = 5300, dx = -2}, {id = 5301, dx = 2}}, victimId = 5302, vz = killZ})
            add("smaller", {attackers = {{id = 5400, dx = 0, score = 10.5}, {id = 5401, dx = 1, score = 100}}, victimId = 5402, vz = killZ, victimScore = 10})
        end
        for _, c in cells do stage(c) end
        watch(cells, 14)
        for _, c in cells do
            if c.victimChar and c.victimChar:GetAttribute("RunState") ~= "Active" and not c.killedAt then c.killedAt = now end
        end
        local function ended(c) return c.victimChar ~= nil and c.victimChar:GetAttribute("RunState") ~= "Active" end

        -- 1. the rule reaches exactly what it should
        check(name .. ": a victim at the MOUTH is " .. (if expect.mouth then "eaten" else "not eaten"), ended(cells.mouth) == expect.mouth, describeKills(cells))
        check(name .. ": a victim at the ROOT is " .. (if expect.root then "eaten" else "not eaten"), ended(cells.root) == expect.root, describeKills(cells))
        check(name .. ": a victim just outside the mouth circle is never eaten", not ended(cells.outside), "")
        check(name .. ": a victim above the vertical limit (" .. limit .. ") is never eaten", not ended(cells.high), "")
        check(name .. ": a victim of the same size is never eaten (the size rule needs x" .. Config.PredationScoreMultiplier .. ")", not ended(cells.equal), "")
        check(name .. ": a bigger victim is never eaten", not ended(cells.bigger), "")
        local mouthVictim = if expect.mouth then cells.mouth else cells.root
        local reached = if expect.mouth or expect.root then (if expect.mouth then cells.mouth else cells.root) else nil
        if reached then
            local attacker = reached.attackers[1]
            -- 2. what a kill does, once
            sleep(5)
            check(name .. ": the kill ended the victim's run as Eaten by the attacker", reached.victim.attrs.LastRunEndReason == "Eaten", tostring(reached.victim.attrs.LastRunEndReason))
            check(name .. ": exactly one bite was cued", attacker.character:GetAttribute("BiteSeq") == 1, tostring(attacker.character:GetAttribute("BiteSeq")))
            check(name .. ": exactly one quarter egg of kill bonus (carry " .. Config.PredationEggPerKill .. ", no whole egg yet)", attacker.character:GetAttribute("PredationEggCarry") == Config.PredationEggPerKill and attacker.character:GetAttribute("PredationEggs") == 0 and attacker.character:GetAttribute("CatchScore") == 0,
                tostring(attacker.character:GetAttribute("PredationEggCarry")) .. "/" .. tostring(attacker.character:GetAttribute("PredationEggs")))
            check(name .. ": growth was added once, for the winner (" .. Config.PredationGrowthPoints .. ")", growthOf(attacker.character) == 1, tostring(growthOf(attacker.character)))
            local settled = 0
            for _, n in server.settleCalls do settled += n end
            check(name .. ": no double catch: the victim's run settled once and he is back at home", reached.victim.Character ~= reached.victimChar and reached.victim.Character:GetAttribute("RunState") ~= "Active", tostring(reached.victim.Character:GetAttribute("RunState")))
            -- kill time: not before the victim's protection ended
            check(name .. ": the kill came after the spawn protection (" .. Config.SpawnProtectionSeconds .. " s)", reached.killedAt ~= nil and reached.killedAt - reached.startedAt >= Config.SpawnProtectionSeconds - 0.01, string.format("%.2f", (reached.killedAt or -1) - reached.startedAt))
        end
        if extra then
            local protected = cells.protected
            check(name .. ": a victim who started his run later is eaten only after HIS protection ended", ended(protected) and protected.killedAt - protected.startedAt >= Config.SpawnProtectionSeconds - 0.01 and protected.startedAt >= 6 - 0.01,
                string.format("started %.2f killed %.2f", protected.startedAt or -1, protected.killedAt or -1))
            local nearest = cells.nearest
            local close, far = nearest.attackers[2], nearest.attackers[1]
            check(name .. ": the NEAREST attacker eats (not the one with the lower id), the other gets nothing", ended(nearest) and close.character:GetAttribute("BiteSeq") == 1 and far.character:GetAttribute("BiteSeq") == nil and growthOf(close.character) == 1 and growthOf(far.character) == 0
                and close.character:GetAttribute("PredationEggCarry") == Config.PredationEggPerKill and (far.character:GetAttribute("PredationEggCarry") or 0) == 0,
                "bites " .. tostring(close.character:GetAttribute("BiteSeq")) .. "/" .. tostring(far.character:GetAttribute("BiteSeq")) .. " growth " .. growthOf(close.character) .. "/" .. growthOf(far.character) .. " carry " .. tostring(close.character:GetAttribute("PredationEggCarry")) .. "/" .. tostring(far.character:GetAttribute("PredationEggCarry")) .. " ended " .. tostring(ended(nearest)))
            local tie = cells.tie
            local low, high = tie.attackers[1], tie.attackers[2]
            check(name .. ": at equal distance the lower UserId eats and only one bonus is paid", ended(tie) and low.character:GetAttribute("BiteSeq") == 1 and high.character:GetAttribute("BiteSeq") == nil and growthOf(low.character) + growthOf(high.character) == 1,
                tostring(low.character:GetAttribute("BiteSeq")) .. "/" .. tostring(high.character:GetAttribute("BiteSeq")))
            -- the too-small attacker (10.5 against a victim of 10: not x1.1) eats nobody; he is himself prey for the big one beside him, so the big one bites twice
            local smaller = cells.smaller
            local little, big = smaller.attackers[1], smaller.attackers[2]
            check(name .. ": an attacker too small for the victim cannot eat him, and is eaten himself by the big one (two bites, two different victims, a quarter egg each)",
                ended(smaller) and little.character:GetAttribute("BiteSeq") == nil and growthOf(little.character) == 0 and little.player.attrs.LastRunEndReason == "Eaten"
                and big.character:GetAttribute("BiteSeq") == 2 and growthOf(big.character) == 2 and big.character:GetAttribute("PredationEggCarry") == 2 * Config.PredationEggPerKill,
                "ended " .. tostring(ended(smaller)) .. " bites " .. tostring(little.character:GetAttribute("BiteSeq")) .. "/" .. tostring(big.character:GetAttribute("BiteSeq")) .. " carry " .. tostring(big.character:GetAttribute("PredationEggCarry")))

            -- 3. a teleport (an implausible step) is skipped for one tick, then the victim is a candidate again
            local tp = cell("teleport", {vz = killZ})
            local attackerTp = tp.attackers[1]
            place(attackerTp.character, tp.X, 6, 0, {GrowthScore = 100, VisualScale = 1, SpeciesId = species, MovementSpeedLimit = 16})
            startRun(server, tp.victim)
            tp.victimChar = tp.victim.Character
            place(tp.victimChar, tp.X + 400, 6, -400, {GrowthScore = 10, VisualScale = 1, MovementSpeedLimit = 16})
            sleep(Config.SpawnProtectionSeconds + 1.37)
            check(name .. ": the far victim is still alive before the teleport", tp.victimChar:GetAttribute("RunState") == "Active", "")
            -- jump 0.05 s before the next tick: without the skip the kill comes ~0.05 s later, with it one whole tick after that
            local tickLen = Config.PredationTickSeconds
            local phase = (now - tickStart) % tickLen
            sleep(if phase > tickLen / 2 then tickLen * 1.5 - phase else tickLen / 2 - phase)
            local moved = now
            place(tp.victimChar, tp.X, 6, killZ)
            local died = stepsUntil(2, function() return tp.victimChar:GetAttribute("RunState") ~= "Active" end)
            local delay = now - moved
            check(name .. ": after a 560 stud jump the victim is not eaten on that very tick but on a later one (" .. string.format("%.2f", delay) .. " s, tick " .. Config.PredationTickSeconds .. " s)", died and delay > tickLen and delay < 2 * tickLen + 0.05, string.format("%.3f", delay))

            -- 4. the same victim again inside the repeat cooldown: eaten, but no second bonus; after the cooldown the bonus is paid again
            local rep = cell("repeat", {vz = killZ})
            local a = rep.attackers[1]
            place(a.character, rep.X, 6, 0, {GrowthScore = 100, VisualScale = 1, SpeciesId = species, MovementSpeedLimit = 16})
            local firstKillAt = nil
            local carries, bites = {}, {}
            for round = 1, 3 do
                -- the victim waits at home until the cell is due: round 2 inside the cooldown, round 3 after it
                if round == 3 then
                    local wait = (firstKillAt + Config.RepeatVictimCatchCooldownSeconds + 2) - now
                    if wait > 0 then sleep(wait) end
                end
                stepsUntil(30, function() return rep.victim.Character ~= nil and rep.victim.Character:GetAttribute("RunState") == "Sanctuary" end)
                sleep(2)
                startRun(server, rep.victim)
                local vc = rep.victim.Character
                place(vc, rep.X, 6, killZ, {GrowthScore = 10, VisualScale = 1, MovementSpeedLimit = 16})
                local killed = stepsUntil(Config.SpawnProtectionSeconds + 4, function() return vc:GetAttribute("RunState") ~= "Active" end)
                if not killed then break end
                if round == 1 then firstKillAt = now end
                sleep(0.5)
                carries[round] = a.character:GetAttribute("PredationEggCarry")
                bites[round] = a.character:GetAttribute("BiteSeq")
            end
            local eps = 1e-9
            check(name .. ": the same victim eaten three times gives three bites and growth each time", bites[1] == 1 and bites[2] == 2 and bites[3] == 3 and growthOf(a.character) == 3, canon(bites) .. " growth " .. growthOf(a.character))
            check(name .. ": the repeat inside " .. Config.RepeatVictimCatchCooldownSeconds .. " s pays no second kill egg, the one after it does", carries[1] == Config.PredationEggPerKill and carries[2] == Config.PredationEggPerKill and math.abs((carries[3] or -1) - 2 * Config.PredationEggPerKill) < eps, canon(carries))
            check(name .. ": kill eggs never became a whole egg here (CatchScore stays 0)", a.character:GetAttribute("CatchScore") == 0, tostring(a.character:GetAttribute("CatchScore")))
        end
        reportErrors(name, takeErrors())
        report(name .. ": " .. describeKills(cells) .. " (species " .. species .. ", head offset " .. string.format("%.2f", h) .. ", radius " .. r .. ")")
    end)
end

-- the rule on (mouth), the same geometry with the flag off, with the flag on but no low-poly dinosaurs, and with HP combat on (the instant rule is replaced)
predationScenario("predation-at-mouth", {CombatEnabled = false, PredationAtMouth = true, LowPolyDinos = true}, {mouth = true, root = false}, true)
predationScenario("predation-at-root", {CombatEnabled = false, PredationAtMouth = false, LowPolyDinos = true}, {mouth = false, root = true}, true)
predationScenario("predation-flag-without-lowpoly", {CombatEnabled = false, PredationAtMouth = true, LowPolyDinos = false}, {mouth = false, root = true}, false)
predationScenario("predation-combat-on", {CombatEnabled = true, PredationAtMouth = true, LowPolyDinos = true}, {mouth = false, root = false}, false)
end
