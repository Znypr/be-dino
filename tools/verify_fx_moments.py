"""BD-433 (docs/123 s2 and s3): offline audit of the three "moment" FX that sit on top of the anime P0 / P1 renders. The REAL Luau modules run
on stubbed Roblox instances (same approach as tools/verify_fx_anime.py):

  1. EffectsLod (pure): RimHighlights Full / Lite / Off, the hard cap, rimFits (budget), Domes caps, domeFits.
  2. MomentRimPlan (pure): Life 1.5 s, Off = none, Lite = fainter outline-only, Reduce Motion = still and no brighten, "new" vs "brighten"
     decision, smooth envelope, colour priority, transparencies and brighten never leave their ranges.
  3. FxRecipes.wantsDome / domeLook, RareHatch.plan().sweep / sweepAt (pure): only with the real mesh, only Full, never Reduce Motion.
  4. The REAL client/MomentRim.luau: ONE Highlight in the mutation colour that fades in and out and is gone after 1.5 s; an existing fused-tier
     rim ("LPTierRim") is brightened and handed back exactly instead of a second Highlight; Full / Lite / Off; Reduce Motion; the global
     Highlight budget (30 alive = refused); the 1.5 s gap; a replaced moment never leaves two of our Highlights; a vanished rim ends cleanly.
  5. The REAL client/RareHatchClient.client.luau: the soft light sweep exists ONLY on the own rare banner, ONLY at Full without Reduce Motion
     and ONLY while the shaftGradient slot holds a real upload (empty id = exactly today's banner); a mutation hatch asks MomentRim for the rim.
  6. The REAL client/FxRig.luau: the shock dome exists only when shock_dome_mesh holds a real upload, at the full look without Reduce Motion, for
     a Seismic mutation reveal and an Epic+ aura equip; it swells, fades and is removed; phone cap 1 / tablet 1 / desktop 2 and a 2 s gap hold;
     domeGradient is bound only when that slot is real; an empty mesh slot adds nothing.
  7. Source scan: the wiring is in place, no asset ids are invented, the slots stay empty.
Drawing itself is Studio-only; nothing here claims a Studio check."""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_fx_anime import ROOT, load_mods, module, src  # noqa: E402

