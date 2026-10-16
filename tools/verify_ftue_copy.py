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
print("BD-370 first-time-player copy verified")
'''


def script():
    src = (ROOT / 'src/shared/FtueCopy.luau').read_text(encoding='utf-8')
    return 'local Copy=(function()\n' + src + '\nend)()\n' + BODY


def check_wiring():
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    for needle in ('FtueCopy).tutorialSteps', 'FtueCopy).homeConfirmLine', 'FtueCopy).homeConfirmTotals', 'FtueCopy).runCompleteEggsLabel'):
        assert needle in boot, 'Bootstrap does not use ' + needle
    for old in ('Banking %d catches', 'will be banked', '"Catches  "', 'BANK & HATCH'):
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
