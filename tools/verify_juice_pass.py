#!/usr/bin/env python3
"""BD-1286 (docs/245 "Juice to add", slice 1): the eat pop + "+N" float on the SIZE plate and the crystal fly-to-counter behind
Config.JuicePassEnabled (client/JuicePass.client.luau, numbers in Shared/JuiceRules.luau).

Runs the REAL JuiceRules.luau in the pinned Luau runtime and checks: growthText ("+N" food points, at least 1, capped, bad input nil);
iconCount 3..6 and 0 for bad input; canStart never lets more than MaxFlying (12) be in the air; the curve starts and ends exactly on its two
points and bows to the side (mirrored for side = -1); iconScale stays positive and shrinks into the counter; rose() only counts rises of numbers.
Source guards: the flag ships false, is pinned off in the default profile, ON in the playtest profile, the rehearsal list and the playtest manifest;
flag off = JuicePass returns before it creates anything, PhoneHud / Bootstrap / GrowthPop carry no juice code; the script respects Reduce Motion
(Theme.MotionEnabled, GuiService.ReducedMotionEnabled, the ReduceMotion attribute), uses TweenService, a pool of MaxFlying icons made once, the existing
amber icon (no new art, no new ids), destroys what it makes, and has no Robux path. Mutants: each guard must fail when its line is broken.
Usage: python tools/verify_juice_pass.py --runner luau.exe"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CLIENT = 'src/client/JuicePass.client.luau'
RULES = 'src/shared/JuiceRules.luau'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
local function near(a, b, e) return math.abs(a - b) <= (e or 1e-6) end

check(R.growthText(0.1, 0.1) == "+1" and R.growthText(0.5, 0.1) == "+5" and R.growthText(0.04, 0.1) == "+1", "+N is food points, at least 1")
check(R.growthText(1e9, 0.1) == "+9999", "+N capped at 9999")
check(R.growthText(0, 0.1) == nil and R.growthText(-1, 0.1) == nil and R.growthText(0 / 0, 0.1) == nil and R.growthText(math.huge, 0.1) == nil, "bad delta: no word")
check(R.growthText("x", 0.1) == nil and R.growthText(1, 0) == nil and R.growthText(1, nil) == nil, "bad input: no word")
check(R.iconCount(1) == 3 and R.iconCount(9) == 3 and R.iconCount(10) == 4 and R.iconCount(49) == 4 and R.iconCount(50) == 5 and R.iconCount(199) == 5 and R.iconCount(200) == 6 and R.iconCount(1e6) == 6, "3..6 icons by amount")
check(R.iconCount(0) == 0 and R.iconCount(-5) == 0 and R.iconCount(nil) == 0 and R.iconCount(0 / 0) == 0, "nothing flies for no gain")
check(R.MaxFlying <= 12 and R.MinIcons == 3 and R.MaxIcons == 6, "limits: 12 in the air, 3..6 per pickup")
check(R.canStart(6, 0) == 6 and R.canStart(6, 9) == 3 and R.canStart(6, 12) == 0 and R.canStart(6, 20) == 0 and R.canStart(0, 0) == 0, "never more than MaxFlying in the air")
for _, side in {1, -1} do
    local x, y = R.curve(100, 500, 40, 60, 0, side)
    check(near(x, 100) and near(y, 500), "curve starts on the event point")
    x, y = R.curve(100, 500, 40, 60, 1, side)
    check(near(x, 40) and near(y, 60), "curve ends on the counter")
end
local ax, ay = R.curve(0, 0, 100, 0, 0.5, 1)
local bx, by = R.curve(0, 0, 100, 0, 0.5, -1)
check(near(ax, 50) and near(bx, 50) and math.abs(ay) > 5 and near(ay, -by), "the curve bows to the side, mirrored for side -1")
for i = 0, 10 do
    local s = R.iconScale(i / 10)
    check(s > 0 and s <= 1.05, "icon scale stays positive and not huge")
end
check(R.iconScale(1) < R.iconScale(0.25), "the icon shrinks into the counter")
check(R.rose(5, 8) == 3 and R.rose(8, 5) == 0 and R.rose(5, 5) == 0 and R.rose(nil, 5) == 0 and R.rose(5, nil) == 0 and R.rose("a", 5) == 0, "only a rise of numbers counts")
check(R.FloatSeconds >= 0.6 and R.FloatSeconds <= 0.8, "+N floats 0.6-0.8 s (docs/245)")
if #fails > 0 then error("juice pass FAILED:\n" .. table.concat(fails, "\n")) end
print("juice pass passed")
'''

GUARDS = [
    # (needle in the client script, what it protects)
    ('if (Config :: any).JuicePassEnabled ~= true or (Config :: any).PhoneHudZonesEnabled ~= true then return end', 'flag off: returns before anything is made'),
    ('GuiService.ReducedMotionEnabled ~= true', 'Reduce Motion: the Roblox setting'),
    ('player:GetAttribute("ReduceMotion") ~= true', 'Reduce Motion: the game setting'),
    ('Theme.MotionEnabled ~= false', 'Reduce Motion: the Theme switch'),
    ('if scale == nil or not motion() then return end', 'no scale pop under Reduce Motion'),
    ('if motion() and not menuOpen() then', 'no flying under Reduce Motion or over an open window'),
    ('crystalsNumber.TextTransparency = 0.5', 'Reduce Motion: the tiny fade on the number'),
    ('local want = Rules.canStart(Rules.iconCount(gained), inAir)', 'the pool limit is applied'),
    ('for i = 1, Rules.MaxFlying do', 'the pool is made once, MaxFlying icons'),
    ('Icons.amber', 'the existing crystal icon'),
    ('label:Destroy()', 'the float label is destroyed'),
    ('while #floats >= Rules.MaxFloats do', 'at most MaxFloats numbers in the air'),
    ('slot.image.Visible, slot.busy = false, false', 'a landed icon goes back to the pool'),
    ('TweenService:Create(slot.alpha', 'icons move with TweenService'),
]


def scan(client=None, rules=None):
    sys.path.insert(0, str(ROOT / 'tools'))
    import release_profiles as profiles
    cfg = read('src/shared/Config.luau')
    assert cfg.count('    JuicePassEnabled = false,\n') == 1, 'the flag ships false, once'
    assert 'JuicePassEnabled = true' in profiles.apply_profile(cfg, 'playtest')[0], 'ON in the playtest profile'
    assert 'JuicePassEnabled' in [k for k, _ in profiles.REHEARSAL_ON], 'in the rehearsal list'
    assert profiles.verify_source(cfg, 'default').errors == [], 'default profile pins it off'
    assert '"JuicePassEnabled"' in read('tools/release_playtest.py'), 'the playtest manifest records it'
    text = read(CLIENT) if client is None else client
    for needle, what in GUARDS:
        assert needle in text, f'JuicePass: {what}'
    assert text.index('JuicePassEnabled ~= true') < text.index('Instance.new'), 'the flag check comes before anything is created'
    for banned in ('rbxassetid', 'Marketplace', 'PromptProductPurchase', 'RemoteEvent', 'FireServer', 'SetAttribute', 'DataStore'):
        assert banned not in text, f'JuicePass: no {banned} (client presentation only, no new art, no Robux path)'
    assert 'RenderStepped' not in text and 'Heartbeat' not in text, 'JuicePass: no per-frame loop; tweens only'
    rtext = read(RULES) if rules is None else rules
    for banned in ('game:GetService', 'Instance.new', 'rbxassetid'):
        assert banned not in rtext, f'JuiceRules: pure, no {banned}'
    for other in ('src/client/PhoneHud.client.luau', 'src/client/Bootstrap.client.luau', 'src/client/GrowthPop.client.luau', 'src/client/ModalCompact.luau'):
        assert 'JuicePass' not in read(other) and 'JuiceRules' not in read(other), f'{other} carries no juice code (flag off = unchanged)'


def mutants():
    """Each broken copy of the client script / rules must fail scan()."""
    text = read(CLIENT)
    broken = 0
    for needle, what in GUARDS:
        try:
            scan(client=text.replace(needle, '-- removed'))
        except AssertionError:
            broken += 1
        else:
            raise SystemExit(f'mutant survived: {what}')
    for name, mutated in (('per-frame loop', text + '\ngame:GetService("RunService").Heartbeat:Connect(function() end)\n'),
                          ('new id in code', text + '\nlocal x = "rbxassetid://1"\n'),
                          ('flag check after Instance.new', text.replace('local Rules = require', 'local made = Instance.new("Frame")\nlocal Rules = require', 1).replace('if (Config :: any).JuicePassEnabled ~= true or (Config :: any).PhoneHudZonesEnabled ~= true then return end', 'local made2 = Instance.new("Frame")\nif (Config :: any).JuicePassEnabled ~= true or (Config :: any).PhoneHudZonesEnabled ~= true then return end'))):
        try:
            scan(client=mutated)
        except AssertionError:
            broken += 1
        else:
            raise SystemExit(f'mutant survived: {name}')
    try:
        scan(rules=read(RULES) + '\nlocal s = game:GetService("Players")\n')
    except AssertionError:
        broken += 1
    else:
        raise SystemExit('mutant survived: rules with a service')
    print(f'{broken} mutants caught')


def run_luau(runner, rules_text, label):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'juice_pass.luau'
        path.write_text('local R=(function()\n' + rules_text.replace('export type', 'type') + '\nend)()\n' + LUAU, encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        return result.returncode == 0 and 'passed' in result.stdout, result.stdout + result.stderr


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    scan()
    mutants()
    ok, out = run_luau(args.runner, read(RULES), 'real')
    print(out, end='')
    if not ok:
        sys.exit(1)
    # rule mutants: the numbers must be checked by the Luau part
    rules = read(RULES)
    for old, new in (('local n = math.max(1, math.floor(delta / perFood + 0.5))', 'local n = math.floor(delta / perFood + 0.5)'),
                     ('return math.max(0, math.min(want, Rules.MaxFlying - inAir))', 'return want'),
                     ('if gained < 10 then return Rules.MinIcons end', 'if gained < 10 then return 1 end'),
                     ('if after <= before then return 0 end', 'if false then return 0 end'),
                     ('return u * u * x0 + 2 * u * t * cx + t * t * x1, u * u * y0 + 2 * u * t * cy + t * t * y1', 'return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t')):
        assert old in rules, f'rules mutant needle missing: {old}'
        good, _ = run_luau(args.runner, rules.replace(old, new), 'mutant')
        if good:
            raise SystemExit(f'rules mutant survived: {old}')
    print('rules mutants caught')