PURE = r'''
-- 1. EffectsLod
assert(Lod.RimHighlights.full == 8 and Lod.RimHighlights.lite == 4 and Lod.RimHighlights.off == 0, "RimHighlights Full / Lite / Off")
assert(Lod.RimHighlightHardCap == 31 and Lod.RimHighlights.full < Lod.RimHighlightHardCap, "far below the engine cap")
assert(not pcall(function() Lod.RimHighlights.full = 99 end), "RimHighlights is frozen")
for _, mode in {"full", "lite", "bogus"} do
    assert(Lod.rimFits(mode, 0) and Lod.rimFits(mode, 29), mode .. ": a moment rim fits while Highlights are free")
    assert(not Lod.rimFits(mode, 30) and not Lod.rimFits(mode, 31) and not Lod.rimFits(mode, 99), mode .. ": one Highlight is always left below the engine cap")
end
for live = 0, 40 do assert(not Lod.rimFits("off", live), "Off never adds a rim") end
assert(Lod.Domes.phone == 1 and Lod.Domes.tablet == 1 and Lod.Domes.desktop == 2, "dome caps")
assert(not pcall(function() Lod.Domes.phone = 9 end), "Domes is frozen")
for dev, cap in {phone = 1, tablet = 1, desktop = 2} do
    for live = 0, 3 do assert(Lod.domeFits(dev, live) == (live < cap), dev .. " dome cap at " .. live) end
end
assert(Lod.domeFits("bogus", 1) and not Lod.domeFits("bogus", 2), "an unknown device plays as desktop")

-- 2. MomentRimPlan
assert(Plan.Life == 1.5 and Plan.FadeIn + Plan.FadeOut <= Plan.Life, "1.5 s, fades fit inside")
assert(Plan.look("off", false) == nil and Plan.look("off", true) == nil, "Off: no look")
do
    local full, lite = Plan.look("full", false), Plan.look("lite", false)
    assert(full and lite and not full.still and not lite.still, "Full and Lite move")
    assert(full.outline < lite.outline and full.fill < 1 and lite.fill == 1, "Lite is outline only and fainter")
    assert(full.brighten > lite.brighten and lite.brighten > 0 and full.whiten > lite.whiten, "Lite brightens gently")
    assert(Plan.look("bogus", false).outline == full.outline, "unknown level plays as Full")
    for _, mode in {"full", "lite"} do
        local calm = Plan.look(mode, true)
        assert(calm.still and calm.brighten == 0 and calm.whiten == 0 and calm.outline == lite.outline and calm.fill == 1, "Reduce Motion: still, Lite look, no brighten (" .. mode .. ")")
    end
end
for _, case in {
    {"full", false, false, "new"}, {"lite", false, false, "new"}, {"off", false, false, "none"}, {"full", true, false, "new"}, {"lite", true, false, "new"}, {"off", true, false, "none"},
    {"full", false, true, "brighten"}, {"lite", false, true, "brighten"}, {"off", false, true, "none"}, {"full", true, true, "none"}, {"lite", true, true, "none"}, {"off", true, true, "none"},
} do
    assert(Plan.mode(case[1], case[2], case[3]) == case[4], "mode " .. case[1] .. " calm " .. tostring(case[2]) .. " tierRim " .. tostring(case[3]) .. " -> " .. case[4])
end
for _, still in {false, true} do
    assert(Plan.envelope(-1, still) == 0 and Plan.envelope(Plan.Life, still) == 0 and Plan.envelope(Plan.Life + 3, still) == 0, "no strength outside 0..Life")
end
do
    assert(Plan.envelope(0, false) == 0 and Plan.envelope(Plan.FadeIn, false) == 1 and Plan.envelope(Plan.Life - Plan.FadeOut, false) == 1, "fades in to 1, holds")
    local prev, peaked, last = 0, false, 0
    for k = 0, 150 do
        local e = Plan.envelope(k * 0.01, false)
        assert(e >= 0 and e <= 1, "strength in 0..1")
        assert(math.abs(e - last) < 0.12, "no jump (calm, no flash): " .. k)
        last = e
        if k * 0.01 <= Plan.FadeIn then assert(e >= prev - 1e-9, "rises smoothly") else if e >= 0.999 then peaked = true end end
        prev = e
    end
    assert(peaked, "it reaches full strength")
    local fall = 1
    for k = 0, 60 do
        local e = Plan.envelope(Plan.Life - Plan.FadeOut + k * 0.01, false)
        assert(e <= fall + 1e-9, "falls smoothly")
        fall = e
    end
    assert(Plan.envelope(0, true) == 1 and Plan.envelope(0.7, true) == 1 and Plan.envelope(Plan.Life - 0.001, true) == 1, "still: a plain switch")
end
do
    local c = Plan.colour({1, 2, 3}, {4, 5, 6})
    assert(c[1] == 1 and Plan.colour(nil, {4, 5, 6})[1] == 4 and Plan.colour(nil, nil)[1] == 255, "colour: mutation, then tier, then the warm default")
    assert(Plan.colour({1}, {4, 5, 6})[1] == 4, "a malformed colour is ignored")
    local look = Plan.look("full", false)
    local o0, f0 = Plan.newTransparency(look, 0)
    local o1, f1 = Plan.newTransparency(look, 1)
    assert(o0 == 1 and f0 == 1 and math.abs(o1 - look.outline) < 1e-9 and math.abs(f1 - look.fill) < 1e-9, "a new rim goes from clear to the look")
    local ox, fx = Plan.newTransparency(look, 9)
    assert(ox == o1 and fx == f1, "strength is clamped")
    for _, base in {0, 0.2, 0.5, 0.9, 1} do
        for k = 0, 10 do
            local f = Plan.brightenFill(base, look, k / 10)
            assert(f >= 0 and f <= base + 1e-9, "brighten never darkens and never goes below 0")
        end
        assert(Plan.brightenFill(base, look, 0) == base, "strength 0 = the tier rim exactly as it was")
    end
    assert(Plan.brightenWhite(look, 0) == 0 and Plan.brightenWhite(look, 1) == look.whiten and Plan.brightenWhite(look, 5) == look.whiten, "outline whiten range")
end

-- 3. dome decision and look
for _, kind in {"aura", "mutation", "trail"} do
    for _, id in {"seismic", "dewdrop", "frost", "aurora", "x"} do
        for tier = 1, 6 do
            for _, reduced in {false, true} do
                for _, detail in {"full", "lite"} do
                    for _, mesh in {false, true} do
                        local want = R.wantsDome(kind, id, tier, reduced, detail, mesh)
                        local expect = mesh and not reduced and detail ~= "lite" and ((kind == "aura" and tier >= 4) or (kind == "mutation" and id == "seismic"))
                        assert(want == expect, kind .. " " .. id .. " tier " .. tier .. " reduced " .. tostring(reduced) .. " " .. detail .. " mesh " .. tostring(mesh))
                    end
                end
            end
        end
    end
end
assert(R.wantsDome("aura", nil, nil, false, "full", true) == false and R.wantsDome("mutation", nil, 3, false, "full", true) == false, "no tier / id = no dome")
assert(R.wantsDome("aura", "x", 4, false, nil, true) == true, "an unset detail is the full look")
do
    assert(R.DomeSeconds > 0.4 and R.DomeSeconds <= 1.2 and R.DomeGap >= 1 and R.DomeSize.from < R.DomeSize.to and R.DomeSize.to <= 8, "a short soft swell, a few studs")
    local g0, t0 = R.domeLook(0)
    local g1, t1 = R.domeLook(R.DomeSeconds)
    assert(g0 == 0 and g1 == 1 and t0 >= 0.55 and t0 <= 0.65 and t1 == 1, "starts small and soft, ends clear")
    local pg, pt = 0, 0
    for k = 0, 40 do
        local g, t = R.domeLook(k * R.DomeSeconds / 40)
        assert(g >= pg - 1e-9 and t >= pt - 1e-9 and t >= 0.6 - 1e-9 and t <= 1 + 1e-9, "grows and fades out monotonically")
        pg, pt = g, t
    end
end

-- 4. banner sweep plan
assert(RH.plan("full", false, "shiny").sweep == 1 and RH.plan("lite", false, "shiny").sweep == 0 and RH.plan("off", false, "shiny").sweep == 0, "sweep: Full only")
assert(RH.plan("full", true, "shiny").sweep == 0 and RH.plan("lite", true, "legendary").sweep == 0, "sweep: never with Reduce Motion")
assert(RH.plan("bogus", false, "shiny").sweep == 1, "an unknown level plays as Full")
assert(RH.plan("full", false, "mutation").pop == 2 and RH.plan("full", false, "mutation").banner, "pops and banner unchanged")
do
    assert(RH.SweepLife >= 0.5 and RH.SweepLife <= 1.5 and RH.SweepAlpha <= 0.5 and RH.SweepWidth > 0.1 and RH.SweepWidth <= 0.5, "a soft, short, partial-width band")
    local p0, a0 = RH.sweepAt(0)
    local p1, a1 = RH.sweepAt(RH.SweepLife)
    assert(p0 == 0 and a0 == 0 and p1 == 1 and a1 == 0, "starts and ends invisible at the two banner ends")
    local prevP, peak = 0, 0
    for k = 0, 60 do
        local p, a = RH.sweepAt(k * RH.SweepLife / 60)
        assert(p >= prevP - 1e-9 and a >= 0 and a <= RH.SweepAlpha + 1e-9, "left to right, never brighter than the cap")
        prevP, peak = p, math.max(peak, a)
    end
    assert(peak >= RH.SweepAlpha * 0.95, "it is visible at the peak")
    assert(select(2, RH.sweepAt(RH.SweepLife + 5)) == 0 and select(1, RH.sweepAt(-1)) == 0, "outside its life")
end
print("moment FX pure checks passed: Highlight budget, rim plan, dome decision, banner sweep plan")
'''

