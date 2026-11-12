#!/usr/bin/env python3
"""BD-1175 (docs/225 sections 3 and 7): the starter run's food trail. Offline proof, in the pinned Luau runner.

What runs here is the REAL src/server/FoodService.luau, src/server/StarterRunService.luau and the real shared modules they require, on
small engine stand-ins (vectors, instances, a deterministic Random that logs every draw, raycasts answered by a flat test ground).

  * RULE (pure Shared/StarterTrail): how many foods make the card's eggs (3 amber at 12/500), the spots tried and their order, the clear
    spawn circle, the gap between trail foods, blocked ground (mocked hits), bad input.
  * OWNER-ONLY FOOD (real FoodService tick): only the owner eats it, even when another player stands closer; it pays the normal points
    once and never comes back; it is removed when the run ends, the character changes or the player leaves; bad requests are refused
    (no run, unknown food, outside the map, the clear spawn circle, blocked ground, too many); stock glow; owner attribute.
  * THE MAP DOES NOT MOVE: the seeded food stream (every draw is logged) and every map food are identical with and without a trail,
    also after respawns, in Legacy and in Kit art mode.
  * SERVICE (real StarterRunService + real FoodService): a trail is laid only after a start the server made, only with the flag on,
    never for a veteran or a refused start; eating the trail gives the card's eggs; a blocked straight line bends.
  * Client rules (pure FtueRules), the words, the wiring (source checks), mutants.

--dump-layout FILE writes a fingerprint of the whole food map built by FoodService (four modes: Legacy, Kit, designed food map, special
food). With --food-source OLD.luau it does the same for another copy of FoodService, so "the refactor did not move one food" is a plain
file comparison (done for BD-1175: identical, see docs/225 section 7).

NOT proven here (Studio only): the real terrain raycasts and obstacle rays at the spawn, what the glow and the hidden food look like,
replication and streaming of the owner attribute, the toast on a phone, the join-to-first-hatch time.
"""
from pathlib import Path
import argparse
import hashlib
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FOOD = 'src/server/FoodService.luau'
SERVICE = 'src/server/StarterRunService.luau'
TRAIL = 'src/shared/StarterTrail.luau'
RULES = 'src/shared/FtueRules.luau'
COPY = 'src/shared/FtueCopy.luau'
CLIENT = 'src/client/StarterRunClient.luau'
CONFIG = 'src/shared/Config.luau'
WORKFLOW = '.github/workflows/build-generated-place.yml'
STUBBED = {'ResourceModels', 'LowPolyDinos'}  # engine art and a flag reader: stand-ins below


def read(path):
    return (ROOT / path).read_bytes().decode('utf-8').replace('\r\n', '\n')


def closure():
    """Shared modules the two server modules need, found by following their requires."""
    seen, todo = ['FtueCopy'], [FOOD, SERVICE, COPY]
    while todo:
        source = read(todo.pop())
        for name in re.findall(r'(?:script\.Parent|Shared|shared)\.(\w+)', source):
            path = 'src/shared/%s.luau' % name
            if name not in seen and name not in STUBBED and (ROOT / path).exists():
                seen.append(name)
                todo.append(path)
    return seen


