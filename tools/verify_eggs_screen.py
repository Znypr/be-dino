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

-- BD-259 / BD-369: "Eggs waiting" counts every unopened egg INCLUDING the card egg: 31 run eggs = 5 in the line + 26 banked -> 31.
assert(L.waitingTotal(5, 26, true) == 31 and L.waitingTotal(1, 0, true) == 1 and L.waitingTotal(0, 3, false) == 3)
assert(L.waitingTotal(0, 0, false) == 0 and L.waitingTotal(-2, -1, true) == 0)

-- Single next-egg card state machine.
local c = L.card(nil, "", 0, 100, 0)
assert(c.kind == "empty" and not c.canOpen)
local t, b = L.cardCopy(c) assert(t == "Go find eggs on the island!" and b == "EXPLORE ISLAND")
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

-- BD-208: official stage rules. The stage is a SQUARE (phone: nothing stretched), only real rbxassetid ids count, and a half-uploaded set falls back.
assert(SR.heroSide(300, 246) == 246 and SR.heroSide(300, 224) == 224 and SR.heroSide(900, 900) == 300 and SR.heroSide(40, 40) == 120, "square side")
assert(SR.heroSide(300.7, 246.9) == 246, "whole pixels")
assert(SR.conditionKey("astra") == "astra" and SR.conditionKey("cracked") == "cracked" and SR.conditionKey("normal") == "normal")
assert(SR.conditionKey(nil) == "normal" and SR.conditionKey("stage") == "normal" and SR.conditionKey("nope") == "normal" and SR.conditionKey(5) == "normal", "unknown data is a plain egg")
assert(SR.resolve({}, "normal").stage == nil, "empty ids: the tile floor and tinted egg stay")
assert(SR.resolve({normal = "rbxassetid://5"}, "normal").egg == nil, "an egg picture alone is never shown")
local both = SR.resolve({stage = "rbxassetid://9", astra = "rbxassetid://7"}, "astra")
assert(both.stage == "rbxassetid://9" and both.egg == "rbxassetid://7")
assert(SR.resolve({stage = "rbxassetid://9"}, "astra").egg == nil, "stage only: the tinted egg stands on the pedestal")
local H = SR.Hero
assert(H.EggScale == 1.25 and H.PedestalY == .74 and H.PedestalY - 0.547 * H.EggScale > 0, "enlarged egg stays inside the stage")
print("Eggs screen checks passed: nest slots, single egg card, auto-open rules, pass gate, summary, never-forced hatching")
'''


def script():
    return ('local RS=' + module('src/shared/RevealSkip.luau') + '\n'
            'local FP=' + module('src/shared/FtueP1.luau') + '\n'
            'local script={Parent={RevealSkip=RS,FtueP1=FP}}\nlocal function require(x) return x end\n'
            'local SR=' + module('src/shared/ConditionStageRules.luau') + '\n'
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
    # BD-208 / BD-094: the Eggs page reads the official stage + condition eggs, with the code-drawn visuals as the exact fallback
    screen = (ROOT / 'src/client/EggsScreen.luau').read_text(encoding='utf-8')
    assert 'ConditionStage.hero(card' in screen and 'StageRules.conditionKey(' in screen and 'StageRules.heroSide(' in screen, 'Eggs card reads the stage'
    assert 'else' + chr(10) + '        stage = EggPicture.stage(card, stageW, stageH, accent)' in screen, 'no stage id: today tile floor stays'
    assert 'EggPicture.add(stage, if entry and look == "genes" then entry.genes else nil, eggSize)' in screen, 'tinted egg fallback stays'
    assert 'art(icon, "egg_nest_single"' in screen, 'nest slots read the nest icon'
    stage_ui = (ROOT / 'src/client/ConditionStage.luau').read_text(encoding='utf-8')
    hero = stage_ui[stage_ui.index('function Stage.hero'):]
    assert hero.count('ScaleType.Fit') == 2 and 'Crop' not in hero and 'Stretch' not in hero, 'phone: both images Fit, never stretched'
    assert 'if not pick.stage then return nil end' in hero, 'unbound stage returns nil (fallback)'
    theme = (ROOT / 'src/shared/UITheme.luau').read_text(encoding='utf-8')
    assert 'id=="egg_nest" or id=="egg_nest_single"' in theme, 'nest icon has a fallback when its id is empty'
    # the owner files exist, and the batch uploader lists every EMPTY stage slot (bound slots are skipped)
    import sys
    sys.path.insert(0, str(ROOT / 'tools'))
    import bind_assets
    import upload_batch
    slots = bind_assets.load_slots()
    names = ['egg_stage', 'egg_cond_cracked', 'egg_cond_dirty', 'egg_cond_normal', 'egg_cond_rainbow', 'egg_cond_astra']
    items, _skipped = upload_batch.collect(slots)
    listed = {it['slot']: it for it in items}
    for n in names:
        current = bind_assets.current_value(slots[n], (ROOT / slots[n]['file']).read_text(encoding='utf-8'))
        assert current or n in listed, f'upload batch misses the empty slot {n}'
        if n in listed:
            assert (ROOT / listed[n]['file']).exists(), f'{n} file missing'


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