INST = r'''
-- A small instance model: parents, children, names, attributes, descendants. Enough to run the real client files.
local METHODS = {}
function METHODS.Destroy(self)
    rawset(self, "Destroyed", true)
    local p = rawget(self, "Parent")
    if p then for i, c in p.children do if c == self then table.remove(p.children, i) break end end end
    rawset(self, "Parent", nil)
end
function METHODS.IsA(self, c) return self.ClassName == c or (c == "BasePart" and self.ClassName == "Part") end
function METHODS.FindFirstChild(self, name, recursive)
    for _, c in self.children do
        if c.Name == name then return c end
        if recursive then local r = c:FindFirstChild(name, true) if r then return r end end
    end
    return nil
end
function METHODS.WaitForChild(self, name) return self:FindFirstChild(name) end
function METHODS.GetDescendants(self)
    local out = {}
    local function walk(n) for _, c in n.children do out[#out + 1] = c walk(c) end end
    walk(self)
    return out
end
function METHODS.IsDescendantOf(self, anc)
    local p = rawget(self, "Parent")
    while p do if p == anc then return true end p = rawget(p, "Parent") end
    return false
end
function METHODS.GetAttribute(self, k) return self.attrs[k] end
function METHODS.SetAttribute(self, k, v) self.attrs[k] = v end
function METHODS.Emit() end
function METHODS.Clear() end
function METHODS.Cross(self, o) return self end
local created = 0
local function inst(class)
    created += 1
    local t = {ClassName = class, children = {}, attrs = {}, Name = class, Order = created, Rotation = 0, Visible = true}
    setmetatable(t, {
        __index = function(_, k) return METHODS[k] end,
        __newindex = function(self, k, v)
            if k == "Parent" then
                local old = rawget(self, "Parent")
                if old then for i, c in old.children do if c == self then table.remove(old.children, i) break end end end
                rawset(self, "Parent", v)
                if v ~= nil then table.insert(v.children, self) end
            else rawset(self, k, v) end
        end,
    })
    return t
end
Instance = {new = inst}
local function color(r, g, b)
    local c = {R = r, G = g, B = b}
    function c.Lerp(self, o, a) return color(self.R + (o.R - self.R) * a, self.G + (o.G - self.G) * a, self.B + (o.B - self.B) * a) end
    return c
end
Color3 = {new = color, fromRGB = function(r, g, b) return color(r / 255, g / 255, b / 255) end}
Enum = setmetatable({}, {__index = function() return setmetatable({}, {__index = function(_, k) return k end}) end})
local V3 = {}
V3.__index = function(t, k) return V3[k] or METHODS[k] end
V3.__add = function(a, b) return setmetatable({X = a.X + b.X, Y = a.Y + b.Y, Z = a.Z + b.Z}, V3) end
V3.__mul = function(a, b) if type(b) == "number" then return setmetatable({X = a.X * b, Y = a.Y * b, Z = a.Z * b}, V3) end return setmetatable({X = a.X * b.X, Y = a.Y * b.Y, Z = a.Z * b.Z}, V3) end
Vector3 = {new = function(x, y, z) return setmetatable({X = x or 0, Y = y or 0, Z = z or 0}, V3) end}
Vector3.zero, Vector3.yAxis = Vector3.new(0, 0, 0), Vector3.new(0, 1, 0)
CFrame = {new = function(p) return {Position = p} end, fromMatrix = function(p) return {Position = p} end}
Vector2 = {new = function(x, y) return {X = x, Y = y} end, zero = {X = 0, Y = 0}}
UDim2 = {fromOffset = function(x, y) return {X = x, Y = y} end, fromScale = function(x, y) return {SX = x, SY = y} end, new = function(a, b, c, d) return {SX = a, OX = b, SY = c, OY = d} end}
UDim = {new = function(a, b) return {Scale = a, Offset = b} end}
NumberSequence = {new = function(x) return x end}
NumberSequenceKeypoint = {new = function(a, b) return {t = a, v = b} end}
NumberRange = {new = function(a, b) return {Min = a, Max = b or a} end}
ColorSequence = {new = function(x) return x end}
ColorSequenceKeypoint = {new = function(a, b) return {t = a, c = b} end}
NOW = 0
do
    local realOs = os
    os = setmetatable({clock = function() return NOW end}, {__index = realOs})
end
MODE, CALM = "full", false
local HEART = {}
local function heartbeat() return {Connect = function(_, fn)
    local c = {fn = fn, on = true}
    HEART[#HEART + 1] = c
    return {Disconnect = function() c.on = false end}
end} end
local function tick(dt) NOW += dt for _, c in HEART do if c.on then c.fn(dt) end end end
local function beating() local n = 0 for _, c in HEART do if c.on then n += 1 end end return n end
workspace = inst("Workspace")
'''

