#!/usr/bin/env python3
"""BD-1170 part A (docs/221 C1 #5 and C3 #2, docs/227): a duplicate shows progress toward the next fusion step (Config.DupProgressEnabled).

What is checked, with the pinned Luau runtime and the REAL src/shared/DupProgress.luau and src/shared/FusionSelection.luau:
  1. the count rule IS the Fusion Menu's rule: for a mixed list (locked, favourite, older dino without a pattern, Shiny, BIG, mutation,
     cosmetics, other species, other stages, junk) Dup.count equals a count made with FusionSelection.context + ineligibility the way the
     menu anchors a selection, equals FusionSelection.bestGroup, and "ready" agrees with what the menu's Fill button can fill;
  2. the words: "1 of 6 for Gold!", "5 of 6 for Gold!", "Ready for Gold!" (at 6 and above), "2 of 3 for Emerald!", "Ready for Diamond!",
     "1 more to go" / "3 more to go" / "Tap to fuse!", no line under 2 copies in the hatch, kid copy (docs/72: short, no "x", no "3/6");
  3. the hatch counting: the number is the count AFTER this hatch (a quiet copy list plus the copies revealed since), a list that was
     asked for before a hatch and arrives after it is thrown away, nothing is asked while eggs are buffered or an egg is opening, a
     failed egg adds nothing, "2x Compy" adds two, no list = no number;
  4. the flag: false in Config and in the default profile, ON in the playtest profile, in the rehearsal list; with the flag off the client
     module touches nothing (run with stubs that raise on any Instance, task or remote use), the reveal and the Index hooks are nil;
  5. wiring: HatchSequence and the Index page call the module, Bootstrap is not touched, the module holds no second eligibility rule;
  6. mutants put each defect back and the checks must fail.
NOT Studio evidence: no Instance is built here, so the look of the line and of the bars (position, size, colour on screen) is unverified.
Usage: python tools/verify_dup_progress.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DUP = 'src/shared/DupProgress.luau'
SEL = 'src/shared/FusionSelection.luau'
CLIENT = 'src/client/DupProgressClient.luau'
CONFIG = 'src/shared/Config.luau'
PROFILES = 'tools/release_profiles.py'
HATCH = 'src/client/HatchSequence.luau'
SCREENS = 'src/client/DinoIndexScreens.luau'
PANELS = 'src/client/DinoIndexPanels.luau'
MENU = 'src/client/FusionMenu.luau'


def reader(mutant=None):
    def read(path):
        text = (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')
        if mutant and mutant[0] == path:
            assert text.count(mutant[1]) == 1, 'mutant anchor must match once in %s: %r' % (path, mutant[1])
            text = text.replace(mutant[1], mutant[2])
        return text
    return read


def wrap(source):
    return '(function()\n' + source + '\nend)()'


PRELUDE = r'''
local script = {Parent = {FusionSelection = "FusionSelection", ProgressionConfig = "ProgressionConfig"}}
local Sel
local function require(key)
    if key == "FusionSelection" then return Sel end
    error("not available offline: " .. tostring(key))
end
Sel = __SEL__
local Dup = __DUP__
'''

BODY = r'''
local serial = 0
local function dino(species, pattern, stage, extra)
    serial += 1
    local d = {instanceId = "p/d:" .. serial, speciesId = species, stage = stage or "base", genes = {patternId = pattern, primaryColorId = "c1", secondaryColorId = "c2"}}
    for k, v in extra or {} do d[k] = v end
    return d
end
local function many(n, species, pattern, stage, extra)
    local t = {} for _ = 1, n do table.insert(t, dino(species, pattern, stage, extra)) end return t
end
local function join(...) local out = {} for _, list in {...} do for _, d in list do table.insert(out, d) end end return out end

-- 1. The count rule is the Fusion Menu's rule -----------------------------------------------------------------------
-- The menu's way: the first selected copy anchors species (and pattern above Gold); every other copy is asked with that context.
local function menuCount(dinos, speciesId, stageId)
    local clean = {}
    for _, d in dinos do if type(d) == "table" and type(d.instanceId) == "string" then table.insert(clean, d) end end
    local byId = Sel.index(clean)
    local best = 0
    for _, anchor in clean do
        if anchor.speciesId == speciesId and Sel.ineligibility(anchor, {targetStage = stageId}) == nil then
            local ctx = Sel.context(stageId, {anchor.instanceId}, byId, nil)
            local n = 0
            for _, d in clean do if Sel.ineligibility(d, ctx) == nil then n += 1 end end
            best = math.max(best, n)
        end
    end
    return best
end
local mixed = join(
    many(3, "compy", "06_wavy_stripes"), many(2, "compy", "03_round_spots"),
    {dino("compy", "06_wavy_stripes", "base", {locked = true})},        -- locked: the menu refuses it
    {dino("compy", "06_wavy_stripes", "base", {favorited = true})},     -- favourite: refused
    {dino("compy", nil, "base")}, {dino("compy", "", "base")},          -- older dino without a saved pattern: refused
    {dino("compy", "06_wavy_stripes", "base", {shiny = true})},         -- Shiny: the menu lets the player pick it, so it counts
    {dino("compy", "03_round_spots", "base", {big = true, mutationId = "frost"})},
    {dino("compy", "03_round_spots", "base", {auraCount = 1, equippedAuraId = "glow"})},
    many(4, "rex", "06_wavy_stripes"),
    many(2, "compy", "06_wavy_stripes", "gold"), many(1, "compy", "03_round_spots", "gold"),
    {dino("compy", "06_wavy_stripes", "gold", {locked = true})},
    many(1, "compy", "06_wavy_stripes", "emerald"), many(2, "compy", "03_round_spots", "emerald"),
    many(1, "compy", "06_wavy_stripes", "diamond"),
    many(5, "trike", "09_dots", "gold"),
    {5, "x", {}, {speciesId = "compy"}})
for _, species in {"compy", "rex", "trike", "nobody"} do
    for _, stage in Sel.Stages do
        local have = Dup.count(mixed, species, stage.id)
        local want = menuCount(mixed, species, stage.id)
        assert(have == want, string.format("count rule differs from the Fusion Menu: %s %s got %d, menu %d", species, stage.id, have, want))
    end
end
assert(Dup.count(mixed, "compy", "gold") == 8, "3 wavy + 2 spots + Shiny + BIG + cosmetic = 8 Base Compy the menu accepts, got " .. Dup.count(mixed, "compy", "gold"))
assert(Dup.count(mixed, "compy", "emerald") == 2, "Emerald needs ONE pattern: 2 wavy Gold (the locked one and the spotted one do not help)")
local n, pattern = Dup.count(mixed, "compy", "diamond")
assert(n == 2 and pattern == "03_round_spots", "Diamond: 2 spotted Emerald")
assert(Dup.count(mixed, "rex", "gold") == 4 and Dup.count(mixed, "rex", "emerald") == 0)
assert(Dup.count(mixed, "compy", "platinum") == 0 and Dup.count(nil, "compy", "gold") == 0 and Dup.count("x", "compy", "gold") == 0)
-- same group as the menu's own goal sentence picks (single-species lists, so bestGroup has one candidate species)
for _, stage in Sel.Stages do
    local only = {}
    for _, d in mixed do if type(d) == "table" and d.speciesId == "compy" and type(d.instanceId) == "string" then table.insert(only, d) end end
    local group = Sel.bestGroup(only, stage.id)
    assert((group and group.count or 0) == Dup.count(only, "compy", stage.id), "bestGroup parity " .. stage.id)
end
-- ready agrees with the menu's Fill button (plain copies only: Fill never takes a Shiny)
for count = 0, 8 do
    local list = many(count, "compy", "06_wavy_stripes")
    local step = Dup.step(list, "compy", "gold")
    local filled = Sel.autoFill(list, {}, "gold", {speciesId = "compy"}, nil)
    assert(step.ready == (#filled == Sel.donorCount("gold")), "ready must mean the menu can fill every slot, at " .. count)
    assert(step.need == Sel.donorCount("gold") and step.have == count)
end
for _, stage in Sel.Stages do assert(Dup.step({}, "compy", stage.id).need == Sel.donorCount(stage.id), "the recipe size comes from FusionSelection.Stages") end
assert(Dup.step({}, "compy", "platinum") == nil)
-- an order change never changes the number or the pattern
local reversed = {} for i = #mixed, 1, -1 do table.insert(reversed, mixed[i]) end
for _, stage in Sel.Stages do
    local a, pa = Dup.count(mixed, "compy", stage.id)
    local b, pb = Dup.count(reversed, "compy", stage.id)
    assert(a == b and pa == pb, "order dependent: " .. stage.id)
end
local tie = join(many(2, "compy", "b_pattern", "gold"), many(2, "compy", "a_pattern", "gold"))
local _, tiePattern = Dup.count(tie, "compy", "emerald")
assert(tiePattern == "a_pattern", "a tie goes to the smallest pattern id")

-- 2. The words --------------------------------------------------------------------------------------------------------
local function gold(count) return Dup.step(many(count, "compy", "06_wavy_stripes"), "compy", "gold") end
assert(Dup.text(gold(0)) == nil, "no copy = no words")
assert(Dup.text(gold(1)) == "1 of 6 for Gold!")
assert(Dup.text(gold(3)) == "3 of 6 for Gold!")
assert(Dup.text(gold(5)) == "5 of 6 for Gold!")
assert(Dup.text(gold(6)) == "Ready for Gold!" and gold(6).ready == true)
assert(Dup.text(gold(9)) == "Ready for Gold!" and gold(9).fraction == 1, "more than enough is still ready, the bar never overflows")
assert(gold(5).ready == false and math.abs(gold(3).fraction - .5) < 1e-9)
assert(Dup.hint(gold(5)) == "1 more to go" and Dup.hint(gold(3)) == "3 more to go" and Dup.hint(gold(6)) == "Tap to fuse!")
assert(Dup.text(Dup.step(many(2, "compy", "06_wavy_stripes", "gold"), "compy", "emerald")) == "2 of 3 for Emerald!")
assert(Dup.text(Dup.step(many(2, "compy", "06_wavy_stripes", "emerald"), "compy", "diamond")) == "Ready for Diamond!")
assert(Dup.step(many(2, "compy", "06_wavy_stripes"), "compy", "gold", 3).have == 5, "extra = copies revealed since the list")
-- the hatch line: a real duplicate only
assert(Dup.hatchLine(nil) == nil and Dup.hatchLine(0) == nil and Dup.hatchLine(1) == nil, "one copy is not a duplicate yet")
assert(Dup.hatchLine(2).text == "2 of 6 for Gold!" and Dup.hatchLine(2).ready == false)
assert(Dup.hatchLine(5).text == "5 of 6 for Gold!")
assert(Dup.hatchLine(6).text == "Ready for Gold!" and Dup.hatchLine(6).ready == true)
assert(Dup.hatchLine(40).text == "Ready for Gold!")
-- kid copy (docs/72): short, plain, no "x", no "3/6", no percent
for count = 1, 12 do
    for _, words in {Dup.text(gold(count)), Dup.hint(gold(count))} do
        assert(#words <= 20, "too long: " .. words)
        assert(not string.find(words, "%d/%d") and not string.find(words, "%dx") and not string.find(words, "%%") and not string.find(words, "%."), "not kid copy: " .. words)
    end
end
-- the Index species page: ladder order, only started steps, words attached
local steps = Dup.speciesSteps(mixed, "compy")
assert(#steps == 3 and steps[1].stageId == "gold" and steps[2].stageId == "emerald" and steps[3].stageId == "diamond")
assert(steps[1].text == "Ready for Gold!" and steps[1].hint == "Tap to fuse!")
assert(steps[2].text == "2 of 3 for Emerald!" and steps[2].hint == "1 more to go")
assert(steps[3].text == "Ready for Diamond!")
steps = Dup.speciesSteps(mixed, "rex")
assert(#steps == 1 and steps[1].text == "4 of 6 for Gold!" and steps[1].hint == "2 more to go", "no Gold copies = no Emerald bar")
steps = Dup.speciesSteps(mixed, "trike")
assert(#steps == 1 and steps[1].stageId == "emerald" and steps[1].text == "Ready for Emerald!", "Gold copies only = the Emerald bar alone")
assert(#Dup.speciesSteps(mixed, "nobody") == 0 and #Dup.speciesSteps(nil, "compy") == 0)
assert(#Dup.speciesSteps({dino("compy", "06_wavy_stripes", "base", {locked = true})}, "compy") == 0, "only a locked copy = nothing to show")

-- 3. The hatch counting ---------------------------------------------------------------------------------------------
assert(Dup.copiesFromName("Compy") == 1 and Dup.copiesFromName("2x Compy") == 2 and Dup.copiesFromName("3x T. rex") == 3 and Dup.copiesFromName(nil) == 1)
local t = Dup.tracker()
assert(Dup.have(t, "compy") == nil, "no list yet = no number")
assert(Dup.quiet(t, 100, 0) == true)
-- an egg opens before any list is known: no number, and no request while it is opening
Dup.opened(t, 100)
assert(Dup.quiet(t, 100.5, 0) == false and Dup.quiet(t, 103, 0) == false, "an opening egg blocks a re-read")
assert(Dup.hatched(t, "compy", 1, 101) == nil, "still no list")
assert(Dup.quiet(t, 101.5, 0) == false, "the egg counts are published a moment after the result")
assert(Dup.quiet(t, 102.1, 3) == false, "buffered eggs are already in the save: never ask now")
assert(Dup.quiet(t, 102.1, 0) == true)
-- a list asked for while quiet and answered while quiet is taken; it already holds that first Compy
local list = many(2, "compy", "06_wavy_stripes")
local token = Dup.request(t)
assert(Dup.quiet(t, 103, 0) == false, "one request at a time")
assert(Dup.arrived(t, token, list, 0) == true and Dup.have(t, "compy") == 2, "the revealed-since count starts again at zero")
-- a party: each reveal adds its own copies, the number is the count AFTER this hatch
Dup.opened(t, 110)
assert(Dup.hatched(t, "compy", 1, 111) == 3)
Dup.opened(t, 112)
assert(Dup.hatched(t, "rex", 1, 113) == 1 and Dup.have(t, "compy") == 3)
Dup.opened(t, 114)
assert(Dup.hatched(t, "compy", 2, 115) == 5, "2x Compy adds two")
Dup.opened(t, 116)
assert(Dup.hatched(t, "compy", 0, 117) == 5, "a failed egg adds nothing")
-- a list asked for, then an egg opens before it arrives: thrown away (it may or may not hold that egg)
token = Dup.request(t)
Dup.opened(t, 120)
local stale = many(9, "compy", "06_wavy_stripes")
assert(Dup.arrived(t, token, stale, 0) == false and Dup.have(t, "compy") == 5, "a stale list must not replace the count")
assert(Dup.hatched(t, "compy", 1, 121) == 6 and Dup.hatchLine(Dup.have(t, "compy")).ready == true)
-- a list that arrives while eggs are buffered is thrown away too; a failed request changes nothing and frees the next one
token = Dup.request(t)
assert(Dup.arrived(t, token, stale, 2) == false and Dup.have(t, "compy") == 6)
token = Dup.request(t)
assert(Dup.arrived(t, token, nil, 0) == false and Dup.have(t, "compy") == 6 and t.requested == nil)
-- quiet again: the server's own list wins (a fusion in between used six)
assert(Dup.quiet(t, 123, 0) == true)
token = Dup.request(t)
assert(Dup.arrived(t, token, many(0, "compy", "x"), 0) == true and Dup.have(t, "compy") == 0)
-- an egg that never answers (menu closed mid-party) stops blocking after Dup.OpenTimeout
Dup.opened(t, 200)
assert(Dup.quiet(t, 200 + Dup.OpenTimeout - .1, 0) == false and Dup.quiet(t, 200 + Dup.OpenTimeout + .1, 0) == true)
print("dup progress logic ok")
'''

# The client module with the flag OFF: every entry point must return before it touches an Instance, a thread or a remote.
CLIENT_OFF = r'''
local touched = function(what) return function() error("flag off must not touch " .. what, 0) end end
local Shared = setmetatable({}, {__index = function(_, k) return "Shared/" .. k end})
local game = {GetService = function(_, name)
    if name == "ReplicatedStorage" then return {WaitForChild = function() return Shared end, FindFirstChild = touched("the remotes")} end
    return setmetatable({}, {__index = function() return touched(name) end})
end}
local script = {Parent = setmetatable({}, {__index = function(_, k) return "Client/" .. k end})}
local Instance = {new = touched("Instance.new")}
local task = setmetatable({}, {__index = function() return touched("task") end})
local UDim2 = setmetatable({}, {__index = function() return touched("UDim2") end})
local function require(key)
    if key == "Shared/Config" then return {DupProgressEnabled = __FLAG__} end
    if key == "Shared/DupProgress" then return setmetatable({}, {__index = function() return touched("DupProgress") end}) end
    if key == "Shared/UITheme" then return {Colors = {}} end
    if key == "Client/PrivateState" then return setmetatable({}, {__index = function() return touched("PrivateState") end}) end
    error("flag off must not require " .. tostring(key), 0)
end
local Client = __CLIENT__
Client.start()
assert(Client.hatchPlay({ZIndex = 1}) == nil, "flag off: no hatch line")
Client.hatchResult(nil, "compy", false, "Compy", nil)
Client.hatchReveal(nil, 0)
assert(Client.indexRow({}, {}, "compy", 50, 44, function() end) == 0, "flag off: no Index row")
print("dup progress client is inert with the flag off")
'''


def run(runner, source):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'dup_progress.luau'
        path.write_text(source, encoding='utf-8')
        done = subprocess.run([runner, str(path)], capture_output=True, text=True, timeout=120)
    return done.returncode == 0, (done.stdout + done.stderr)


def logic(runner, read):
    source = PRELUDE.replace('__SEL__', wrap(read(SEL))).replace('__DUP__', wrap(read(DUP))) + BODY
    return run(runner, source)


def client_off(runner, read, flag='false'):
    return run(runner, CLIENT_OFF.replace('__FLAG__', flag).replace('__CLIENT__', wrap(read(CLIENT))))


def code_only(text):
    return '\n'.join(line.split('--', 1)[0] for line in text.splitlines())


def static_checks(read):
    cfg = read(CONFIG)
    assert len(re.findall(r'^    DupProgressEnabled = false,$', cfg, re.M)) == 1, 'DupProgressEnabled ships false in Config (once)'
    profiles = read(PROFILES)
    assert '_flag_off("DupProgressEnabled",' in profiles, 'the default profile pins the flag off'
    assert 'Rule("DupProgressEnabled", "set", True,' in profiles, 'the playtest profile sets it on (docs/157 standing rule)'
    assert '("DupProgressEnabled", "BD-1170' in profiles, 'the rehearsal list has it'
    assert '"DupProgressEnabled"' in read('tools/release_playtest.py'), 'the playtest manifest records it'
    dup = code_only(read(DUP))
    assert dup.count('Sel.ineligibility(d, {targetStage = stageId, speciesId = speciesId}) == nil') == 1, 'the count asks the Fusion Menu rule'
    for needle in ('.locked', '.favorited', '.stage ==', '.stage ~=', 'donorCount = ', 'Instance', 'game:', 'math.random'):
        assert needle not in dup, 'DupProgress must not hold its own rule or touch the engine: ' + needle
    client = read(CLIENT)
    assert 'local function on(): boolean return Config.DupProgressEnabled == true end' in client, 'one flag read'
    for needle in ('    if not on() or tracker then return end', '    if not on() then return nil end', '    if not on() then return 0 end'):
        assert client.count(needle) == 1, 'client guard missing: ' + needle
    ccode = code_only(client)
    for needle in ('FireServer', 'OnClientEvent', 'rbxassetid', 'Sfx', 'action = "fuse"', 'action = "quote"'):
        assert needle not in ccode, 'the client module only reads the copy list: ' + needle
    assert ccode.count('InvokeServer({action = "list"') == 1, 'one read-only request: the Fusion Menu list'
    assert 'if cursor ~= nil then return nil end' in ccode, 'a list that does not fit is not counted (no wrong number)'
    hatch = read(HATCH)
    assert hatch.count('local dupLine = dupPlay(a.body)') == 1 and hatch.count('    if (Config :: any).DupProgressEnabled ~= true then return nil end\n    local ok, client = pcall(require, script.Parent.DupProgressClient)\n    return if ok and type(client) == "table" then client.hatchPlay(body) else nil') == 1, 'the reveal makes the line, only with the flag on'
    assert hatch.count('if dupLine then require(script.Parent.DupProgressClient).hatchResult(dupLine, r.speciesId, failed, a.nameLabel.Text, a.body:FindFirstChild("TapHint")) end') == 1, 'the result is counted'
    assert hatch.count('if dupLine then require(script.Parent.DupProgressClient).hatchReveal(dupLine,') == 1, 'the line shows with the reveal'
    screens = read(SCREENS)
    assert screens.count('dupRow=if Config.DupProgressEnabled==true then function(parent,dinos,top,height,rowWidth,left)') == 1 and 'end else nil,' in screens, 'flag off = the Index page gets no row'
    assert screens.count('if (Config :: any).DupProgressEnabled==true then pcall(function() require(script.Parent.DupProgressClient).start() end) end') == 1, 'the copy list is read from start-up, only with the flag on'
    assert 'client.openFusion(species,stage,openFusion)' in screens, 'the tap opens the Fusion Menu on this dino'
    assert read(PANELS).count('if ctx.dupRow then top += ctx.dupRow(right, st.list, top, T) end') == 1, 'the row sits above the cards'
    menu = read(MENU)
    assert 'function FusionMenu.preset(speciesId: string, stageId: string)' in menu and 's.targetStage, s.filters, s.selection, s.visible, s.filtersOpen = stageId, {speciesId = speciesId}, {}, FusionMenu.CardBatch, false' in menu, 'preset = the tab and the Dino filter'
    assert 'DupProgress' not in read('src/client/Bootstrap.client.luau'), 'Bootstrap stays out of it (size and local ceilings)'
    for path in ('src/server', ):
        for file in (ROOT / path).rglob('*.luau'):
            assert 'DupProgress' not in file.read_text(encoding='utf-8'), 'no server change: ' + str(file)


def check(runner, mutant=None):
    read = reader(mutant)
    try:
        static_checks(read)
    except AssertionError as error:
        return False, 'static: %s\n' % error
    ok, out = logic(runner, read)
    if not ok:
        return False, out
    ok2, out2 = client_off(runner, read)
    if not ok2:
        return False, out + out2
    # the stubs are honest: with the flag ON the same run must hit an engine call (otherwise the flag-off run proves nothing)
    ok3, out3 = client_off(runner, read, 'true')
    if ok3 or 'flag off must not touch' not in out3:
        return False, out + out2 + 'the flag-off harness did not notice the flag being on:\n' + out3
    return True, out + out2


MUTANTS = {
    'locked and favourite copies count (a second, looser rule)': (DUP, 'type(d) == "table" and Sel.ineligibility(d, {targetStage = stageId, speciesId = speciesId}) == nil then', 'type(d) == "table" and d.speciesId == speciesId and d.stage == recipe.source and type(d.genes) == "table" and type(d.genes.patternId) == "string" then'),
    'other species count too': (DUP, 'Sel.ineligibility(d, {targetStage = stageId, speciesId = speciesId}) == nil then', 'Sel.ineligibility(d, {targetStage = stageId}) == nil then'),
    'Emerald counts every pattern together': (DUP, '    if recipe.anyPattern then return total, nil end', '    if true then return total, nil end'),
    'a pattern tie depends on the list order': (DUP, 'if n > best or (n == best and bestPattern ~= nil and pattern < bestPattern) then', 'if n > best then'),
    'ready one copy late (step)': (DUP, "    return {stageId = stageId, name = recipe.name, have = have, need = need, ready = have >= need,", "    return {stageId = stageId, name = recipe.name, have = have, need = need, ready = have > need,"),
    'ready one copy late (hatch line)': (DUP, 'need = recipe.donorCount, ready = have >= recipe.donorCount}', 'need = recipe.donorCount, ready = have > recipe.donorCount}'),
    'the hatch line shows on the first copy': (DUP, 'Dup.MinForLine = 2', 'Dup.MinForLine = 1'),
    'the words are "3/6 Gold"': (DUP, 'return string.format("%d of %d for %s!", step.have, step.need, step.name)', 'return string.format("%d/%d %s", step.have, step.need, step.name)'),
    'ready still shows the number': (DUP, '    if step.ready then return "Ready for " .. step.name .. "!" end\n', ''),
    'the hint counts the whole recipe': (DUP, '    local left = step.need - step.have', '    local left = step.need'),
    'the bar overflows above the recipe': (DUP, 'fraction = math.clamp(have / need, 0, 1), patternId = pattern}', 'fraction = have / need, patternId = pattern}'),
    'the Index shows steps the player has not started': (DUP, '        if step and step.have >= 1 then', '        if step then'),
    'a stale copy list is accepted': (DUP, 'if type(dinos) ~= "table" or token ~= t.events or buffered > 0 then return false end', 'if type(dinos) ~= "table" or buffered > 0 then return false end'),
    'a copy list is accepted while eggs are buffered': (DUP, 'if type(dinos) ~= "table" or token ~= t.events or buffered > 0 then return false end', 'if type(dinos) ~= "table" or token ~= t.events then return false end'),
    'revealed copies are counted twice after a new list': (DUP, '    t.base, t.extra = dinos, {}', '    t.base = dinos'),
    'a failed egg counts as a copy': (DUP, '    copies = math.max(0, math.floor(copies))\n    if copies > 0 then', '    copies = math.max(1, math.floor(copies))\n    if copies > 0 then'),
    '"2x Compy" counts once': (DUP, '    return tonumber(string.match(text, "^(%d+)x ")) or 1', '    return 1'),
    'the list is re-read while an egg is opening': (DUP, '    if t.openAt ~= nil and now - t.openAt < Dup.OpenTimeout then return false end\n', ''),
    'the list is re-read while eggs are buffered': (DUP, '    if buffered > 0 or t.requested ~= nil then return false end', '    if t.requested ~= nil then return false end'),
    'two requests at once': (DUP, '    if buffered > 0 or t.requested ~= nil then return false end', '    if buffered > 0 then return false end'),
    'the list is re-read right after a result': (DUP, '    return now - t.lastEvent >= Dup.QuietSeconds', '    return true'),
    'the flag is on in the source': (CONFIG, '    DupProgressEnabled = false,', '    DupProgressEnabled = true,'),
    'the client ignores the flag': (CLIENT, 'local function on(): boolean return Config.DupProgressEnabled == true end', 'local function on(): boolean return true end'),
    'the Index row ignores the flag': (CLIENT, '    if not on() then return 0 end\n', ''),
    'the hatch line ignores the flag': (CLIENT, '    if not on() then return nil end\n', ''),
    'the Index page passes the row with the flag off': (SCREENS, 'dupRow=if Config.DupProgressEnabled==true then function(parent,dinos,top,height)', 'dupRow=if true then function(parent,dinos,top,height)'),
    'a long list is counted partly': (CLIENT, '    if cursor ~= nil then return nil end\n', ''),
    'the reveal never counts the egg': (HATCH, '        if dupLine then require(script.Parent.DupProgressClient).hatchResult(dupLine, r.speciesId, failed, a.nameLabel.Text, a.body:FindFirstChild("TapHint")) end -- BD-1170: counts this egg\'s copies\n', ''),
    'the reveal requires the module with the flag off': (HATCH, '    if (Config :: any).DupProgressEnabled ~= true then return nil end\n    local ok, client = pcall(require, script.Parent.DupProgressClient)', '    local ok, client = pcall(require, script.Parent.DupProgressClient)'),
    'the default profile does not pin the flag off': (PROFILES, '_flag_off("DupProgressEnabled",', '_flag_off("DupProgressEnabledX",'),
    'the playtest profile does not switch it on': (PROFILES, 'Rule("DupProgressEnabled", "set", True,', 'Rule("DupProgressEnabled", "set", False,'),
    'the flag is missing from the rehearsal list': (PROFILES, '("DupProgressEnabled", "BD-1170', '("DupProgressEnabledX", "BD-1170'),
    'the menu preset forgets the species': (MENU, 's.targetStage, s.filters, s.selection, s.visible, s.filtersOpen = stageId, {speciesId = speciesId}, {}, FusionMenu.CardBatch, false', 's.targetStage, s.filters, s.selection, s.visible, s.filtersOpen = stageId, {}, {}, FusionMenu.CardBatch, false'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    ok, out = check(args.runner)
    print(out, end='')
    if not ok:
        raise SystemExit('duplicate progress check failed')
    print('Duplicate progress wiring passed: flag off in Config and the default profile, on in the playtest profile, in the rehearsal list; no server file, no Bootstrap change')
    if args.no_mutants:
        return
    from concurrent.futures import ThreadPoolExecutor
    names = list(MUTANTS)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda n: check(args.runner, MUTANTS[n]), names))
    for name, (passed, _out) in zip(names, results):
        assert not passed, 'MUTANT SURVIVED (the duplicate progress check did not notice): ' + name
        print('  mutant caught: ' + name)
    print('Duplicate progress passed: %d mutants caught' % len(MUTANTS))


if __name__ == '__main__':
    sys.exit(main())