PRELUDE = r'''
local realOs = os
local clock = 0
local os = setmetatable({clock = function() return clock end}, {__index = realOs})
local vmt = {}
local function vec(x, y, z) return setmetatable({X = x, Y = y, Z = z or 0}, vmt) end
vmt.__add = function(a, b) return vec(a.X + b.X, a.Y + b.Y, a.Z + b.Z) end
vmt.__sub = function(a, b) return vec(a.X - b.X, a.Y - b.Y, a.Z - b.Z) end
vmt.__unm = function(a) return vec(-a.X, -a.Y, -a.Z) end
vmt.__mul = function(a, b) if type(a) == "number" then a, b = b, a end return vec(a.X * b, a.Y * b, a.Z * b) end
vmt.__index = function(t, k) if k == "Magnitude" then return math.sqrt(t.X * t.X + t.Y * t.Y + t.Z * t.Z) end return nil end
local Vector3 = {new = vec, one = vec(1, 1, 1), xAxis = vec(1, 0, 0), zAxis = vec(0, 0, 1)}
local Vector2 = {new = function(x, y) return vec(x, y, 0) end}
local CFrame = {new = function(v) return {Position = v} end, Angles = function(a, b, c) return {angles = {a, b, c}} end}
local Color3 = {fromRGB = function(r, g, b) return {r, g, b} end, new = function(r, g, b) return {r, g, b} end}
local Enum = setmetatable({}, {__index = function(_, group) return setmetatable({}, {__index = function(_, item) return group .. "." .. item end}) end})
local RaycastParams = {new = function() return {} end}
-- a deterministic stream per Random object; every draw of a SEEDED stream (the food map's) is logged
local seededDraws, seededSum = 0, 0
local Random = {new = function(seed)
    local state = (seed or 987654321) % 2147483647
    if state == 0 then state = 1 end
    local self = {}
    local function unit()
        state = (state * 48271) % 2147483647
        if seed ~= nil then seededDraws += 1 seededSum = (seededSum * 31 + state) % 1000000007 end
        return state / 2147483647
    end
    function self:NextNumber(lo, hi) local u = unit() if lo then return lo + u * (hi - lo) end return u end
    function self:NextInteger(lo, hi) return lo + math.floor(unit() * (hi - lo + 1)) end
    return self
end}
local created = {}
local methods = {}
local imt = {}
imt.__index = function(t, k) if k == "Parent" then return rawget(t, "_parent") end return methods[k] end
imt.__newindex = function(t, k, v)
    if k ~= "Parent" then rawset(t, k, v) return end
    local old = rawget(t, "_parent")
    if old and old.children then local i = table.find(old.children, t) if i then table.remove(old.children, i) end if old.onRemoved then old.onRemoved(t) end end
    rawset(t, "_parent", v)
    if v and v.children then table.insert(v.children, t) if v.onAdded then v.onAdded(t) end end
end
local function newInstance(class)
    local o = setmetatable({ClassName = class, Name = class, attrs = {}, children = {}}, imt)
    table.insert(created, o)
    return o
end
function methods:SetAttribute(k, v) self.attrs[k] = v end
function methods:GetAttribute(k) return self.attrs[k] end
function methods:IsA(k) return k == self.ClassName or (k == "BasePart" and (self.ClassName == "Part" or self.ClassName == "MeshPart")) end
function methods:GetChildren() return table.clone(self.children) end
function methods:GetDescendants() local out = {} for _, c in self.children do table.insert(out, c) for _, d in c:GetDescendants() do table.insert(out, d) end end return out end
function methods:FindFirstChild(name) for _, c in self.children do if c.Name == name then return c end end return nil end
function methods:FindFirstChildWhichIsA(k) for _, c in self.children do if c:IsA(k) then return c end end return nil end
function methods:Destroy() self.destroyed = true for _, c in table.clone(self.children) do c:Destroy() end self.Parent = nil end
function methods:PivotTo(cf) self.pivot = cf.Position end
function methods:ScaleTo(s) self.scale = s end
function methods:Clone() local c = newInstance(self.ClassName) c.Name = self.Name c.Size = self.Size return c end
local Instance = {new = newInstance}
local workspace = newInstance("Workspace")
rawset(workspace, "BeDinoArena", {}) rawset(workspace, "Terrain", {}) rawset(workspace, "Gravity", 196.2)
-- the test ground: flat at y = 0. terrain(x, z) = "ok" | "water" | "steep" | "none"; obstacle(x, z) = true for a rock or a trunk
local terrain = function(x, z) return "ok" end
local obstacle = function(x, z) return false end
function workspace:Raycast(origin, direction, params)
    local filter = params.FilterDescendantsInstances
    if filter[2] ~= nil then return nil end -- mouth to food: nothing in the way
    if filter[1] == self.Terrain then
        local kind = terrain(origin.X, origin.Z)
        if kind == "none" then return nil end
        return {Position = vec(origin.X, 0, origin.Z), Normal = vec(0, if kind == "steep" then 0.3 else 1, 0), Material = if kind == "water" then Enum.Material.Water else Enum.Material.Grass}
    end
    if obstacle(origin.X, origin.Z) then return {Position = origin} end
    return nil
end
local playerList = {}
local removing = {}
local Players = {PlayerRemoving = {Connect = function(_, fn) table.insert(removing, fn) end}, PlayerAdded = {Connect = function() end}}
function Players:GetPlayers() return playerList end
local moduleProxy = setmetatable({}, {__index = function(_, name) return {__module = name} end})
local ReplicatedStorage = {Shared = moduleProxy, FindFirstChild = function() return nil end}
local Http = {JSONDecode = function() return {} end, JSONEncode = function() return "[]" end}
local game = {GetService = function(_, name) return ({Players = Players, ReplicatedStorage = ReplicatedStorage, HttpService = Http})[name] end}
local spawned, spawnNow = {}, false
local onWait = nil
local task = {spawn = function(fn) if spawnNow then fn() else table.insert(spawned, fn) end end,
    wait = function(s) if onWait then onWait(s) end end, delay = function() end}
local warnings = {}
local warn = function(s) table.insert(warnings, tostring(s)) end
local MODULES, cache, stubs = {}, {}, {}
local function require(token)
    local name = token.__module
    if stubs[name] ~= nil then return stubs[name] end
    if cache[name] == nil then
        assert(MODULES[name], "module not embedded: " .. tostring(name))
        cache[name] = MODULES[name]({Parent = moduleProxy}, require)
        if name == "Config" then cache[name] = table.clone(cache[name]) end -- the tests flip flags on a copy (the real Config is frozen)
    end
    return cache[name]
end
local function fresh(name) return MODULES[name]({Parent = moduleProxy}, require) end -- a new copy of a server module (its own state)
stubs.LowPolyDinos = {enabled = function() return false end}
stubs.ResourceModels = {clone = function(artId)
    local model = newInstance("Model")
    local mesh = newInstance("MeshPart")
    mesh.Size = vec(1, 2, 1.5)
    mesh.Parent = model
    return model
end}
stubs.RunLifecycle = {noteNestWeather = function() end}
stubs.ObjectiveService = {record = function() end} -- only required while Config.ObjectivesEnabled (the switch-on rehearsal)
stubs.TelemetryService = {noteFood = function() end} -- only required while Config.RunTelemetryEnabled
'''