RIM = r'''
--@@MODS
MODS.SettingsModel = {get = function() return {effects = MODE, calm = CALM} end}
function MODS.WaitForChild(self, name) return self[name] end
local Rim = (function()
local require = function(x) return x end
local game = {GetService = function(_, name)
    if name == "RunService" then return {Heartbeat = heartbeat()} end
    return {WaitForChild = function() return MODS end}
end}
--@@RIMSRC
end)()
local Plan = MODS.MomentRimPlan

local function dino(withTierRim)
    local character = inst("Model")
    character.Name = "Character"
    character.Parent = workspace
    local visual = inst("Model")
    visual.Name = "LocalMeshVisual"
    visual.Parent = character
    local tier
    if withTierRim then
        tier = inst("Highlight")
        tier.Name = "LPTierRim"
        tier.FillTransparency, tier.OutlineTransparency = 0.85, 0
        tier.FillColor, tier.OutlineColor = Color3.fromRGB(255, 206, 92), Color3.fromRGB(255, 230, 150)
        tier.Parent = visual
    end
    return character, visual, tier
end
local function highlights() local n = 0 for _, d in workspace:GetDescendants() do if d.ClassName == "Highlight" then n += 1 end end return n end
local function moment(visual) return visual:FindFirstChild("MomentRim") end
local function cleanWorld() for i = #workspace.children, 1, -1 do workspace.children[i]:Destroy() end end
local function others(n) -- Highlights of the rest of the world (food glows, other tier rims)
    local folder = inst("Folder")
    folder.Parent = workspace
    for i = 1, n do local h = inst("Highlight") h.Name = "Other" h.Parent = folder end
end
local function reset(mode, calm)
    cleanWorld()
    MODE, CALM = mode or "full", calm or false
    NOW += 10 -- clear of the 1.5 s gap
    Rim.stop()
end
local function runLife(visual, onTick)
    local steps = 0
    while Rim.isActive() and steps < 200 do
        tick(0.05)
        steps += 1
        if onTick then onTick(steps * 0.05) end
    end
    return steps * 0.05
end
local SEISMIC = Color3.fromRGB(210, 173, 113)

-- A. Full, no tier rim: ONE Highlight in the mutation colour, fades in and out, gone after 1.5 s.
do
    reset("full", false)
    local character, visual = dino(false)
    local before = highlights()
    assert(Rim.play(character, {mutationId = "seismic"}) == true and Rim.isActive(), "a moment starts")
    local rim = moment(visual)
    assert(rim and rim.ClassName == "Highlight" and rim.Adornee == visual and rim.Parent == visual and highlights() == before + 1, "ONE Highlight on the own dino")
    assert(math.abs(rim.FillColor.R - SEISMIC.R) < 1e-6 and math.abs(rim.FillColor.G - SEISMIC.G) < 1e-6 and math.abs(rim.FillColor.B - SEISMIC.B) < 1e-6, "mutation colour")
    assert(rim.OutlineTransparency == 1 and rim.FillTransparency == 1, "it starts clear (no pop)")
    local minOut, minFill, last, rising, peakAt = 1, 1, 1, true, nil
    local life = runLife(visual, function(t)
        if not rim.Destroyed then
            minOut, minFill = math.min(minOut, rim.OutlineTransparency), math.min(minFill, rim.FillTransparency)
            assert(math.abs(rim.OutlineTransparency - last) < 0.35, "no flash: " .. t)
            last = rim.OutlineTransparency
            assert(highlights() <= before + 1, "never a second Highlight")
        end
    end)
    assert(math.abs(minOut - Plan.Looks.full.outline) < 1e-6 and math.abs(minFill - Plan.Looks.full.fill) < 1e-6, "it reaches the Full look")
    assert(life >= 1.4 and life <= 1.6, "about 1.5 s: " .. life)
    assert(rim.Destroyed and highlights() == before and not Rim.isActive() and beating() == 0, "the Highlight is destroyed and the Heartbeat released")
end

-- B. Lite: outline only and fainter. Off: nothing at all.
do
    reset("lite", false)
    local character, visual = dino(false)
    assert(Rim.play(character, {mutationId = "frost"}) == true)
    local rim, minOut, minFill = moment(visual), 1, 1
    runLife(visual, function() if not rim.Destroyed then minOut, minFill = math.min(minOut, rim.OutlineTransparency), math.min(minFill, rim.FillTransparency) end end)
    assert(math.abs(minOut - Plan.Looks.lite.outline) < 1e-6 and minFill == 1, "Lite: fainter outline, no fill")
    reset("off", false)
    local c2, v2 = dino(false)
    assert(Rim.play(c2, {mutationId = "seismic"}) == false and moment(v2) == nil and highlights() == 0 and not Rim.isActive() and beating() == 0, "Off: no Highlight, no loop")
    reset("off", false)
    local c3, v3 = dino(true)
    assert(Rim.play(c3, {}) == false and highlights() == 1 and v3:FindFirstChild("LPTierRim").FillTransparency == 0.85, "Off: a tier rim is left alone too")
end

-- C. Reduce Motion: a still rim (one value the whole time, no fade) and no pulse on a tier rim.
for _, mode in {"full", "lite"} do
    reset(mode, true)
    local character, visual = dino(false)
    assert(Rim.play(character, {mutationId = "ember"}) == true)
    local rim, seen, n = moment(visual), {}, 0
    runLife(visual, function()
        if not rim.Destroyed then
            seen[rim.OutlineTransparency .. "/" .. rim.FillTransparency] = true
            n += 1
        end
    end)
    local kinds = 0 for _ in seen do kinds += 1 end
    assert(kinds == 1 and n >= 25, mode .. " Reduce Motion: the rim holds still (" .. kinds .. " looks)")
    assert(rim.Destroyed and not Rim.isActive(), "and it is gone after 1.5 s")
    reset(mode, true)
    local c2, v2, tier = dino(true)
    assert(Rim.play(c2, {}) == false and not Rim.isActive() and highlights() == 1 and tier.FillTransparency == 0.85 and moment(v2) == nil, mode .. " Reduce Motion: no pulse on the tier rim, no second Highlight")
end

-- D. A fused-tier rim is brightened and handed back; never a second Highlight.
for _, mode in {"full", "lite"} do
    reset(mode, false)
    local character, visual, tier = dino(true)
    local baseOutline = tier.OutlineColor
    assert(Rim.play(character, {mutationId = "seismic"}) == true and Rim.isActive(), "brighten starts")
    assert(moment(visual) == nil and highlights() == 1, "no second Highlight beside the tier rim")
    local minFill, maxWhite = 1, 0
    runLife(visual, function()
        assert(highlights() == 1 and moment(visual) == nil, "still one Highlight")
        minFill = math.min(minFill, tier.FillTransparency)
        maxWhite = math.max(maxWhite, tier.OutlineColor.B - baseOutline.B)
    end)
    local look = Plan.Looks[mode]
    assert(math.abs(minFill - (0.85 - look.brighten)) < 1e-6, mode .. ": the tier rim brightens by the look (" .. minFill .. ")")
    assert(maxWhite > 0, "the outline moves toward white")
    assert(tier.FillTransparency == 0.85 and tier.OutlineColor.R == baseOutline.R and tier.OutlineColor.G == baseOutline.G and tier.OutlineColor.B == baseOutline.B, "handed back exactly")
    assert(not tier.Destroyed and highlights() == 1 and beating() == 0, "the tier rim survives; the loop is released")
end

-- E. The global Highlight budget: refused at 30 alive (one below the engine cap), allowed at 29; a tier rim still brightens (no new Highlight).
do
    reset("full", false)
    others(30)
    local character, visual = dino(false)
    assert(Rim.play(character, {}) == false and moment(visual) == nil and highlights() == 30 and not Rim.isActive(), "30 Highlights alive: refused")
    reset("full", false)
    others(29)
    local c2, v2 = dino(false)
    assert(Rim.play(c2, {}) == true and highlights() == 30, "29 alive: allowed, ends at the soft cap")
    runLife(v2)
    reset("lite", false)
    others(30)
    local c3, v3 = dino(false)
    assert(Rim.play(c3, {}) == false, "Lite obeys the same cap")
    reset("full", false)
    others(30)
    local c4, v4, tier = dino(true)
    assert(Rim.play(c4, {}) == true and highlights() == 31, "a tier rim brightens even when the budget is full (no new Highlight)")
    runLife(v4)
end

-- F. Gap and replacement.
do
    reset("full", false)
    local character, visual = dino(false)
    assert(Rim.play(character, {mutationId = "seismic"}) == true)
    tick(0.4)
    assert(Rim.play(character, {mutationId = "ember"}) == false, "a repeat inside the 1.5 s gap is ignored")
    NOW += 1.2 -- the gap is over but the loop has not run: the old moment is still active
    assert(Rim.isActive() and Rim.play(character, {mutationId = "ember"}) == true, "after the gap a new moment replaces it")
    local mine = 0 for _, c in visual.children do if c.Name == "MomentRim" then mine += 1 end end
    assert(mine == 1 and highlights() == 1, "never two of our Highlights")
    runLife(visual)
    assert(highlights() == 0 and beating() == 0)
end

-- G. A rim that vanishes mid-way (a tier rim rebuilt, the dino removed) ends cleanly.
do
    reset("full", false)
    local character, visual, tier = dino(true)
    assert(Rim.play(character, {}) == true)
    tick(0.3)
    tier:Destroy()
    tick(0.05)
    assert(not Rim.isActive() and beating() == 0, "a destroyed tier rim ends the moment")
    reset("full", false)
    local c2, v2 = dino(false)
    assert(Rim.play(c2, {}) == true)
    tick(0.3)
    c2:Destroy()
    moment(v2).Parent = nil
    tick(0.05)
    assert(not Rim.isActive() and beating() == 0, "a rim that left the world ends the moment")
    assert(Rim.play(nil, {}) == false, "no character, no rim")
    local orphan = inst("Model")
    assert(Rim.play(orphan, {}) == false, "a character outside the world gets nothing")
end

-- H. Colour priority: unknown mutation -> fused tier tint -> warm default.
do
    reset("full", false)
    local character, visual = dino(false)
    visual:SetAttribute("LPTier", "emerald")
    assert(Rim.play(character, {mutationId = "nope"}) == true)
    local tint = Color3.fromRGB(60, 220, 140)
    assert(math.abs(moment(visual).FillColor.G - tint.G) < 1e-6, "the tier tint when no mutation colour")
    runLife(visual)
    reset("full", false)
    local c2, v2 = dino(false)
    assert(Rim.play(c2, nil) == true)
    local warm = Color3.fromRGB(255, 236, 170)
    assert(math.abs(moment(v2).FillColor.B - warm.B) < 1e-6, "the warm default otherwise")
    runLife(v2)
end
print("MomentRim client checks passed: one Highlight, fade in/out, tier rim brightened not stacked, Full / Lite / Off, Reduce Motion, Highlight budget, gap, clean ends")
'''

