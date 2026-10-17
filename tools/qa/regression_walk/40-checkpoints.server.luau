--!nocheck
-- BD-541 regression walk, SERVER checkpoints. Run in the SERVER datamodel (Studio MCP execute_luau, Play mode) at the moments the README
-- names: first call = baseline (checkpoint 0), then 1 (after chunk 1), 2 (after chunk 2), 3 (after chunk 3). The call number advances by
-- itself; force one with `shared.BDWalkCP = 2;` in front. READ ONLY: it looks at the server's truth (profile values, attributes, the
-- server log), it never changes a profile, a run or a remote. Output lines: WALKS <cp> PASS/FAIL/ODD ...
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")
local SSS = game:GetService("ServerScriptService")
local LogService = game:GetService("LogService")
local HttpService = game:GetService("HttpService")
local S = shared.BDWalkS
if type(S) ~= "table" then S = {cp = -1, base = {}} shared.BDWalkS = S end
local cp = shared.BDWalkCP or (S.cp + 1)
shared.BDWalkCP = nil
S.cp = cp

local function add(list, ok, text) table.insert(list, {ok, text}) return ok end
local list = Players:GetPlayers()
table.sort(list, function(a, b) return a.UserId < b.UserId end)
local player = list[1]
local c = {}
if not add(c, player ~= nil, "a player is in the server") then
    local text = string.format("WALKS %d FAIL no player", cp)
    print(text)
    return text
end
local Server = SSS:FindFirstChild("Server")
local PS = Server and Server:FindFirstChild("PrivateState") and require(Server.PrivateState)
local function priv(name) return if PS then PS.get(player, name) else player:GetAttribute(name) end
-- execute_luau runs in its own Lua VM, so require(Server.PrivateState) may be a NEW instance with an empty store (2026-10-17 run: every
-- value nil). Probe with a value that is always set once the profile is loaded; when it is nil every private-value check says ODD, not FAIL.
local privOk = PS ~= nil and PS.get(player, "CollectionJson") ~= nil
local function addp(list, ok, text)
    if privOk then return add(list, ok, text) end
    return add(list, nil, "private value not readable from this script context (" .. text .. "); the client steps check the same fact")
end
local function num(name) local v = priv(name) return if type(v) == "number" then v else 0 end
local function json(name)
    local v = priv(name)
    if type(v) ~= "string" or v == "" then return nil end
    local ok, d = pcall(function() return HttpService:JSONDecode(v) end)
    return if ok then d else nil
end
local function copies()
    local total = 0
    for _, e in json("CollectionJson") or {} do
        if type(e) == "table" then
            total += (e.base or 0) + (e.gold or 0) + (e.emerald or 0) + (e.diamond or 0)
            if type(e.variants) == "table" then for _, v in e.variants do if type(v) == "table" then total += v.count or 0 end end end -- hatched copies live here
        end
    end
    return total
end
local char = player.Character
local runState = if char then char:GetAttribute("RunState") else nil
add(c, PS ~= nil, "server PrivateState module found")
add(c, if privOk then true else nil, if privOk then "owner-only values readable" else "owner-only values NOT readable here (separate module instance): those checks are ODD")
add(c, player:GetAttribute("ProfileState") == "Loaded", "ProfileState " .. tostring(player:GetAttribute("ProfileState")))
add(c, player:GetAttribute("ProfileState") ~= "SaveFailed" and player:GetAttribute("ProfileState") ~= "LeaseLost", "no SaveFailed / LeaseLost")
local errors = 0
local first
for _, e in LogService:GetLogHistory() do
    -- BD-596: Studio's own "Failed to upload TexturePack" lines (unpublished place) are not game errors
    if e.messageType == Enum.MessageType.MessageError and e.timestamp >= (S.base.errTime or 0) and string.sub(e.message, 1, 28) ~= "Failed to upload TexturePack" then errors += 1 first = first or e.message end
end
add(c, errors == 0, if errors == 0 then "no server errors since the baseline" else errors .. " server error(s): " .. string.sub(first, 1, 100))

if cp == 0 then
    local Config = require(RS.Shared.Config)
    add(c, runState == "Sanctuary", "at home (RunState " .. tostring(runState) .. ")")
    add(c, workspace:GetAttribute("FoodSpawnStatus") == "Ready" and (workspace:GetAttribute("FoodCount") or 0) > 0, "food ready: " .. tostring(workspace:GetAttribute("FoodCount")))
    add(c, workspace:GetAttribute("IslandTerrainReady") == true and workspace:FindFirstChild("BeDinoArena") ~= nil, "island terrain and arena built")
    add(c, player:GetAttribute("IsAdmin") == true, if player:GetAttribute("IsAdmin") == true then "admin remote available (unpublished Studio)" else "not admin: steps 3 and 5 slower / skipped")
    add(c, true, string.format("flags: CaveHub=%s LowPolyDinos=%s ClassMovement=%s profile=%s mode=%s", tostring(Config.CaveHub), tostring(Config.LowPolyDinos), tostring(Config.ClassMovementEnabled), tostring(Config.ReleaseProfile), tostring(player:GetAttribute("ProfileMode"))))
    S.base = {errTime = os.time() - 1, species = player:GetAttribute("EquippedSpeciesId"), copies = copies(), lastRun = player:GetAttribute("LastRunId"), settled = priv("LastSettledRunId")}
