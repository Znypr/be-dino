"""BD-369..381: first-time-player P1/P2 fixes (docs/112, docs/113). Runs the real pure module src/shared/FtueP1.luau and
checks the client wiring (one place per fix; Bootstrap gets no new top-level locals)."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BODY = r'''
-- BD-369 Eggs screen
assert(P.waitingText(1, 0) == "Eggs waiting: 1", "a READY card is counted")
assert(P.waitingText(5, 26) == "Eggs waiting: 31" and P.waitingText(0, 3) == "Eggs waiting: 3")
assert(P.waitingText(0, 0) == nil and P.waitingText(-2, -1) == nil, "never 'waiting: 0'")
assert(P.NestLine:find("one at a time"), "the nest timer is explained")
assert(P.EmptyStatus == "Go find eggs on the island!" and P.EmptyButton == "EXPLORE ISLAND")
assert(P.CrackedHint == "Some eggs can crack!")
assert(not P.crackedHintShown(1, true) and not P.crackedHintShown(2, true), "first two eggs are safe: no hint")
assert(P.crackedHintShown(3, true), "the first card after the two safe eggs gets the hint")
assert(not P.crackedHintShown(3, false), "no card, no hint")
assert(not P.crackedHintShown(40, true), "a veteran does not see it forever")
assert(not P.crackedHintShown(-5, true) and not P.crackedHintShown(0, true))

-- BD-371 end buttons
local function join(t) return table.concat(t, ",") end
assert(join(P.hatchButtons(true, 0)) == "done,again", "splat with nothing left: Done + Try again")
assert(join(P.hatchButtons(true, 3)) == "next", "splat with eggs left: Next egg")
assert(join(P.hatchButtons(false, 0)) == "done", "last egg: a real Done button")
assert(join(P.hatchButtons(false, 2)) == "", "a normal egg uses the tap hint")
for _, kind in { "next", "done", "again" } do
    assert(P.ButtonText[kind] and #P.ButtonText[kind] <= 10, kind)
    assert(P.contrast(P.ButtonColors[kind], P.ButtonTextColor) >= 4.5, "contrast for " .. kind .. " = " .. P.contrast(P.ButtonColors[kind], P.ButtonTextColor))
end
assert(P.contrast({255, 255, 255}, {0, 0, 0}) > 20.9 and P.contrast({128, 128, 128}, {128, 128, 128}) == 1, "contrast maths")
assert(P.contrast({93, 237, 31}, {255, 255, 255}) < 4.5, "white text on the green would fail (why the text is dark)")

-- BD-372 shop
local up = {price = 120, requiredLevel = 3}
local text, ok = P.upgradeButton(up, 1, 1000000)
assert(text == "Reach level 3" and ok == false, "locked by level: grey reason, never UPGRADE")
text, ok = P.upgradeButton(up, 3, 50) assert(text == "Need 120 Crystals" and ok == false)
text, ok = P.upgradeButton(up, 3, 120) assert(text == "UPGRADE: 120 CRYSTALS" and ok == true)
text, ok = P.upgradeButton(nil, 9, 0) assert(text == "MAX LEVEL" and ok == false)
assert(P.upgradeHint(up, 1) ~= "Reach level 3 to buy this." and P.upgradeHint(up, 3) == "Ready to buy!" and P.upgradeHint(nil, 3) == "Top level reached")
assert(P.ConditionsHeader:find("first 2 eggs are safe") and not P.ConditionsHeader:lower():find("tier"))

-- BD-445 shop tabs and the no-crystals hint
local function has(list, v) for _, x in list do if x == v then return true end end return false end
assert(not has(P.shopTabs(1), "conditions") and not has(P.shopTabs(2), "conditions") and has(P.shopTabs(3), "conditions"))
assert(#P.shopTabs(1) == 4 and #P.shopTabs(3) == 5 and P.shopTabs(1)[4] == "crystals")
assert(P.noCrystalsHintShown(0, "auras") and not P.noCrystalsHintShown(5, "auras") and not P.noCrystalsHintShown(0, "crystals"))
assert(not P.fastTravelEntryShown(1, false) and P.fastTravelEntryShown(2, false) and P.fastTravelEntryShown(1, true), "BD-447 perk entry gate")
assert(P.NoCrystalsHint == "Play a run to earn crystals!" and #P.NoCrystalsHint <= 40)

-- BD-374 controls
local desk, phone = P.controlsLines(false, false), P.controlsLines(true, false)
assert(#desk == 2 and #phone == 2)
for _, line in { desk[1], desk[2], phone[1], phone[2] } do assert(#line <= 60, line) end
assert(desk[1]:find("W A S D") and desk[1]:find("Space") and desk[1]:find("E"), "move, jump, leap")
assert(P.controlsLines(false, true)[2]:find("Bite: F") and not desk[2]:find("Bite"), "bite key only while fighting is on")
assert(phone[1]:lower():find("stick") and phone[2]:find("LEAP"))

-- BD-375 go home
assert(P.HomeConfirmTitle == "Go home?" and P.HomeConfirmButton == "GO HOME" and P.HomeToast == "Going home...")

-- BD-376 plain words
assert(P.BuffWord.loot == "Eggs" and P.MinTextSize >= 14)
assert(P.indexCount(1, 0, 0) == "1 Base" and P.indexCount(1, 2, 0) == "1 Base  \u{2022}  2 Gold" and P.indexCount(0, 0, 3) == "3 Diamond" and P.indexCount(0, 0, 0) == "0 Base")

-- BD-378 one found toast
local t, body = P.foundToast(1, nil) assert(t == "You found an egg!" and body == nil)
t = P.foundToast(2, nil) assert(t == "You found 2 eggs!")
t, body = P.foundToast(1, "Frost") assert(t == "You found a Frost egg!" and body == "A weather egg! Hatch it at Home")
t, body = P.foundToast(3, "Frost") assert(t == "You found 3 eggs!" and body ~= nil, "several eggs: one merged toast, still explained")
t = P.foundToast(0, nil) assert(t == "You found an egg!", "never 0 eggs")
for _, name in { "Dewdrop", "Charged", "Frost", "Seismic", "Ember", "Aurora", "Blood Moon" } do
    local text, extra = P.foundToast(1, name)
    assert(#text <= 30 and #(extra :: string) <= 44, "fits NotifyQueue.MaxText/MaxBody: " .. name)
end
assert(P.ToastTopY <= 8)

-- BD-379 world text
assert(P.worldTextAllowed(false) == true and P.worldTextAllowed(true) == false)
print("BD-369..381 first-time-player fixes verified")
'''


def script():
    src = (ROOT / 'src/shared/FtueP1.luau').read_text(encoding='utf-8')
    return 'local P=(function()\n' + src + '\nend)()\n' + BODY


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def check_wiring():
    boot = read('src/client/Bootstrap.client.luau')
    eggs = read('src/client/EggsScreen.luau')
    hatch = read('src/client/HatchSequence.luau')
    hud = read('src/client/HudV2.luau')
    settings = read('src/client/SettingsMenu.luau')
    server = read('src/server/ProfileRepository.luau')
    for needle, where, name in (
        ('Copy.waitingText', eggs, 'Eggs screen count'), ('Copy.NestLine', eggs, 'nest line'), ('Copy.crackedHintShown', eggs, 'cracked hint'),
        ('ctx.explore()', eggs, 'explore button'), ('Copy.hatchButtons', hatch, 'end buttons'), ('onAgain', hatch, 'try again'),
        ('Copy.foundToast', hud, 'one found toast'), ('controlsLines', settings, 'controls list'),
        ('upgradeButton(', boot, 'shop upgrade lock'), ('worldTextAllowed', boot, 'world text vs modal'),
        ('indexCount(', boot, 'index count'), ('"Go home?"', boot, 'go home title'), ('"GO HOME"', boot, 'go home button'),
        ('Going home...', boot, 'go home toast'),
    ):
        assert needle in where, 'missing wiring: ' + name
    assert 'Return to Sanctuary?' not in boot and 'Returning to Sanctuary' not in boot, 'old wording is back'
    assert 'egg caught!' not in boot, 'BD-378: no second "caught!" toast from Bootstrap'
    for old in ('"1 run egg"', 'run eggs"', '"1 egg nest"', 'egg nests"'):
        assert old not in server, 'BD-373 old reward words are back: ' + old


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    check_wiring()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'ftue_p1.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