RARE = r'''
--@@MODS
function MODS.WaitForChild(self, name) return self[name] end
local plays = {}
local rimStub = {play = function(character, info) plays[#plays + 1] = {character = character, info = info} return true end}
local function scenario(effects, calm, bound, own)
    local Assets = MODS.EffectAssets
    Assets.Requested.shaftGradient.id = if bound then "rbxassetid://812345679" else ""
    Assets.Requested.starPop.id = ""
    HEART = {}
    plays = {}
    local handler
    local delayed = {}
    MODS.SettingsModel = {get = function() return {effects = effects, calm = calm} end}
    MODS.Sfx = {play = function() end}
    MODS.HatchTimeline = {durations = function() return {revealAt = 0.5} end}
    local remote = {OnClientEvent = {Connect = function(_, fn) handler = fn return {Disconnect = function() end} end}}
    local screen = nil
    local player = {Character = "OWN_CHARACTER", WaitForChild = function() return inst("PlayerGui") end}
    Instance = {new = function(class)
        local t = inst(class)
        if class == "ScreenGui" then rawset(t, "AbsoluteSize", {X = 1000, Y = 800}) screen = t end
        return t
    end}
    local env = {GetService = function(_, name)
        if name == "Players" then return {LocalPlayer = player}
        elseif name == "RunService" then return {Heartbeat = heartbeat()} end
        return {WaitForChild = function(_, n) if n == "BeDinoRemotes" then return {WaitForChild = function() return remote end} end return MODS end}
    end}
    local task = {delay = function(t, fn) delayed[#delayed + 1] = {t = t, fn = fn} end}
    local script = {Parent = {WaitForChild = function() return rimStub end}}
    ;(function()
        local game, task, require, script = env, task, function(x) return x end, script
--@@RARESRC
    end)()
    return handler, delayed, function() return screen end
end
local function labelsOf(screen) local list = {} for _, c in screen.children do if c.ClassName == "TextLabel" then list[#list + 1] = c end end return list end
local function bands(label) local list = {} for _, c in label.children do if c.ClassName == "ImageLabel" then list[#list + 1] = c end end return list end
local function runOwn(effects, calm, bound, kind, extra)
    local handler, delayed, getScreen = scenario(effects, calm, bound)
    local data = {k = "me", text = "You hatched a Shiny Rex!", kind = kind or "shiny", rarity = 5}
    for k, v in extra or {} do data[k] = v end
    handler(data)
    for _, d in delayed do if d.t == 0.5 then d.fn() end end
    local screen = getScreen()
    return screen, labelsOf(screen)[1]
end

-- A. EMPTY shaftGradient: exactly today's banner, never a sweep, for every setting.
for _, effects in {"full", "lite", "off"} do
    for _, calm in {false, true} do
        local screen, label = runOwn(effects, calm, false)
        assert(label and #bands(label) == 0 and not label.ClipsDescendants and beating() <= 1, "empty slot: no sweep (" .. effects .. " calm " .. tostring(calm) .. ")")
    end
end

-- B. BOUND: ONE sweep, only on the own banner, only Full without Reduce Motion.
for _, case in {{"full", false, 1}, {"lite", false, 0}, {"off", false, 0}, {"full", true, 0}, {"lite", true, 0}, {"off", true, 0}} do
    local effects, calm, want = case[1], case[2], case[3]
    local screen, label = runOwn(effects, calm, true)
    local list = bands(label)
    assert(#list == want, effects .. " calm " .. tostring(calm) .. ": " .. want .. " sweeps, got " .. #list)
    if want == 1 then
        local band = list[1]
        local R = MODS.RareHatch
        assert(band.Image == "rbxassetid://812345679" and band.Rotation == 90 and label.ClipsDescendants, "the shaftGradient render, on its side, clipped by the banner")
        assert(band.Size.Y == 420 * R.SweepWidth and band.Size.X == 56 * 1.4, "band size follows the banner")
        local grad = band.children[1]
        assert(grad and grad.ClassName == "UIGradient" and grad.Transparency[1].v == 1 and grad.Transparency[2].v == 0, "soft edges through a UIGradient")
        assert(beating() >= 1, "driven by a Heartbeat connection")
        local lastX, peak, shown = -1e9, 1, false
        for step = 1, 40 do
            tick(0.05)
            if not band.Destroyed then
                assert(band.Position.X >= lastX - 1e-9, "left to right")
                lastX = band.Position.X
                assert(band.Position.Y == 28, "centred in the banner")
                peak = math.min(peak, band.ImageTransparency)
                assert(band.ImageTransparency >= 1 - R.SweepAlpha - 1e-9, "never brighter than the cap")
                shown = true
            end
        end
        assert(shown and peak < 0.65, "it was visible")
        assert(lastX > 400 * 0.5, "it crossed the banner")
        assert(band.Destroyed and #bands(label) == 0, "gone after its life")
        for step = 1, 80 do tick(0.05) end
        assert(beating() == 0, "every Heartbeat connection is released afterwards")
    end
end

-- C. Another player's rare banner never sweeps, even at Full with the slot bound.
do
    local handler, delayed, getScreen = scenario("full", false, true)
    handler({k = "all", text = "Sam hatched a Shiny Rex!", kind = "shiny"})
    local screen = getScreen()
    local labels = labelsOf(screen)
    assert(#labels == 1 and #bands(labels[1]) == 0 and not labels[1].ClipsDescendants, "someone else's banner: no sweep")
    assert(#plays == 0, "and no rim")
    assert(beating() == 0, "and no loop")
    handler({k = "me", text = "You hatched a Shiny Rex!", kind = "shiny", rarity = 5})
    for _, d in delayed do if d.t == 0.5 then d.fn() end end
    local all = labelsOf(screen)
    assert(#all == 2 and #bands(all[1]) == 0 and #bands(all[2]) == 1, "only the own banner got the sweep")
end

-- D. A mutation hatch asks MomentRim for the own-dino rim (its own Full / Lite / Off rules decide what is drawn); other rares do not.
do
    runOwn("full", false, false, "mutation", {mutation = true, mutationId = "seismic"})
    assert(#plays == 1 and plays[1].character == "OWN_CHARACTER" and plays[1].info.mutationId == "seismic", "a mutation hatch lights the own dino")
    runOwn("full", false, false, "shiny", {mutation = true, mutationId = "frost"})
    assert(#plays == 1 and plays[1].info.mutationId == "frost", "a Shiny that also carries a mutation lights it too")
    runOwn("full", false, false, "shiny")
    assert(#plays == 0, "a plain Shiny does not")
    runOwn("full", false, false, "legendary")
    assert(#plays == 0, "a plain Legendary does not")
    runOwn("lite", true, true, "mutation", {mutation = true, mutationId = "x" .. string.rep("y", 40)})
    assert(#plays == 1 and plays[1].info.mutationId == nil, "an over-long id is dropped, the call is still made")
end
MODS.EffectAssets.Requested.shaftGradient.id = ""
print("RareHatchClient sweep checks passed: empty slot = today's banner, one sweep on the OWN banner at Full only, none for others / Lite / Off / Reduce Motion, mutation hatch asks for the rim")
'''

