"""BD-370: first-time-player copy (docs/112). Runs the real Luau module and checks the client wiring.
Plain words for children (docs/72): no 'catches', 'banked' or 'bank' on the first-run screens."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BODY = r'''
local steps = Copy.tutorialSteps
assert(#steps == 3)
for _, s in steps do
    assert(#s[2] <= 16 and #s[3] <= 52, "short lines: " .. s[3])
    for _, word in { "catch", "bank", "sanctuary", "cluster", "mobile" } do
        assert(not s[2]:lower():find(word) and not s[3]:lower():find(word), "jargon " .. word .. " in " .. s[3])
    end
end
assert(steps[1][3]:find("eat") and steps[3][3]:find("HOME"), "steps teach eating and the HOME button")
assert(Copy.homeConfirmTotals(1, 65.7) == "You found 1 egg  \u{2022}  Growth 65")
assert(Copy.homeConfirmTotals(0, 3) == "You found 0 eggs  \u{2022}  Growth 3")
assert(Copy.homeConfirmTotals(12, 900) == "You found 12 eggs  \u{2022}  Growth 900")
for _, line in { Copy.homeConfirmLine, Copy.runCompleteEggsLabel, Copy.homeConfirmTotals(2, 1) } do
    assert(not line:lower():find("catch") and not line:lower():find("bank"), line)
end
for _, line in { Copy.sanctuaryTip1, Copy.sanctuaryTip2 } do
    assert(#line <= 70, line)
    for _, word in { "catch", "bank", "cluster", "sanctuary" } do assert(not line:lower():find(word), word .. " in " .. line) end
end
local rows = Copy.runCompleteRows({eggs = 60, crystals = 114, nests = 0, nestCrystals = 0, growth = 0})
assert(#rows == 2 and rows[1][2] == "Eggs found  60" and rows[2][2] == "+114 Crystals", "no growth at 0, no duplicate egg line")
local full = Copy.runCompleteRows({eggs = 3, crystals = 5, nests = 1, nestCrystals = 20, growth = 7.9})
assert(#full == 5 and full[3][2] == "+1 nest" and full[4][2] == "Extra nests: +20 Crystals" and full[5][2] == "Growth  7")
local hunt = Copy.runCompleteRows({eggs = 5, crystals = 1, killEggs = 2})
assert(#hunt == 3 and hunt[3][2] == "Hunting bonus: +2 eggs" and Copy.runCompleteRows({eggs = 5, killEggs = 1})[3][2] == "Hunting bonus: +1 egg")
assert(#Copy.runCompleteRows({eggs = 5, killEggs = 0}) == 2, "no hunting row at 0")
for _, r in full do assert(not r[2]:lower():find("catch") and #r[2] <= 30, r[2]) end
print("BD-370 first-time-player copy verified")
'''


def script():
    src = (ROOT / 'src/shared/FtueCopy.luau').read_text(encoding='utf-8')
    return 'local Copy=(function()\n' + src + '\nend)()\n' + BODY


def check_wiring():
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8') + (ROOT / 'src/client/SmallScreens.luau').read_text(encoding='utf-8')  # BD-1110: tutorial and Go home? moved
    for needle in ('FtueCopy).tutorialSteps', 'FtueCopy).homeConfirmLine', 'FtueCopy).homeConfirmTotals'):
        assert needle in boot, 'Bootstrap does not use ' + needle
    rc = (ROOT / 'src/client/RunComplete.luau').read_text(encoding='utf-8')
    assert 'FtueCopy' in rc and 'runCompleteRows' in rc and '"OPEN EGGS"' in rc and 'trophy' in rc and '"amber"' in rc, 'BD-448 Run Complete module'
    assert 'RunComplete).build' in boot and 'LastRewardText","Saving' not in boot, 'Bootstrap must use the RunComplete module'
    for old in ('Banking %d catches', 'will be banked', '"Catches  "', 'BANK & HATCH', 'Eat small food clusters', 'Bank catches and reward'):
        assert old not in boot, 'old jargon is back: ' + old


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    check_wiring()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'ftue_copy.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
