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
local t, b = L.cardCopy(c) assert(t == "Go find eggs on the island!" and b == "Explore")
c = L.card(nil, "", 0, 100, 3) assert(c.kind == "banked" and not c.canOpen)
c = L.card({readyAt = 160}, "e1", 160, 100, 4) assert(c.kind == "growing" and c.remaining == 60 and not c.canOpen and c.waiting == 4)
t, b = L.cardCopy(c) assert(t == "Growing..." and b == "GROWING")
c = L.card({readyAt = 160}, "e1", 160, 160, 4) assert(c.kind == "ready" and c.canOpen and c.remaining == 0)
t, b = L.cardCopy(c) assert(t == "Ready to open!" and b == "OPEN EGG", "owner 2026-10-18: a clear ready state")
assert(L.cardCopy(L.card({readyAt = 160}, "e1", 160, 100, 4))[2] ~= "OPEN EGG", "a growing egg never shows the ready button")

-- Owner 2026-10-18: "Egg 1 of 55" (every unopened egg, the card egg included); the captions name the two chips; only Cracked has a shell line.
assert(FP.eggOfText(5, 50) == "Egg 1 of 55" and FP.eggOfText(1, 0) == "Egg 1 of 1" and FP.eggOfText(0, 3) == "Egg 1 of 3")
assert(FP.eggOfText(0, 0) == nil and FP.eggOfText(-2, -1) == nil, "never 'Egg 1 of 0'")
assert(FP.eggOfText(5, 26) == "Egg 1 of " .. tostring(L.waitingTotal(5, 26, true)), "same count as the waiting total")
assert(FP.ChipTypeCaption == "Egg type" and FP.ChipShellCaption == "Shell")
assert(#FP.CrackedShellLine <= 32 and not FP.CrackedShellLine:find("%d"), "short kid copy")
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
-- BD-1057: a secret find and a Legendary are never skipped silently under Skip the rest / Open all.
for r = 1, 5 do
    assert(not L.shouldAutoOpen({1, 2, 3, 4, 5}, false, false, r, {secret = true}, false), "a secret is never auto-opened")
    assert(not L.shouldAutoOpen({}, false, false, r, {secret = true}, true), "Open all never opens a secret")
    assert(not L.shouldAutoOpen({}, false, false, r, {secretSpeciesId = "dodo"}, true), "Open all never opens a secret (id form)")
end
assert(not L.shouldAutoOpen({}, false, false, 5, plain, true), "Open all stops on a Legendary")
assert(not L.shouldAutoOpen({}, false, true, 5, plain, true), "Open all stops on a Legendary (pass owner)")
for r = 1, 4 do assert(L.shouldAutoOpen({}, false, false, r, plain, true), "Open all still covers rarity " .. r) end
assert(L.shouldAutoOpen({5}, false, false, 5, plain, false), "the player's own AUTO choice for Legendary is honoured")
assert(L.shouldAutoOpen({}, false, false, 3, plain, true), "Open all covers every rarity")
assert(L.shouldAutoOpen({1}, false, false, 1, {failed = true}, false), "cracked eggs may auto-open (counted in the summary)")

-- BD-525: the species is read from "<count>x <species>" and mapped to its rarity for EVERY species; unreadable or unknown
-- species are never skipped (they used to default to a Common "compy").
local RAR = {compy = 1, raptor = 1, gallimimus = 1, microraptor = 1, dimorphodon = 1, archaeopteryx = 2, stegosaurus = 2, parasaurolophus = 2,
    pachycephalosaurus = 2, pteranodon = 2, triceratops = 3, brachiosaurus = 3, baryonyx = 3, ichthyosaurus = 3, plesiosaurus = 3,
    ankylosaurus = 4, elasmosaurus = 4, therizinosaurus = 4, quetzalcoatlus = 4, tyrannosaurus = 5, spinosaurus = 5, mosasaurus = 5}
for species, rarity in RAR do
    for _, count in {0, 1, 2, 3} do
        assert(L.parseSpecies(count .. "x " .. species) == species, "parse " .. species)
        local skip, id, r = L.autoOpenDecision({rarity}, false, false, count .. "x " .. species, RAR, {}, false)
        assert(skip and id == species and r == rarity, "ticked rarity of " .. species .. " is skipped")
        local other = if rarity == 1 then 2 else 1
        assert(not (L.autoOpenDecision({other}, false, false, count .. "x " .. species, RAR, {}, false)), "other rarity ticked: " .. species .. " is shown")
    end
end
for _, bad in {"", "x", "compy", "1x", "1x ", "New dinosaur", "1x two words", "1x Compy!", 5, false} do
    assert(L.parseSpecies(bad) == nil, "unreadable text gives no species")
    assert(not (L.autoOpenDecision({1, 2, 3, 4, 5}, false, false, bad, RAR, {}, true)), "unreadable text is never skipped")
end
assert(not (L.autoOpenDecision({1, 2, 3, 4, 5}, false, false, "1x notaspecies", RAR, {}, true)), "unknown species is never skipped")
-- BD-1057: a secret species is not in the rarity table, so Skip the rest shows it; a Legendary is shown too (its own AUTO tick still skips it).
for _, secretId in {"chickosaurus", "pigeon", "dodo", "duck", "penguin", "budgiesaurus", "foxosaurus", "cockatoosaurus", "eaglesaurus"} do
    assert(not (L.autoOpenDecision({1, 2, 3, 4, 5}, false, false, "1x " .. secretId, RAR, {}, true)), "Skip the rest shows the secret " .. secretId)
    assert(not (L.autoOpenDecision({1, 2, 3, 4, 5}, false, false, "1x " .. secretId, RAR, {secret = true}, true)), "secret outcome " .. secretId)
end
for _, legendary in {"tyrannosaurus", "spinosaurus", "mosasaurus"} do
    assert(not (L.autoOpenDecision({}, false, false, "1x " .. legendary, RAR, {}, true)), "Skip the rest shows the Legendary " .. legendary)
    assert((L.autoOpenDecision({5}, false, false, "1x " .. legendary, RAR, {}, false)), "own AUTO tick for Legendary skips " .. legendary)
end

-- BD-525: every auto-open setting (all 32 subsets of the five rarities) x every rarity x every kind of egg: an egg is skipped
-- exactly when its rarity is ticked and it is not Shiny, BIG, mutated, Rainbow or Astra; everything else is shown.
local kinds = {
    {name = "plain", outcome = {big = false, shiny = false, eventMutationId = "", genes = {conditionId = "normal"}}, notable = false},
    {name = "dirty", outcome = {genes = {conditionId = "dirty"}}, notable = false},
    {name = "cracked", outcome = {genes = {conditionId = "cracked"}}, notable = false},
    {name = "failed splat", outcome = {failed = true, genes = {conditionId = "cracked"}}, notable = false},
    {name = "rainbow", outcome = {genes = {conditionId = "rainbow"}}, notable = true},
    {name = "astra", outcome = {genes = {conditionId = "astra"}}, notable = true},
    {name = "shiny", outcome = {shiny = true, genes = {conditionId = "normal"}}, notable = true},
    {name = "big", outcome = {big = true, genes = {conditionId = "normal"}}, notable = true},
    {name = "mutation", outcome = {eventMutationId = "ember", genes = {conditionId = "normal"}}, notable = true},
}
local rep = {"compy", "archaeopteryx", "triceratops", "ankylosaurus", "tyrannosaurus"} -- one species per rarity
local checked = 0
for mask = 0, 31 do
    local selection = {}
    for r = 1, 5 do if bit32.band(mask, bit32.lshift(1, r - 1)) ~= 0 then table.insert(selection, r) end end
    for r = 1, 5 do
        local ticked = bit32.band(mask, bit32.lshift(1, r - 1)) ~= 0
        for _, kind in kinds do
            local skip = L.autoOpenDecision(selection, false, false, "1x " .. rep[r], RAR, kind.outcome, false)
            assert(skip == (ticked and not kind.notable), string.format("setting %d rarity %d %s: skip=%s", mask, r, kind.name, tostring(skip)))
            -- the same through the pass gate: locked means nothing is skipped, an owned pass changes nothing
            assert(not (L.autoOpenDecision(selection, true, false, "1x " .. rep[r], RAR, kind.outcome, false)))
            assert((L.autoOpenDecision(selection, true, true, "1x " .. rep[r], RAR, kind.outcome, false)) == skip)
            checked += 1
        end
    end
end
assert(checked == 32 * 5 * #kinds)
-- Why a Common egg stayed on screen: only Rainbow/Astra need a word (Shiny, BIG and mutations show on the reveal itself), and only
-- when the player's setting covers the rarity.
assert(L.shownReason({1}, false, false, 1, {conditionId = "rainbow"}) == "Rainbow egg! Always shown")
assert(L.shownReason({1}, false, false, 1, {conditionId = "astra"}) == "Astra egg! Always shown")
assert(L.shownReason({2}, false, false, 1, {conditionId = "rainbow"}) == nil, "rarity not on AUTO: normal heading")
assert(L.shownReason({}, false, false, 1, {conditionId = "rainbow"}) == nil and L.shownReason({1}, true, false, 1, {conditionId = "rainbow"}) == nil)
assert(L.shownReason({1}, false, false, 1, {conditionId = "dirty"}) == nil and L.shownReason({1}, false, false, 1, nil) == nil)

-- Pass gate: when required and missing, rows are locked and the setting is ignored.
assert(not L.locked(false, false) and not L.locked(false, true) and L.locked(true, false) and not L.locked(true, true))
assert(#L.effective({1, 2}, true, false) == 0 and #L.effective({1, 2}, true, true) == 2 and #L.effective({1, 2}, false, false) == 2)
assert(not L.shouldAutoOpen({1, 2}, true, false, 1, plain, false) and L.shouldAutoOpen({1, 2}, true, true, 1, plain, false))
assert(not L.shouldAutoOpen({}, true, false, 1, plain, true), "locked also blocks Open all")

-- Auto-opened summary: best find on top, counts per rarity.
local summary = {total = 6, failed = 1, byRarity = {3, 1, 1, 0, 1}}
local lines = L.summaryLines(summary)
assert(lines[1] == "Auto-opened: 6" and lines[2] == "1 Legendary  |  1 Rare  |  1 Uncommon  |  3 Common  |  1 egg did not hatch", lines[2])
-- BD-1001: cracked eggs are counted on their own (plain words), not twice inside the rarity counts.
local hatchedOnly = {total = 6, failed = 2, byRarity = {3, 1, 1, 0, 1}, hatchedByRarity = {1, 1, 1, 0, 1}}
assert(L.summaryLines(hatchedOnly)[2] == "1 Legendary  |  1 Rare  |  1 Uncommon  |  1 Common  |  2 eggs did not hatch", L.summaryLines(hatchedOnly)[2])
-- BD-1001: "Skip the rest" (openAll) goes through cracked eggs, with or without a readable species, even when they carry Shiny/BIG/event flags.
local crackedOutcomes = {{failed = true, genes = {conditionId = "cracked"}}, {failed = true, shiny = true, big = true, eventMutationId = "ember", genes = {conditionId = "cracked"}}}
for _, outcome in crackedOutcomes do
    for _, text in {"0x compy", "0x tyrannosaurus", "0x notaspecies", "garbage", ""} do
        local skip, _, rarity = L.autoOpenDecision({}, false, false, text, RAR, outcome, true)
        assert(skip and rarity ~= nil, "Skip the rest does not stop at a cracked egg: " .. text)
        assert(not (L.autoOpenDecision({}, false, false, text, RAR, outcome, false)), "one-by-one reveal still shows the splat: " .. text)
        assert(not (L.autoOpenDecision({}, true, false, text, RAR, outcome, true)), "locked pass still blocks skipping")
    end
end
assert(not (L.autoOpenDecision({}, false, false, "1x notaspecies", RAR, {genes = {conditionId = "cracked"}}, true)), "an unreadable species that did not fail is still shown")
-- 150 eggs with every second one cracked: Skip the rest shows none of them one by one.
local stops = 0
for i = 1, 150 do
    local outcome = if i % 2 == 0 then {failed = true, shiny = i % 10 == 0, genes = {conditionId = "cracked"}} else {genes = {conditionId = "normal"}}
    local text = (if i % 2 == 0 then "0x " else "1x ") .. "compy"
    if not (L.autoOpenDecision({}, false, false, text, RAR, outcome, true)) then stops += 1 end
end
assert(stops == 0, "a 150-egg batch needs no taps after Skip the rest")
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
    assert 'EggsScreen.render' in boot and 'EggsLogic.autoOpenDecision' in boot
    # BD-525: the handler no longer parses the species itself and no longer defaults an unreadable egg to a Common one
    claimed = boot[boot.index('PrivateState.onChanged("LastClaimedChestId"'):boot.index('docs/133 demo hook')]
    assert 'string.match' not in claimed and 'shouldAutoOpen' not in claimed, 'auto-open decision lives in EggsLogic.autoOpenDecision'
    # BD-525: every claim has its own 8 s watchdog; an older one must not reset autoHatching while a later claim is in flight
    assert 'hatchState.serial==serial' in boot, 'claim watchdog is per claim'
    # BD-519: the hatch owns its body position; open() must not slide it
    opener = boot[boot.index('local function open(name: string)'):boot.index('local fusionProbe')]
    assert 'if name~="hatch" then' in opener and 'Theme.cancel(body)' in opener, 'open() must not slide the hatch body (BD-519)'
    handler = boot[boot.index('"LastSettledRunId"'):boot.index('"LastExitStatusAt"')]
    assert 'hatchNext' not in handler and 'autoHatching=true' not in handler, 'run end must never force hatching'
    nest = boot[boot.index('"LastNestClaimAt"'):boot.index('"LastRewardText"')]
    assert 'hatchNext' not in nest, 'opening a nest must not auto-hatch'
    assert 'ProcessReceipt' not in boot and 'PromptGamePassPurchase' not in boot, 'no Robux purchase code'
    # BD-1019 (docs/181): the Eggs screen and the hatch it starts stay closable. The nest cards, the Next egg card and its OPEN button live in the
    # menu body below X, so nothing in EggsScreen may be a full-screen or Active cover; closing (X, tap outside, Escape, gamepad B) leaves the queue alone.
    eggs_ui = (ROOT / 'src/client/EggsScreen.luau').read_text(encoding='utf-8')
    assert 'fromScale(1, 1)' not in eggs_ui and 'Active = true' not in eggs_ui, 'EggsScreen must not cover the menu header (X)'
    assert 'openEgg=function()' in boot and 'if hatchPending then return end' in boot, 'OPEN starts one claim at a time; closing never re-sends it'
    assert 'onAbort=function() skipAllReveals=false' in boot, 'closing a hatch party mid-way resets Skip-the-rest (the next party must not start skipping)'
    # BD-208 / BD-094: the Eggs page reads the official stage + condition eggs, with the code-drawn visuals as the exact fallback
    screen = (ROOT / 'src/client/EggsScreen.luau').read_text(encoding='utf-8')
    assert 'ConditionStage.hero(card' in screen and 'StageRules.conditionKey(' in screen and 'StageRules.heroSide(' in screen, 'Eggs card reads the stage'
    assert 'else' + chr(10) + '        stage = EggPicture.stage(card, stageW, stageH, accent)' in screen, 'no stage id: today tile floor stays'
    assert 'EggPicture.add(stage, if entry and look == "genes" then entry.genes else nil, eggSize)' in screen, 'tinted egg fallback stays'
    assert 'art(icon, "egg_nest_single"' in screen, 'nest slots read the nest icon'
    # owner 2026-10-18: the card says which egg it is, names both chips, and a Cracked shell says it may not hatch
    assert 'Copy.eggOfText(' in screen and 'Copy.waitingText(' not in screen, 'card shows Egg 1 of N'
    assert 'Copy.ChipTypeCaption' in screen and 'Copy.ChipShellCaption' in screen, 'both chips have a caption'
    assert 'Copy.CrackedShellLine' in screen and 'conditionId == "cracked"' in screen, 'Cracked shell line'
    assert 'Copy.ReadyStatus' in screen and 'READY!' not in screen, 'ready state text lives in FtueP1'
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
