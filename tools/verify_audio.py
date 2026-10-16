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


# BD-339/341/342: pure rules from src/shared/SfxRules.luau (offline: nobody has listened to the result).
RULES_BODY = r'''
local function v(n, e, s, vol) return {name = n, endsAt = e, startedAt = s, volume = vol} end
assert(R.MaxVoices == 2)
assert(R.limit({}, "pickup", 10) == "play")
assert(R.limit({v("pickup", 11, 10, .2)}, "ui_click", 10) == "play")
assert(R.limit({v("pickup", 11, 10, .2), v("shop_buy", 11, 10, .3)}, "ui_click", 10) == "drop", "third normal cue dropped")
assert(R.limit({v("pickup", 10.4, 10, .2), v("shop_buy", 11, 10, .3)}, "ui_click", 10.5) == "play", "finished cues free a voice")
local action, idx = R.limit({v("shop_buy", 12, 10, .3), v("pickup", 12, 10, .2)}, "hatch_reveal_epic", 10.5)
assert(action == "replace" and idx == 2, "important cue replaces the lowest priority")
action, idx = R.limit({v("level_up", 12, 10, .4), v("run_end", 12, 10, .2)}, "hatch_reveal_rare", 10.5)
assert(action == "replace" and idx == 2, "replaces run_end")
assert(R.limit({v("hatch_reveal_rare", 12, 10, .7), v("fusion_reveal", 12, 10, .7)}, "run_end", 10.5) == "drop", "lower than both: dropped")
action, idx = R.limit({v("level_up", 12, 10, .4), v("level_up", 12, 11, .4)}, "level_up", 11.5)
assert(action == "replace" and idx == 1, "equal priority: oldest replaced")
local order = {"hatch_reveal_rare", "fusion_reveal", "level_up", "run_end", "shop_buy", "weather_start", "pickup", "ui_click"}
for i = 1, #order - 1 do assert(R.priority(order[i]) > R.priority(order[i + 1]), order[i]) end
for name in S.Sounds do assert(R.Priority[name], "every cue has a priority: " .. name) end
assert(R.duck("hatch_reveal_epic", "pickup") == .6 and R.duck("level_up", "ui_click") == .6, "40% duck")
assert(R.duck("pickup", "ui_click") == 1 and R.duck("shop_buy", "pickup") == 1, "unimportant cues do not duck")
assert(R.duck("run_end", "hatch_reveal_epic") == 1, "never ducks a higher priority cue")
assert(R.deduped("level_up", 10, 10.5) and not R.deduped("level_up", 10, 10.9) and not R.deduped("level_up", nil, 10))
assert(not R.deduped("run_end", 10, 10.1))
for _, n in {"pickup", "ui_click", "hatch_crack", "level_up"} do
    local seen = {}
    for i = 1, 200 do
        local j = R.jitter(n, i)
        assert(j >= .96 - 1e-9 and j <= 1.04 + 1e-9, "jitter range")
        assert(j == R.jitter(n, i), "deterministic")
        seen[string.format("%.4f", j)] = true
    end
    local count = 0 for _ in seen do count += 1 end
    assert(count > 20, "jitter varies: " .. n)
end
assert(R.jitter("hatch_reveal_epic", 3) == 1 and R.jitter("fusion_reveal", 3) == 1)
local alias = R.Aliases.crystal_reward
assert(alias and S.Sounds[alias.cue] and alias.volume < 1 and alias.cooldown >= 1)
local function names(c) local t = {} for _, x in c do table.insert(t, x.name) end return t end
local raw = {{t = 1, name = "hatch_rattle"}, {t = 1.5, name = "hatch_crack_stage"}, {t = 1.6, name = "hatch_crack_stage"}, {t = 2, name = "hatch_crack_stage"}, {t = 3, name = "hatch_burst"}, {t = 3.12, name = "hatch_reveal_common"}, {t = 0.5, name = "pickup"}}
local common = R.hatchCues(raw, 1)
local stages, last = 0, -1e9
for _, c in common do
    if c.name == "hatch_crack_stage" then stages += 1 end
    if string.sub(c.name, 1, 6) == "hatch_" then assert(c.t - last >= R.HatchStagger - 1e-9, "stagger " .. c.name) last = c.t end
end
assert(stages == 1, "Common keeps one stage crack")
assert(not table.find(names(common), "hatch_rattle") and table.find(names(common), "hatch_reveal_common") and table.find(names(common), "pickup"))
local rs = 0 for _, c in R.hatchCues(raw, 3) do if c.name == "hatch_crack_stage" then rs += 1 end end
assert(rs == 3 and R.hatchStack(1).chime == false and R.hatchStack(3).chime and R.hatchStack(5).chime, "rarity escalates")
assert(R.hatchStack(1).stages <= R.hatchStack(2).stages and R.hatchStack(2).stages <= R.hatchStack(5).stages)
local revealT, burstT
for _, c in R.hatchCues({{t = 3, name = "hatch_burst"}, {t = 3.12, name = "hatch_reveal_rare"}}, 3) do if c.name == "hatch_reveal_rare" then revealT = c.t end if c.name == "hatch_burst" then burstT = c.t end end
assert(revealT - burstT >= .3 - 1e-9, "reveal does not start with the burst")
-- BD-437 reveal ladder: strictly rising pitch and volume across the five stings, Epic/Legendary layers use REGISTERED cues.
local prevRate, prevVol = 0, 0
for i, n in S.RevealNames do
    local e = S.Sounds[n]
    assert(e.rate > prevRate and e.volume > prevVol, "reveal ladder steps up at tier " .. i)
    assert(e.rate >= .9 and e.rate <= 1.15 and e.volume <= S.MaxCueVolume, "bounded pitch and volume")
    prevRate, prevVol = e.rate, e.volume
    assert(R.priority(n) == 100, "every reveal sting keeps top priority")
end
assert(#R.layers("hatch_reveal_common") == 0 and #R.layers("hatch_reveal_uncommon") == 0 and #R.layers("hatch_reveal_rare") == 0, "no layers below Epic")
for _, n in {"hatch_reveal_epic", "hatch_reveal_legendary"} do
    local ls = R.layers(n)
    assert(#ls == 1, "exactly one layer keeps within the 2-voice limit")
    for _, l in ls do assert(S.Sounds[l.cue] and S.Sounds[l.cue].id ~= "" and l.delay >= .1 and l.delay <= .4 and l.volume <= 1, "layer is an existing cue, delayed") end
    assert(R.duck(ls[1].cue, n) == 1, "a layer never ducks its own main sting")
end
print("Sfx rules checks passed: limiter, priority, duck, dedupe, jitter, hatch stack, reveal ladder")
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
    sfx_src = read('src/shared/Sfx.luau')
    for needle in ('R.limit(active', 'R.duck(', 'R.jitter(', 'R.deduped(', 'Sfx.playAlias'):
        if needle not in sfx_src:
            errors.append('BD-339/342: Sfx must apply SfxRules (%s)' % needle)
    if 'SfxRules.hatchCues' not in read('src/client/HatchSequence.luau'):
        errors.append('BD-341: HatchSequence must stagger cues through SfxRules.hatchCues')
    if 'Sfx.playAlias("crystal_reward")' not in boot:
        errors.append('BD-342: crystal reward cue missing')
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

    # BD-339/341/342 pure rules.
    with tempfile.TemporaryDirectory() as tmp:
        sfx = (ROOT / 'src/shared/Sfx.luau').read_text(encoding='utf-8')
        rules = (ROOT / 'src/shared/SfxRules.luau').read_text(encoding='utf-8')
        path = Path(tmp) / 'rules.luau'
        path.write_text('local S=(function()' + chr(10) + sfx + chr(10) + 'end)()' + chr(10) + 'local R=(function()' + chr(10) + rules + chr(10) + 'end)()' + chr(10) + RULES_BODY, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'Sfx rules checks passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
