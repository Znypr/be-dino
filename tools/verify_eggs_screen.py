"""Combined Eggs screen checks (owner 2026-10-15): pure logic in src/shared/EggsLogic.luau run with the
pinned Luau runtime (nest slots, single next-egg card state machine, auto-open selection, never-skip rules,
AutoOpenRequiresPass gating, never-forced hatching) plus static source guards on Bootstrap. Drawing is Studio-only."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
local H = 3600
-- Nest slots: always five, ready / the one opening with a timer / queued / dim empty.
local nests = {{id = "a", state = "ready"}, {id = "b", state = "incubating", readyAt = 1000 + 2 * H}, {id = "c", state = "waiting"}}
local slots = L.nestSlots(nests, 5, 1000)
assert(#slots == 5 and slots[1].state == "ready" and slots[1].text == "READY" and slots[1].id == "a")
assert(slots[2].state == "opening" and slots[2].remaining == 2 * H, "the opening nest shows its timer")
assert(slots[3].state == "queued" and slots[3].text == "Queued" and slots[4].state == "empty" and slots[5].state == "empty")
assert(L.nestHeader(nests, 5) == "Nests 3/5" and L.nestHeader({}, 5) == "Nests 0/5")
assert(L.nestSlots({}, 5, 0)[1].state == "empty" and L.nestSlots(nests, 2, 1000)[3] == nil, "never more slots than capacity")

-- Single next-egg card state machine.
local c = L.card(nil, "", 0, 100, 0)
assert(c.kind == "empty" and not c.canOpen)
local t, b = L.cardCopy(c) assert(t == "No eggs yet. Finish a run to catch some!" and b == "NO EGGS")
c = L.card(nil, "", 0, 100, 3) assert(c.kind == "banked" and not c.canOpen)
c = L.card({readyAt = 160}, "e1", 160, 100, 4) assert(c.kind == "growing" and c.remaining == 60 and not c.canOpen and c.waiting == 4)
t, b = L.cardCopy(c) assert(t == "Growing..." and b == "GROWING")
c = L.card({readyAt = 160}, "e1", 160, 160, 4) assert(c.kind == "ready" and c.canOpen and c.remaining == 0)
t, b = L.cardCopy(c) assert(t == "READY!" and b == "OPEN")
c = L.card(nil, "e1", 90, 100, 1) assert(c.kind == "ready", "falls back to NextChestReadyAt without a queue entry")

-- Auto-open selection and never-skip rules.
local plain = {}
for r = 1, 5 do
    assert(not L.shouldAutoOpen({}, false, false, r, plain, false), "default opens nothing automatically")
end
assert(L.shouldAutoOpen({1}, false, false, 1, plain, false) and not L.shouldAutoOpen({1}, false, false, 2, plain, false))
assert(L.shouldAutoOpen({1, 2}, false, false, 2, plain, false) and not L.shouldAutoOpen({1, 2}, false, false, 5, plain, false))
local notable = {{shiny = true}, {big = true}, {eventMutationId = "gold_rush"}, {genes = {conditionId = "rainbow"}}, {genes = {conditionId = "astra"}}}
for _, outcome in notable do
    for r = 1, 5 do
        assert(not L.shouldAutoOpen({1, 2, 3, 4, 5}, false, false, r, outcome, false), "notable eggs are never auto-opened")
        assert(not L.shouldAutoOpen({}, false, false, r, outcome, true), "Open all never opens notable eggs either")
    end
end
assert(not L.shouldAutoOpen({1}, false, false, 1, nil, false), "unknown data is never hidden")
assert(L.shouldAutoOpen({}, false, false, 3, plain, true), "Open all covers every rarity")
assert(L.shouldAutoOpen({1}, false, false, 1, {failed = true}, false), "cracked eggs may auto-open (counted in the summary)")

-- Pass gate: when required and missing, rows are locked and the setting is ignored.
assert(not L.locked(false, false) and not L.locked(false, true) and L.locked(true, false) and not L.locked(true, true))
assert(#L.effective({1, 2}, true, false) == 0 and #L.effective({1, 2}, true, true) == 2 and #L.effective({1, 2}, false, false) == 2)
assert(not L.shouldAutoOpen({1, 2}, true, false, 1, plain, false) and L.shouldAutoOpen({1, 2}, true, true, 1, plain, false))
assert(not L.shouldAutoOpen({}, true, false, 1, plain, true), "locked also blocks Open all")

-- Auto-opened summary: best find on top, counts per rarity.
local summary = {total = 6, failed = 1, byRarity = {3, 1, 1, 0, 1}}
local lines = L.summaryLines(summary)
assert(lines[1] == "Auto-opened: 6" and lines[2] == "1 Legendary  |  1 Rare  |  1 Uncommon  |  3 Common  |  1 cracked", lines[2])
assert(#L.summaryLines({total = 0, failed = 0, byRarity = {0, 0, 0, 0, 0}}) == 1)

-- Never forced into hatching.
assert(L.afterRun() == "results")
assert(L.afterReveal(false, 5) == "continue" and L.afterReveal(false, 0) == "eggs" and L.afterReveal(true, 3) == "continue" and L.afterReveal(true, 0) == "eggs", "BD-170: Next egg never drops back to the Eggs screen while eggs remain")
print("Eggs screen checks passed: nest slots, single egg card, auto-open rules, pass gate, summary, never-forced hatching")
'''


def script():
    return ('local RS=' + module('src/shared/RevealSkip.luau') + '\n'
            'local script={Parent={RevealSkip=RS}}\nlocal function require(x) return x end\n'
            'local L=' + module('src/shared/EggsLogic.luau') + '\n' + BODY)


def static_checks():
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    config = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    assert re.search(r'AutoOpenRequiresPass\s*=\s*false', config), 'AutoOpenRequiresPass must default to false'
    assert '"NESTS"' not in boot and 'name=="nests"' not in boot, 'one Eggs screen: no separate NESTS rail button or menu'
    assert 'EggsScreen.render' in boot and 'EggsLogic.shouldAutoOpen' in boot
    handler = boot[boot.index('"LastSettledRunId"'):boot.index('"LastExitStatusAt"')]
    assert 'hatchNext' not in handler and 'autoHatching=true' not in handler, 'run end must never force hatching'
    nest = boot[boot.index('"LastNestClaimAt"'):boot.index('"LastRewardText"')]
    assert 'hatchNext' not in nest, 'opening a nest must not auto-hatch'
    assert 'ProcessReceipt' not in boot and 'PromptGamePassPurchase' not in boot, 'no Robux purchase code'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    static_checks()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'eggs_screen.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