RIG = r'''
--@@MODS
MODS.WaitForChild = function(self, n) return self[n] end
local Slots, Assets, Recipes, Lod, Look = MODS.AssetSlots, MODS.EffectAssets, MODS.FxRecipes, MODS.EffectsLod, MODS.MutationLook
local Rig = (function()
local require = function(x) return x end
local game = {GetService = function(_, name)
    if name == "UserInputService" then return {TouchEnabled = true, MouseEnabled = false} end
    return {WaitForChild = function() return MODS end}
end}
--@@RIGSRC
end)()
workspace.CurrentCamera = {ViewportSize = {X = 400, Y = 800}}

local function newRoot()
    local root = inst("Part")
    root.Name = "HumanoidRootPart"
    root.Position = Vector3.new(0, 5, 0)
    root.CFrame = CFrame.new(root.Position)
    root.AssemblyLinearVelocity = Vector3.zero
    root.Parent = workspace
    return root
end
local function domes()
    local folder = workspace:FindFirstChild("LocalDinoFX")
    local list = {}
    if folder then for _, c in folder.children do if c.Name == "FxDome" then list[#list + 1] = c end end end
    return list
end
local function fxParts() local folder = workspace:FindFirstChild("LocalDinoFX") return if folder then #folder.children else 0 end
local function reset()
    for i = #workspace.children, 1, -1 do workspace.children[i]:Destroy() end
    Slots.Meshes.shock_dome_mesh, Slots.Meshes.aura_shell_mesh = "", ""
    Assets.Requested.domeGradient.id, Assets.Requested.shellEdge.id = "", ""
    NOW += 100
end
local AURA = {id = "testaura", rarity = "Epic", color = {255, 120, 80}}
local function aura(rarity) return {id = "testaura", rarity = rarity, color = {255, 120, 80}} end
local function attach(kind, item, opts)
    local rig = Rig.attach(newRoot(), kind, item, opts)
    rig.budgetCost = {}
    return rig
end
local DOME_ID = "rbxassetid://912345678"
local function step(rig, n) for i = 1, n do rig:update(1, os.clock(), false) NOW += 1 / 30 end end

-- A. EMPTY mesh slot: nothing is added anywhere (the same parts as a bound run minus the dome).
do
    reset()
    for _, case in {{"mutation", Look.get("seismic")}, {"aura", aura("Legendary")}} do
        reset()
        local rig = attach(case[1], case[2], {device = "desktop", detail = "full"})
        local empty = fxParts()
        assert(#domes() == 0 and rig.dome == nil, case[1] .. ": empty slot = no dome")
        rig:destroy()
        reset()
        Slots.Meshes.shock_dome_mesh = DOME_ID
        local bound = attach(case[1], case[2], {device = "desktop", detail = "full"})
        assert(#domes() == 1 and fxParts() == empty + 1, case[1] .. ": a bound slot adds exactly ONE part")
        bound:destroy()
    end
end

-- B. WHICH moments get a dome (mesh bound).
do
    reset()
    Slots.Meshes.shock_dome_mesh = DOME_ID
    local function wants(kind, item, opts)
        NOW += 10
        local rig = attach(kind, item, opts)
        local got = #domes()
        rig:destroy()
        for i = #workspace.children, 1, -1 do workspace.children[i]:Destroy() end
        return got == 1
    end
    assert(wants("mutation", Look.get("seismic"), {device = "desktop", detail = "full"}), "Seismic reveal: yes")
    assert(wants("mutation", Look.get("seismic"), {device = "desktop"}), "an unset detail is the full look")
    for _, id in {"dewdrop", "charged", "frost", "ember", "aurora", "bloodmoon"} do assert(not wants("mutation", Look.get(id), {device = "desktop", detail = "full"}), id .. ": no dome") end
    for _, rarity in {"Epic", "Legendary", "Mythic"} do assert(wants("aura", aura(rarity), {device = "desktop", detail = "full"}), rarity .. " aura equip: yes") end
    for _, rarity in {"Common", "Uncommon", "Rare"} do assert(not wants("aura", aura(rarity), {device = "desktop", detail = "full"}), rarity .. " aura: no dome") end
    assert(not wants("trail", {id = "t", rarity = "Legendary", color = {200, 200, 255}}, {device = "desktop", detail = "full"}), "trails never")
    assert(not wants("mutation", Look.get("seismic"), {device = "desktop", detail = "lite"}) and not wants("aura", aura("Mythic"), {device = "desktop", detail = "lite"}), "Lite: none")
    assert(not wants("mutation", Look.get("seismic"), {device = "desktop", detail = "full", reduce = true}) and not wants("aura", aura("Mythic"), {device = "desktop", detail = "full", reduce = true}), "Reduce Motion: none")
end

-- C. The look: texture only for a real domeGradient, a swell that fades, removed after DomeSeconds.
do
    reset()
    Slots.Meshes.shock_dome_mesh = DOME_ID
    local rig = attach("mutation", Look.get("seismic"), {device = "desktop", detail = "full"})
    local dome = domes()[1]
    local mesh
    for _, c in dome.children do if c.ClassName == "SpecialMesh" then mesh = c end end
    assert(mesh and mesh.MeshId == DOME_ID and mesh.TextureId == nil, "the mesh is bound, the texture is not while domeGradient is empty")
    assert(dome.Anchored and not dome.CanCollide and not dome.CanQuery and not dome.CanTouch and not dome.CastShadow and dome.Size.X == 4, "an anchored, non-colliding, shadowless carrier part")
    assert(dome.Transparency >= 0.55 and dome.Transparency <= 0.65, "soft at the start")
    local lastScale, lastClear, seen = 0, 0, 0
    for k = 1, 60 do
        rig:update(1, os.clock(), false)
        if rig.dome then
            seen += 1
            assert(mesh.Scale.X >= lastScale - 1e-9 and dome.Transparency >= lastClear - 1e-9, "it swells and fades monotonically")
            assert(mesh.Scale.X * 4 <= Recipes.DomeSize.to + 1e-6 and dome.Transparency >= 0.6 - 1e-9 and dome.Transparency <= 1, "inside its size and opacity limits")
            lastScale, lastClear = mesh.Scale.X, dome.Transparency
        end
    end
    assert(seen >= 24 and seen <= 30, "about DomeSeconds at 30 Hz: " .. seen)
    assert(rig.dome == nil and dome.Destroyed and #domes() == 0, "the dome is removed after its life")
    rig:destroy()

    reset()
    Slots.Meshes.shock_dome_mesh = DOME_ID
    Assets.Requested.domeGradient.id = "rbxassetid://912345679"
    local rig2 = attach("mutation", Look.get("seismic"), {device = "desktop", detail = "full"})
    local m2
    for _, c in domes()[1].children do if c.ClassName == "SpecialMesh" then m2 = c end end
    assert(m2.TextureId == "rbxassetid://912345679" and m2.VertexColor and m2.VertexColor.X > 0, "a real domeGradient is bound and tinted by vertex colour")
    rig2:destroy()
    reset()
    Assets.Requested.domeGradient.id = "rbxassetid://912345679" -- texture alone (mesh slot empty) still draws nothing
    local rig3 = attach("mutation", Look.get("seismic"), {device = "desktop", detail = "full"})
    assert(#domes() == 0, "the texture alone never makes a dome")
    rig3:destroy()
    reset()
    Slots.Meshes.shock_dome_mesh = DOME_ID
    local rig4 = attach("aura", aura("Epic"), {device = "desktop", detail = "full"})
    assert(#domes() == 1)
    rig4:destroy()
    assert(#domes() == 0, "destroying the rig removes a running dome")
end

-- D. Scene caps and the gap: phone 1, tablet 1, desktop 2, two seconds apart.
do
    for _, case in {{"phone", 1}, {"tablet", 1}, {"desktop", 2}} do
        local device, cap = case[1], case[2]
        reset()
        Slots.Meshes.shock_dome_mesh = DOME_ID
        local made, rigs = 0, {}
        local first = attach("mutation", Look.get("seismic"), {device = device, detail = "full"})
        rigs[1] = first
        local same = attach("mutation", Look.get("seismic"), {device = device, detail = "full"})
        assert(#domes() == 1, device .. ": a second dome in the same instant is held back by the gap")
        same:destroy()
        for i = 2, 4 do
            NOW += 2.1
            rigs[i] = attach("mutation", Look.get("seismic"), {device = device, detail = "full"})
        end
        local alive = #domes()
        assert(alive == cap, device .. ": at most " .. cap .. " domes alive at once, got " .. alive)
        -- a dome that ended frees its slot
        for _, rig in rigs do for k = 1, 40 do rig:update(1, os.clock(), false) end end
        assert(#domes() == 0, device .. ": all domes ended")
        NOW += 2.1
        local again = attach("mutation", Look.get("seismic"), {device = device, detail = "full"})
        assert(#domes() == 1, device .. ": the slot is free again")
        again:destroy()
        for _, rig in rigs do rig:destroy() end
        assert(#domes() == 0)
    end
end
Slots.Meshes.shock_dome_mesh, Assets.Requested.domeGradient.id = "", ""
print("FxRig dome checks passed: empty mesh slot = nothing added, Seismic reveal + Epic+ aura equip only, Full only, no Reduce Motion, swell and remove, caps phone 1 / tablet 1 / desktop 2, 2 s gap")
'''


