"""BD-430 / BD-431 (docs/123 s3): offline audit of the readers that wear the anime FX P0 / P1 renders. The textures and meshes themselves are
checked by tools/verify_fx_textures.py; this file checks the CODE that reads them, with the real Luau modules:

  1. EffectAssets: the new keys exist with EMPTY ids, flameTongue / starPop are 512 px 4x4 OneShot sheets (128 px cells), a bound id is used.
  2. FxRecipes.wantsShell / shellFade (pure): aura shell from Epic up, mutation shell for its reveal only, never in the lite look, never with
     Reduce Motion, never without the real mesh; the shell fades in and (mutation) out.
  3. HatchFxPlan.shaft / shaftLook (pure): Epic and up, Full look only, never with Reduce Motion, inside the device sprite cap, soft and bounded.
  4. RareHatch.plan().pop: two star pops at Full, one at Lite, none at Off or Calm.
  5. The REAL client/HatchFx.luau on stubbed Roblox instances: an empty shaftGradient slot builds exactly today's sprites; a bound one adds ONE
     shaft sprite behind the bloom; Lite / Off / Reduce Motion / failed eggs / low tiers show none; visible sprites never exceed the cap.
  6. The REAL client/RareHatchClient.client.luau: an empty starPop slot draws no pop; a bound one flanks the own banner with star pops that
     play the 16-cell flipbook once (Lite 1, Off and Calm 0), stay on screen, are gone after their life, and never appear for the others' banner.
  7. Source scan: FxRig uses FxRecipes.wantsShell / shellFade, the shell texture is bound only for a real shellEdge, no asset ids are invented.
Drawing itself is Studio-only; nothing here claims a Studio check."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def src(path, subs=None):
    text = (ROOT / path).read_text(encoding='utf-8')
    for a, b in (subs or {}).items():
        text = text.replace(a, b)
    return text


def module(path, subs=None):
    return '(function()\n' + src(path, subs) + '\nend)()'


PURE = r'''
-- 1. EffectAssets
-- 2026-10-17: the lead bound the uploaded ids. The slot may be empty OR one valid registered id; the EMPTY-state checks below
-- still run (ids are cleared for them and restored at the end, where the bound state is checked too).
local BOUND = {}
for _, key in {"flameTongue", "starPop", "domeGradient", "speedStreaks", "shaftGradient", "shellEdge"} do
    local req = A.Requested[key]
    assert(req and (req.id == "" or A.isValid(req.id)), key .. " exists with an empty or valid id (never an invented one)")
    BOUND[key] = req.id
    req.id = ""
    assert(not A.isReal(key) and A.resolve(key) == A.Builtin[req.fallback], key .. " empty resolves to its built-in sprite")
end
for _, key in {"flameTongue", "starPop"} do
    assert(A.Sheets[key].size == 512 and A.Sheets[key].grid == 4 and A.FlipbookMode[key] == "OneShot", key .. " is a 512 px 4x4 OneShot sheet")
    assert(not A.isSheet(key) and A.cellRect(key, 3) == nil, key .. " empty: not a sheet yet")
end
A.Requested.starPop.id = "rbxassetid://812345678"
assert(A.isSheet("starPop") and A.isRealUi("starPop") and A.resolve("starPop") == "rbxassetid://812345678", "a bound starPop is used")
do
    local x, y, px = A.cellRect("starPop", 6)
    assert(px == 128 and x == 128 and y == 128, "starPop cell 6 is 128 px at (128,128)")
    local seen = {}
    for k = 0, 20 do seen[A.frameAt("starPop", k / 20, k * 0.05, 1)] = true end
    local n = 0 for c in seen do assert(c >= 1 and c <= 16) n += 1 end
    assert(n >= 14, "OneShot plays (nearly) every cell over one life: " .. n)
    assert(A.frameAt("starPop", 0, 0, 1) == 1 and A.frameAt("starPop", 1, 1, 1) == 16, "first and last cell")
end
A.Requested.starPop.id = ""
A.Requested.shaftGradient.id = "rbxassetid://812345679"
assert(A.isRealUi("shaftGradient") and not A.isSheet("shaftGradient") and A.cellRect("shaftGradient", 1) == nil, "shaftGradient is a single image")
A.Requested.shaftGradient.id = ""

-- 2. shell decision
for _, kind in {"aura", "mutation", "trail"} do
    for tier = 1, 6 do
        for _, reduced in {false, true} do
            for _, detail in {"full", "lite"} do
                for _, mesh in {false, true} do
                    local want = R.wantsShell(kind, tier, reduced, detail, mesh)
                    local expect = mesh and not reduced and detail ~= "lite" and ((kind == "aura" and tier >= 4) or kind == "mutation")
                    assert(want == expect, kind .. " tier " .. tier .. " reduced " .. tostring(reduced) .. " " .. detail .. " mesh " .. tostring(mesh))
                end
            end
        end
    end
end
assert(R.wantsShell("aura", nil, false, "full", true) == false, "an aura with no tier has no shell")
for _, kind in {"aura", "mutation"} do
    local last = -1
    for k = 0, 10 do
        local f = R.shellFade(kind, k * 0.05)
        assert(f >= last - 1e-9 and f >= 0 and f <= 1, kind .. " shell fades IN smoothly")
        last = f
    end
    assert(R.shellFade(kind, 0) == 0 and R.shellFade(kind, R.Timing.fadeIn) >= 0.999, kind .. " shell starts clear and is full after the fade-in")
end
assert(R.shellFade("aura", 100) == 1, "an aura shell stays")
do
    local life = R.ShellSeconds.mutation
    assert(life >= 3 and life <= 10, "a mutation shell is a reveal, a few seconds")
    assert(R.shellFade("mutation", life - 2) == 1 and R.shellFade("mutation", life) == 0 and R.shellFade("mutation", life + 5) == 0, "the mutation shell fades out by its life")
    local prev = 1
    for k = 0, 20 do
        local f = R.shellFade("mutation", life - 1 + k * 0.05)
        assert(f <= prev + 1e-9, "the mutation shell fades OUT smoothly")
        prev = f
    end
end

-- 3. hatch light shaft plan (a tablet Mythic egg is exactly at its cap: the shaft takes the slot of the least important sprite)
local S = P.Shaft
assert(S.minTier == 4 and S.alpha <= 0.4 and S.alpha <= P.Limits.maxAlpha and S.width <= P.Panel[1] and S.height <= P.Panel[2], "shaft limits")
for _, dev in {"phone", "tablet", "desktop"} do
    for tier = 1, 6 do
        for _, mode in {"full", "lite", "off", "bogus"} do
            for _, reduce in {false, true} do
                local n = P.shaft(tier, dev, reduce, mode)
                assert(n == 0 or n == 1, "shaft is 0 or 1 sprite")
                if reduce or mode ~= "full" or tier < 4 then assert(n == 0, "no shaft: " .. dev .. " tier " .. tier .. " " .. mode .. " reduce " .. tostring(reduce)) end
                local c, m = P.withShaft(tier, dev, reduce, mode)
                assert(m == n, "withShaft agrees with shaft")
                assert(P.total(c) + m <= P.Caps[dev], "shaft + sprites fit the " .. dev .. " cap at tier " .. tier .. " " .. mode)
                local base = P.counts(tier, dev, reduce)
                local trimmed = 0
                for _, name in {"sparks", "motes", "puffs", "shocks", "fg", "drops", "bloom"} do
                    assert(c[name] <= base[name], "never more than the plain plan")
                    trimmed += base[name] - c[name]
                end
                if P.total(base) + m <= P.Caps[dev] then assert(trimmed == 0, "no trimming while the cap has room") else assert(trimmed >= 1 and c.fg < base.fg or c.motes < base.motes, "the least important sprite goes first") end
            end
        end
        if tier >= 4 then assert(P.shaft(tier, dev, false, "full") == 1, "Epic and up get the shaft at Full on " .. dev) end
    end
end
do
    local lastA = -1
    for k = 0, 20 do
        local scale, a = P.shaftLook(k / 20, nil)
        assert(scale >= 0.65 - 1e-9 and scale <= 1 + 1e-9 and a >= lastA - 1e-9 and a >= 0 and a <= S.alpha + 1e-9, "shaft fades in softly through the build-up")
        lastA = a
    end
    assert(select(2, P.shaftLook(0, nil)) == 0 and select(2, P.shaftLook(0.3, nil)) == 0, "no shaft in the first third of the build-up")
    local _, peak = P.shaftLook(1, 0)
    local prev = peak
    for k = 0, 40 do
        local _, a = P.shaftLook(1, k * 0.1)
        assert(a <= prev + 1e-9 and a >= S.alpha * 0.64, "after the burst the shaft only eases down, never below two thirds")
        prev = a
    end
    assert(math.abs(peak - S.alpha) < 1e-9, "the shaft peaks at its alpha")
end

-- 4. rare banner pops
assert(RH.plan("full", false, "shiny").pop == 2 and RH.plan("lite", false, "shiny").pop == 1, "two pops at Full, one at Lite")
assert(RH.plan("off", false, "shiny").pop == 0 and RH.plan("full", true, "legendary").pop == 0 and RH.plan("lite", true, "shiny").pop == 0, "Off and Calm: no pops")
assert(RH.plan("bogus", false, "shiny").pop == RH.Pop.full, "an unknown level plays as Full")
assert(RH.plan("full", true, "shiny").banner and RH.plan("off", true, "legendary").sound == "shiny_bang", "banner + sound stay")
assert(RH.PopLife > 0.5 and RH.PopLife <= 1.5 and RH.PopSize >= 32 and RH.PopSize <= 96, "a pop is short and small")
for key, id in BOUND do
    A.Requested[key].id = id
    assert(A.isReal(key) == (id ~= "") and A.resolve(key) == (if id ~= "" then id else A.Builtin[A.Requested[key].fallback]), key .. " bound id resolves to itself, empty to its sprite")
end
print("anime FX pure checks passed: slots empty, shell decision, hatch shaft plan, rare banner pops")
'''


def pure_script():
    out = 'local R = ' + module('src/shared/FxRecipes.luau') + '\n'
    out += 'local A = ' + module('src/shared/EffectAssets.luau') + '\n'
    out += 'local P = ' + module('src/shared/HatchFxPlan.luau', {'require(script.Parent.FxRecipes)': 'R'}) + '\n'
    out += 'local RH = ' + module('src/shared/RareHatch.luau') + '\n'
    return out + PURE


STUBS = r'''
-- Minimal Roblox stubs: enough to run the real client files. Instances record their children so sprite counts can be audited.
local created = 0
local function newInst(class)
    created += 1
    local t = {ClassName = class, children = {}, Order = created, Visible = true, Rotation = 0}
    setmetatable(t, {__newindex = function(self, k, v)
        rawset(self, k, v)
        if k == "Parent" and v ~= nil then table.insert(v.children, self) end
    end})
    function t.Destroy(self) self.Destroyed = true end
    function t.WaitForChild(self, name) return self[name] end
    return t
end
Instance = {new = newInst}
Vector2 = {new = function(x, y) return {X = x, Y = y} end}
UDim2 = {fromOffset = function(x, y) return {X = x, Y = y} end, new = function(a, b, c, d) return {SX = a, OX = b, SY = c, OY = d} end}
UDim = {new = function(a, b) return {Scale = a, Offset = b} end}
NumberSequence = {new = function(x) return x end}
NumberSequenceKeypoint = {new = function(a, b) return {t = a, v = b} end}
local function color(r, g, b)
    local c = {R = r, G = g, B = b}
    function c.Lerp(self, o, a) return color(self.R + (o.R - self.R) * a, self.G + (o.G - self.G) * a, self.B + (o.B - self.B) * a) end
    return c
end
Color3 = {new = color, fromRGB = function(r, g, b) return color(r / 255, g / 255, b / 255) end}
Enum = setmetatable({}, {__index = function() return setmetatable({}, {__index = function(_, k) return k end}) end})
local UIS = {TouchEnabled = true, MouseEnabled = false}
local CAM = {ViewportSize = {X = 400, Y = 800}}
workspace = {CurrentCamera = CAM}
MODE = "full"
CALM = false
'''

HATCH = r'''
--@@MODS
MODS.SettingsModel = {effects = function() return MODE end}
local Hatch = (function()
local require = function(x) return x end
local game = {GetService = function(_, name)
    if name == "UserInputService" then return UIS end
    return {WaitForChild = function() return MODS end}
end}
--@@HATCHSRC
end)()
local Plan, Assets = MODS.HatchFxPlan, MODS.EffectAssets
local function frame() return newInst("Frame") end
local function allNodes(p)
    local list = {}
    for _, group in {p.bloom, p.sparks, p.motes, p.puffs, p.shocks, p.fg, p.drops} do for _, n in group do list[#list + 1] = n end end
    if p.shaft then list[#list + 1] = p.shaft end
    return list
end
local function visible(p) local n = 0 for _, node in allNodes(p) do if node.obj.Visible then n += 1 end end return n end
local function spriteCount(frameObj) return #frameObj.children end
local RED = Color3.fromRGB(255, 80, 80)

-- A. EMPTY slot: exactly today's sprites, no shaft anywhere.
Assets.Requested.shaftGradient.id = ""
local emptyCounts = {}
for _, device in {"phone", "desktop"} do
    UIS.TouchEnabled, UIS.MouseEnabled = device == "phone", device ~= "phone"
    local back, front = frame(), frame()
    local pool = Hatch.ensure(back, front)
    assert(pool.device == device and pool.shaft == nil, "empty slot: no shaft sprite on " .. device)
    emptyCounts[device] = spriteCount(back)
    for tier = 1, 6 do
        local h = Hatch.begin(pool, true)
        Hatch.style(h, tier, RED, false)
        assert(h.shaft == 0, "empty slot: shaft stays off")
        for k = 0, 8 do
            Hatch.update(h, k * 0.3, math.min(1, k / 5), if k >= 5 then (k - 5) * 0.3 else nil, k >= 6)
            assert(visible(pool) <= Plan.Caps[device], "empty slot: within the sprite cap")
        end
    end
end

-- B. BOUND slot: ONE extra sprite behind the bloom, only where the plan allows it.
Assets.Requested.shaftGradient.id = "rbxassetid://812345679"
for _, device in {"phone", "desktop"} do
    UIS.TouchEnabled, UIS.MouseEnabled = device == "phone", device ~= "phone"
    local back, front = frame(), frame()
    local pool = Hatch.ensure(back, front)
    assert(pool.shaft and pool.shaft.obj.Image == "rbxassetid://812345679" and pool.shaft.obj.ZIndex == Plan.Shaft.z, "bound: the shaft sprite uses the upload, drawn under the bloom")
    assert(spriteCount(back) == emptyCounts[device] + 1, "bound: exactly ONE more sprite than today on " .. device)
    assert(Plan.Shaft.z < pool.bloom[1].obj.ZIndex, "the shaft sits behind the bloom discs")
    assert(pool.shaft.obj.AnchorPoint.Y == 0 and #pool.shaft.obj.children == 1, "top-anchored, one UIGradient for the soft sides")
    local grad = pool.shaft.obj.children[1]
    assert(grad.ClassName == "UIGradient" and grad.Transparency[1].v == 1 and grad.Transparency[#grad.Transparency].v == 1 and grad.Transparency[2].v == 0, "sides fade out through the gradient")
    for _, mode in {"full", "lite", "off"} do
        MODE = mode
        for _, motion in {true, false} do
            for tier = 1, 6 do
                for _, failed in {false, true} do
                    local h = Hatch.begin(pool, motion)
                    Hatch.style(h, tier, RED, failed)
                    local expect = if motion and mode == "full" and tier >= 4 then 1 else 0
                    assert(h.shaft == expect, device .. " " .. mode .. " motion " .. tostring(motion) .. " tier " .. tier .. " shaft plan " .. h.shaft)
                    local peakOpacity, shown = 0, false
                    for k = 0, 24 do
                        local bp = math.min(1, k / 12)
                        local since = if k >= 12 then (k - 12) * 0.25 else nil
                        Hatch.update(h, k * 0.25, bp, since, k >= 13)
                        local sh = pool.shaft.obj
                        if sh.Visible then
                            shown = true
                            peakOpacity = math.max(peakOpacity, 1 - sh.ImageTransparency)
                            assert(1 - sh.ImageTransparency <= Plan.Shaft.alpha + 1e-9, "shaft opacity within its limit")
                            assert(sh.Size.X == Plan.Shaft.width and sh.Size.Y <= Plan.Shaft.height and sh.Position.Y == 0, "shaft geometry")
                        end
                        assert(visible(pool) <= Plan.Caps[device], device .. " " .. mode .. " tier " .. tier .. ": visible sprites within the cap (" .. visible(pool) .. ")")
                    end
                    if expect == 1 and not failed then assert(shown and peakOpacity >= Plan.Shaft.alpha * 0.95, "a planned shaft appears and reaches its alpha")
                    else assert(not shown, device .. " " .. mode .. " motion " .. tostring(motion) .. " tier " .. tier .. " failed " .. tostring(failed) .. ": no shaft shown") end
                    Hatch.hide(h)
                    assert(not pool.shaft.obj.Visible, "hide() hides the shaft")
                end
            end
        end
    end
    MODE = "full"
end
Assets.Requested.shaftGradient.id = ""
print("HatchFx client checks passed: empty slot = today's sprites, bound slot = one shaft sprite for Epic+ at Full only, caps hold, Lite / Off / Reduce Motion / failed eggs show none")
'''

RARE = r'''
--@@MODS
function MODS.WaitForChild(self, name) return self[name] end
-- Run the REAL RareHatchClient once per scenario with fresh stubs (the script keeps its own state, so each run is a new copy).
local function scenario(effects, calm, bound, width)
    local Assets = MODS.EffectAssets
    Assets.Requested.starPop.id = if bound then "rbxassetid://812345678" else ""
    local handler
    local conns = {}
    local delayed = {}
    local played = {}
    local gui
    MODS.SettingsModel = {get = function() return {effects = effects, calm = calm} end}
    MODS.Sfx = {play = function(n) played[#played + 1] = n end}
    MODS.HatchTimeline = {durations = function() return {revealAt = 0.5} end}
    local remote = {OnClientEvent = {Connect = function(_, fn) handler = fn return {Disconnect = function() end} end}}
    local screen = nil
    Instance = {new = function(class)
        local t = newInst(class)
        if class == "ScreenGui" then rawset(t, "AbsoluteSize", {X = width, Y = 800}) screen = t end
        return t
    end}
    local env = {GetService = function(_, name)
        if name == "Players" then
            return {LocalPlayer = {WaitForChild = function() return newInst("PlayerGui") end}}
        elseif name == "RunService" then
            return {Heartbeat = {Connect = function(_, fn)
                local c = {fn = fn, on = true}
                conns[#conns + 1] = c
                return {Disconnect = function() c.on = false end}
            end}}
        end
        return {WaitForChild = function(_, n) if n == "BeDinoRemotes" then return {WaitForChild = function() return remote end} end return MODS end}
    end}
    local task = {delay = function(t, fn) delayed[#delayed + 1] = {t = t, fn = fn} end}
    ;(function()
        local game, task, require = env, task, function(x) return x end
        local script = {Parent = {WaitForChild = function() return {play = function() return false end} end}} -- MomentRim (BD-433) is audited by verify_fx_moments.py
--@@RARESRC
    end)()
    assert(handler, "the client connected to the RareHatch remote")
    -- another player's rare: a plain banner, never a star pop
    handler({k = "all", text = "Sam hatched a Shiny Rex!"})
    local function images() local list = {} for _, c in screen.children do if c.ClassName == "ImageLabel" then list[#list + 1] = c end end return list end
    local function labels() local list = {} for _, c in screen.children do if c.ClassName == "TextLabel" then list[#list + 1] = c end end return list end
    assert(#labels() == 1 and #images() == 0, "someone else's rare is a banner only")
    -- the own rare
    handler({k = "me", text = "You hatched a Shiny Rex!", kind = "shiny", rarity = 5})
    assert(#delayed >= 1, "the celebration waits for the reveal")
    for _, d in delayed do if d.t == 0.5 then d.fn() end end -- the reveal moment (HatchTimeline stub revealAt)
    local pops = {}
    for _, img in images() do if img.Image == "rbxassetid://812345678" then pops[#pops + 1] = img end end
    local function step(dt) for _, c in conns do if c.on then c.fn(dt) end end end
    local function alive() local n = 0 for _, c in conns do if c.on then n += 1 end end return n end
    return {pops = pops, screen = screen, images = images, labels = labels, step = step, alive = alive, played = played, plan = MODS.RareHatch.plan(effects, calm, "shiny")}
end

local gold = Color3.fromRGB(255, 214, 77)
-- A. EMPTY slot: today's banner and confetti, never a star pop.
for _, effects in {"full", "lite", "off"} do
    local s = scenario(effects, false, false, 1000)
    assert(#s.pops == 0, "empty starPop slot: no pop sprites (" .. effects .. ")")
    assert(#s.labels() == 2, "banners for the others and the own hatch")
    assert(s.played[1] == "shiny_bang", "the sound still plays")
    local total = #s.images()
    assert(total == s.plan.confetti, "confetti count is exactly today's plan: " .. total .. " vs " .. s.plan.confetti)
end

-- B. BOUND slot: pops flank the own banner by the plan; Off and Calm draw none.
for _, case in {{"full", false, 2}, {"lite", false, 1}, {"off", false, 0}, {"full", true, 0}, {"lite", true, 0}} do
    local effects, calm, want = case[1], case[2], case[3]
    local s = scenario(effects, calm, true, 1000)
    assert(#s.pops == want, effects .. " calm " .. tostring(calm) .. ": " .. want .. " pops, got " .. #s.pops)
    assert(#s.labels() == 2 and s.played[1] == "shiny_bang", "banner and sound unchanged")
    if want > 0 then
        for i, p in s.pops do
            assert(p.Size.X == MODS.RareHatch.PopSize and p.ImageColor3.R == gold.R and p.ImageColor3.G == gold.G, "pop size and gold tint")
            assert(p.Position.Y == 98 and p.ZIndex == 5, "pops sit at the banner's height, above it")
            assert(p.ImageRectSize.X == 128 and p.ImageRectSize.Y == 128, "a 128 px cell")
        end
        if want == 2 then assert(s.pops[1].Position.X > 500 and s.pops[2].Position.X < 500, "one pop each side of the banner") end
        assert(s.alive() >= 1, "the flipbook is driven by a Heartbeat connection")
        local cells = {}
        for step = 1, 30 do
            s.step(0.05)
            for _, p in s.pops do
                if not p.Destroyed then
                    assert(p.ImageRectOffset.X % 128 == 0 and p.ImageRectOffset.Y % 128 == 0 and p.ImageRectOffset.X <= 384 and p.ImageRectOffset.Y <= 384, "valid cell")
                    cells[p.ImageRectOffset.X .. "," .. p.ImageRectOffset.Y] = true
                end
            end
        end
        local n = 0 for _ in cells do n += 1 end
        assert(n >= 12, "the 4x4 flipbook advances (" .. n .. " cells)")
        for _, p in s.pops do assert(p.Destroyed, "each pop is gone after its life") end
        for step = 1, 100 do s.step(0.05) end -- confetti lives up to 3.2 s
        assert(s.alive() == 0, "every Heartbeat connection is released when the effects are gone")
    end
end

-- C. A narrow phone keeps both pops on screen.
do
    local s = scenario("full", false, true, 360)
    assert(#s.pops == 2)
    for _, p in s.pops do assert(p.Position.X - 32 >= 0 and p.Position.X + 32 <= 360, "pop inside a 360 px wide screen: " .. p.Position.X) end
end
print("RareHatchClient checks passed: empty slot = today's banner and confetti, bound slot = star pops by Full 2 / Lite 1 / Off 0 / Calm 0, flipbook plays once, gone after")
'''


def load_mods(names):
    out = 'local MODS = {}\n'
    for name, path, subs in names:
        out += 'MODS.' + name + ' = ' + module(path, subs) + '\n'
    return out


def hatch_script():
    mods = load_mods([('FxRecipes', 'src/shared/FxRecipes.luau', None), ('EffectAssets', 'src/shared/EffectAssets.luau', None),
                      ('HatchFxPlan', 'src/shared/HatchFxPlan.luau', {'require(script.Parent.FxRecipes)': 'MODS.FxRecipes'})])
    body = HATCH.replace('--@@MODS', mods)
    client = src('src/client/HatchFx.luau')
    # the client file requires Shared.<Module>; MODS is the Shared folder
    return STUBS + body.replace('--@@HATCHSRC', client)


def rare_script():
    mods = load_mods([('RareHatch', 'src/shared/RareHatch.luau', None), ('EffectAssets', 'src/shared/EffectAssets.luau', None)])
    body = RARE.replace('--@@MODS', mods)
    client = src('src/client/RareHatchClient.client.luau')
    return STUBS + body.replace('--@@RARESRC', client)


def scan():
    rig = src('src/client/FxRig.luau')
    for needle in ['Recipes.wantsShell(kind, resolved.tier, resolved.reduced, opts.detail, Slots.mesh("aura_shell_mesh") ~= nil)',
                   'Recipes.shellFade(self.shellKind, self.age)', 'Assets.isReal("shellEdge")', 'special.TextureId = Assets.resolve("shellEdge")',
                   'SHELL_NATIVE', 'self.shellMesh.Scale']:
        assert needle in rig, 'FxRig must contain ' + needle
    assert 'kind == "aura" and not resolved.reduced' not in rig, 'FxRig no longer decides the shell itself'
    hatch = src('src/client/HatchFx.luau')
    for needle in ['Assets.isRealUi("shaftGradient")', 'Plan.withShaft(h.tier, h.pool.device, not h.motion, Settings.effects())', 'Plan.shaftLook(bp, since)', 'if p.shaft then p.shaft.obj.Visible = false end']:
        assert needle in hatch, 'HatchFx must contain ' + needle
    rare = src('src/client/RareHatchClient.client.luau')
    for needle in ['Assets.isRealUi("starPop")', 'Assets.frameAt("starPop"', 'plan.pop', 'room = math.max(0, 2 - #pops)']:
        assert needle in rare, 'RareHatchClient must contain ' + needle
    for path in ['src/client/FxRig.luau', 'src/client/HatchFx.luau', 'src/client/RareHatchClient.client.luau', 'src/shared/HatchFxPlan.luau', 'src/shared/RareHatch.luau', 'src/shared/FxRecipes.luau']:
        assert not re.search(r'rbxassetid://\d+', src(path)), path + ' must not contain asset ids'
    ea = src('src/shared/EffectAssets.luau')
    for key in ['flameTongue', 'starPop', 'domeGradient', 'speedStreaks', 'shaftGradient', 'shellEdge']:
        m = re.search(key + r' = \{id = "(rbxassetid://\d+)?", fallback', ea)
        assert m, key + ' slot must be empty or one valid rbxassetid'
        if m.group(1):  # bound after the 2026-10-17 batch upload: the id must be a registered docs/77 row, never invented
            assert m.group(1).split('//')[1] in src('docs/77-asset-registry.md'), key + ' bound id is not in the asset registry'
    slots = src('src/shared/AssetSlots.luau')
    for key in ['shock_dome_mesh', 'shaft_cone_mesh', 'aura_shell_mesh']:
        assert re.search(key + r' = "",', slots), key + ' mesh slot must stay empty until uploaded'
    print('Source scan passed: readers wired to the pure plans, no invented asset ids, slots empty')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    scan()
    code = 0
    with tempfile.TemporaryDirectory() as d:
        for name, text in (('pure.luau', pure_script()), ('hatch.luau', hatch_script()), ('rare.luau', rare_script())):
            path = Path(d) / name
            path.write_text(text, encoding='utf-8')
            result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
            print(result.stdout, end='')
            print(result.stderr, end='')
            code = code or result.returncode
    raise SystemExit(code)
