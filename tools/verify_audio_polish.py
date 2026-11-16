#!/usr/bin/env python3
"""BD-1218 + BD-1219 (docs/242 benchmark gaps 3 and 4): music beds, sounds for the silent cues and dino footsteps behind
Config.AudioPolishEnabled.

Runs the REAL Shared/AudioPolish, Sfx and SfxRules in the pinned Luau runtime and checks: every fill targets an existing empty Sfx slot and
every one of the 14 benchmark slots is filled; volumes stay calm (docs/87: beds 0.1-0.3, cues <= 0.5, steps <= 0.2); apply() fills the
slots, adds the window pops, points the crystal alias at crystal_cue and keeps spaced rattles, while the default rules still drop them;
the bed choice (hatch > island > home), the crossfade step and sound-off fade; surfaces and the step cadence; the rare celebration sound.
Source guards: every id is a Roblox-licensed Creator Store id listed in docs/77 with its source; the flag ships false (once), is pinned off
in the default profile, ON in the playtest profile, in the rehearsal list and the manifest; the client script returns on its first lines with
the flag off and attaches every Sound to the mixer; Bootstrap and the hatch files are not touched; client sound only (no remote, no
DataStore). NOT a listening test: nobody heard these sounds (Studio load evidence: docs/evidence/2026-11-16-audio).
Usage: python tools/verify_audio_polish.py --runner luau.exe"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
POLISH = 'src/shared/AudioPolish.luau'
CLIENT = 'src/client/AudioPolish.client.luau'
BENCHMARK_SLOTS = ['hatch_rattle', 'hatch_burst', 'rare_hatch_fanfare', 'mutation_dewdrop_reveal', 'mutation_charged_reveal',
                   'mutation_frost_reveal', 'mutation_seismic_reveal', 'mutation_ember_reveal', 'mutation_aurora_reveal',
                   'mutation_bloodmoon_reveal', 'defeat_soft', 'cracked_fail', 'crystal_cue', 'nest_open_cue']


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def module(text):
    return '(function()\n' + text + '\nend)()'


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
local SLOTS = {SLOTS}
check(#SLOTS == 14, "14 benchmark slots")
for _, name in SLOTS do
    check(S.Sounds[name] ~= nil and S.Sounds[name].id == "", "default build keeps the slot empty: " .. name)
    check(A.Fills[name] ~= nil, "slot filled: " .. name)
end
for name, f in A.Fills do
    check(S.Sounds[name] ~= nil, "fill targets an existing Sfx slot: " .. name)
    check(S.normalizeId(f.id) ~= nil, "valid id: " .. name)
    check(f.volume > 0 and f.volume <= .5, "calm cue volume: " .. name)
    check(f.rate >= .75 and f.rate <= 1.2, "rate bounded: " .. name)
end
for _, name in {"ui_open", "ui_close"} do check(S.Sounds[name] and S.Sounds[name].id == "" and A.Fills[name] and A.Fills[name].volume <= .25, "quiet window pop slot: " .. name) end
for _, name in A.MusicOrder do
    local m = A.Music[name]
    check(m ~= nil and S.normalizeId(m.id) ~= nil and m.volume >= .1 and m.volume <= .3, "calm bed: " .. name)
end
check(A.Music.hatch.volume < A.Music.island.volume and A.Music.hatch.volume < A.Music.home.volume, "softer under the hatch")
for name, st in A.Steps do
    check(#st.ids >= 1 and st.volume <= .2, "quiet steps: " .. name)
    for _, id in st.ids do check(S.normalizeId(id) ~= nil, "step id: " .. name) end
end
-- bed choice and crossfade
check(A.musicTarget("Island", "") == "island", "island bed")
check(A.musicTarget("Sanctuary", "") == "home" and A.musicTarget(nil, "") == "home", "home bed")
check(A.musicTarget("Island", "hatch") == "hatch" and A.musicTarget("Sanctuary", "hatch") == "hatch", "hatch bed wins")
check(A.musicTarget("Island", "shop") == "island", "a menu keeps the place bed")
local t = A.bedTargets("island", true)
check(t.island == A.Music.island.volume and t.home == 0 and t.hatch == 0, "one bed at a time")
local off = A.bedTargets("island", false)
check(off.island == 0 and off.home == 0 and off.hatch == 0, "sound off fades every bed")
local level, steps = 0, 0
while level < A.Music.island.volume and steps < 1000 do level = A.step(level, A.Music.island.volume, 1 / 60, A.Music.island.volume) steps += 1 end
check(math.abs(steps / 60 - A.FadeSeconds) < .1, "full fade in FadeSeconds")
check(A.step(.2, 0, 100, .2) == 0 and A.step(0, .2, 100, .2) == .2, "never overshoots")
-- footsteps
check(A.surface("Grass") == "soft" and A.surface("LeafyGrass") == "soft" and A.surface("Plastic") == "soft", "soft default")
check(A.surface("Sand") == "sand" and A.surface("Rock") == "rock" and A.surface("WoodPlanks") == "wood" and A.surface("Snow") == "snow", "surfaces")
check(A.surface("Air") == nil and A.surface(nil) == nil, "no steps in the air")
check(A.surface("Air", true) == "water" and A.surface("Grass", true) == "water", "swimming = water")
check(A.stepInterval(0) == nil and A.stepInterval(2) == nil and A.stepInterval(0 / 0) == nil, "standing = no steps")
local fast, slow = A.stepInterval(40), A.stepInterval(10)
check(fast ~= nil and slow ~= nil and fast < slow and fast >= A.StepMin, "faster = quicker steps, bounded")
check((A.stepInterval(16, 2) :: number) > (A.stepInterval(16, 1) :: number), "a bigger dino steps slower")
-- rare celebration sound
check(A.rareSound("", {kind = "secret"}) == "", "secret stays silent")
check(A.rareSound("shiny_bang", {kind = "mutation", mutationId = "frost"}) == "mutation_frost_reveal", "mutation reveal")
check(A.rareSound("shiny_bang", {mutation = true, mutationId = "Bloodmoon"}) == "mutation_bloodmoon_reveal", "case-insensitive id")
check(A.rareSound("shiny_bang", {kind = "mutation", mutationId = "nope"}) == "rare_hatch_fanfare", "unknown mutation = fanfare")
check(A.rareSound("shiny_bang", {kind = "shiny"}) == "rare_hatch_fanfare", "other finds = fanfare")
-- rattles: dropped by default, kept (spaced, never moving the cracks) after apply
local raw = {{t = 1, name = "hatch_rattle"}, {t = 1.1, name = "hatch_rattle"}, {t = 1.5, name = "hatch_crack_stage"}, {t = 1.6, name = "hatch_rattle"}, {t = 3, name = "hatch_burst"}}
local function names(cues) local out = {} for _, c in cues do table.insert(out, c.name) end return out end
local function count(cues, n) local k = 0 for _, c in cues do if c.name == n then k += 1 end end return k end
local before = R.hatchCues(raw, 3)
check(count(before, "hatch_rattle") == 0, "default rules drop rattles")
local nFills = 0 for _ in A.Fills do nFills += 1 end
local filled = A.apply(S, R)
check(filled == nFills and nFills == 16, "apply fills the 14 benchmark slots + 2 window pops (got " .. filled .. ")")
for _, name in SLOTS do check(S.Sounds[name].id ~= "", "filled after apply: " .. name) end
check(S.Sounds.ui_open.id ~= "" and S.Sounds.ui_close.id ~= "" and R.priority("ui_open") <= 10, "window pops filled, lowest priority")
check(R.Aliases.crystal_reward.cue == "crystal_cue", "crystal alias uses crystal_cue")
check(A.apply(S, R) == 0, "apply is idempotent")
local after = R.hatchCues(raw, 3)
check(count(after, "hatch_rattle") == 1, "one spaced rattle kept (got " .. count(after, "hatch_rattle") .. ")")
local crackBefore, crackAfter
for _, c in before do if c.name == "hatch_crack_stage" then crackBefore = c.t end end
for _, c in after do if c.name == "hatch_crack_stage" then crackAfter = c.t end end
check(crackBefore == crackAfter, "a rattle never moves the cracks")
if #fails > 0 then for _, f in fails do print("FAIL: " .. f) end error("audio polish checks failed") end
print("Audio polish checks passed")
'''


def luau_body():
    return LUAU.replace('{SLOTS}', '{' + ', '.join('"%s"' % s for s in BENCHMARK_SLOTS) + '}')


def static_checks():
    errors = []
    polish, client = read(POLISH), read(CLIENT)
    registry = read('docs/77-asset-registry.md')
    ids = sorted(set(re.findall(r'rbxassetid://(\d+)', polish)))
    if len(ids) < 20:
        errors.append('expected 20+ distinct ids in %s, found %d' % (POLISH, len(ids)))
    for i in ids:
        rows = [line for line in registry.split('\n') if line.startswith('|') and ('| %s |' % i) in line]
        if not rows:
            errors.append('id %s has no docs/77 row' % i)
        elif not any('APMOfficial' in r or 'ProSoundEffects' in r for r in rows):
            errors.append('id %s: docs/77 row must name its Roblox-licensed source (APMOfficial / ProSoundEffects)' % i)
    config = read('src/shared/Config.luau')
    if len(re.findall(r'^    AudioPolishEnabled = false,$', config, re.M)) != 1:
        errors.append('Config.AudioPolishEnabled must ship false exactly once')
    profiles = read('tools/release_profiles.py')
    for needle in ('_flag_off("AudioPolishEnabled",', 'Rule("AudioPolishEnabled", "set", True,', '("AudioPolishEnabled", "BD-1218'):
        if needle not in profiles:
            errors.append('release_profiles.py is missing %s' % needle)
    if '"AudioPolishEnabled"' not in read('tools/release_playtest.py'):
        errors.append('the playtest manifest must show AudioPolishEnabled')
    head = '\n'.join(client.split('\n')[:12])
    if 'if Config.AudioPolishEnabled ~= true then return end' not in head:
        errors.append('the client script must return on its first lines with the flag off')
    if client.count('Instance.new("Sound")') > client.count('Mixer.attach('):
        errors.append('every Sound in the client script must go through AudioMixer.attach')
    for needle in ('Mixer.attach(sound, "music")', 'Mixer.attach(s, "sfx")', 'Theme.HatchSoundEnabled', 'Sfx.Master'):
        if needle not in client:
            errors.append('client script must use %s' % needle)
    for banned in ('RemoteEvent', 'FireServer', 'DataStore', 'InvokeServer'):
        if banned in client or banned in polish:
            errors.append('client sound only: %s found' % banned)
    for path in ['src/client/Bootstrap.client.luau', 'src/client/HatchSequence.luau'] + [str(p.relative_to(ROOT)).replace('\\', '/') for p in (ROOT / 'src').rglob('HatchStage*.luau')]:
        if 'AudioPolish' in read(path):
            errors.append('%s must not mention AudioPolish (owned elsewhere)' % path)
    rare = read('src/client/RareHatchClient.client.luau')
    if 'if Config.AudioPolishEnabled == true then plan.sound = require(Shared:WaitForChild("AudioPolish")).rareSound(plan.sound, data) end' not in rare:
        errors.append('RareHatchClient must pick the rare sound through AudioPolish only with the flag on')
    if 'R.KeepRattle = false' not in read('src/shared/SfxRules.luau'):
        errors.append('SfxRules must keep dropping rattles by default')
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    problems = static_checks()
    for p in problems:
        print('FAIL:', p)
    source = ('local S=' + module(read('src/shared/Sfx.luau')) + '\nlocal R=' + module(read('src/shared/SfxRules.luau')) +
              '\nlocal A=' + module(read(POLISH)) + '\n' + luau_body())
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'audio_polish.luau'
        path.write_text(source, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    print(result.stdout, end='')
    if result.returncode or 'Audio polish checks passed' not in result.stdout or problems:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode or 1)


if __name__ == '__main__':
    main()
