"""BD-1241 (docs/240 R8, emulator pass 2026-11-17): the HUD "Codes" button keeps clear of the HUD pieces.

Runs the REAL src/shared/CodesButtonSpot.luau with the pinned Luau runner:
  * the measured Studio case (1274 x 481): the old fixed spot (right edge, y 162) sat on the timers column (weather chip); the rule moves
    it left of the column, clear of every published piece, inside the canvas;
  * a tall desktop canvas (1914 x 841) keeps the old spot (nothing there);
  * phone canvases (iPhone 844 x 390, small Android 640 x 360) with a timers column under the crystals plate get a clear spot;
  * when no spot is clear the old spot is returned and reported as not clear (never off screen).
And a source scan: GiftsPanel uses the rule only inside the Config.MenusCohesionEnabled block (flag off = the old fixed spot).

    python tools/verify_codes_button_spot.py --runner <luau.exe>
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

BODY = r'''
local function overlaps(a, b) return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h end
local function check(name, width, height, blockers, expectClear)
    local default = {x = width - 128, y = 162, w = 110, h = 44}
    local r, ok = Spot.place(default, blockers, width, height)
    assert(ok == expectClear, name .. ": clear=" .. tostring(ok))
    if ok then
        for _, b in blockers do assert(not overlaps(r, b), name .. ": still overlaps a HUD piece") end
        assert(r.x >= 0 and r.y >= 0 and r.x + r.w <= width and r.y + r.h <= height, name .. ": off the canvas")
        assert(r.w >= 44 and r.h >= 44, name .. ": tap target under 44 px")
    end
    return r
end
-- Rects measured in the playtest build at 1274 x 481 (BeDinoUI attributes, 2026-11-17)
local studio = {
    {x = 1049.97, y = 157.82, w = 216.03, h = 166.18}, -- TimersRect (LEAP, weather chip, potions)
    {x = 1069.61, y = 8, w = 196.39, h = 62.92},       -- WalletBlockRect
    {x = 8, y = 8, w = 158.63, h = 48.34},             -- HudRect
    {x = 8, y = 102.34, w = 201, h = 144},             -- RailRect
    {x = 517, y = 279, w = 240, h = 48},               -- ChipRect
    {x = 544.85, y = 369.68, w = 184.31, h = 45.32},   -- ActionRect
    {x = 8, y = 367, w = 120, h = 48},                 -- FeedbackRect
    {x = 136, y = 367, w = 120, h = 48},               -- AdminRect
}
local moved = check("studio 1274x481", 1274, 423, studio, true)
assert(moved.y == 162 and moved.x < 1049.97, "studio: expected the spot left of the timers column")
local desk = check("desktop 1914x841", 1914, 783, {{x = 1600, y = 600, w = 290, h = 160}, {x = 1636, y = 8, w = 260, h = 62}}, true)
assert(desk.x == 1914 - 128 and desk.y == 162, "desktop: the old spot must stay")
check("iPhone 844x390", 844, 390, {{x = 680, y = 120, w = 150, h = 200}, {x = 650, y = 8, w = 186, h = 56}, {x = 8, y = 8, w = 150, h = 46}}, true)
check("Android 640x360", 640, 360, {{x = 500, y = 110, w = 132, h = 190}, {x = 470, y = 8, w = 162, h = 52}, {x = 8, y = 8, w = 140, h = 44}}, true)
local full = check("no room", 300, 220, {{x = 0, y = 0, w = 300, h = 220}}, false)
assert(full.x == 300 - 128 and full.y == 162, "no room: the old spot is returned")
assert(Spot.fromAttribute({}) == nil and Spot.fromAttribute(nil) == nil)
print("CodesButtonSpot passed")
'''


def scan():
    src = (ROOT / "src/client/GiftsPanel.client.luau").read_text(encoding="utf-8")
    assert src.count("CodesButtonSpot") == 1, "GiftsPanel must require CodesButtonSpot exactly once"
    block = src[src.index("Config.MenusCohesionEnabled == true then\n        local Spot"):]
    assert block.index("CodesButtonSpot") < block.index("\n    end\nend)"), "the rule must sit inside the MenusCohesionEnabled block"
    assert 'UDim2.new(1, -128, 0, 162)' in src, "flag off keeps the old fixed spot"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    args = parser.parse_args()
    scan()
    module = (ROOT / "src/shared/CodesButtonSpot.luau").read_text(encoding="utf-8")
    script = "local Spot = (function()\n" + module + "\nend)()\n" + BODY
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "codes_button_spot.luau"
        path.write_text(script, encoding="utf-8")
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end="")
        print(result.stderr, end="")
        raise SystemExit(result.returncode)