def pure_script():
    out = 'local Lod = ' + module('src/shared/EffectsLod.luau') + '\n'
    out += 'local Plan = ' + module('src/shared/MomentRimPlan.luau') + '\n'
    out += 'local R = ' + module('src/shared/FxRecipes.luau') + '\n'
    out += 'local RH = ' + module('src/shared/RareHatch.luau') + '\n'
    return out + PURE


def rim_script():
    mods = load_mods([('MomentRimPlan', 'src/shared/MomentRimPlan.luau', None), ('EffectsLod', 'src/shared/EffectsLod.luau', None),
                      ('MutationLook', 'src/shared/MutationLook.luau', None), ('LowPolyTier', 'src/shared/LowPolyTier.luau', None)])
    return INST + RIM.replace('--@@MODS', mods).replace('--@@RIMSRC', src('src/client/MomentRim.luau'))


def rare_script():
    mods = load_mods([('RareHatch', 'src/shared/RareHatch.luau', None), ('EffectAssets', 'src/shared/EffectAssets.luau', None)])
    return INST + RARE.replace('--@@MODS', mods).replace('--@@RARESRC', src('src/client/RareHatchClient.client.luau'))


def rig_script():
    mods = load_mods([('FxRecipes', 'src/shared/FxRecipes.luau', None), ('EffectAssets', 'src/shared/EffectAssets.luau', None),
                      ('AssetSlots', 'src/shared/AssetSlots.luau', None), ('EffectsLod', 'src/shared/EffectsLod.luau', None),
                      ('MutationLook', 'src/shared/MutationLook.luau', None), ('PhoneGuards', 'src/shared/PhoneGuards.luau', None)])
    return INST + RIG.replace('--@@MODS', mods).replace('--@@RIGSRC', src('src/client/FxRig.luau'))