elseif cp == 1 then
    add(c, runState == "Active", "run is Active (RunState " .. tostring(runState) .. ")")
    add(c, player:GetAttribute("Location") == "Island", "Location " .. tostring(player:GetAttribute("Location")))
    local eggs = if char then char:GetAttribute("CatchScore") or 0 else 0
    add(c, eggs >= 1, "server counted " .. eggs .. " caught eggs")
    S.cp1 = {eggs = eggs}
    add(c, workspace:GetAttribute("Admin_foodMultiplier") == 10, "Food worth is x" .. tostring(workspace:GetAttribute("Admin_foodMultiplier")))
    add(c, player:GetAttribute("LastLeapStatus") == "leaping", "LastLeapStatus " .. tostring(player:GetAttribute("LastLeapStatus")))
    add(c, (player:GetAttribute("LeapRejectCount") or 0) == 0, "leap rejects " .. tostring(player:GetAttribute("LeapRejectCount") or 0))
    add(c, player:GetAttribute("MovementSecurityStatus") ~= "REJECTED" and (player:GetAttribute("MovementRejectCount") or 0) == 0, "movement guard rejects " .. tostring(player:GetAttribute("MovementRejectCount") or 0))
elseif cp == 2 then
    add(c, runState == "Sanctuary", "home again (RunState " .. tostring(runState) .. ")")
    local score = player:GetAttribute("LastRunCatchScore") or -1
    add(c, player:GetAttribute("LastRunEndReason") == "ManualExit", "end reason " .. tostring(player:GetAttribute("LastRunEndReason")))
    add(c, score >= ((S.cp1 or {}).eggs or 1), "run score " .. tostring(score) .. " covers the eggs seen at checkpoint 1")
    addp(c, num("LastRunEggCount") == math.min(math.floor(score), 150), "banked run eggs " .. num("LastRunEggCount") .. " equal the catches")
    addp(c, priv("LastSettledRunId") ~= S.base.settled, "a settlement was recorded exactly for this run")
    S.cp2 = {lastRun = player:GetAttribute("LastRunId"), settled = priv("LastSettledRunId")}
    addp(c, copies() > (S.base.copies or 0), string.format("dino copies %d -> %d (the hatch party saved them)", S.base.copies or 0, copies()))
    add(c, player:GetAttribute("EquippedSpeciesId") ~= S.base.species, "equipped species changed: " .. tostring(S.base.species) .. " -> " .. tostring(player:GetAttribute("EquippedSpeciesId")))
    add(c, char ~= nil and math.abs((char:GetAttribute("VisualScale") or 1) - 1) < 0.01, "hub size is 1x on the server (VisualScale " .. tostring(char and char:GetAttribute("VisualScale")) .. ")")
    local skip = json("RevealSkipJson")
    addp(c, skip ~= nil and #skip == 0 or nil, "auto-open choices back to none: " .. tostring(priv("RevealSkipJson")))
elseif cp == 3 then
    add(c, runState == "Sanctuary", "home after the second run (RunState " .. tostring(runState) .. ")")
    add(c, player:GetAttribute("LastRunId") ~= (S.cp2 or {}).lastRun, "second run has its own id")
    addp(c, priv("LastSettledRunId") ~= (S.cp2 or {}).settled, "second settlement recorded")
    local progression = json("ProgressionJson") or {}
    local buffs = 0
    for _, b in progression.buffs or {} do if type(b) == "table" and (b.expiresAt or 0) > os.time() - 600 then buffs += 1 end end
    addp(c, buffs >= 0 and type(progression.potions) == "table", "progression profile readable, potions table present")
    local settings = json("SettingsJson")
    addp(c, settings ~= nil and settings.calm == false, "Reduce Motion saved as off again: " .. tostring(settings and settings.calm))
    add(c, workspace:GetAttribute("Admin_foodMultiplier") == 1, "Food worth reset to x1")
    add(c, (workspace:GetAttribute("WeatherId") or "clear") == "clear", "weather " .. tostring(workspace:GetAttribute("WeatherId")))
    add(c, (player:GetAttribute("LeapRejectCount") or 0) == 0 and (player:GetAttribute("MovementRejectCount") or 0) == 0, "no leap or movement rejections in the whole walk")
    addp(c, num("Crystals") >= 0, "crystals " .. num("Crystals"))
else
    add(c, nil, "unknown checkpoint " .. tostring(cp) .. ": use 0 to 3")
end

local verdict = "PASS"
local fails, odds, passes = {}, {}, {}
for _, ck in c do
    if ck[1] == false then verdict = "FAIL" table.insert(fails, "FAIL " .. ck[2])
    elseif ck[1] == nil then if verdict == "PASS" then verdict = "ODD" end table.insert(odds, "ODD " .. ck[2])
    else table.insert(passes, ck[2]) end
end
local parts = {}
for _, group in {fails, odds, passes} do for _, s in group do table.insert(parts, s) end end
local text = string.format("WALKS %d %s checkpoint %s :: %s", cp, verdict, ({[0] = "baseline", "after chunk 1 (steps 1-4)", "after chunk 2 (steps 5-8)", "after chunk 3 (steps 9-13)"})[cp] or "?", table.concat(parts, " | "))
print(text)
return text
