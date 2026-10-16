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
assert(P.Richness.aurora <= 1.25 and P.Richness.bloodmoon <= 1.25, "richer, never louder")
assert(P.counts("nope", "desktop", "full", false).glow == 0, "unknown id draws nothing")
assert(#P.AuroraCycle == 4 and P.colorIndex("aurora", 5) == 1)
print("MutationRevealPlan checks passed")
'''


def script():
    text = (ROOT / 'src/shared/MutationRevealPlan.luau').read_text(encoding='utf-8')
    return 'local P = (function()\n' + text + '\nend)()\n' + BODY


def scan():
    seq = (ROOT / 'src/client/HatchSequence.luau').read_text(encoding='utf-8')
    for needle in ['MutationReveal.begin', 'MutationReveal.update', 'MutationReveal.hide']:
        assert needle in seq, 'HatchSequence must call ' + needle
    cl = (ROOT / 'src/client/MutationReveal.luau').read_text(encoding='utf-8')
    for needle in ['MutationRevealPlan', 'MutationLook', 'EffectAssets', 'Settings.effects()']:
        assert needle in cl, 'MutationReveal must use ' + needle
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
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'reveal.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