def scan():
    rig = src('src/client/FxRig.luau')
    for needle in ['Recipes.wantsDome(kind, resolved.id, resolved.tier, resolved.reduced, opts.detail, Slots.mesh("shock_dome_mesh") ~= nil)',
                   'Lod.domeFits(device, liveDomes)', 'Recipes.DomeGap', 'Recipes.domeLook(self.domeAge)', 'Assets.isReal("domeGradient")',
                   'self:_endDome()']:
        assert needle in rig, 'FxRig must contain ' + needle
    rare = src('src/client/RareHatchClient.client.luau')
    for needle in ['Assets.isRealUi("shaftGradient")', 'plan.sweep > 0', 'Rare.sweepAt(s.age)', 'MomentRim.play']:
        assert needle in rare, 'RareHatchClient must contain ' + needle
    # the sweep call sits inside the OWN celebration only: the "all" branch calls banner() and nothing else
    assert re.search(r'elseif data\.k == "all" then banner\(data\.text, false\) end', rare), 'the others\' banner path must stay a plain banner'
    assert rare.count('sweep(label, width, height)') == 1, 'exactly one sweep call site'
    cosmetic = src('src/client/CosmeticVisuals.client.luau')
    for needle in ['MomentRim.play', 'lastOwnMutation']:
        assert needle in cosmetic, 'CosmeticVisuals must contain ' + needle
    assert 'if own then' in cosmetic and cosmetic.index('MomentRim.play') > cosmetic.index('if own then'), 'the rim is for the OWN dino only'
    mr = src('src/client/MomentRim.luau')
    for needle in ['Lod.rimFits(effects, liveHighlights())', 'Plan.TierRimName', 'Plan.mode(effects, calm, tierRim ~= nil)', 'finish() -- a new moment replaces']:
        assert needle in mr, 'MomentRim must contain ' + needle
    assert mr.count('Instance.new("Highlight")') == 1, 'MomentRim makes at most ONE Highlight'
    for path in ['src/client/MomentRim.luau', 'src/shared/MomentRimPlan.luau', 'src/client/FxRig.luau', 'src/client/RareHatchClient.client.luau', 'src/shared/RareHatch.luau',
                 'src/shared/FxRecipes.luau', 'src/shared/EffectsLod.luau']:
        assert not re.search(r'rbxassetid://\d+', src(path)), path + ' must not contain asset ids'
    slots = src('src/shared/AssetSlots.luau')
    assert re.search(r'shock_dome_mesh = "",', slots), 'shock_dome_mesh must stay empty until uploaded'
    ea = src('src/shared/EffectAssets.luau')
    for key in ['domeGradient', 'shaftGradient']:
        m = re.search(key + r' = \{id = "(rbxassetid://\d+)?", fallback', ea)
        assert m, key + ' slot must be empty or one valid rbxassetid'
        if m.group(1):  # bound after the 2026-10-17 batch upload: the id must be a registered docs/77 row, never invented
            assert m.group(1).split('//')[1] in src('docs/77-asset-registry.md'), key + ' bound id is not in the asset registry'
    print('Source scan passed: moment FX wired to the pure plans, sweep only on the own banner, one Highlight, no invented asset ids, slots empty')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    scan()
    code = 0
    with tempfile.TemporaryDirectory() as d:
        for name, text in (('pure.luau', pure_script()), ('rim.luau', rim_script()), ('rare.luau', rare_script()), ('rig.luau', rig_script())):
            path = Path(d) / name
            path.write_text(text, encoding='utf-8')
            result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
            print(result.stdout, end='')
            print(result.stderr, end='')
            code = code or result.returncode
    raise SystemExit(code)
