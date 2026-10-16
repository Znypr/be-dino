"""Audio mixer checks (src/shared/AudioMixer.luau, src/client/VolumeSliders.luau).

Executes the pure mixer maths with the pinned Luau runtime (defaults, clamping/snapping, master x channel, percent text,
slider fraction) and statically checks that every game sound is routed through a SoundGroup: Sfx.play, HatchPresentation and
WeatherAudio. Levels are session-only (no profile field). Studio checks: docs/93-settings-audio-admin.md.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]

BODY = r'''
local D = M.Defaults
assert(D.master == 0.8 and D.sfx == 0.7 and D.ambience == 0.6, "defaults 0.8 / 0.7 / 0.6")
for _, key in M.Order do assert(M.get(key) == D[key], "starts at default " .. key) end
assert(M.clamp(2) == 1 and M.clamp(-1) == 0 and M.clamp(0.54) == 0.5 and M.clamp(0.56) == 0.6, "clamp and snap to 0.1")
assert(M.clamp("x", 0.3) == 0.3 and M.clamp(0 / 0, 0.4) == 0.4 and M.clamp(nil) == 0, "bad input keeps the fallback")
assert(math.abs(M.effective(0.8, 0.7, 0.5) - 0.28) < 1e-9, "master x channel x base")
assert(M.effective(2, 2, 0.5) == 0.5 and M.effective(0, 1, 1) == 0, "levels clamp to 0..1; master 0 mutes")
assert(M.percent(0.8) == "80%" and M.percent(0) == "0%" and M.percent(1) == "100%")
assert(M.fromFraction(0.31) == 0.3 and M.fromFraction(5) == 1 and M.fromFraction(-5) == 0)
assert(M.set("sfx", 0.35) == 0.4 or M.get("sfx") == 0.4, "set snaps")
assert(M.set("nope", 1) == 0 and M.get("nope") == 0, "unknown channel ignored")
local before = M.get("master")
assert(M.set("master", "loud") == before, "non-number leaves the level alone")
M.reset() assert(M.get("master") == 0.8 and M.get("sfx") == 0.7 and M.get("ambience") == 0.6, "reset restores defaults")
assert(M.group("sfx") == nil, "no SoundGroups outside Roblox, and no error")
print("Audio mixer checks passed: defaults, clamp/snap, master x channel, percent, fraction, reset")
'''

# BD-258: reward cues play one at a time (pure Sfx.cueSlot); run_end stays first and the soft chime is kept.
CUE_BODY = r'''
local gap, wait = S.CueGap, S.CueMaxWait
assert(gap >= .6, "stagger is at least 0.6 s")
local start, free = S.cueSlot(0, 10, .6)
assert(start == 10 and free > 10.6, "idle: the cue starts now")
-- run_end (0.6 s) at t=10, then level_up in the same instant: it waits until the chime is over.
local s2, free2 = S.cueSlot(free, 10, 1.5)
assert(s2 ~= nil and s2 >= 10 + gap and s2 >= free, "second cue starts after the first chime")
-- a third cue (nest opened) queues behind the second, never on top of it
local s3 = S.cueSlot(free2, 10, 1.5)
assert(s3 ~= nil and s3 >= free2 and s3 - 10 >= 2 * gap)
-- a long backlog drops the cue instead of playing it seconds late
assert(S.cueSlot(10 + wait + 1, 10, 1) == nil, "too late: dropped")
-- far in the future the slot is free again
assert(S.cueSlot(free2, 100, 1) == 100)
-- The cue table: the run end chime is short and soft, level_up stays quiet.
assert(S.Sounds.run_end.len <= .7 and S.Sounds.run_end.volume <= .25 and S.Sounds.level_up.len >= 1)
-- BD-081 audit: global rapid throttle for pickups, volume clamp.
assert(S.rapidThrottled("pickup", 10, 10.05) and S.rapidThrottled("pickup_hi", 10, 10.05), "variants share the throttle")
assert(not S.rapidThrottled("pickup", 10, 10 + S.RapidGap + .01) and not S.rapidThrottled("pickup", nil, 10))
assert(not S.rapidThrottled("shop_buy", 10, 10.01), "other cues are unaffected")
assert(S.clampVolume(2) == S.MaxCueVolume and S.clampVolume(.3) == .3 and S.clampVolume(-1) == 0)
assert(S.MaxCueVolume <= .9)
for _, e in S.Sounds do assert(e.gap >= 0 and e.volume > 0) end
print("Reward cue checks passed: one at a time, 0.6 s stagger, drop when late")
'''


def static_checks():
    errors = []
    read = lambda p: (ROOT / p).read_text(encoding='utf-8')
    if 'attach(sound, "sfx")' not in read('src/shared/Sfx.luau'):
        errors.append('Sfx.play must route its sounds through the Sfx SoundGroup')
    if 'attach(s,"sfx")' not in read('src/shared/HatchPresentation.luau'):
        errors.append('HatchPresentation sounds must use the Sfx SoundGroup')
    if 'Mixer.attach(sound,"ambience")' not in read('src/client/WeatherAudio.client.luau'):
        errors.append('WeatherAudio must route beds and accents through the Ambience SoundGroup')
    # Nothing may create a Sound without going through the mixer.
    for path in sorted((ROOT / 'src').rglob('*.luau')):
        text = path.read_text(encoding='utf-8')
        if 'Instance.new("Sound")' in text and 'attach(' not in text:
            errors.append('%s creates a Sound without AudioMixer.attach' % path.relative_to(ROOT))
    boot = read('src/client/Bootstrap.client.luau')
    if 'SettingsMenu' not in boot or 'VolumeSliders' not in read('src/client/SettingsMenu.luau') or 'AudioMixer' not in read('src/client/SettingsMenu.luau'):
        errors.append('Settings must show the volume sliders')
    if boot.count('Sfx.playCue("run_end")') != 1 or boot.count('Sfx.playCue("level_up")') < 2 or 'Sfx.play("run_end")' in boot or 'Sfx.play("level_up")' in boot:
        errors.append('BD-258: run_end and level_up must go through Sfx.playCue (one reward cue at a time)')
    if re.search(r'^local (VolumeSliders|AudioMixer|Mixer)\b', boot, re.M):
        errors.append('Bootstrap.client is at the 200-local limit: no new top-level locals')
    return errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    problems = static_checks()
    for problem in problems:
        print('FAIL:', problem)
    source = '(function()\n' + (ROOT / 'src/shared/AudioMixer.luau').read_text(encoding='utf-8') + '\nend)()'
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'audio.luau'
        path.write_text('local M=' + source + '\n' + BODY, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout or problems:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)

    # Pure cue scheduling from src/shared/Sfx.luau (Roblox services are only touched inside Sfx.play, never at require time).
    with tempfile.TemporaryDirectory() as tmp:
        sfx = (ROOT / 'src/shared/Sfx.luau').read_text(encoding='utf-8')
        path = Path(tmp) / 'cue.luau'
        path.write_text('local S=(function()' + chr(10) + sfx + chr(10) + 'end)()' + chr(10) + CUE_BODY, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'Reward cue checks passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
