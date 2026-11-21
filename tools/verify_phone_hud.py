#!/usr/bin/env python3
"""BD-1258 / BD-1259 / BD-1260 / BD-1268 / BD-1269 / BD-1271 phone HUD zones (Config.PhoneHudZonesEnabled, src/shared/PhoneHudLayout.luau,
src/client/PhoneHud.client.luau), docs/244 s2.14, owner phone test 2026-11-17.

Runs the REAL PhoneHudLayout in the pinned Luau runtime on phone canvases (3088x1440, 2400x1080 and 1334x750 landscape in design px, each
with a 36 px Roblox top bar and with the bigger Studio top bar of the evidence captures) and a desktop canvas, with 5 tiles (home) and 3
tiles (in a run), with and without CHOMP, and checks:
  * no two persistent HUD pieces touch, none sits in the middle box (x 33-67 %, y 25-76 %) or off the canvas;
  * the toast lane and the goal hint never cover a persistent piece; the lane sits above LEAP / CHOMP and is at most half the screen wide;
  * every text size is >= 19 on a touch canvas (>= 14 on desktop), counters bigger than timer words, every tap target >= 44 px;
  * exactly two word buttons on the left, the right tiles are squares 13.5 % h (or the 44 px floor);
  * kid words: "3 min left", "Weather in 4 min", "Rain is here!", short counters "1,250" / "12.4K" / "3.4M".
Source guards: the flag ships false, off in the default profile, ON in playtest and in the rehearsal list; the client script returns at once
without the flag; Bootstrap.client is untouched; Toasts only use the lane with the flag; RailRun skips a PhoneHudOwned button.
Usage: python tools/verify_phone_hud.py --runner luau.exe"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
# (W, H) of the BeDinoUI canvas in design px: the phone's points minus the Roblox top bar (36 px), and the Studio captures (58 px bar).
CANVASES = [(1029, 444), (873, 357), (667, 339), (1013, 406), (857, 319)]
# Smaller than any real phone canvas (the smallest Studio capture, 58 px bar on a 359 px viewport): no overlaps, but the middle-box margin is not asked.
TINY = [(651, 301)]
DESKTOP = [(1274, 423), (1920, 1000)]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
local function run(W, H, touch, tiny)
    for _, tiles in {5, 3} do
        for _, chomp in {true, false} do
            for _, timers in {0, 3} do
                local lay = L.compute({W = W, H = H, touch = touch, tiles = tiles, chomp = chomp, timers = timers})
                local tag = string.format("%dx%d tiles=%d chomp=%s timers=%d", W, H, tiles, tostring(chomp), timers)
                for _, p in L.problems(lay) do check(tiny == true and string.find(p, "middle box", 1, true) ~= nil, tag .. ": " .. p) end
                check(#lay.left == 2, tag .. ": exactly two word buttons")
                for _, r in lay.tiles do check(math.abs(r.w - r.h) < 0.01 and r.w >= math.min(13.5 * lay.unit, 1e9) - 0.01, tag .. ": square tiles 13.5 % h") end
                check(lay.lane.y + lay.lane.h <= lay.action.y, tag .. ": the toast lane sits above LEAP and CHOMP")
                check(lay.lane.w <= W * 0.5 + 0.01, tag .. ": the lane is at most half the screen wide")
                check(#lay.squares == (if chomp then 2 else 1), tag .. ": LEAP (and CHOMP) squares")
            end
        end
    end
end
for _, c in Phones do run(c[1], c[2], true) end
for _, c in Desktops do run(c[1], c[2], false) end
for _, c in Tiny do run(c[1], c[2], true, true) end
check(L.textSize(2.8, 444, true) >= 19 and L.textSize(4.4, 444, true) > L.textSize(3.2, 444, true), "phone text floor and counter > timer")
check(L.timeLeft(179) == "3 min left" and L.timeLeft(40) == "40 s left", "kid timer words")
local a, b = L.bannerWords("clear", "Clear", 240)
check(a == "Sunny!" and b == "Weather in 4 min", "banner between events")
a, b = L.bannerWords("rain", "Rain", 125)
check(a == "Rain is here!" and b == "3 min left", "banner during an event")
check(L.counterText(1250) == "1,250" and L.counterText(12450) == "12.4K" and L.counterText(3400000) == "3.4M" and L.counterText(10000) == "10K", "short counters")
check(L.homeWord("Active") == nil and L.homeWord("Sanctuary") == "GO", "home tile word")
if #fails > 0 then for _, f in fails do print("FAIL: " .. f) end error("phone HUD checks failed") end
print("Phone HUD checks passed (" .. #Phones .. " phone and " .. #Desktops .. " desktop canvases)")
'''


def source_checks():
    errors = []
    if '    PhoneHudZonesEnabled = false,\n' not in read('src/shared/Config.luau'):
        errors.append('Config.PhoneHudZonesEnabled must ship false')
    profiles = read('tools/release_profiles.py')
    if ('_flag_off("PhoneHudZonesEnabled"' not in profiles or 'Rule("PhoneHudZonesEnabled", "set", True' not in profiles
            or '("PhoneHudZonesEnabled", "BD-1258' not in profiles):
        errors.append('PhoneHudZonesEnabled: off in default, on in playtest, in the rehearsal list')
    client = read('src/client/PhoneHud.client.luau')
    if 'if (Config :: any).PhoneHudZonesEnabled ~= true then return end' not in client:
        errors.append('the client script must return at once without the flag')
    for bad in ('RemoteEvent', ':FireServer', 'DataStore'):
        if bad in client:
            errors.append('the phone HUD is presentation only: ' + bad)
    if 'PhoneHud' in read('src/client/Bootstrap.client.luau'):
        errors.append('Bootstrap.client must not change (size ceiling)')
    toasts = read('src/client/Toasts.luau')
    if 'local LaneOn = (require(Shared.Config) :: any).PhoneHudZonesEnabled == true' not in toasts or 'if LaneOn and laneFrame then' not in toasts:
        errors.append('Toasts use the lane only with the flag')
    if 'if b:GetAttribute("PhoneHudOwned") == true then continue end' not in read('src/client/RailRun.luau'):
        errors.append('RailRun must skip a button the phone HUD owns')
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    problems = source_checks()
    for p in problems:
        print('FAIL:', p)
    def table(items):
        return '{' + ','.join('{%d,%d}' % c for c in items) + '}'
    source = ('local L=(function()\n' + read('src/shared/PhoneHudLayout.luau') + '\nend)()\nlocal Phones=' + table(CANVASES) +
              '\nlocal Desktops=' + table(DESKTOP) + '\nlocal Tiny=' + table(TINY) + '\n' + LUAU)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'phone_hud.luau'
        path.write_text(source, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    print(result.stdout, end='')
    if result.returncode or 'Phone HUD checks passed' not in result.stdout or problems:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode or 1)


if __name__ == '__main__':
    main()