TESTS = r'''
local Config = require({__module = "Config"})
local Trail = require({__module = "StarterTrail"})
local R = require({__module = "FtueRules"})
local Copy = require({__module = "FtueCopy"})
local CatchRules = require({__module = "FoodCatchRules"})
local Food = fresh("FoodService")
local function near(a, b) return math.abs(a - b) < 1e-6 end

-- one line per map food, in creation order, plus the seeded stream: the fingerprint of a built food map
local function fingerprint(from, skipOwned)
    local lines = {}
    for i = from + 1, #created do
        local o = created[i]
        if (o.ClassName == "Part" or o.ClassName == "MeshPart") and o.attrs.Points ~= nil and not (skipOwned and o.attrs.OwnerUserId ~= nil) then
            local keys = {}
            for k in o.attrs do table.insert(keys, k) end
            table.sort(keys)
            local attrs = {}
            for _, k in keys do table.insert(attrs, k .. "=" .. tostring(o.attrs[k])) end
            local glow, model = 0, 0
            for _, c in o.children do if c.ClassName == "Highlight" then glow += 1 elseif c.ClassName == "Model" then model += 1 end end
            local p, s = o.Position, o.Size
            table.insert(lines, string.format("%s|%s|%s|%s|%.5f,%.5f,%.5f|%.5f,%.5f,%.5f|%s|g%d|m%d|t%s", o.Name, o.ClassName,
                if o.Parent then "placed" else "dropped", tostring(o.destroyed == true), if p then p.X else 0/0, if p then p.Y else 0/0, if p then p.Z else 0/0,
                s.X, s.Y, s.Z, table.concat(attrs, ","), glow, model, tostring(o.Transparency)))
        end
    end
    return lines
end
local function build(mode)
    Config.FoodArtMode = if mode == "kit" or mode == "special" then "Kit" else "Legacy"
    Config.FoodLayerEnabled = mode == "layer"
    Config.SpecialFoodsEnabled = mode == "special"
    local mark = #created
    seededDraws, seededSum = 0, 0
    spawned = {}
    Food.start({addGrowth = function() end})
    return mark, spawned[#spawned]
end
local function resetModes() Config.FoodArtMode, Config.FoodLayerEnabled, Config.SpecialFoodsEnabled = "Legacy", false, false end

if DUMP then
    for _, mode in {"legacy", "kit", "layer", "special"} do
        local mark = build(mode)
        local lines = fingerprint(mark, false)
        print(string.format("== %s foods=%d count=%s status=%s fallbacks=%s seededDraws=%d seededSum=%d", mode, #lines, tostring(workspace.attrs.FoodCount),
            tostring(workspace.attrs.FoodSpawnStatus), tostring(workspace.attrs.FoodPlacementFallbacks), seededDraws, seededSum))
        for _, line in lines do print(line) end
    end
    return
end

------------------------------------------------------------------ the pure trail rule
do
    assert(Trail.Kind == "amber" and Food.kindPoints("amber") == 50, "the trail food is the existing amber (50 points)")
    assert(Config.FoodCatchRate == 12 / 500 and Config.StarterRunEggs == 3, "the numbers this row was written for (PROVISIONAL)")
    local one = CatchRules.award(Food.kindPoints(Trail.Kind), 0, 1)
    assert(one == 1, "one amber is one egg at 12/500")
    assert(Trail.count(Config.StarterRunEggs, 50, Config.FoodCatchRate) == 3, "3 amber make the 3 eggs of the card")
    local total, carry = 0, 0
    for _ = 1, 3 do local whole, rest = CatchRules.award(50, carry, 1) total += whole carry = rest end
    assert(total == 3, "eating the trail reaches the card: " .. total)
    assert(Trail.count(1, 50, 12 / 500) == 1 and Trail.count(5, 50, 12 / 500) == 5 and Trail.count(3, 15, 12 / 500) == Trail.MaxFoods and Trail.count(3, 1, 12 / 500) == Trail.MaxFoods, "smallest count, never more than MaxFoods")
    for _, bad in {{0, 50, 0.024}, {3, 0, 0.024}, {3, 50, 0}, {0/0, 50, 0.024}, {3, "x", 0.024}, {3, 50, nil}, {math.huge, 50, 0.024}} do
        assert(Trail.count(bad[1], bad[2], bad[3]) == 0, "bad input: no trail")
    end
    assert(Trail.MaxFoods <= Food.OwnedMaxPerPlayer, "the server ceiling is above the longest trail")
    local o = {originX = 0, originZ = 30, dirX = 0, dirZ = -1, count = 3}
    local all = function() return true end
    local spots = Trail.place(o, all)
    assert(#spots == 3, "three foods on open ground")
    for i, spot in spots do
        assert(near(spot.x, 0) and near(spot.z, 30 - (Trail.FirstStuds + (i - 1) * Trail.StepStuds)) and spot.index == i, "straight ahead, first 14 studs out, then every 8")
        assert(Trail.outsideClear(spot.x, spot.z), "outside the clear spawn circle")
    end
    assert(Trail.FirstStuds >= Trail.ClearRadius + Trail.ClearMargin, "the first food starts outside the circle")
    -- the direction is used, and its length does not matter
    local east = Trail.place({originX = 0, originZ = 30, dirX = 7, dirZ = 0, count = 2}, all)
    assert(near(east[1].x, 14) and near(east[1].z, 30) and near(east[2].x, 22), "the trail follows the direction")
    for _, dir in {{0, 0}, {0/0, 1}, {nil, nil}, {math.huge, 0}} do
        local d = Trail.place({originX = 0, originZ = 30, dirX = dir[1], dirZ = dir[2], count = 1}, all)
        assert(#d == 1 and near(d[1].x, 0) and near(d[1].z, 16), "no usable direction: the way a fresh run start looks")
    end
    -- mocked ground: the straight line is blocked, the trail bends to the first free spot (20 degrees, right before left)
    local tried = {}
    local bent = Trail.place(o, function(x, z) table.insert(tried, {x, z}) return math.abs(x) > 2 end)
    assert(#bent == 3 and near(tried[1][1], 0) and near(tried[1][2], 16), "straight ahead is tried first")
    for i, spot in bent do
        local d = Trail.FirstStuds + (i - 1) * Trail.StepStuds
        assert(near(spot.x, math.sin(math.rad(20)) * d) and near(spot.z, 30 - math.cos(math.rad(20)) * d), "the next spot is 20 degrees to the side at the same distance")
    end
    -- nothing valid: no food at all (never a food in a bad place), and the ground answer must be exactly true
    assert(#Trail.place(o, function() return false end) == 0 and #Trail.place(o, function() return nil end) == 0 and #Trail.place(o, function() return 1 end) == 0)
    -- the clear circle is the rule's own check: ground that says yes inside the circle is still refused
    local inside = Trail.place({originX = 0, originZ = 52, dirX = 0, dirZ = -1, count = 3}, all) -- walking straight through the spawn circle
    assert(#inside == 3)
    for _, spot in inside do assert(Trail.outsideClear(spot.x, spot.z), "never inside the clear spawn circle") end
    assert(not Trail.outsideClear(0, 30) and not Trail.outsideClear(0, 30 - 11.5) and Trail.outsideClear(0, 30 - 12))
    -- two trail foods are never on top of each other, even when only one small patch of ground is valid
    local patch = Trail.place(o, function(x, z) return math.abs(x) < 1 and z < 17 and z > 9 end)
    for i = 1, #patch do for j = i + 1, #patch do
        local dx, dz = patch[i].x - patch[j].x, patch[i].z - patch[j].z
        assert(dx * dx + dz * dz >= Trail.MinGapStuds * Trail.MinGapStuds, "the gap between trail foods holds")
    end end
    assert(#patch >= 1 and #patch < 3, "a small patch gives a shorter trail")
    assert(#Trail.place({originX = 0, originZ = 30, dirX = 0, dirZ = -1, count = 99}, all) == Trail.MaxFoods, "never a long trail")
    for _, bad in {false, {}, {originX = 0, originZ = 30, count = 0/0}, {originX = 0/0, originZ = 30, count = 3}} do assert(#Trail.place(bad, all) == 0) end
    assert(#Trail.place(o, nil) == 0)
    -- client rules and words
    assert(R.starterTrailVisible(nil, 7) and R.starterTrailVisible(7, 7) and not R.starterTrailVisible(8, 7) and not R.starterTrailVisible("7", 7) and not R.starterTrailVisible(7, nil))
    assert(R.starterTrailHintNow({mine = 3, shown = false}) and R.starterTrailHintNow({mine = 1}))
    assert(not R.starterTrailHintNow({mine = 0, shown = false}) and not R.starterTrailHintNow({mine = 3, shown = true}) and not R.starterTrailHintNow({shown = false}) and not R.starterTrailHintNow(nil))
    assert(Copy.starterTrailHint == "Follow the shiny food!")
    print("trail rule ok")
end

------------------------------------------------------------------ players
local function mkPlayer(id, x, z, state)
    local player = {UserId = id, Name = "P" .. id, Parent = Players}
    local root = {Position = vec(x, 1, z), AssemblyLinearVelocity = vec(0, 0, 0), CFrame = {LookVector = vec(0, 0, -1)}}
    function root:IsA(k) return k == "BasePart" end
    local humanoid = {Health = 100, WalkSpeed = 16}
    local character = {attrs = {DinoAttached = true, RunState = state or "Active"}, root = root}
    function character:SetAttribute(k, v) self.attrs[k] = v end
    function character:GetAttribute(k) return self.attrs[k] end
    function character:FindFirstChild(k) return if k == "HumanoidRootPart" then root else nil end
    function character:FindFirstChildOfClass(k) return if k == "Humanoid" then humanoid else nil end
    player.Character = character
    return player, character
end
local function ticks(tick, n, players)
    playerList = players
    local waits = 0
    onWait = function(s) waits += 1 clock += (s or 0.08) if waits > n then error("STOP_TICKS") end end
    local ok, err = pcall(tick)
    onWait = nil
    playerList = {}
    assert(not ok and string.find(tostring(err), "STOP_TICKS"), "the tick loop ran: " .. tostring(err))
end
local function folderOf(mark)
    for i = mark + 1, #created do if created[i].ClassName == "Folder" and created[i].Name == "Food" then return created[i] end end
    error("no Food folder")
end
local function ownedParts(folder, id)
    local out = {}
    for _, part in folder.children do if part.attrs.OwnerUserId ~= nil and (id == nil or part.attrs.OwnerUserId == id) then table.insert(out, part) end end
    return out
end
-- a valid spot with no map food within 12 studs, so only the trail food can be eaten there
local function quietSpot(folder, skip)
    for x = 60, 300, 4 do for z = 60, 300, 4 do
        if Food.groundOk(x, z) then
            local free = true
            for _, part in folder.children do
                local dx, dz = part.Position.X - x, part.Position.Z - z
                if dx * dx + dz * dz < 144 then free = false break end
            end
            if free and (skip or 0) <= 0 then return x, z end
            if free then skip -= 1 end
        end
    end end
    error("no quiet spot")
end
local function eaten(character) return character.attrs.CatchScore or 0 end

------------------------------------------------------------------ owner-only food in the real FoodService
do
    resetModes()
    local stranger = mkPlayer(11, 0, 0)
    assert(Food.addOwned(stranger, "amber", 100, 100) == false and Food.groundOk(100, 100) == false and Food.ownedCount(stranger) == 0, "before the food exists every call says no")
    Food.clearOwned(stranger)
    local mark, tick = build("legacy")
    local folder = folderOf(mark)
    local mapCount = workspace.attrs.FoodCount
    assert(mapCount > 1400 and #ownedParts(folder) == 0 and #warnings == 0, "the map is built, no owner-only food by itself")
    local x, z = quietSpot(folder)
    local a, ac = mkPlayer(101, x + 60, z)
    local b, bc = mkPlayer(55, x, z) -- B stands ON the spot and has the lower user id
    -- refused requests
    local hub = mkPlayer(102, x, z, "Sanctuary")
    assert(Food.addOwned(hub, "amber", x, z) == false, "not in a run: no food")
    assert(Food.addOwned(a, "pizza", x, z) == false and Food.addOwned(a, nil, x, z) == false, "unknown food")
    assert(Food.addOwned(a, "amber", 0/0, z) == false and Food.addOwned(a, "amber", x, "z") == false and Food.addOwned(a, "amber", 9999, z) == false and Food.addOwned(a, "amber", x, -9999) == false, "not a spot on the map")
    assert(Food.addOwned(a, "amber", 0, 30) == false and Food.addOwned(a, "amber", 5, 24) == false and Food.groundOk(0, 30) == false, "the clear spawn circle stays clear")
    terrain = function(tx, tz) return if math.abs(tx - x) < 1 then "water" else "ok" end
    assert(Food.addOwned(a, "amber", x, z) == false, "water")
    terrain = function(tx, tz) return if math.abs(tx - x) < 1 then "steep" else "ok" end
    assert(Food.addOwned(a, "amber", x, z) == false, "a steep slope")
    terrain = function() return "ok" end
    obstacle = function(tx, tz) return math.abs(tx - x) < 1 end
    assert(Food.addOwned(a, "amber", x, z) == false and Food.groundOk(x, z) == false, "a rock or a trunk")
    obstacle = function() return false end
    assert(#ownedParts(folder) == 0 and Food.ownedCount(a) == 0, "a refused request leaves nothing behind")
    -- accepted
    assert(Food.groundOk(x, z) == true and Food.addOwned(a, "amber", x, z) == true, "valid ground in a run")
    local mine = ownedParts(folder, 101)
    assert(#mine == 1 and Food.ownedCount(a) == 1 and Food.ownedCount(b) == 0)
    local part = mine[1]
    assert(part.Name == "amber" and part.attrs.Points == 50 and part.attrs.OwnerUserId == 101 and part.attrs.StarterFood == false and part.attrs.SpecialFood == nil, "the existing amber, with its owner")
    assert(near(part.Position.X, x) and near(part.Position.Z, z) and part.Position.Y > 0, "on the ground at the asked spot")
    assert(part.Anchored == true and part.CanCollide == false and part.CanTouch == false and part.CanQuery == false, "the same physics switches as every food")
    local glows = 0
    for _, c in part.children do if c.ClassName == "Highlight" then glows += 1 assert(c.FillTransparency == 0.7, "the stock glow of the special food") end end
    assert(glows == 1, "one stock Highlight")
    assert(workspace.attrs.FoodCount == mapCount, "the map's food count is the map's")
    -- B stands on it for many ticks: nothing (B is closer AND has the lower id, the old tie rule would have picked B)
    ticks(tick, 6, {a, b})
    assert(eaten(bc) == 0 and (bc.attrs.FoodCatchCarry or 0) == 0 and part.Parent == folder and not part.destroyed, "another player cannot eat it")
    assert(eaten(ac) == 0, "the owner far away eats nothing")
    -- the owner walks there: the normal points, once
    ac.root.Position = vec(x, 1, z)
    ticks(tick, 6, {a, b})
    assert(eaten(ac) == 1 and near(ac.attrs.FoodCatchCarry, 50 * Config.FoodCatchRate - 1), "the owner gets one egg from one amber: " .. eaten(ac))
    assert(part.destroyed == true and part.Parent == nil and #ownedParts(folder) == 0 and Food.ownedCount(a) == 0, "eaten food is removed")
    assert(eaten(bc) == 0, "and still nothing for the other player")
    clock += 100000
    ticks(tick, 6, {a, b})
    assert(#ownedParts(folder) == 0 and eaten(ac) == 1 and eaten(bc) == 0, "it never comes back")
    -- the ceiling
    local x2, z2 = quietSpot(folder, 3)
    for i = 1, Food.OwnedMaxPerPlayer do assert(Food.addOwned(a, "amber", x2 + (i % 3) * 2, z2 + (i // 3) * 2) == true) end
    assert(Food.addOwned(a, "amber", x2 + 7, z2 + 7) == false and Food.ownedCount(a) == Food.OwnedMaxPerPlayer, "a hard ceiling per player")
    assert(Food.addOwned(b, "berry", x2 + 7, z2 + 7) == true and Food.ownedCount(b) == 1, "per player, not for the server")
    -- the run ends: the owner's food goes on the next tick, the other player's stays
    ac.attrs.RunState = "Results"
    ticks(tick, 1, {a, b})
    assert(Food.ownedCount(a) == 0 and #ownedParts(folder, 101) == 0 and Food.ownedCount(b) == 1, "removed when the run ends")
    -- a new character (death, respawn): gone
    local _, newCharacter = mkPlayer(55, x2, z2)
    b.Character = newCharacter
    ticks(tick, 1, {a, b})
    assert(Food.ownedCount(b) == 0, "removed with the character it was made for")
    -- the player leaves: gone at once, without waiting for a tick
    ac.attrs.RunState = "Active"
    assert(Food.addOwned(a, "amber", x2, z2) == true and Food.ownedCount(a) == 1)
    for _, fn in removing do fn(a) end
    assert(Food.ownedCount(a) == 0 and #ownedParts(folder) == 0, "removed when the player leaves")
    -- and a player object that is no longer in the game (leave seen by the tick)
    assert(Food.addOwned(a, "amber", x2, z2) == true)
    a.Parent = nil
    ticks(tick, 1, {})
    assert(Food.ownedCount(a) == 0, "removed when the owner is gone")
    assert(#warnings == 0)
    print("owner-only food ok")
end

------------------------------------------------------------------ the map does not move
for _, mode in {"legacy", "kit"} do
    local function scenario(withTrail)
        clock = 0
        local mark, tick = build(mode)
        local folder = folderOf(mark)
        local builtDraws, builtSum = seededDraws, seededSum
        local x, z = quietSpot(folder)
        local first = nil
        for _, part in folder.children do if part.attrs.StarterFood == false then first = part break end end
        local eater = mkPlayer(201, first.Position.X, first.Position.Z)
        local starter, sc = mkPlayer(202, x, z)
        if withTrail then
            for i = 0, 2 do assert(Food.addOwned(starter, "amber", x + i * 2, z) == true) end
        end
        ticks(tick, 4, {eater, starter}) -- the eater eats map food, the starter its trail
        if withTrail then assert(eaten(sc) >= 1 and Food.ownedCount(starter) < 3, "the trail was eaten in this scenario") end
        clock += 100000
        ticks(tick, 2, {}) -- the eaten map food respawns: this draws from the seeded stream
        assert(seededDraws > builtDraws, "the respawn drew from the seeded stream (the scenario exercises it)")
        return table.concat(fingerprint(mark, true), "\n"), seededDraws, seededSum, builtDraws, builtSum
    end
    local plain, draws, sum, builtDraws, builtSum = scenario(false)
    local trail, draws2, sum2, builtDraws2, builtSum2 = scenario(true)
    assert(builtDraws == builtDraws2 and builtSum == builtSum2, mode .. ": the build is deterministic")
    assert(draws == draws2 and sum == sum2, mode .. ": owner-only food drew from the seeded map stream (" .. draws .. " vs " .. draws2 .. ")")
    assert(plain == trail, mode .. ": a map food differs with a trail in the world")
end
resetModes()
print("map unchanged ok")

------------------------------------------------------------------ the real StarterRunService lays the trail
do
    local function world(flag, opts)
        opts = opts or {}
        Config.StarterRunEnabled = flag
        clock = 0
        local mark, tick = build("legacy")
        local folder = folderOf(mark)
        local private, starts = {}, {}
        stubs.PrivateState = {get = function(p, name) return private[p] and private[p][name] end}
        stubs.FoodService = Food
        local answer = if opts.answer == nil then true else opts.answer
        stubs.RunLifecycle = {noteNestWeather = function() end, requestStart = function(p)
            table.insert(starts, p)
            if answer ~= true then return answer end
            p.Character.attrs.RunState = "Active" -- what RunLifecycle.begin does, after the teleport to the island spawn
            p.Character.root.Position = vec(0, 8, 30)
            return true
        end}
        local Service = fresh("StarterRunService")
        local joined = {}
        Players.PlayerAdded = {Connect = function(_, fn) table.insert(joined, fn) end}
        local function join(id, starter)
            local p, c = mkPlayer(id, 0, 521, "Sanctuary")
            p.CharacterAdded = {Connect = function() end}
            private[p] = {StarterRun = if starter then 1 else 0}
            table.insert(playerList, p)
            return p, c
        end
        local function start()
            spawnNow = true
            onWait = function(s) clock += s end
            Service.start()
            spawnNow, onWait = false, nil
        end
        return {folder = folder, tick = tick, starts = starts, join = join, start = start, joined = joined}
    end
    -- flag off: the service does nothing, so no trail
    do
        playerList = {}
        local w = world(false)
        local p = w.join(301, true)
        w.start()
        assert(#w.starts == 0 and #w.joined == 0 and Food.ownedCount(p) == 0 and #ownedParts(w.folder) == 0, "flag off: no start, no trail")
    end
    -- flag on: a starter gets the trail of 3 amber in front of the spawn, a veteran gets a normal game
    do
        playerList = {}
        local w = world(true)
        local p, c = w.join(302, true)
        local veteran = w.join(303, false)
        w.start()
        assert(#w.starts == 1 and w.starts[1] == p, "only the starter's run is started")
        local trail = ownedParts(w.folder, 302)
        assert(#trail == 3 and Food.ownedCount(p) == 3 and Food.ownedCount(veteran) == 0 and #ownedParts(w.folder) == 3, "3 foods for the starter, none for the veteran")
        table.sort(trail, function(l, r) return l.Position.Z > r.Position.Z end)
        for i, part in trail do
            assert(part.Name == "amber" and part.attrs.Points == 50 and near(part.Position.X, 0) and near(part.Position.Z, 30 - (14 + (i - 1) * 8)), "a straight line from the spawn: " .. part.Position.Z)
            assert(Trail.outsideClear(part.Position.X, part.Position.Z))
        end
        -- the veteran walks the trail first: nothing. Then the starter: the card's eggs, and the trail is gone.
        local vc = veteran.Character
        vc.attrs.RunState = "Active"
        for _, part in table.clone(trail) do
            vc.root.Position = vec(part.Position.X, 1, part.Position.Z)
            ticks(w.tick, 3, {p, veteran})
        end
        assert(#ownedParts(w.folder, 302) == 3, "the veteran took none of it")
        local before = eaten(c)
        for _, part in table.clone(trail) do
            c.root.Position = vec(part.Position.X, 1, part.Position.Z)
            ticks(w.tick, 3, {p, veteran})
        end
        assert(#ownedParts(w.folder) == 0 and Food.ownedCount(p) == 0, "the starter ate the whole trail")
        assert(eaten(c) - before >= Config.StarterRunEggs, "the trail alone reaches the card: " .. (eaten(c) - before) .. " eggs")
    end
    -- a blocked line in front of the spawn: the trail bends, every food is still on valid ground
    do
        playerList = {}
        obstacle = function(x, z) return math.abs(x) < 2.5 end
        local w = world(true)
        local p = w.join(304, true)
        w.start()
        local trail = ownedParts(w.folder, 304)
        assert(#trail == 3, "a bent trail is still three foods")
        for _, part in trail do assert(math.abs(part.Position.X) >= 2.5 and Trail.outsideClear(part.Position.X, part.Position.Z) and Food.groundOk(part.Position.X, part.Position.Z), "beside the blocked line") end
        obstacle = function() return false end
    end
    -- no valid ground anywhere near: the run starts, there is just no trail
    do
        playerList = {}
        terrain = function(x, z) return if math.abs(x) < 80 and math.abs(z - 30) < 80 then "water" else "ok" end
        local w = world(true)
        local p, c = w.join(305, true)
        w.start()
        assert(#w.starts == 1 and c.attrs.RunState == "Active" and Food.ownedCount(p) == 0, "no ground: a normal run without a trail")
        terrain = function() return "ok" end
    end
    -- a refused start lays nothing
    do
        playerList = {}
        local w = world(true, {answer = false})
        local p = w.join(306, true)
        w.start()
        assert(#w.starts >= 2 and Food.ownedCount(p) == 0 and #ownedParts(w.folder) == 0, "no run, no trail")
    end
    Config.StarterRunEnabled = false
    playerList = {}
    assert(#warnings == 0)
    print("trail service ok")
end
'''

