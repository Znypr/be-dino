"""BD-162: offline audit of the hatch mutation reveal plan (src/shared/MutationRevealPlan.luau): sprite budgets per device and
Effects mode (Full / Lite / Off), Reduce Motion (one still glow), calm limits (opacity, radius, size), every mutation has a
motion, richness never louder than the cap, no invented asset ids, and HatchSequence wiring. Drawing is Studio-only."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]

BODY = r'''
local L = P.Limits
local ids = {"dewdrop", "charged", "frost", "seismic", "ember", "aurora", "bloodmoon"}
for _, id in ids do
    assert(P.Motifs[id] and P.Richness[id], id .. " needs a motif and richness")
    local prevTotal
    for _, dev in {"phone", "tablet", "desktop"} do
        local full, lite = P.counts(id, dev, "full", false), P.counts(id, dev, "lite", false)
        assert(P.total(full) <= P.Caps[dev] and P.total(lite) <= P.Caps[dev], id .. " over cap on " .. dev)
        assert(P.total(lite) <= P.total(full), "lite never above full")
        assert(full.motifs >= P.Floors.motifs and full.puffs >= 1 and full.rings >= 1, "floors hold")
        local off = P.counts(id, dev, "off", false)
        assert(off.glow == 1 and off.rings == 1 and off.motifs == 0 and off.puffs == 0, "Off keeps only the glow and one ring")
        local still = P.counts(id, dev, "full", true)
        assert(still.glow == 1 and still.motifs == 0 and still.puffs == 0 and still.rings == 0, "Reduce Motion: one still glow")
        assert(P.loopCount(full) >= 1 and P.loopCount(full) <= full.motifs)
        if prevTotal then assert(P.total(full) >= prevTotal, "devices never shrink upward") end
        prevTotal = P.total(full)
    end
    local n = P.counts(id, "desktop", "full", false).motifs
    for step = 0, 120 do
        local t = step * 0.05
        for i = 1, n do
            local dx, dy, size, op = P.motif(id, i, n, t)
            assert(math.sqrt(dx * dx + dy * dy) <= L.maxRadius + 1e-6, id .. " motif leaves the radius")
            assert(size <= L.maxSize and op >= 0 and op <= L.maxAlpha + 1e-6, id .. " size or opacity")
        end
        local gs, ga = P.glow(id, t)
        assert(ga <= L.glowAlpha + 1e-6 and gs <= 360)
        for i = 1, 2 do local rs, ra = P.ring(i, t) assert(ra <= L.maxAlpha) assert(rs <= 430) end
        for i = 1, 3 do local _, _, ps, pa = P.puff(i, 3, t) assert(pa <= L.puffAlpha + 1e-6 and ps <= 140) end
    end
    local first = P.motif(id, 1, 5, -1)
    assert(first == 0, "nothing before the reveal")
end
-- BD-186..189: the pooled sprites the client builds (1 glow + 2 rings + 3 puffs + up to Caps motifs) always cover the plan's counts, in every
-- Effects mode on every device, so the textured look can never need more sprites than the cap allows (Lite is half of Full).
for _, id in ids do
    for _, dev in {"phone", "tablet", "desktop"} do
        for _, mode in {"full", "lite", "off"} do
            local c = P.counts(id, dev, mode, false)
            assert(c.rings <= 2 and c.puffs <= 3 and c.motifs <= P.Caps[dev], id .. " " .. dev .. " " .. mode .. " fits the pooled sprites")
            assert(P.total(c) <= P.Caps[dev], id .. " " .. dev .. " " .. mode .. " under the sprite cap")
        end
        assert(P.total(P.counts(id, dev, "lite", false)) <= P.total(P.counts(id, dev, "full", false)))
    end
end
-- Flipbook phase: motif k stays in 0..1 and wraps every motifLife; puffs run once from 0 to 1 over puffLife; nothing before the reveal.
for step = 0, 200 do
    local t = step * 0.05
    for i = 1, 14 do
        local k, age = P.motifPhase(i, 14, t)
        assert(k >= 0 and k < 1 and age >= 0 and age < L.motifLife + 1e-9, "motif phase range")
    end
    local k, age = P.puffPhase(t)
    assert(k >= 0 and k <= 1 and age >= 0, "puff phase range")
end
do
    local k0 = P.motifPhase(1, 5, 0)
    local k1 = P.motifPhase(1, 5, L.motifLife)
    assert(math.abs(k0 - k1) < 1e-9, "motif phase wraps every motifLife")
    local a = P.motifPhase(1, 5, 0.3)
    local b = P.motifPhase(2, 5, 0.3)
    assert(math.abs(a - b) > 0.1, "sprites are staggered")
    assert(select(1, P.puffPhase(-1)) == 0 and select(1, P.puffPhase(10)) == 1)
end
assert(P.Richness.aurora <= 1.25 and P.Richness.bloodmoon <= 1.25, "richer, never louder")
assert(P.counts("nope", "desktop", "full", false).glow == 0, "unknown id draws nothing")
assert(#P.AuroraCycle == 4 and P.colorIndex("aurora", 5) == 1)
print("MutationRevealPlan checks passed")
'''


def script():
    text = (ROOT / 'src/shared/MutationRevealPlan.luau').read_text(encoding='utf-8')
    return 'local P = (function()\n' + text + '\nend)()\n' + BODY


CLIENT = r'''
-- BD-186..189: drive the REAL client/MutationReveal.luau against stubbed Roblox instances.
local created = 0
local live = {}
Instance = {new = function(class)
    created += 1
    local t = {ClassName = class, Order = created, Visible = true}
    function t.Destroy(self) self.Destroyed = true end
    live[#live + 1] = t
    return t
end}
Vector2 = {new = function(x, y) return {X = x, Y = y} end}
UDim2 = {fromOffset = function(x, y) return {X = x, Y = y} end}
UDim = {new = function(a, b) return {Scale = a, Offset = b} end}
local function color(r, g, b)
    local c = {R = r, G = g, B = b}
    function c.Lerp(self, o, a) return color(self.R + (o.R - self.R) * a, self.G + (o.G - self.G) * a, self.B + (o.B - self.B) * a) end
    return c
end
Color3 = {new = color, fromRGB = function(r, g, b) return color(r / 255, g / 255, b / 255) end}
local UIS = {TouchEnabled = true, MouseEnabled = false}
local CAM = {ViewportSize = {X = 400, Y = 800}}
workspace = {CurrentCamera = CAM}
MODE = "full"
game = {GetService = function(_, name)
    if name == "UserInputService" then return UIS end
    return {WaitForChild = function() return MODS end}
end}

--@@LOAD
local function setReal(on: boolean)
    for key, req in Assets.Requested do
        if string.match(key, "^glowPlate[RDC]") or key == "ringSeismic" or key == "smokeDense" or key == "smokeWispy" or string.match(key, "^motif") then
            if on then req.id = "rbxassetid://" .. tostring(700000000 + #key * 1000 + string.byte(key, #key)) else req.id = "" end
        end
    end
end
local function visibleCount(p)
    local n = if p.glow.obj.Visible then 1 else 0
    for _, list in {p.rings, p.puffs, p.motifs} do for _, node in list do if node.obj.Visible then n += 1 end end end
    return n
end
local function newFront() return {Name = "front"} end
local ids = Look.Order
local function sameRect(a, b) return a.X == b.X and a.Y == b.Y end

-- 1. EMPTY slots: exactly today's keys, no flipbook animation, no tint changes, the pool sizes of the plan.
setReal(false)
for _, id in ids do
    local front = newFront()
    local h = Reveal.begin(front, id, true)
    local p, entry = h.pool, P.Motifs[id]
    assert(p.glow.key == "glowPlate" and not p.glow.img, id .. " empty: the glow is the native disc")
    assert(#p.rings == 2 and #p.puffs == 3 and #p.motifs == (P.Caps[p.device]), id .. " empty: pool sizes")
    for _, ring in p.rings do assert(ring.key == "ringShock" and ring.stroke and not ring.img and not ring.anim, id .. " empty: native stroked ring") end
    for _, puff in p.puffs do assert(puff.key == "smokeSheet" and puff.img and not puff.anim and not puff.coloured, id .. " empty: fx3 smoke puffs, fixed cell") end
    for _, m in p.motifs do assert(m.key == entry.key and not m.anim and not m.coloured, id .. " empty: today's motif key " .. entry.key) end
    local rects = {}
    for i, puff in p.puffs do rects[i] = puff.obj.ImageRectOffset end
    local mrects = {}
    for i, m in p.motifs do mrects[i] = m.obj.ImageRectOffset end
    for step = 0, 40 do
        Reveal.update(h, step * 0.1)
        for i, puff in p.puffs do assert(sameRect(puff.obj.ImageRectOffset, rects[i]), id .. " empty: puff cell never changes") end
        for i, m in p.motifs do assert(sameRect(m.obj.ImageRectOffset, mrects[i]), id .. " empty: motif cell never changes") end
    end
    assert(h.counts.glow == 1)
end

-- 2. REAL slots: each mutation reads its own textures with the 4 x 4 flipbook; coloured art is untinted; caps hold in every mode.
setReal(true)
local function keyId(key) return Assets.Requested[key].id end
local sheetsSeen = 0
for _, device in {"phone", "desktop"} do
    UIS.TouchEnabled, UIS.MouseEnabled = device == "phone", device ~= "phone"
    for _, mode in {"full", "lite", "off"} do
        MODE = mode
        for _, id in ids do
            local map = R.MutationTex[id]
            local front = newFront()
            local h = Reveal.begin(front, id, true)
            local p = h.pool
            assert(p.device == device, "device class " .. device)
            assert(p.glow.key == map.glow and p.glow.img and p.glow.obj.Image == keyId(map.glow), id .. " glow plate " .. map.glow)
            for _, ring in p.rings do
                local want = map.ring or "ringShock"
                assert(ring.key == want, id .. " ring key")
                if map.ring then assert(ring.img and ring.obj.Image == keyId(map.ring), id .. " ring uses the real texture") end
            end
            for _, puff in p.puffs do
                assert(puff.key == (map.smoke or "smokeSheet"), id .. " smoke key")
                assert(puff.anim == (map.smoke ~= nil), id .. " only mapped smoke animates")
                if map.smoke then assert(puff.img and Assets.isSheet(map.smoke) and puff.obj.Image == keyId(map.smoke)) end
            end
            for _, m in p.motifs do
                assert(m.key == map.motif and m.img and m.anim and m.obj.Image == keyId(map.motif), id .. " motif " .. map.motif)
                assert(m.coloured == (map.motif == "motifAurora"))
            end
            local counts = h.counts
            local cap = P.Caps[device]
            local rectsSeen, maxVisible = {}, 0
            local motifTints = {}
            for step = 0, 60 do
                local since = step * 0.1
                Reveal.update(h, since)
                local v = visibleCount(p)
                maxVisible = math.max(maxVisible, v)
                assert(v <= P.total(counts) and v <= cap, id .. " " .. device .. " " .. mode .. " visible " .. v .. " > cap " .. cap)
                local m1 = p.motifs[1]
                if m1 and m1.obj.Visible then
                    local r = m1.obj.ImageRectOffset
                    assert(r.X % 128 == 0 and r.Y % 128 == 0 and r.X <= 384 and r.Y <= 384 and m1.obj.ImageRectSize.X == 128 and m1.obj.ImageRectSize.Y == 128, id .. " valid 128 px cell")
                    rectsSeen[r.X .. "," .. r.Y] = true
                    motifTints[#motifTints + 1] = m1.obj.ImageColor3
                end
                for i, m in p.motifs do
                    if m.obj.Visible and map.motif == "motifAurora" then
                        local c = m.obj.ImageColor3
                        assert(c.R == 1 and c.G == 1 and c.B == 1, "Aurora art is not tinted")
                    end
                end
            end
            if mode == "off" then
                assert(counts.motifs == 0 and counts.puffs == 0 and maxVisible <= 2, id .. " Off keeps the glow and one ring only")
            else
                local n = 0 for _ in rectsSeen do n += 1 end
                assert(n >= 4, id .. " " .. device .. " " .. mode .. " the motif flipbook advances (" .. n .. " cells)")
                sheetsSeen += 1
                if map.motif ~= "motifAurora" then
                    local tinted = false
                    for _, c in motifTints do if not (c.R == 1 and c.G == 1 and c.B == 1) then tinted = true end end
                    assert(tinted, id .. " white art is tinted from MutationLook")
                end
            end
            if mode == "lite" then
                local full = P.counts(id, device, "full", false)
                assert(P.total(counts) <= P.total(full) and P.total(counts) <= cap, id .. " lite is smaller than full")
            end
        end
    end
end
MODE = "full"
assert(sheetsSeen == 7 * 2 * 2, "ran every mutation in Full and Lite on both devices")

-- 3. Reduce Motion (motion = false): one still glow disc with the mapped plate, nothing else, no particles.
UIS.TouchEnabled, UIS.MouseEnabled = true, false
for _, id in ids do
    local front = newFront()
    local h = Reveal.begin(front, id, false)
    local p = h.pool
    assert(h.counts.motifs == 0 and h.counts.puffs == 0 and h.counts.rings == 0 and h.still)
    for step = 0, 30 do
        Reveal.update(h, step * 0.1)
        assert(visibleCount(p) == 1 and p.glow.obj.Visible and p.glow.key == R.MutationTex[id].glow, id .. " Reduce Motion: one still plate")
        assert(p.glow.obj.Size.X == P.StillGlow[1], "still glow size does not move")
    end
end

-- 4. Switching mutations rebuilds the pool in draw order (glow, rings, puffs, motifs), destroys the old sprites, and reuses it when nothing changed.
do
    local front = newFront()
    local a = Reveal.begin(front, "frost", true).pool
    local oldGlow = a.glow
    local again = Reveal.begin(front, "frost", true).pool
    assert(again.glow == oldGlow, "same mutation keeps the pooled sprites")
    local b = Reveal.begin(front, "seismic", true).pool
    assert(b == a and b.glow ~= oldGlow and oldGlow.obj.Destroyed, "a new mutation replaces the sprites")
    assert(b.glow.obj.Order < b.rings[1].obj.Order and b.rings[2].obj.Order < b.puffs[1].obj.Order and b.puffs[3].obj.Order < b.motifs[1].obj.Order, "draw order glow < rings < puffs < motifs")
    assert(b.rings[1].key == "ringSeismic" and b.puffs[1].key == "smokeDense" and b.motifs[1].key == "motifPebbles")
    local c = Reveal.begin(front, "dewdrop", true).pool
    assert(c.rings[1].key == "ringShock" and c.glow.key == "glowPlateDroplet" and c.motifs[1].key == "motifDroplets")
end

-- 5. A slot that goes back to empty (or an id that is not valid) falls back to today's look.
setReal(false)
Assets.Requested.motifAurora.id = "rbxassetid://abc"
do
    local h = Reveal.begin(newFront(), "aurora", true)
    assert(h.pool.motifs[1].key == "swirl" and not h.pool.motifs[1].anim and h.pool.glow.key == "glowPlate", "invalid id keeps today's look")
    Assets.Requested.motifAurora.id = ""
end
print("MutationReveal client checks passed: empty slots keep today's look, real slots use the mapped textures with the 4x4 flipbook, caps hold in Full/Lite/Off, Reduce Motion is one still plate")
'''


def client_script():
    """Runs the REAL client/MutationReveal.luau (and the real shared modules) against stubbed Roblox instances."""
    def mod(path):
        return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'
    out = 'local MODS = {}\n'
    for name, path in (('MutationLook', 'MutationLook'), ('MutationRevealPlan', 'MutationRevealPlan'), ('EffectAssets', 'EffectAssets'), ('FxRecipes', 'FxRecipes')):
        out += 'MODS.' + name + ' = ' + mod('src/shared/' + path + '.luau') + '\n'
    out += 'local P, Look, Assets, R = MODS.MutationRevealPlan, MODS.MutationLook, MODS.EffectAssets, MODS.FxRecipes\n'
    head, tail = CLIENT.split('--@@LOAD\n')
    out += head
    out += 'MODS.SettingsModel = {effects = function() return MODE end}\n'
    client_src = (ROOT / 'src/client/MutationReveal.luau').read_text(encoding='utf-8')
    out += 'local Reveal = (function()\nlocal require = function(x) return x end\n' + client_src + '\nend)()\n'
    out += tail
    return out


def scan():
    seq = (ROOT / 'src/client/HatchSequence.luau').read_text(encoding='utf-8')
    for needle in ['MutationReveal.begin', 'MutationReveal.update', 'MutationReveal.hide']:
        assert needle in seq, 'HatchSequence must call ' + needle
    cl = (ROOT / 'src/client/MutationReveal.luau').read_text(encoding='utf-8')
    for needle in ['MutationRevealPlan', 'MutationLook', 'EffectAssets', 'Settings.effects()']:
        assert needle in cl, 'MutationReveal must use ' + needle
    # BD-186..189: textures come from the one FxRecipes table, only for valid uploads, and every default key is today's key
    for needle in ['Recipes.mutationTex(id, slot, Assets.isRealUi)', 'Plan.motifPhase', 'Plan.puffPhase', 'Assets.frameAt', 'MutationTexColoured']:
        assert needle in cl, 'MutationReveal must use ' + needle
    for default in ['pick("glow", "glowPlate")', 'pick("ring", "ringShock")', 'pick("smoke", "smokeSheet")', 'pick("motif", entry.key)']:
        assert default in cl, 'empty slot must keep today\'s key: ' + default
    assert 'for i = 1, 2 do p.rings[i]' in cl and 'for i = 1, 3 do p.puffs[i]' in cl and 'Plan.Caps[p.device]' in cl, 'pooled sprite counts changed'
    assert 'm.coloured then col = WHITE' in cl, 'coloured motif art must not be tinted'
    assert 'if not n.anim then return end' in cl, 'only the new mutation sheets animate; older keys keep their fixed cell'
    for path in ['src/shared/MutationRevealPlan.luau', 'src/client/MutationReveal.luau']:
        assert not re.search(r'rbxassetid://\d+', (ROOT / path).read_text(encoding='utf-8')), path + ' must not contain asset ids'
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    assert 'MutationReveal' not in boot, 'Bootstrap is at the local-register limit: only pass mutationId'
    print('Source scan passed: hatch wired, no invented asset ids')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    scan()
    code = 0
    with tempfile.TemporaryDirectory() as d:
        for name, text in (('reveal.luau', script()), ('reveal_client.luau', client_script())):
            path = Path(d) / name
            path.write_text(text, encoding='utf-8')
            result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
            print(result.stdout, end='')
            print(result.stderr, end='')
            code = code or result.returncode
    raise SystemExit(code)
