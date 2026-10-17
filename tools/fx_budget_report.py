"""BD-429 (docs/123 s6): offline FX budget audit. Scans the client FX code, asks the real recipe modules (FxRecipes,
WeatherLooks, HatchTimeline, MutationRevealPlan, EffectsLod) for per-effect costs, sums the WORST concurrent moments
per device class, and fails when a moment exceeds the PROVISIONAL budgets below. No Studio needed (CI).
Real numbers come from tools/qa/fx_probe.client.luau (docs/117); this report is the model, the probe is the truth.
Usage: python tools/fx_budget_report.py --runner <luau> [--input probe.tsv] [--list]"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]

# PROVISIONAL budgets per device class (docs/123 s6). A real phone number from fx_probe replaces a guess.
# live3d = ParticleEmitter particles alive at once in the whole 3D world, weather included (Rate x mean Lifetime; NOT the cosmetic-only 'about 300' of docs/107, docs/115 PB1); big = large soft sprites (overdraw);
# beams / trails / lights = instances enabled at once; ui = on-screen UI FX frames (hatch + mutation panel).
BUDGETS = {
    'phone':   {'live3d': 3300, 'big': 120, 'beams': 48, 'trails': 14, 'lights': 24, 'ui': 130},
    'tablet':  {'live3d': 5600, 'big': 220, 'beams': 72, 'trails': 20, 'lights': 24, 'ui': 160},
    'desktop': {'live3d': 7600, 'big': 520, 'beams': 160, 'trails': 40, 'lights': 24, 'ui': 220},
}
# Phone lights/beams come from the shared file tools/qa/phone_budgets.json (single source of truth, docs/126, docs/127).
import json
_PB = json.loads((ROOT / 'tools' / 'qa' / 'phone_budgets.json').read_text(encoding='utf-8'))['phone']
BUDGETS['phone']['lights'] = _PB['lights']['value']
BUDGETS['phone']['beams'] = _PB['beams']['value']
# BD-497 (docs/146 s10): phone weather density now comes from the same file ("guards"; src/shared/PhoneGuards.luau, verify_phone_guards checks they agree).
# Before the guard it was 0.5; the forecast passes that value explicitly to print before / after.
_GUARDS = json.loads((ROOT / 'tools' / 'qa' / 'phone_budgets.json').read_text(encoding='utf-8'))['guards']
PHONE_WEATHER_DENSITY = _GUARDS['weatherDensity']['value']
PHONE_WEATHER_DENSITY_BEFORE = 0.5
PLAYERS = 12  # EffectsLod.MaxDinos.full: effect dinos in one view

CLIENT_FILES = ['HatchSequence', 'MutationReveal', 'RareHatchClient', 'CosmeticVisuals.client', 'WeatherVisuals.client',
                'CaveAtmosphere', 'FxRig', 'HatchFx', 'HatchEggV2']
SHARED_FILES = ['FxUi', 'FxRecipes', 'CosmeticEffects', 'MutationEffects', 'ShinyEffects', 'EffectsLod', 'LowPolyDinos']
CLASSES = ['ParticleEmitter', 'Beam', 'Trail', 'PointLight', 'SpotLight', 'SurfaceLight', 'Highlight']


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


def scan_sources():
    """Static inventory: Instance.new / acquire counts per class per file, max Rate literal, Emit calls."""
    rows, missing = [], []
    for name in CLIENT_FILES + SHARED_FILES:
        path = next((p for p in (ROOT / 'src/client' / (name + '.luau'), ROOT / 'src/shared' / (name + '.luau')) if p.exists()), None)
        if path is None:
            missing.append(name)
            continue
        text = path.read_text(encoding='utf-8')
        counts = {c: len(re.findall(r'(?:Instance\.new|acquire)\(\s*"%s"' % c, text)) for c in CLASSES}
        rates = [float(x) for x in re.findall(r'\.Rate\s*=\s*(\d+(?:\.\d+)?)\b', text)]
        rows.append((path.relative_to(ROOT).as_posix(), counts, max(rates) if rates else 0, len(re.findall(r'\bEmit\(', text))))
    return rows, missing


LUA = r'''
local DEVICES = {"phone", "tablet", "desktop"}
local out = {}
local function row(...) local t = {} for _, v in {...} do table.insert(t, tostring(v)) end table.insert(out, table.concat(t, "\t")) end
for _, dev in DEVICES do
    for _, detail in {"full", "lite"} do
        local best = {aura = {alive = 0, beams = 0, trails = 0, lights = 0, burst = 0}, trail = {alive = 0, beams = 0, trails = 0, lights = 0, burst = 0}, mutation = {alive = 0, beams = 0, trails = 0, lights = 0, burst = 0}}
        local function take(kind, item)
            local c = R.resolve(kind, item, {device = dev, detail = detail}).cost
            local b = best[kind]
            for k in b do if c[k] > b[k] then b[k] = c[k] end end
        end
        for _, a in Config.Auras do take("aura", a) end
        for _, t in Config.Trails do take("trail", t) end
        for _, id in Look.Order do take("mutation", Look.get(id)) end
        for kind, b in best do row("DINO", dev, detail, kind, b.alive, b.beams, b.trails, b.lights, b.burst) end
    end
    row("DEVCAP", dev, R.Devices[dev].alive, R.Devices[dev].fullDinos)
end
for _, lite in {false, true} do -- fused-tier sparkle (LowPolyDinos): worst tier, particles alive per fused dino
    local worst = 0
    for _, id in TierLook.Order do worst = math.max(worst, TierLook.sparkleAlive(TierLook.get(id), lite)) end
    row("TIERSPARK", if lite then "lite" else "full", worst)
end
for _, mode in {"full", "lite", "off"} do row("LOD", mode, Lod.MaxDinos[mode], Lod.CullRange[mode]) end
for id in W.Rigs do local c, big = W.concurrent(id) row("WEATHER", id, c, big) end
for _, dev in DEVICES do
    local worst = 0
    for _, id in Look.Order do for _, mode in {"full", "lite", "off"} do
        worst = math.max(worst, MP.total(MP.counts(id, dev, mode, false)))
    end end
    row("MUTUI", dev, worst)
end
print(table.concat(out, "\n"))
'''


def run_model(runner):
    s = 'local Config = ' + module('src/shared/ProgressionConfig.luau') + '\n'
    s += 'local Look = ' + module('src/shared/MutationLook.luau') + '\n'
    s += 'local Assets = ' + module('src/shared/EffectAssets.luau') + '\n'
    s += 'local R = ' + module('src/shared/FxRecipes.luau') + '\n'
    s += 'local Lod = ' + module('src/shared/EffectsLod.luau') + '\n'
    s += 'local W = ' + module('src/shared/WeatherLooks.luau') + '\n'
    s += 'local MP = ' + module('src/shared/MutationRevealPlan.luau') + '\n'
    s += 'local TierLook = ' + module('src/shared/LowPolyTier.luau') + '\n' + LUA
    with tempfile.NamedTemporaryFile('w', suffix='.luau', delete=False, encoding='utf-8') as f:
        f.write(s)
    r = subprocess.run([runner, f.name], capture_output=True, text=True)
    Path(f.name).unlink()
    if r.returncode != 0:
        sys.exit('model script failed:\n' + r.stdout + r.stderr)
    rows = [line.split('\t') for line in r.stdout.strip().splitlines()]
    # HatchTimeline requires sibling modules, so its caps are read from source (one egg at a time = the concurrent worst).
    text = (ROOT / 'src/shared/HatchTimeline.luau').read_text(encoding='utf-8')
    caps = [re.search(r'T\.%s\s*=\s*(\d+)' % n, text) for n in ('MaxParticles', 'OrbitMax', 'FireworkMax', 'RainMax', 'PaintMax')]
    assert all(caps), 'HatchTimeline caps not found'
    rows.append(['HATCHUI'] + [c.group(1) for c in caps])
    return rows


def moments(rows, phone_density=None):
    dino, devcap, lod, weather, ui, hatch_ui, tier_spark = {}, {}, {}, {}, {}, 0, {}
    keys = ['alive', 'beams', 'trails', 'lights', 'burst']
    for r in rows:
        k = r[0]
        if k == 'DINO': dino[(r[1], r[2], r[3])] = dict(zip(keys, map(float, r[4:9])))
        elif k == 'DEVCAP': devcap[r[1]] = int(r[3])
        elif k == 'TIERSPARK': tier_spark[r[1]] = float(r[2])
        elif k == 'LOD': lod[r[1]] = int(r[2])
        elif k == 'WEATHER': weather[r[1]] = (float(r[2]), float(r[3]))
        elif k == 'HATCHUI': hatch_ui = sum(int(x) for x in r[1:6])
        elif k == 'MUTUI': ui[r[1]] = int(r[2])
    out = {}
    for dev in ['phone', 'tablet', 'desktop']:
        dens = (PHONE_WEATHER_DENSITY if phone_density is None else phone_density) if dev == 'phone' else 1.0
        wid = max(weather, key=lambda i: weather[i][0])
        wtot, wbig = weather[wid][0] * dens, weather[wid][1] * dens
        fullN = min(devcap[dev], PLAYERS)
        liteN = min(PLAYERS, lod['full']) - fullN
        stack = lambda d: {k: sum(dino[(dev, d, kind)][k] for kind in ('aura', 'trail', 'mutation')) for k in keys}
        sf, sl = stack('full'), stack('lite')
        sf['alive'] += tier_spark['full']; sl['alive'] += tier_spark['lite']  # worst case: every dino is also a fused Diamond with its tier sparkle
        everyone = {k: sf[k] * fullN + sl[k] * liteN for k in keys}
        base = {'live3d': everyone['alive'] + everyone['burst'], 'big': 0, 'beams': everyone['beams'],
                'trails': everyone['trails'], 'lights': everyone['lights'], 'ui': 0}
        m1 = dict(base, live3d=base['live3d'] + wtot, big=wbig, ui=hatch_ui + ui[dev])
        m2 = dict(base, live3d=base['live3d'] + wtot, big=wbig)
        out[dev] = [
            ('15-egg reveal (Legendary Shiny + mutation) + worst weather %s + %d players with aura+trail+mutation' % (wid, PLAYERS), m1),
            ('open world: %d players with aura+trail+mutation, worst weather %s' % (PLAYERS, wid), m2),
            ('aura party: %d players, clear sky' % PLAYERS, base),
        ]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', default='luau')
    ap.add_argument('--input', help='optional fx_probe.client.luau TSV from Studio, checked against the same budgets')
    ap.add_argument('--list', action='store_true', help='print the static source inventory only')
    a = ap.parse_args()
    inv, missing = scan_sources()
    print('Source inventory (Instance.new / acquire per class; max Rate literal; Emit calls)')
    for path, c, rate, emits in inv:
        print('  %-44s %s rate<=%g emit=%d' % (path, ' '.join('%s=%d' % (k[:6], v) for k, v in c.items() if v), rate, emits))
    for m in missing:
        print('  (not in this build: %s)' % m)
    if a.list:
        return
    fails = 0
    for dev, items in moments(run_model(a.runner)).items():
        b = BUDGETS[dev]
        print('\n%s budget %s' % (dev.upper(), b))
        for name, m in items:
            over = [k for k in b if m.get(k, 0) > b[k] + 1e-6]
            print('  %-4s %s\n       %s' % ('FAIL' if over else 'ok', name, ' '.join('%s=%g/%g' % (k, round(m[k], 1), b[k]) for k in b)))
            fails += len(over)
    if a.input:
        for line in Path(a.input).read_text(encoding='utf-8').splitlines():
            p = line.split('\t')
            if p[0] == 'MOMENT' and p[1] in BUDGETS:
                vals = {x.split('=')[0]: float(x.split('=')[1]) for x in p[3:] if '=' in x}
                over = [k for k in BUDGETS[p[1]] if vals.get(k, 0) > BUDGETS[p[1]][k]]
                print('  probe %s %s: %s' % (p[1], p[2], 'FAIL ' + ','.join(over) if over else 'ok'))
                fails += len(over)
    if fails:
        sys.exit('FX budget exceeded in %d place(s): lower a rate/count or change the PROVISIONAL budget with evidence (docs/123 s6)' % fails)
    print('\nFX budget report passed (PROVISIONAL budgets; real numbers still need tools/qa/fx_probe.client.luau in Studio)')


if __name__ == '__main__':
    main()