MARKERS = ('trail rule ok', 'owner-only food ok', 'map unchanged ok', 'trail service ok')


def script(replacements=None, dump=False, food_source=None):
    def source(path):
        text = read(path) if not (path == FOOD and food_source) else Path(food_source).read_bytes().decode('utf-8').replace('\r\n', '\n')
        for old, new in (replacements or {}).get(path, []):
            assert old in text, 'mutant target missing in %s: %s' % (path, old)
            text = text.replace(old, new)
        return text
    out = [PRELUDE, 'local DUMP = %s\n' % ('true' if dump else 'false')]
    for name in closure():
        out.append('MODULES.%s = function(script, require)\n%s\nend\n' % (name, source('src/shared/%s.luau' % name)))
    for name, path in (('FoodService', FOOD), ('StarterRunService', SERVICE)):
        out.append('MODULES.%s = function(script, require)\n%s\nend\n' % (name, source(path)))
    return ''.join(out) + TESTS


def run(runner, replacements=None, dump=False, food_source=None):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'starter_trail.luau'
        path.write_text(script(replacements, dump, food_source), encoding='utf-8', newline='\n')
        try:
            result = subprocess.run([runner, str(path)], capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            return False, 'TIMEOUT\n'
    out = result.stdout + result.stderr
    if dump:
        return result.returncode == 0 and out.count('== ') == 4, out
    return result.returncode == 0 and all(marker in result.stdout for marker in MARKERS), out


MUTANTS = {
    'another player can eat owner-only food': {FOOD: [('if food.hidden or (food.owner ~= nil and food.owner ~= candidate.player) then return end', 'if food.hidden then return end')]},
    'owner-only food respawns like map food': {FOOD: [('                if food.owner ~= nil then\n                    removeOwned(food) -- BD-1175: eaten once, never comes back\n                else', '                if false then\n                else')]},
    'owner-only food stays after the run': {FOOD: [('if owner.Parent == nil or character ~= food.character or character:GetAttribute("RunState") ~= "Active" then removeOwned(food) end', 'if owner.Parent == nil or character ~= food.character then removeOwned(food) end')]},
    'owner-only food stays for a new character': {FOOD: [('if owner.Parent == nil or character ~= food.character or character:GetAttribute("RunState") ~= "Active" then removeOwned(food) end', 'if owner.Parent == nil or character:GetAttribute("RunState") ~= "Active" then removeOwned(food) end')]},
    'owner-only food stays when the owner is gone': {FOOD: [('if owner.Parent == nil or character ~= food.character or', 'if character ~= food.character or')]},
    'owner-only food stays when the player leaves': {FOOD: [('windows[player] = nil owned.clear(player) end)', 'windows[player] = nil end)')]},
    'owner-only food draws from the seeded map stream': {FOOD: [('makePickup(kind, false, false, sx, sz, count + 1, eventRandom)', 'makePickup(kind, false, false, sx, sz, count + 1, random)')]},
    'owner-only food skips the ground rule': {FOOD: [('        return groundAt(x, z) -- the SAME ground,', '        return Vector3.new(x, 0, z) -- the SAME ground,')]},
    'owner-only food can be put outside the map': {FOOD: [('or x ~= x or z ~= z or math.abs(x) > extent or math.abs(z) > extent then return nil end', 'or x ~= x or z ~= z then return nil end')]},
    'owner-only food outside a run': {FOOD: [('if not character or character:GetAttribute("RunState") ~= "Active" then return false end -- only inside a run', 'if not character then return false end -- only inside a run')]},
    'no ceiling per player': {FOOD: [('            if count >= FoodService.OwnedMaxPerPlayer then return false end\n', '')]},
    'the ceiling is for the whole server': {FOOD: [('for food in ownedFoods do if food.owner == player then n += 1 end end\n        return n', 'for food in ownedFoods do n += 1 end\n        return n')]},
    'no owner attribute': {FOOD: [('            pickup:SetAttribute("OwnerUserId", player.UserId)', '            pickup:SetAttribute("OwnerUserIdX", player.UserId)')]},
    'no glow on the trail': {FOOD: [('            addGlow(pickup, kind.color)\n            pickup.Position', '            pickup.Position')]},
    'the trail counts as map food': {FOOD: [('            ownedFoods[food] = true\n', '            ownedFoods[food] = true\n            workspace:SetAttribute("FoodCount", (workspace:GetAttribute("FoodCount") or 0) + 1)\n')]},
    'eaten owner-only food stays in the world': {FOOD: [('        food.part:Destroy() -- a kit model is a child of the part', '        -- a kit model is a child of the part')]},
    'the trail is laid inside the spawn circle': {TRAIL: [('local free = Trail.outsideClear(spot.x, spot.z)', 'local free = true')]},
    'the trail ignores the ground': {TRAIL: [('if free and groundOk(spot.x, spot.z) == true then', 'if free then')]},
    'trail foods on top of each other': {TRAIL: [('if dx * dx + dz * dz < Trail.MinGapStuds * Trail.MinGapStuds then free = false break end', '')]},
    'the trail is one food short': {TRAIL: [('if math.floor(n * pointsPerFood * catchRate + 1e-9) >= math.floor(cardEggs) then return n end', 'if math.ceil(n * pointsPerFood * catchRate) >= math.floor(cardEggs) then return n end')]},
    'the trail has no maximum': {TRAIL: [('for index = 1, math.min(math.floor(o.count), Trail.MaxFoods) do', 'for index = 1, math.floor(o.count) do')]},
    'the trail starts at the feet': {TRAIL: [('Trail.FirstStuds = 14', 'Trail.FirstStuds = 4')]},
    'the trail ignores the direction': {TRAIL: [('    dx, dz = dx / length, dz / length\n', '    dx, dz = 0, -1\n')]},
    'the trail is berries': {TRAIL: [('Trail.Kind = "amber"', 'Trail.Kind = "berry"')]},
    # two guards (the service lays it only after its own start; FoodService refuses outside a run): only both removed gives a hub player food
    'the service lays a trail for a refused start': {SERVICE: [('                    if ok and began == true then\n', '                    pcall(layTrail, player, character)\n                    if ok and began == true then\n')],
                                                     FOOD: [('if not character or character:GetAttribute("RunState") ~= "Active" then return false end -- only inside a run', 'if not character then return false end -- only inside a run')]},
    'the service never lays the trail': {SERVICE: [('                        pcall(layTrail, player, character) -- BD-1175', '                        -- BD-1175')]},
    'the service lays food for everybody to eat': {SERVICE: [('if FoodService.addOwned(player, StarterTrail.Kind, spot.x, spot.z) then placed += 1 end', 'if FoodService.addOwned(nil, StarterTrail.Kind, spot.x, spot.z) then placed += 1 end')]},
    'the service skips the ground check': {SERVICE: [('(Config :: any).FoodCatchRate)}, FoodService.groundOk)', '(Config :: any).FoodCatchRate)}, function() return true end)')]},
    'a client shows everybody\'s trail': {RULES: [('return type(ownerUserId) == "number" and ownerUserId == myUserId', 'return true')]},
    'a client hides ordinary food': {RULES: [('    if ownerUserId == nil then return true end\n    return type(ownerUserId)', '    return type(ownerUserId)')]},
    'the hint shows without a trail': {RULES: [('return type(s.mine) == "number" and s.mine >= 1', 'return true')]},
    'the hint repeats for every food': {RULES: [('if type(s) ~= "table" or s.shown == true then return false end\n    return type(s.mine)', 'if type(s) ~= "table" then return false end\n    return type(s.mine)')]},
    'the hint has other words': {COPY: [('Copy.starterTrailHint = "Follow the shiny food!"', 'Copy.starterTrailHint = "Go eat the 3 ambers (50 pts)"')]},
}

SOURCE_MUTANTS = {
    'the map food uses another random stream': (FOOD, 'makePickup(kind, special, starter, sx, sz, itemIndex, random)', 'makePickup(kind, special, starter, sx, sz, itemIndex, eventRandom)'),
    'a second glow instance is built': (FOOD, '            addGlow(pickup, kind.color)\n            pickup.Position', '            local glow = Instance.new("Highlight") glow.Parent = pickup\n            pickup.Position'),
    'the spawn circle moved in FoodService only': (FOOD, '(Vector2.new(x, z) - Vector2.new(0, 30)).Magnitude < 11', '(Vector2.new(x, z) - Vector2.new(0, 30)).Magnitude < 20'),
    'the spawn circle moved in the trail rule only': (TRAIL, 'Trail.ClearRadius, Trail.ClearMargin = 0, 30, 11, 1', 'Trail.ClearRadius, Trail.ClearMargin = 0, 30, 6, 1'),
    'the trail module touches the engine': (TRAIL, 'local Trail = {}', 'local Trail = {}\nlocal _ = workspace:Raycast(Vector3.zero, Vector3.zero)'),
    'a trail flag of its own, on in source': (CONFIG, '    StarterRunEnabled = false,', '    StarterRunEnabled = false,\n    StarterTrailEnabled = true,'),
    'the service lays the trail outside the flag': (SERVICE, 'function StarterRunService.start()\n    if not enabled() then return end', 'function StarterRunService.start()\n    if false then return end'),
    'the service reads the ground by itself': (SERVICE, '(Config :: any).FoodCatchRate)}, FoodService.groundOk)', '(Config :: any).FoodCatchRate)}, function(x, z) return workspace:Raycast(Vector3.new(x, 50, z), Vector3.new(0, -100, 0)) ~= nil end)'),
    'the trail failure stops the run start': (SERVICE, 'pcall(layTrail, player, character)', 'layTrail(player, character)'),
    'the client does not hide other players\' trail': (CLIENT, '    else\n        hideFood(part)\n    end', '    end'),
    'the client decides ownership by itself': (CLIENT, 'if Rules.starterTrailVisible(owner, player.UserId) then', 'if owner ~= 0 then'),
    'the client touches ordinary food': (CLIENT, '    if owner == nil then return end -- ordinary food', '    -- ordinary food'),
    'the client watches food with the flag off': (CLIENT, '    latch()\n    task.spawn(watchFood)', '    latch()\nend\ntask.spawn(watchFood)\ndo'),
    'the client never watches the food': (CLIENT, '    task.spawn(watchFood) -- BD-1175', '    -- BD-1175'),
    'the hint is typed by hand': (CLIENT, 'd.notify(Copy.starterTrailHint, Theme.Colors.gold,', 'd.notify("Follow the shiny food!", Theme.Colors.gold,'),
    'the hint ignores the rule': (CLIENT, 'if Rules.starterTrailHintNow({mine = mine, shown = trailHintShown}) then', 'if true then'),
    'the client waits for the food forever': (CLIENT, 'workspace:WaitForChild("Food", 120)', 'workspace:WaitForChild("Food")'),
    'the client tells the server what it ate': (CLIENT, '        trailMine[part] = true\n', '        trailMine[part] = true\n        d.endRun:FireServer(part)\n'),
    'the verifier left the CI workflow': (WORKFLOW, 'python tools/verify_starter_trail.py --runner /tmp/luau/luau', 'python tools/verify_starter_trailX.py'),
}


def check_sources(overrides=None):
    """overrides: {path: source} for a source mutant. Returns the first problem or None."""
    def src(path):
        return overrides[path] if overrides and path in overrides else read(path)
    food = src(FOOD)
    for needle, count in (('makePickup(kind, special, starter, sx, sz, itemIndex, random)', 1), ('makePickup(kind, false, false, sx, sz, count + 1, eventRandom)', 1),
                          ('Instance.new("Highlight")', 1), ('local random = Random.new(Config.FoodSeed)', 1), ('(Vector2.new(x, z) - Vector2.new(0, 30)).Magnitude < 11', 1),
                          ('local function makePickup(', 1), ('rng:NextNumber', 2)):
        if food.count(needle) != count:
            return 'FoodService: expected %d x %s' % (count, needle)
    # inside makePickup the only stream is the one passed in; the map's seeded stream is drawn in the same places as before the refactor
    maker = food.split('local function makePickup(', 1)[1].split('        return pickup, visual\n', 1)[0]
    if 'random:' in maker or 'eventRandom' in maker:
        return 'makePickup must draw only from the stream it is given'
    if food.count('random:Next') != 6:
        return 'FoodService draws from the seeded map stream in exactly six places (centre x and z, kind roll, special roll, respawn angle and radius)'
    if 'rbxassetid' in food:
        return 'no new art in FoodService'
    trail = src(TRAIL)
    if 'Trail.ClearX, Trail.ClearZ, Trail.ClearRadius, Trail.ClearMargin = 0, 30, 11, 1' not in trail:
        return 'StarterTrail keeps the same clear spawn circle as FoodService.groundAt (0, 30, radius 11)'
    code = '\n'.join(line.split('--', 1)[0] for line in trail.splitlines())
    for word in ('workspace', 'game', 'Instance', 'Vector3', 'Raycast', 'require', 'Random', 'task.'):
        if word in code:
            return 'StarterTrail is pure (no engine call): ' + word
    for needle in ('Trail.FirstStuds = 14 -- PROVISIONAL', 'Trail.StepStuds = 8 -- PROVISIONAL', 'Trail.Kind = "amber"'):
        if needle not in trail:
            return 'StarterTrail lost: ' + needle
    config = src(CONFIG)
    if config.count('    StarterRunEnabled = false,') != 1 or 'StarterTrail' in config:
        return 'one flag (StarterRunEnabled, false in source); the trail has no flag of its own'
    service = src(SERVICE)
    for needle in ('function StarterRunService.start()\n    if not enabled() then return end', 'pcall(layTrail, player, character)',
                   '(Config :: any).FoodCatchRate)}, FoodService.groundOk)', 'FoodService.addOwned(player, StarterTrail.Kind, spot.x, spot.z)',
                   'StarterTrail.count((Config :: any).StarterRunEggs, FoodService.kindPoints(StarterTrail.Kind), (Config :: any).FoodCatchRate)'):
        if service.count(needle) != 1:
            return 'StarterRunService lost: ' + needle
    if service.count('layTrail') != 2 or service.index('if ok and began == true then') > service.index('pcall(layTrail, player, character)'):
        return 'the trail is laid in one place: after a start the server made, inside pcall'
    service_code = '\n'.join(line.split('--', 1)[0] for line in service.splitlines())
    for word in ('Raycast', 'Instance.new', 'workspace'):
        if word in service_code:
            return 'StarterRunService builds nothing and reads no ground by itself: ' + word
    client = src(CLIENT)
    code = '\n'.join(line for line in client.splitlines() if line.strip() and not line.strip().startswith('--'))
    for needle in ('    if owner == nil then return end -- ordinary food', 'if Rules.starterTrailVisible(owner, player.UserId) then', '    else\n        hideFood(part)\n    end',
                   'if Rules.starterTrailHintNow({mine = mine, shown = trailHintShown}) then', 'd.notify(Copy.starterTrailHint, Theme.Colors.gold,',
                   'workspace:WaitForChild("Food", 120)', 'local owner = part:GetAttribute("OwnerUserId")'):
        if client.count(needle) != 1:
            return 'StarterRunClient lost: ' + needle
    attach = client.split('function Starter.attach(', 1)[1]
    if '    latch()\n    task.spawn(watchFood) -- BD-1175' not in attach or attach.count('task.spawn(watchFood)') != 1 or client.count('watchFood') != 2 or attach.index('if not enabled() or attached then return end') > attach.index('task.spawn(watchFood)'):
        return 'the food watcher starts only inside attach, after the flag check'
    if code.count('FireServer') != 1 or 'Instance.new' in code or 'SetAttribute' in code:
        return 'the client only shows: one FireServer (the card button), no instance, no attribute written'
    if 'Follow the shiny food' in code:
        return 'the hint words live in FtueCopy only'
    if src(WORKFLOW).count('python tools/verify_starter_trail.py --runner /tmp/luau/luau') != 1:
        return 'the CI workflow runs this verifier'
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    parser.add_argument('--dump-layout', help='write the food map fingerprint (four modes) to this file and stop')
    parser.add_argument('--food-source', help='with --dump-layout: another copy of FoodService.luau (for example the one on origin/main)')
    args = parser.parse_args()
    if args.dump_layout:
        ok, out = run(args.runner, dump=True, food_source=args.food_source)
        Path(args.dump_layout).write_text(out, encoding='utf-8', newline='\n')
        print('%s: %d lines, sha256 %s' % (args.dump_layout, out.count('\n'), hashlib.sha256(out.encode('utf-8')).hexdigest()))
        for line in out.splitlines():
            if line.startswith('== '):
                print(line)
        sys.exit(0 if ok else 1)
    problem = check_sources()
    if problem:
        print('FAIL', problem)
        sys.exit(1)
    ok, out = run(args.runner)
    print(out, end='')
    if not ok:
        sys.exit(1)
    if not args.no_mutants:
        for name, replacements in MUTANTS.items():
            passed, _ = run(args.runner, replacements)
            assert not passed, 'MUTANT SURVIVED: ' + name
            print('  mutant caught: ' + name)
        for name, (path, old, new) in SOURCE_MUTANTS.items():
            source = read(path)
            assert old in source, 'mutant target missing in %s: %s' % (path, old)
            assert check_sources({path: source.replace(old, new)}) is not None, 'SOURCE MUTANT SURVIVED: ' + name
            print('  source mutant caught: ' + name)
    print('Starter trail passed: 3 amber make the card, spots on valid ground outside the clear spawn circle (mocked hits), owner-only claim in the real '
          'FoodService tick, no respawn, removed at run end / new character / leave, refused requests, the seeded map stream and every map food unchanged '
          'with a trail (Legacy and Kit), the real StarterRunService lays it only for a server-made starter start, client rules, words, wiring, %d mutants caught'
          % (0 if args.no_mutants else len(MUTANTS) + len(SOURCE_MUTANTS)))


if __name__ == '__main__':
    main()
