"""Settings v2 checks (BD-263..266): pure model in src/shared/SettingsModel.luau plus static wiring checks.

Runs the model with the pinned Luau runtime (defaults, clamps, old profile without the field, save/load roundtrip,
tab list, Fast mode, change listeners) and checks the menu, sync, server field and consumers are wired.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_sources  # noqa: E402  (docs/150: ProfileRepository plus its parts)

BODY = r'''
local D = M.Defaults
-- tabs
assert(#M.Tabs == 4 and M.Tabs[1] == "sound" and M.Tabs[2] == "look" and M.Tabs[3] == "controls" and M.Tabs[4] == "help", "four tabs in order")
for _, id in M.Tabs do assert(M.TabLabels[id], "label for " .. id) end
-- defaults: Full everywhere, calm off, mixer defaults
local d = M.normalize(nil)
assert(d.effects == "full" and d.weather == "full" and d.calm == false and d.jumpSize == "normal")
assert(d.master == 0.8 and d.sfx == 0.7 and d.ambience == 0.6)
-- migration: a profile saved before settings v2 has no field; junk anywhere falls back to defaults
assert(M.equal(M.fromStore(nil), d), "old profile reads as defaults")
assert(M.equal(M.fromStore("junk"), d) and M.equal(M.fromStore(5), d) and M.equal(M.fromStore({}), d))
local bad = M.normalize({sound = {master = "loud", sfx = 0 / 0, ambience = {}}, effects = "ultra", weather = 7, calm = "yes", jumpSize = "huge"})
assert(M.equal(bad, d), "bad values fall back to defaults")
-- clamps and snapping
local c = M.normalize({sound = {master = 5, sfx = -3, ambience = 0.54}})
assert(c.master == 1 and c.sfx == 0 and c.ambience == 0.5, "volume clamps to 0..1 and snaps to tenths")
-- save / load roundtrip (plain primitive table, idempotent)
local s = M.normalize({sound = {master = 0.3, sfx = 0.2, ambience = 1}, effects = "lite", weather = "off", calm = true, jumpSize = "big"})
local store = M.toStore(s)
assert(store.v == 1 and store.sound.master == 0.3 and store.effects == "lite" and store.weather == "off" and store.calm == true and store.jumpSize == "big")
assert(M.equal(M.fromStore(store), s), "roundtrip keeps every value")
assert(M.equal(M.fromStore(M.toStore(M.fromStore(store))), s), "roundtrip is idempotent")
-- runtime value + listeners
local seen = 0
M.onChange(function() seen += 1 end)
assert(M.effects() == "full" and M.weather() == "full" and M.calm() == false)
M.set("effects", "lite") assert(M.effects() == "lite" and seen == 1)
M.set("effects", "lite") assert(seen == 1, "no change, no event")
M.set("effects", "nonsense") assert(M.effects() == "lite", "bad value ignored")
M.set("weather", "off") assert(M.weather() == "off")
M.set("calm", true) assert(M.calm() == true)
M.set("master", 0.35) assert(M.get().master == 0.4 or M.get().master == 0.3, "volume snaps")
M.set("master", "x") assert(M.get().master <= 0.4)
M.set("jumpSize", "big") assert(M.jumpSize() == "big")
-- Fast mode switch: Lite + Lite on, Full + Full off; derived, never stored
M.set("fast", true) assert(M.effects() == "lite" and M.weather() == "lite" and M.isFast(M.get()))
M.set("effects", "full") assert(not M.isFast(M.get()), "changing one by hand ends Fast mode")
M.set("fast", false) assert(M.effects() == "full" and M.weather() == "full")
-- particle factors: Lite is half, Off is none, unknown is full
assert(M.factor("full") == 1 and M.factor("lite") == 0.5 and M.factor("off") == 0 and M.factor(nil) == 1 and M.factor("x") == 1)
-- BD-349: Weather level -> emitter share used by WeatherVisuals; Calm is independent of the level and applies via Theme.MotionEnabled
M.reset() M.set("weather", "lite") assert(M.factor(M.weather()) == 0.5 and not M.calm())
M.set("weather", "off") assert(M.factor(M.weather()) == 0)
M.set("weather", "full") M.set("calm", true) assert(M.factor(M.weather()) == 1 and M.calm() == true)
M.reset() assert(M.equal(M.get(), d), "reset restores defaults")
print("Settings checks passed: tabs, defaults, clamps, old-profile migration, roundtrip, fast mode, factors")
'''


def static_checks():
    errors = []
    read = lambda p: (ROOT / p).read_text(encoding='utf-8')
    boot = read('src/client/Bootstrap.client.luau')
    if 'SettingsMenu' not in boot:
        errors.append('Bootstrap settings screen must use SettingsMenu')
    if re.search(r'^local (SettingsMenu|SettingsModel|Settings)\b', boot, re.M):
        errors.append('Bootstrap.client is at the 200-local limit: no new top-level locals')
    menu = read('src/client/SettingsMenu.luau')
    for tab in ('drawSound', 'drawLook', 'drawControls'):
        if tab not in menu:
            errors.append('SettingsMenu is missing ' + tab)
    for needle in ('"Effects"', '"Weather"', '"Calm motion"', '"Fast mode"'):
        if needle not in menu:
            errors.append('Look tab is missing ' + needle)
    if not re.search(r'ROW = 56', menu) or not re.search(r'48', menu):
        errors.append('controls must be 48 px high (44 px touch minimum)')
    if 'ProfileRepository' in menu:
        errors.append('menu must not touch the server module')
    repo = profile_sources.repository_text()
    if 'function ProfileRepository.setSettings' not in repo or 'SettingsJson' not in repo or 'profile.settings' not in repo:
        errors.append('ProfileRepository must save profile.settings and publish SettingsJson')
    if 'ProfileSchemaVersion = 1' not in read('src/shared/Config.luau'):
        errors.append('settings are an additive field: ProfileSchemaVersion must not change')
    if 'SetSettings' not in read('src/server/ChestService.luau'):
        errors.append('server needs the SetSettings remote')
    sync = read('src/client/SettingsSync.client.luau')
    if 'Theme.MotionEnabled = not s.calm' not in sync or 'SetSettings' not in sync:
        errors.append('SettingsSync must wire Calm motion to Theme.MotionEnabled and send changes')
    if 'SettingsModel' not in read('src/client/WeatherVisuals.client.luau'):
        errors.append('WeatherVisuals must read the Weather setting')
    if 'SettingsModel' not in read('src/client/CosmeticVisuals.client.luau'):
        errors.append('CosmeticVisuals must read the Effects setting')
    if 'EffectsLod' not in read('src/client/CosmeticVisuals.client.luau'):
        errors.append('CosmeticVisuals must use EffectsLod distance LOD (BD-095)')
    return errors


LOD_BODY = r'''
-- BD-095 distance LOD: Full keeps today's behaviour, Lite shrinks the bands, Off keeps only the mutation cue
assert(L.detail("full", "aura", 10, false, 1, 3) == "full" and L.detail("full", "aura", 10, false, 4, 3) == "lite")
assert(L.detail("full", "aura", 100, false, 1, 3) == "lite" and L.detail("full", "aura", 181, false, 1, 3) == "none")
assert(L.detail("full", "aura", 500, true, 99, 3) == "full", "own dino is never culled and keeps full detail")
assert(L.detail("lite", "aura", 5, false, 1, 3) == "lite" and L.detail("lite", "aura", 81, false, 1, 3) == "none")
assert(L.detail("lite", "aura", 5, true, 1, 3) == "lite", "Lite never uses the full layer count")
assert(L.detail("lite", "aura", 5, false, 7, 3) == "none", "Lite caps the number of dinos with effects")
assert(L.detail("off", "aura", 1, true, 1, 3) == "none" and L.detail("off", "trail", 1, false, 1, 3) == "none")
assert(L.detail("off", "mutation", 1, false, 1, 3) == "lite" and L.detail("off", "mutation", 61, false, 1, 3) == "none")
assert(L.detail("bogus", "aura", 10, false, 1, 3) == "full", "unknown mode reads as Full")
assert(L.visible("full", 100, false, 1) and not L.visible("full", 200, false, 1) and L.visible("off", 10, false, 1) and not L.visible("off", 70, false, 1))
-- Lite never costs more than Full at any distance (monotonic)
local rank = {none = 0, lite = 1, full = 2}
for d = 0, 220, 5 do for r = 1, 14 do for _, own in {true, false} do
    assert(rank[L.detail("lite", "aura", d, own, r, 3)] <= rank[L.detail("full", "aura", d, own, r, 3)])
    assert(rank[L.detail("off", "aura", d, own, r, 3)] <= rank[L.detail("lite", "aura", d, own, r, 3)])
end end end
print("Effects LOD checks passed: bands, caps, own dino, Off mutation cue, monotonic")
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    problems = static_checks()
    for problem in problems:
        print('FAIL:', problem)
    source = '(function()\n' + (ROOT / 'src/shared/SettingsModel.luau').read_text(encoding='utf-8') + '\nend)()'
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'settings.luau'
        path.write_text('local M=' + source + '\n' + BODY, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout or problems:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
        lod = '(function()' + chr(10) + (ROOT / 'src/shared/EffectsLod.luau').read_text(encoding='utf-8') + chr(10) + 'end)()'
        lpath = Path(tmp) / 'lod.luau'
        lpath.write_text('local L=' + lod + chr(10) + LOD_BODY, encoding='utf-8')
        lres = subprocess.run([args.runner, str(lpath)], capture_output=True, text=True, encoding='utf-8')
        print(lres.stdout, end='')
        if lres.returncode or 'passed' not in lres.stdout:
            print(lres.stderr)
            raise SystemExit(lres.returncode or 1)
