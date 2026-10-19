#!/usr/bin/env python3
"""BD-1124 (docs/202 R11 and R12, docs/220): short timer words on the HUD, potion drain bars and the big "Found 1/22" bar of the Index
(Config.TimerChipsEnabled). Executes the pure rules of src/shared/TimerWords.luau with the pinned Luau runtime (flag off = the Build 020
sentences, flag on = the short words; kid words of docs/72), checks the wiring in the client files statically (Bootstrap hands the weather
and potion lines to HudTimers; PotionChips draws the drain bar from TimerWords.drain; the Index and the Potion Shop read the flag) and puts
each defect back (mutants). NOT Studio evidence. Usage: python tools/verify_timer_words.py --runner luau.exe [--no-mutants]"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def module(path, replacements=None):
    source = read(path)
    for old, new in (replacements or {}).get(path, []):
        assert old in source, 'mutant target missing in %s: %s' % (path, old)
        source = source.replace(old, new)
    return '(function()\n' + source + '\nend)()'


BODY = r'''
-- flag off: exactly the Build 020 sentences
assert(W.weather("clear", nil, 240, false) == "Weather in 4 min", W.weather("clear", nil, 240, false))
assert(W.weather("rain", "Rain", 120, false) == "Rain 2 min")
assert(W.weather("rain", nil, 120, false) == "Rain 2 min" or W.weather("rain", nil, 120, false) == "rain 2 min")
assert(W.potion("speed", 180, false) == "Speed potion 3 min", W.potion("speed", 180, false))
assert(W.restock(123, 25, false) == "Crystals: 123  •  New offers in 25 s", W.restock(123, 25, false))
-- flag on: icon + short words, the colon keeps "what" and "how long" apart
assert(W.weather("clear", nil, 240, true) == "Next: 4 min", W.weather("clear", nil, 240, true))
assert(W.weather("rain", "Rain", 120, true) == "Rain: 2 min", W.weather("rain", "Rain", 120, true))
assert(W.weather("aurora", "Northern Lights", 3600, true) == "Northern Lights: 1 h")
assert(W.weather("rain", "", 40, true) == "rain: 40 s", "an empty name falls back to the id")
assert(W.potion("speed", 180, true) == "Speed: 3 min" and W.potion("growth", 30, true) == "Growth: 30 s")
assert(W.restock(123, 25, true) == "Crystals: 123  •  New in 25 s", W.restock(123, 25, true))
assert(W.found(1, 22) == "Found 1/22" and W.found(22, 22) == "Found 22/22", W.found(1, 22))
-- the potion lines: running potions sorted, expired ones dropped, the boost line last
local buffs = {speed = {id = "speed_common", expiresAt = 1180}, growth = {id = "growth_rare", expiresAt = 900}, loot = {id = "loot_epic", expiresAt = 1030}}
local lines = W.potionLines(buffs, 1000, true, {"Speed +20%"})
assert(#lines == 3 and lines[1] == "Loot: 30 s" and lines[2] == "Speed: 3 min" and lines[3] == "Speed +20%", table.concat(lines, "|"))
local old = W.potionLines(buffs, 1000, false, {})
assert(#old == 2 and old[1] == "Loot potion 30 s" and old[2] == "Speed potion 3 min", table.concat(old, "|"))
assert(#W.potionLines({}, 1000, true, {}) == 0)
-- the drain bar: full when drunk, empty at the end, clamped, none without a duration
assert(W.drain(1300, 300, 1000) == 1 and W.drain(1150, 300, 1000) == 0.5 and W.drain(1000, 300, 1000) == 0)
assert(W.drain(1600, 300, 1000) == 1 and W.drain(900, 300, 1000) == 0, "clamped to 0..1")
assert(W.drain(1300, nil, 1000) == nil and W.drain(1300, 0, 1000) == nil, "no bar without a duration")
-- kid words (docs/72): never "5m 0s", "1.25x", no digits glued to a letter
for _, s in {W.weather("clear", nil, 300, true), W.weather("rain", "Rain", 3660, true), W.potion("speed", 300, true), W.restock(5, 61, true), W.found(3, 22)} do
    assert(not s:find("%dm %ds") and not s:find("%d%a") and not s:find("x%s") and not s:find("%d%.%d+x"), "kid words: " .. s)
end
print("timer words ok")
'''


def script(replacements=None):
    s = 'local UIFormatMod=' + module('src/shared/UIFormat.luau', replacements) + '\n'
    s += 'script={Parent={UIFormat="U"}}\nrequire=function(_) return UIFormatMod end\n'
    s += 'local W=' + module('src/shared/TimerWords.luau', replacements) + '\n'
    return s + BODY


MUTANTS = {
    'the flag-off weather sentence changed': {'src/shared/TimerWords.luau': [('if id == "clear" then return if short then "Next: " .. time else "Weather in " .. time end', 'if id == "clear" then return "Next: " .. time end')]},
    'the short weather line loses the colon (name and time run together)': {'src/shared/TimerWords.luau': [('return if short then what .. ": " .. time else what .. " " .. time', 'return what .. " " .. time')]},
    'the short potion line keeps the word potion': {'src/shared/TimerWords.luau': [('return if short then word .. ": " .. UIFormat.duration(secondsLeft) else', 'return if false then word .. ": " .. UIFormat.duration(secondsLeft) else')]},
    'expired potions stay on the list': {'src/shared/TimerWords.luau': [('if buff.expiresAt > now then table.insert(lines, W.potion(kind, buff.expiresAt - now, short)) end', 'table.insert(lines, W.potion(kind, buff.expiresAt - now, short))')]},
    'the potion lines are not sorted': {'src/shared/TimerWords.luau': [('    table.sort(lines)\n', '')]},
    'the restock line keeps the long sentence': {'src/shared/TimerWords.luau': [('if short then "Crystals: %s  •  New in %s" else', 'if false then "Crystals: %s  •  New in %s" else')]},
    'the Index count says Collected X of Y': {'src/shared/TimerWords.luau': [('return string.format("Found %d/%d", found, total)', 'return string.format("Collected %d of %d", found, total)')]},
    'the drain bar is not clamped (a potion from a longer catalog overflows)': {'src/shared/TimerWords.luau': [('return math.clamp((expiresAt - now) / duration, 0, 1)', 'return (expiresAt - now) / duration')]},
    'a potion without a duration gets a full bar': {'src/shared/TimerWords.luau': [('if duration == nil or duration <= 0 then return nil end', 'if duration == nil or duration <= 0 then return 1 end')]},
}

SOURCE_MUTANTS = {
    'the flag is on in the source': ('src/shared/Config.luau', 'TimerChipsEnabled = false,', 'TimerChipsEnabled = true,'),
    'Bootstrap writes the weather sentence itself again': ('src/client/Bootstrap.client.luau', 'require(script.Parent.HudTimers).refresh(progression(),now)', 'weatherText.Text="Weather in "..timerText(60)'),
    'the drain bar ignores the flag': ('src/client/PotionChips.luau', 'return Config.TimerChipsEnabled == true', 'return true'),
    'the drain bar is drawn full and never refreshed': ('src/client/PotionChips.luau', 'fill.Size = UDim2.new(fraction or 0, 0, 1, 0)', 'fill.Size = UDim2.new(1, 0, 1, 0)'),
    'the Index bar ignores the flag': ('src/client/DinoIndexScreens.luau', 'local bigBar=Config.TimerChipsEnabled==true', 'local bigBar=false'),
    'the Index bar stays 34 px with the flag on': ('src/client/DinoIndexScreens.luau', 'if bigBar then 44 else nil', 'nil'),
    'the restock line ignores the flag': ('src/client/ShopScreens.luau', 'restock(num("Crystals"),left,Config.TimerChipsEnabled==true)', 'restock(num("Crystals"),left,false)'),
}


def check_sources(overrides=None):
    """overrides: {path: source} for a source mutant. Returns the first problem or None."""
    def src(path):
        if overrides and path in overrides:
            return overrides[path]
        return read(path)
    cfg = src('src/shared/Config.luau')
    if 'TimerChipsEnabled = false,' not in cfg:
        return 'the flag must be false in source'
    boot = src('src/client/Bootstrap.client.luau')
    if 'Weather in ' in boot.split('local function refreshProgressionHUD()')[1].split('-- BD-052')[0]:
        return 'Bootstrap must not write the weather sentence itself (HudTimers does)'
    if 'require(script.Parent.HudTimers).attach({tile=weatherTile,text=weatherText,buffs=buffsText,notify=notify,num=num})' not in boot:
        return 'Bootstrap hands the tile and labels to HudTimers.attach'
    if 'require(script.Parent.HudTimers).refresh(progression(),now)' not in boot:
        return 'Bootstrap refreshes the timers through HudTimers.refresh'
    if 'PotionChips).update' in boot:
        return 'PotionChips.update is called from HudTimers, not Bootstrap'
    hud = src('src/client/HudTimers.luau')
    for needle in ('Words.weather(id, workspace:GetAttribute("WeatherName")', 'Words.potionLines(p.buffs, now, short, boosts)', 'PotionChips.update(p.buffs, now)', 'Sfx.play("weather_start")', 'return Config.TimerChipsEnabled == true'):
        if needle not in hud:
            return 'HudTimers lost: ' + needle
    chips = src('src/client/PotionChips.luau')
    for needle in ('return Config.TimerChipsEnabled == true', 'Words.drain(buff.expiresAt, durationOf(buff.id), now)', 'fill.Size = UDim2.new(fraction or 0, 0, 1, 0)', 'if withBars and durationOf(id) then'):
        if needle not in chips:
            return 'PotionChips lost: ' + needle
    index = src('src/client/DinoIndexScreens.luau')
    if 'local bigBar=Config.TimerChipsEnabled==true' not in index or 'if bigBar then progress.short else progress.text' not in index or 'if bigBar then 44 else nil' not in index:
        return 'the Index bar is big and says Found X/Y only with the flag on'
    shop = src('src/client/ShopScreens.luau')
    if 'restock(num("Crystals"),left,Config.TimerChipsEnabled==true)' not in shop:
        return 'the Potion Shop restock line reads the flag'
    if 'short = string.format("Found %d/%d", found, total)' not in src('src/shared/IndexProgress.luau'):
        return 'IndexProgress.summary carries the short count'
    return None


def run(runner, replacements=None):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'timer_words.luau'
        path.write_text(script(replacements), encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True)
    return result.returncode == 0 and 'timer words ok' in result.stdout, result.stdout + result.stderr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    problem = check_sources()
    if problem:
        print('FAIL', problem)
        sys.exit(1)
    ok, out = run(args.runner)
    print(out, end='')
    if not ok:
        sys.exit(1)
    if not args.no_mutants:
        for name, replacements in MUTANTS.items():
            passed, _ = run(args.runner, replacements)
            assert not passed, 'MUTANT SURVIVED: ' + name
            print('  mutant caught: ' + name)
        for name, (path, old, new) in SOURCE_MUTANTS.items():
            source = read(path)
            assert old in source, 'mutant target missing in %s: %s' % (path, old)
            assert check_sources({path: source.replace(old, new)}) is not None, 'SOURCE MUTANT SURVIVED: ' + name
            print('  source mutant caught: ' + name)
    print('Timer words passed: flag-off sentences unchanged, short words, potion lines, drain bar, Index count, wiring, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS) + len(SOURCE_MUTANTS)))


if __name__ == '__main__':
    main()
