#!/usr/bin/env python3
"""BD-1247 warmer light and atmosphere (Config.WarmLightEnabled, src/shared/WarmLight.luau, src/client/WarmLight.client.luau), owner
2026-11-16 "game still looks empty", "Yes, build all".

Runs the REAL WarmLight rules in the pinned Luau runtime and checks:
  * enabled() needs WarmLightEnabled AND WorldV3Enabled;
  * calm (docs/87): grade saturation and contrast small (<= .25 / <= .12), a warm tint (red >= green >= blue), gentle bloom (intensity
    <= .6, threshold >= .8) and faint sun rays (<= .1); the look fades over FadeSeconds (no pops) and is 0 in any weather but clear and off
    the island;
  * motes: every World V3 zone has its motes with an uploaded texture key (EffectAssets.Requested, a real id), slow lifetimes, small sizes;
    the phone rate is at most half the desktop rate; the busiest zone stays under MOTE_CAP live particles per device class, and the
    clear-sky moment of tools/fx_budget_report.py adds them (WarmLight.liveParticles) against the live3d budgets (docs/126).
Source guards: the flag ships false, is pinned off in the default profile, ON in the playtest profile and in the rehearsal list; the client
script returns at once without the flag, writes only its own WarmGrade / WarmBloom / WarmRays (never the weather's), keeps the emitter box
anchored with no collision, touch or query, and stops the motes under Reduce Motion; Bootstrap.client and WeatherVisuals are untouched.
Usage: python tools/verify_warm_light.py --runner luau.exe"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MOTE_CAP = {'Desktop': 140, 'Tablet': 110, 'Phone': 70}  # live mote particles at once (rate x mean lifetime), busiest zone


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def module(text):
    return '(function()\n' + text + '\nend)()'


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
check(W.enabled({WarmLightEnabled = true, WorldV3Enabled = true}), "enabled with both flags")
check(not W.enabled({WarmLightEnabled = true}) and not W.enabled({WorldV3Enabled = true}) and not W.enabled(nil), "off otherwise")
local g = W.Grade
check(g.saturation > 0 and g.saturation <= .25 and g.contrast >= 0 and g.contrast <= .12 and math.abs(g.brightness) <= .05, "calm grade")
check(g.tint[1] == 255 and g.tint[1] >= g.tint[2] and g.tint[2] >= g.tint[3] and g.tint[3] >= 190, "warm, light tint")
check(W.Bloom.intensity > 0 and W.Bloom.intensity <= .6 and W.Bloom.threshold >= .8, "gentle bloom")
check(W.Rays.intensity > 0 and W.Rays.intensity <= .1, "faint sun rays")
check(W.target("clear", true) == 1 and W.target(nil, true) == 1, "on in clear weather on the island")
for _, id in {"rain", "storm", "blizzard", "volcanic", "aurora", "bloodmoon"} do check(W.target(id, true) == 0, "off in weather " .. id) end
check(W.target("clear", false) == 0, "off away from the island")
check(W.FadeSeconds >= 1.5, "slow fade")
check(math.abs(W.step(0, 1, W.FadeSeconds / 2) - .5) < 1e-6 and W.step(1, 0, 10) == 0 and W.step(.5, .5, 1) == .5, "linear fade, clamped")
for _, zone in Zones do
    local m = W.Motes[zone]
    check(m ~= nil, "motes for " .. zone)
    if m then
        local req = Fx.Requested[m.texture]
        check(req ~= nil and string.match(req.id, "^rbxassetid://%d+$") ~= nil, "uploaded texture for " .. zone .. " motes")
        check(m.life[1] >= 5 and m.life[2] <= 15 and m.size[2] <= .5, "slow, small motes in " .. zone)
        check(W.rateFor(zone, "Phone", 1) <= W.rateFor(zone, "Desktop", 1) * .5 + 1e-6, "phone rate at most half in " .. zone)
        check(W.rateFor(zone, "Desktop", 0) == 0, "no motes at weight 0")
    end
end
check(W.rateFor("nowhere", "Desktop", 1) == 0, "unknown zone: no motes")
for device, cap in Caps do check(W.liveParticles(device) <= cap, device .. " motes " .. W.liveParticles(device) .. " <= " .. cap) end
if #fails > 0 then for _, f in fails do print("FAIL: " .. f) end error("warm light checks failed") end
print(string.format("Warm light checks passed (live motes desktop %d, tablet %d, phone %d)", W.liveParticles("Desktop"), W.liveParticles("Tablet"), W.liveParticles("Phone")))
'''


def source_checks():
    errors = []
    if '    WarmLightEnabled = false,\n' not in read('src/shared/Config.luau'):
        errors.append('Config.WarmLightEnabled must ship false')
    profiles = read('tools/release_profiles.py')
    if '_flag_off("WarmLightEnabled"' not in profiles or 'Rule("WarmLightEnabled", "set", True' not in profiles or '("WarmLightEnabled", "BD-1247' not in profiles:
        errors.append('WarmLightEnabled: off in default, on in playtest, in the rehearsal list')
    client = read('src/client/WarmLight.client.luau')
    if 'if not W.enabled(Config) then return end' not in client:
        errors.append('the client script must return at once without the flag')
    for bad in ('WeatherGrade', 'WeatherBloom', 'WeatherRays', 'RemoteEvent', ':FireServer'):
        if bad in client:
            errors.append('the warm light must not touch ' + bad)
    if 'box.Anchored, box.CanCollide, box.CanTouch, box.CanQuery, box.CastShadow = true, false, false, false, false' not in client:
        errors.append('the mote box must be anchored with no collision, touch or query')
    if 'local motes = Theme.MotionEnabled and level > 0' not in client:
        errors.append('Reduce Motion must stop the motes')
    if 'WarmLight' in read('src/client/Bootstrap.client.luau') or 'WarmLight' in read('src/client/WeatherVisuals.client.luau'):
        errors.append('Bootstrap.client and WeatherVisuals must not change')
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    problems = source_checks()
    for p in problems:
        print('FAIL:', p)
    zones = re.findall(r'\{id = "(\w+)", name =', read('src/shared/WorldV3.luau'))
    source = ('local W=' + module(read('src/shared/WarmLight.luau')) + '\nlocal Fx=' + module(read('src/shared/EffectAssets.luau')) +
              '\nlocal Zones={' + ','.join('"%s"' % z for z in zones) + '}' +
              '\nlocal Caps={' + ','.join('%s=%d' % kv for kv in MOTE_CAP.items()) + '}\n' + LUAU)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'warm.luau'
        path.write_text(source, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    print(result.stdout, end='')
    if result.returncode or 'Warm light checks passed' not in result.stdout or problems:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode or 1)


if __name__ == '__main__':
    main()
