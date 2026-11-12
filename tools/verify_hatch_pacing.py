#!/usr/bin/env python3
"""BD-1164 (owner decision 2026-11-10, docs/115, docs/226): hatch pacing behind Config.HatchFastCommonsEnabled.

Runs the pure rules with the pinned Luau runtime (the real src/shared/HatchPacing.luau and HatchTimeline.luau, with RevealSkip,
HatchV2Plan, ProgressionConfig and Sfx):
  1. which egg of a batch is fast (Common, Uncommon, a cracked egg), which keeps the full show (Rare and up, Shiny, BIG, mutation,
     Rainbow, Astra, secret, unreadable), the first-3 rule of a brand-new save, which egg moves on by itself (never the last one);
  2. ordering: one plan per egg in rising rarity, the fast eggs first, the "something special" lead-in exactly once on the first
     Rare+ egg after a fast run;
  3. the timeline: a fast egg is about 1 s, has no paint buckets and at most two sound cues, taps cannot break it, Skip the rest still
     works, the lead-in holds the build-up clock; flag off = every number and every state exactly as before;
  4. the REAL hatch screen (src/client/HatchSequence.luau) in the engine mock of verify_close_paths, flag off and on: a fast egg
     moves on by itself in about 1 s with no tap hint and no NEXT EGG button, a cracked one too, the Rare egg after a fast run shows
     the lead-in line and cue and then waits for the tap, the last egg waits, a brand-new save gets the full show, Reduce Motion;
  5. the measurement of docs/226: seconds per egg by rarity and the total of a 15-egg and a 120-egg batch, before and after
     (--report prints the table).
Then checks the wiring statically (flag false in source, profiles, the client reads the flag, no server file knows it, no new sound
id) and puts each defect back (mutants). NOT Studio, phone, eyes or ears evidence: nobody has watched or heard the fast path.
Usage: python tools/verify_hatch_pacing.py --runner luau.exe [--no-mutants] [--report]"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_close_paths  # noqa: E402  (the engine mock that runs the REAL HatchSequence: tools/close_paths_smoke.luau)

PACING = 'src/shared/HatchPacing.luau'
TIMELINE = 'src/shared/HatchTimeline.luau'
SEQUENCE = 'src/client/HatchSequence.luau'
CONFIG = 'src/shared/Config.luau'
PROFILES = 'tools/release_profiles.py'
WORKFLOW = '.github/workflows/build-generated-place.yml'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def module(path, replacements=None):
    source = read(path)
    for old, new in (replacements or {}).get(path, []):
        assert old in source, 'mutant target missing in %s: %s' % (path, old)
        source = source.replace(old, new)
    return '(function()\n' + source + '\nend)()'


BODY = r'''
local function near(a, b, e) return math.abs(a - b) <= (e or 1e-6) end
local function egg(rarity, failed, remaining, outcome)
    local o = outcome or {}
    o.failed = failed == true
    return {rarity = rarity, failed = failed == true, remaining = remaining or 5, outcome = o}
end
local function party(copies)
    local b = T.newBatch()
    P.begin(b, copies)
    return b
end

-- 1. FLAG OFF: the plan is always the full show, the party table is not touched, every duration is the shipped one.
do
    local b = party(1)
    for rarity = 1, 5 do
        local p = P.plan(false, b, egg(rarity))
        assert(not p.fast and not p.auto and not p.special and p.why == "off", "flag off: full show")
    end
    assert(not P.plan(false, b, egg(1, true)).fast and not P.plan(nil, b, egg(1)).fast, "flag off or missing: a cracked egg is not fast either")
    assert(b.shown == 0 and b.fastRun == 0, "flag off: the party table is not touched")
    local m = T.durations(true)
    assert(near(m.build, 3.6) and near(m.burst, .6) and near(m.settle, .8) and near(m.readyAt, 5.0) and m.fast == false and near(m.revealLag, .1), "the full show is 3.6 + .6 + .8 s, as shipped")
    local splat = T.durations(true, 1, true)
    assert(near(splat.build, 3.6) and near(splat.readyAt, 5.3) and splat.fast == false, "the full cracked egg is 5.3 s, as shipped")
    local leg = T.durations(true, 5)
    assert(near(leg.build, 4.1) and near(leg.readyAt, 6.0), "Legendary: +.5 s rattle and +.5 s hold, as shipped")
    local red = T.durations(false)
    assert(red.build == 0 and near(red.readyAt, .45) and red.revealLag == 0, "Reduce Motion as shipped")
    for rarity = 1, 5 do
        local a, c = T.durations(true, rarity, false, false), T.durations(true, rarity, false, false, false)
        assert(a.build == c.build and a.readyAt == c.readyAt and a.paint.endsAt == c.paint.endsAt, "fast = false changes nothing")
    end
    local s = T.new(true, 1, false, true)
    T.supply(s, 3, false)
    assert(s.lead == 0 and s.durs.fast == false and T.leadGlow(s) == 0, "the old supply call: no lead, no fast")
    for _ = 1, 600 do T.step(s, 1 / 60) end
    assert(T.readyAction(s.durs, s.t, .1, false) == "hint" and T.readyAction(s.durs, s.t, .1, nil) == "hint", "without the fast path an egg waits for the player")
    assert(T.readyAction(s.durs, s.t, .1, true) == "hint", "a full-show egg never moves on by itself, whatever the caller asks")
    assert(not s.done, "nothing advanced")
end

-- 2. WHICH EGGS ARE FAST (flag on, a save that already holds dinosaurs).
do
    local b = party(7)
    assert(b.fresh == false)
    local c = P.plan(true, b, egg(1))
    assert(c.fast and c.auto and not c.special and c.why == "fast", "Common: fast and moves on by itself")
    assert(P.plan(true, b, egg(2)).fast, "Uncommon: fast")
    for rarity = 3, 5 do
        local p = P.plan(true, party(7), egg(rarity))
        assert(not p.fast and not p.auto and p.why == "rare", "Rare and up keep the full show")
    end
    assert(P.plan(true, party(7), egg(nil)).fast == false and P.plan(true, party(7), egg(0 / 0)).fast == false, "an unreadable rarity keeps the full show")
    for rarity = 1, 5 do
        local p = P.plan(true, party(7), egg(rarity, true))
        assert(p.fast and p.auto, "a cracked egg is short too, whatever it would have been")
    end
    for _, o in {{shiny = true}, {big = true}, {eventMutationId = "frost"}, {genes = {conditionId = "rainbow"}}, {genes = {conditionId = "astra"}}, {secret = true}} do
        local p = P.plan(true, party(7), egg(1, false, 5, o))
        assert(not p.fast and not p.auto and p.why == "notable" and not p.special, "a notable Common keeps the full show")
    end
    assert(P.plan(true, party(7), egg(1, true, 5, {shiny = true})).fast, "a cracked egg has nothing notable to show")
    assert(P.plan(true, party(7), egg(1, false, 5, {genes = {conditionId = "dirty"}})).fast, "Dirty and Normal eggs are not notable")
    local last = P.plan(true, party(7), egg(1, false, 0))
    assert(last.fast and not last.auto, "the last egg of the party never moves on by itself: DONE is the player's")
    assert(P.FastMaxRarity == 2 and P.FullShowFirstEggs == 3)
end

-- 3. FIRST-3 RULE: a brand-new save (only the starter Compy) sees its first 3 eggs with the full show.
do
    assert(P.isFresh(1) and P.isFresh(0) and not P.isFresh(2) and not P.isFresh(nil) and not P.isFresh("1") and not P.isFresh(0 / 0))
    local b = party(1)
    assert(b.fresh == true)
    local whys = {}
    for i = 1, 6 do
        if i > 1 then P.begin(b, 9) end -- every egg calls begin: only the first one of the party decides (the collection has grown by then)
        local p = P.plan(true, b, egg(1, i == 2))
        whys[i] = p.why
        assert(p.fast == (i > 3) and p.auto == (i > 3), "eggs 1-3 full, egg 4 and later fast")
    end
    assert(whys[1] == "first" and whys[2] == "first" and whys[3] == "first" and whys[4] == "fast", "a cracked egg inside the first 3 is a full show too")
    assert(b.shown == 6 and b.fastRun == 3)
    T.batchReset(b)
    assert(b.shown == 0 and b.fastRun == 0 and b.fresh == false and b.index == 0, "the party ends: the pacing facts end with it")
    P.begin(b, 9)
    assert(P.plan(true, b, egg(1)).fast, "the next party of the same save is not brand-new any more")
    local old = party(2)
    assert(P.plan(true, old, egg(1)).fast, "a save with a hatched dinosaur gets no first-3 show")
end

-- 4. ORDERING: one plan per egg, in the order given (rising rarity), fast eggs first, the lead-in once.
local function batchOf(counts, failEvery, notableEvery)
    -- rising rarity; `failEvery` = {a, b}: a of every b eggs are cracked; every `notableEvery`-th hatching egg is BIG
    local eggs, hatching = {}, 0
    local total = 0
    for _, n in counts do total += n end
    local k = 0
    for rarity, n in counts do
        for _ = 1, n do
            k += 1
            local failed = (k * failEvery[1] + 3) % failEvery[2] < failEvery[1]
            local o = {}
            if not failed then
                hatching += 1
                if notableEvery and hatching % notableEvery == 0 then o.big = true end
            end
            table.insert(eggs, egg(rarity, failed, total - k, o))
        end
    end
    return eggs
end
local function planAll(enabled, eggs, copies)
    local b = party(copies)
    local plans = {}
    for i, e in eggs do P.begin(b, copies) plans[i] = P.plan(enabled, b, e) end
    return plans
end
do
    local eggs = batchOf({86, 29, 4, 1, 0}, {0, 5}) -- 120 eggs, nothing cracked or notable: the cleanest picture of the rule
    local plans = planAll(true, eggs, 7)
    assert(#plans == 120, "one plan per egg: still one egg at a time")
    local specials, firstFull = 0, nil
    for i, p in plans do
        if p.special then specials += 1 assert(i == 116, "the lead-in is on the first Rare+ egg after the fast run") end
        if not p.fast and not firstFull then firstFull = i end
        assert(p.fast == (eggs[i].rarity <= 2), "Common and Uncommon fast, Rare and up full")
    end
    assert(firstFull == 116 and specials == 1, "115 fast eggs, then the special one; the next Rare+ eggs need no second lead-in")
    assert(not plans[120].auto and not plans[120].fast, "the last (rarest) egg is a full show that waits for the player")
    -- no contrast, no lead-in: fewer than SpecialAfterFast fast eggs before the Rare
    local short = planAll(true, {egg(1, false, 2), egg(3, false, 1), egg(4, false, 0)}, 7)
    assert(not short[2].special and not short[3].special, "one fast egg is not a run")
    local run = planAll(true, {egg(1, false, 3), egg(2, false, 2), egg(3, false, 1), egg(3, false, 0)}, 7)
    assert(run[3].special and not run[4].special, "two fast eggs, then the Rare: lead-in; the Rare after it: none")
    local notable = planAll(true, {egg(1, false, 3), egg(1, false, 2), egg(1, false, 1, {shiny = true}), egg(3, false, 0)}, 7)
    assert(not notable[3].special and not notable[4].special, "a notable Common is no lead-in, and it ends the fast run")
    local cracked = planAll(true, {egg(1, true, 2), egg(3, true, 1), egg(3, false, 0)}, 7)
    assert(cracked[2].fast and cracked[3].special, "cracked eggs count as fast eggs; a cracked Rare is never the special one")
    local fresh = planAll(true, {egg(1, false, 3), egg(1, false, 2), egg(3, false, 1), egg(3, false, 0)}, 1)
    assert(fresh[3].why == "first" and not fresh[3].special and not fresh[4].special, "inside the first 3 there is no fast run, so no lead-in")
    assert(not planAll(false, eggs, 7)[116].special, "flag off: no lead-in")
end

-- 5. TIMELINE of the fast path.
do
    local f = T.durations(true, 1, false, false, true)
    assert(f.fast == true and f.paint.endsAt == 0 and f.paint.leftStart == 0, "no paint buckets on the fast path")
    local total = f.readyAt + f.revealLag
    assert(total >= .8 and total <= 1.2, "a fast egg is about 1 s from on screen to next egg, got " .. total)
    assert(f.build >= .2 and f.build <= .5 and f.burst > 0 and f.settle >= .4, "short wobble, burst, and the name stays up for at least .4 s")
    local fs = T.durations(true, 1, true, false, true)
    assert(fs.fast and fs.readyAt + fs.revealLag >= .8 and fs.readyAt + fs.revealLag <= 1.3 and fs.burst + fs.settle >= T.SplatDrop + .5, "the fast splat is short and the yolk still lands and spreads")
    local fr = T.durations(false, 1, false, false, true)
    assert(fr.fast and fr.build == 0 and fr.burst == 0 and fr.readyAt >= .7 and fr.readyAt <= 1.2 and fr.revealLag == 0, "Reduce Motion: a short fade, about 1 s")
    for rarity = 1, 5 do
        local a = T.durations(true, rarity, false, false, true)
        assert(a.build == f.build and a.readyAt == f.readyAt, "the fast timing has no rarity anticipation")
    end
    local v2 = T.durations(true, 1, false, true, true)
    assert(v2.build == f.build and v2.paint.endsAt == 0, "the v2 hatch takes the same fast path")
    assert(T.FastPop < .8 and T.FastPop <= f.burst + f.settle, "the dinosaur's pop ends before the egg moves on")
    -- cues: at most two per fast egg, existing names only
    local cues = T.cues(f, 1, false, Sfx.revealName(1))
    assert(#cues == 2 and cues[1].name == "hatch_burst" and cues[2].name == Sfx.revealName(1), "a fast egg plays the burst and its reveal cue, nothing else")
    assert(#T.cues(fs, 1, true, Sfx.revealName(1)) == 1, "a fast cracked egg plays the burst only")
    for _, c in cues do assert(Sfx.Sounds[c.name], "unknown Sfx name " .. c.name) end
    assert(#T.cues(T.durations(true, 1), 1, false, Sfx.revealName(1)) > 10, "the full show keeps its cue list")
    -- state machine: the answer arrives, the egg runs through and moves on by itself; taps cannot break it
    local s = T.new(true, 1, false, true)
    T.step(s, .2)
    T.supply(s, 1, false, true)
    assert(s.durs.fast and s.lead == 0)
    assert(T.tap(s) == "ignore", "a tap during the short wobble does nothing")
    local steps, action = 0, "wait"
    while action == "wait" and steps < 600 do
        T.step(s, 1 / 60) steps += 1
        action = T.readyAction(s.durs, s.t, T.FastRevealLag, true)
    end
    assert(action == "advance" and steps / 60 <= 1.0, "moves on by itself, within about 1 s of the answer")
    assert(T.readyAction(s.durs, s.t, T.FastRevealLag, false) == "hint", "the last egg of a party shows DONE instead")
    assert(T.readyAction(s.durs, s.durs.readyAt, T.FastRevealLag, true) == "wait", "never before the dinosaur has been shown for the settle time")
    assert(T.tap(s) == "advance" and s.done, "a tap on the settled egg is the same move, exactly once")
    -- Skip the rest still works on a fast egg
    s = T.new(true, 1, false, true) T.supply(s, 1, false, true) T.step(s, .1)
    assert(T.skipAll(s) == "fastforward" and near(s.t, s.durs.build), "Skip the rest during the wobble jumps to the burst")
    T.step(s, 2) assert(T.skipAll(s) == "advance" and s.done, "Skip the rest on a settled egg moves on")
    assert(T.shouldSkip({}, 1, {}, true) == true and T.shouldSkip({}, 1, {shiny = true}, true) == false, "the skip rules are untouched")
end

-- 6. The "something special" lead-in.
do
    assert(P.SpecialLead >= .4 and P.SpecialLead <= 1.2, "the lead-in is a breath, not a wait")
    assert(Sfx.Sounds[P.SpecialCue] and Sfx.Sounds[P.SpecialCue].id ~= "", "the lead-in cue is an existing registered sound")
    assert(#P.SpecialText <= 28, "docs/72: a short line")
    local s = T.new(true, 1, false, true)
    T.step(s, .2)
    T.supply(s, 3, false, false, P.SpecialLead)
    local t0, idle0 = s.t, s.idle
    assert(near(s.lead, P.SpecialLead) and T.leadGlow(s) == 0, "the glow starts at 0")
    T.step(s, P.SpecialLead / 2)
    assert(near(s.t, t0) and near(s.idle, idle0 + P.SpecialLead / 2), "the build-up clock waits during the lead-in, the wobble goes on")
    assert(T.leadGlow(s) > .9 and T.leadGlow(s) <= 1, "the glow swells to its top in the middle")
    assert(T.tap(s) == "ignore", "a tap during the lead-in does nothing")
    T.step(s, P.SpecialLead / 2 + .25)
    assert(near(s.t, t0 + .25) and s.lead == 0 and T.leadGlow(s) == 0, "then the normal build-up runs, with the time left over")
    for i = 0, 100 do
        local q = T.new(true, 1, false, true) T.supply(q, 3, false, false, 1) T.step(q, i / 100)
        local g = T.leadGlow(q)
        assert(g >= 0 and g <= 1, "glow bounds")
    end
    local full = T.durations(true, 3)
    assert(near(s.durs.build, full.build) and near(s.durs.readyAt, full.readyAt), "the Rare egg keeps its whole build-up and reveal after the lead-in")
    -- Skip the rest ends the lead-in at once
    local k = T.new(true, 1, false, true) T.supply(k, 3, false, false, P.SpecialLead)
    assert(T.skipAll(k) == "fastforward" and k.lead == 0 and near(k.t, k.durs.build))
    -- no lead-in for a fast egg or without motion
    local a = T.new(true, 1, false, true) T.supply(a, 1, false, true, P.SpecialLead) assert(a.lead == 0, "a fast egg has no lead-in")
    local r = T.new(false, 1, false, true) T.supply(r, 3, false, false, P.SpecialLead) assert(r.lead == 0, "Reduce Motion has no lead-in")
end

-- 7. MEASUREMENT (docs/226). Seconds from "egg on screen" to "next egg on screen". Assumptions, not rules: the player taps TAP seconds
-- after the tap hint; the server answer arrives inside the first .35 s (while the egg already wobbles), so it adds nothing.
local TAP = .7
local cracked = Progression.Conditions[1]
assert(cracked.id == "cracked")
local weights = Progression.ConditionWeights[1]
local sum = 0 for _, w in weights do sum += w end
local failShare = weights[1] / sum * (1 - cracked.hatchChance)
assert(near(failShare, .4), "tier 0: 50% Cracked x 80% fail = 40% of eggs do not hatch (the measurement below uses 2 of every 5)")
local function seconds(eggs, enabled, copies, fastForward)
    local plans = planAll(enabled, eggs, copies)
    local total, fast, special, waits = 0, 0, 0, 0
    for i, e in eggs do
        local p = plans[i]
        local durs = T.durations(true, e.rarity, e.failed, false, p.fast)
        total += P.eggSeconds(durs, p, TAP, fastForward)
        if p.fast then fast += 1 end
        if p.special then special += 1 end
        if not p.auto then waits += 1 end
    end
    return total, fast, special, waits
end
local function fmt(s) local whole = math.floor(s + .5) return string.format("%d:%02d", whole // 60, whole % 60) end
local report = {}
local function line(text) table.insert(report, text) end
line("per egg, full motion, seconds (build-up + burst + reveal settle + reveal lag; the tap of " .. TAP .. " s is extra where the egg waits):")
local names = {"Common", "Uncommon", "Rare", "Epic", "Legendary"}
for rarity = 1, 5 do
    local before = T.durations(true, rarity)
    local planFast = {fast = rarity <= 2, auto = rarity <= 2, special = false}
    local after = T.durations(true, rarity, false, false, planFast.fast)
    line(string.format("  %-10s before %.2f + tap = %.2f | after %.2f%s", names[rarity], P.eggSeconds(before, nil, 0), P.eggSeconds(before, nil, TAP),
        P.eggSeconds(after, planFast, 0), if planFast.fast then " (moves on by itself)" else string.format(" + tap = %.2f (+%.1f lead-in after a fast run)", P.eggSeconds(after, planFast, TAP), P.SpecialLead)))
end
do
    local before, after = T.durations(true, 1, true), T.durations(true, 1, true, false, true)
    line(string.format("  %-10s before %.2f + tap = %.2f | after %.2f (moves on by itself)", "Cracked", P.eggSeconds(before, nil, 0), P.eggSeconds(before, nil, TAP), P.eggSeconds(after, {fast = true, auto = true}, 0)))
    line(string.format("  tapped through today (build-up skipped at the %.1f s tap gate): %.2f + tap = %.2f per egg", before.tapGate, P.eggSeconds(T.durations(true, 1), nil, 0, true), P.eggSeconds(T.durations(true, 1), nil, TAP, true)))
end
local results = {}
for _, spec in {{name = "15 eggs (11 Common, 3 Uncommon, 1 Rare)", counts = {11, 3, 1, 0, 0}}, {name = "120 eggs (86 Common, 29 Uncommon, 4 Rare, 1 Epic)", counts = {86, 29, 4, 1, 0}}} do
    local eggs = batchOf(spec.counts, {2, 5}, 5) -- 2 of 5 cracked (config), every 5th hatching egg notable (BD-1056 Studio count: 18 stops in about 93 hatched)
    local failedN, notableN = 0, 0
    for _, e in eggs do if e.failed then failedN += 1 elseif e.outcome.big then notableN += 1 end end
    local watch = seconds(eggs, false, 7, false)
    local tapped = seconds(eggs, false, 7, true)
    local after, fast, special, waits = seconds(eggs, true, 7, false)
    local fresh, freshFast = seconds(eggs, true, 1, false)
    line(string.format("%s, %d cracked, %d notable (BIG / Shiny / Rainbow / Astra):", spec.name, failedN, notableN))
    line(string.format("  BEFORE watching every egg: %s (%.0f s), %d taps", fmt(watch), watch, #eggs))
    line(string.format("  BEFORE tapping every build-up away: %s (%.0f s), %d taps", fmt(tapped), tapped, 2 * #eggs))
    line(string.format("  AFTER  (flag on): %s (%.0f s), %d taps, %d fast eggs, %d lead-in", fmt(after), after, waits, fast, special))
    line(string.format("  AFTER  brand-new save (first 3 eggs full show): %s (%.0f s), %d fast eggs", fmt(fresh), fresh, freshFast))
    table.insert(results, {watch = watch, tapped = tapped, after = after, fresh = fresh, n = #eggs, fast = fast})
end
assert(results[1].n == 15 and results[2].n == 120)
assert(near(results[1].watch, seconds(batchOf({11, 3, 1, 0, 0}, {2, 5}, 5), nil, 7, false)), "flag missing = flag off")
assert(results[1].after < results[1].watch * .5 and results[2].after < results[2].watch * .4, "the fast path at least halves a typical batch")
assert(results[2].after < results[2].tapped, "the fast path beats tapping every build-up away, with far fewer taps")
assert(results[2].after <= 5 * 60, "a 120-egg batch stays under 5 minutes")
assert(results[1].fresh > results[1].after and results[1].fresh - results[1].after < 3 * 6.5, "the first-3 show costs a brand-new save a few seconds, once")
if REPORT then for _, text in report do print(text) end end
print("hatch pacing rules passed")
'''


SCREEN = r'''
do -- BD-1164: the real hatch screen with the fast path. The base smoke above ran with the flag off (as shipped).
    local Config = requireModule(SharedFolder.Config)
    local TL = requireModule(SharedFolder.HatchTimeline)
    local Pace = requireModule(SharedFolder.HatchPacing)
    stubs.FtueRules = {copies = 9}
    stubs.FtueRules.collectionCopies = function() return stubs.FtueRules.copies end
    stubs.SecretSpeciesConfig = {isSecret = function() return false end}
    register("FtueRules") register("SecretSpeciesConfig")
    local played = {}
    stubs.Sfx.play = function(name) table.insert(played, name) end
    local function start(opts)
        local menu = buildMenu(1280, 720, 860, 520, 1)
        local handle = playHatch(menu, opts)
        return menu, handle
    end
    local function untilNext(menu, limit)
        local n = 0
        while menu.nexts == 0 and n < limit * 30 do frames(1) n += 1 end
        return n / 30
    end
    local function shown(menu, name) local o = menu.body:FindFirstChild(name) return o ~= nil and o.Visible == true end

    -- flag OFF: a Common egg with eggs waiting stays until the player taps, exactly as before
    assert(Config.HatchFastCommonsEnabled == false, "the mock starts with the flag off")
    TL.batchReset(TL.session)
    local m = start({rarity = 1, remaining = 3})
    check(untilNext(m, 9) >= 9 and m.nexts == 0 and shown(m, "TapHint"), "flag off: a Common egg waits for the tap")
    check(TL.session.shown == 0 and TL.session.fastRun == 0, "flag off: no pacing facts are kept")
    m.gui:Destroy()

    Config.HatchFastCommonsEnabled = true
    TL.batchReset(TL.session)
    -- a save that already holds dinosaurs: Common egg, eggs waiting
    m = start({rarity = 1, remaining = 3})
    local took = untilNext(m, 9)
    check(m.nexts == 1 and took >= .8 and took <= 1.2, "flag on: a Common egg moves on by itself in about 1 s, took " .. took)
    check(not shown(m, "TapHint") and m.body:FindFirstChild("EndButtons") == nil, "a fast egg shows no tap hint and no button")
    check(m.aborts == 0 and m.closed == 0, "moving on is not a close")
    frames(30)
    check(m.nexts == 1, "the next egg is asked for exactly once")
    m.gui:Destroy()
    -- the answer arrives a moment after the egg is on screen (the usual path: Open, then supply)
    do
        local menu = buildMenu(1280, 720, 860, 520, 1)
        local handle, _, dino = playHatch(menu, {result = false, remaining = 3})
        frames(9)
        check(handle.pending() and menu.nexts == 0, "the egg wobbles while the answer is on its way")
        handle.supply(resultFor(dino, {rarity = 2, remaining = 3}))
        local t = untilNext(menu, 9)
        check(menu.nexts == 1 and t <= 1.0, "an Uncommon egg supplied later moves on within about 1 s of the answer, took " .. t)
        menu.gui:Destroy()
    end
    -- a cracked egg: short splat, no NEXT EGG button, moves on by itself
    m = start({rarity = 1, failed = true, remaining = 3})
    took = untilNext(m, 9)
    check(m.nexts == 1 and took >= .8 and took <= 1.35, "a cracked egg moves on by itself, took " .. took)
    check(m.body:FindFirstChild("EndButtons") == nil, "a fast cracked egg has no NEXT EGG button")
    m.gui:Destroy()
    -- the Rare egg after the fast run: lead-in line and the existing cue, then the full show, then it waits
    table.clear(played)
    m = start({rarity = 3, remaining = 3})
    frames(6)
    local line = m.body:FindFirstChild("SpecialLine")
    check(line ~= nil and line.Text == Pace.SpecialText, "the Rare egg after a fast run shows the lead-in line")
    check(table.find(played, Pace.SpecialCue) ~= nil, "the lead-in plays the existing soft cue")
    took = untilNext(m, 9)
    check(m.nexts == 0 and took >= 9, "a Rare egg never moves on by itself")
    check(shown(m, "TapHint") and m.body:FindFirstChild("SpecialLine") == nil, "the Rare egg ends on the tap hint; the lead-in line is gone")
    tapOn(m, m.body)
    check(m.nexts == 1, "the tap moves on")
    m.gui:Destroy()
    -- the next Rare egg: no second lead-in
    m = start({rarity = 3, remaining = 3})
    frames(6)
    check(m.body:FindFirstChild("SpecialLine") == nil, "a Rare egg right after a Rare egg has no lead-in")
    m.gui:Destroy()
    -- the last egg of the party: fast timing, but DONE is the player's
    m = start({rarity = 1, remaining = 0})
    took = untilNext(m, 9)
    check(m.nexts == 0 and shown(m, "EndButtons"), "the last egg waits on DONE")
    m.gui:Destroy()
    -- Skip the rest on a fast egg
    m = start({rarity = 1, remaining = 3})
    frames(3)
    local skip = m.gui:FindFirstChild("SkipAll", true)
    check(skip ~= nil, "Skip the rest is on the fast egg's card")
    if skip then skip.Activated:Fire() end
    check(m.skipAlls == 1, "Skip the rest still reaches Bootstrap")
    took = untilNext(m, 9)
    check(m.nexts == 1, "and the egg still moves on once")
    m.gui:Destroy()
    -- Reduce Motion
    m = start({rarity = 1, remaining = 3, motion = false})
    took = untilNext(m, 9)
    check(m.nexts == 1 and took >= .7 and took <= 1.2, "Reduce Motion: a fast egg is a short fade, took " .. took)
    m.gui:Destroy()
    -- closing mid-egg is an abort, never a next egg
    m = start({rarity = 1, remaining = 3})
    frames(6)
    m.close()
    frames(60)
    check(m.aborts == 1 and m.nexts == 0, "X during a fast egg stops the party")
    m.gui:Destroy()
    -- a brand-new save (only the starter Compy): the first 3 eggs keep the full show, the 4th is fast
    TL.batchReset(TL.session)
    stubs.FtueRules.copies = 1
    for i = 1, 4 do
        m = start({rarity = 1, remaining = 5})
        stubs.FtueRules.copies = 3 -- the collection grows as soon as the first egg hatched
        took = untilNext(m, 9)
        if i <= 3 then
            check(m.nexts == 0 and shown(m, "TapHint"), "brand-new save: egg " .. i .. " is a full show that waits")
        else
            check(m.nexts == 1 and took <= 1.2, "brand-new save: egg 4 is fast")
        end
        m.gui:Destroy()
    end
    TL.batchReset(TL.session)
    Config.HatchFastCommonsEnabled = false
    print("hatch pacing screen passed")
end
'''
END_LINE = 'if failures > 0 then error(failures .. " close-path checks failed") end'


def screen_script(replacements=None):
    reps = {}  # the mock's Config is a plain copy with the flag off (verify_close_paths.module_part); the scenario switches it on
    for path, pairs in (replacements or {}).items():
        name = Path(path).stem
        reps.setdefault(name, []).extend(pairs)
    source = verify_close_paths.build_script(reps)
    assert source.count(END_LINE) == 1
    return source.replace(END_LINE, SCREEN + END_LINE)


def run_screen(runner, replacements=None):
    result = verify_close_paths.run(runner, screen_script(replacements))
    out = result.stdout + result.stderr
    return result.returncode == 0 and 'hatch pacing screen passed' in result.stdout, out


def script(replacements=None, report=False):
    return ('local RS=' + module('src/shared/RevealSkip.luau') + '\n'
            'local V2=' + module('src/shared/HatchV2Plan.luau') + '\n'
            'local script={Parent={RevealSkip=RS,HatchV2Plan=V2}}\nlocal function require(x) return x end\n'
            'local T=' + module(TIMELINE, replacements) + '\n'
            'local P=' + module(PACING, replacements) + '\n'
            'local Sfx=' + module('src/shared/Sfx.luau') + '\n'
            'local Progression=' + module('src/shared/ProgressionConfig.luau') + '\n'
            'local REPORT=' + ('true' if report else 'false') + '\n' + BODY)


MUTANTS = {
    'the flag is ignored: fast with the flag off': {PACING: [('if enabled ~= true or type(batch) ~= "table" or type(egg) ~= "table" then', 'if type(batch) ~= "table" or type(egg) ~= "table" then')]},
    'Rare eggs are fast too': {PACING: [('P.FastMaxRarity = 2', 'P.FastMaxRarity = 3')]},
    'only Common eggs are fast': {PACING: [('P.FastMaxRarity = 2', 'P.FastMaxRarity = 1')]},
    'an unreadable rarity is fast': {PACING: [('elseif type(rarity) ~= "number" or rarity ~= rarity or rarity > P.FastMaxRarity then', 'elseif type(rarity) == "number" and rarity > P.FastMaxRarity then')]},
    'a notable egg is fast': {PACING: [('    elseif RevealSkip.isNotable(egg.outcome) then\n        why = "notable"', '    elseif false then\n        why = "notable"')]},
    'a cracked egg keeps the long show': {PACING: [('    elseif failed then\n        why = "fast"', '    elseif failed then\n        why = "rare"')]},
    'a cracked notable egg keeps the long show': {PACING: [('    elseif failed then\n        why = "fast" -- a cracked egg shows only its splat: short too\n    elseif RevealSkip.isNotable(egg.outcome) then\n        why = "notable"',
                                                           '    elseif RevealSkip.isNotable({shiny = egg.outcome and egg.outcome.shiny}) then\n        why = "notable"\n    elseif failed then\n        why = "fast"')]},
    'no first-3 show': {PACING: [('if batch.fresh == true and shown <= P.FullShowFirstEggs then', 'if false then')]},
    'the first-3 show is for every save': {PACING: [('if batch.fresh == true and shown <= P.FullShowFirstEggs then', 'if shown <= P.FullShowFirstEggs then')]},
    'the first show is 2 eggs': {PACING: [('P.FullShowFirstEggs = 3', 'P.FullShowFirstEggs = 2')]},
    'a save with 2 dinosaurs counts as brand-new': {PACING: [('copies == copies and copies <= 1', 'copies == copies and copies <= 2')]},
    'every egg decides brand-new again': {PACING: [('    if (batch.shown or 0) == 0 then\n', '    if true then\n')]},
    'the last egg moves on by itself': {PACING: [('auto = fast and remaining > 0,', 'auto = fast,')]},
    'full-show eggs move on by themselves': {PACING: [('auto = fast and remaining > 0,', 'auto = remaining > 0,')]},
    'the lead-in needs no fast run': {PACING: [('and run >= P.SpecialAfterFast', 'and run >= 0')]},
    'the lead-in comes on every Rare': {PACING: [('batch.fastRun = if fast then run + 1 else 0', 'batch.fastRun = run + 1')]},
    'a cracked Rare gets the lead-in': {PACING: [('    elseif failed then\n        why = "fast"', '    elseif failed and (rarity or 1) < 3 then\n        why = "fast"'), ('local special = why == "rare" and not failed and', 'local special = why == "rare" and')]},
    'a notable Common gets the lead-in': {PACING: [('local special = why == "rare" and not failed', 'local special = why ~= "fast" and why ~= "first" and not failed')]},
    'the lead-in is a long wait': {PACING: [('P.SpecialLead = .7', 'P.SpecialLead = 2.5')]},
    'the lead-in uses a new, unregistered sound': {PACING: [('P.SpecialCue = "level_up"', 'P.SpecialCue = "hatch_special_new"')]},
    'the lead-in line is rule text': {PACING: [('P.SpecialText = "Ooh! Something special!"', 'P.SpecialText = "A rare dinosaur egg is about to hatch now"')]},
    'the party end keeps the pacing facts': {TIMELINE: [('    batch.shown, batch.fastRun, batch.fresh = 0, 0, false\n', '')]},
    'a fast egg takes 3 s': {TIMELINE: [('T.Fast = {build = .3, burst = .15, settle = .5, tapGate = .5}', 'T.Fast = {build = 2.3, burst = .15, settle = .5, tapGate = .5}')]},
    'a fast egg is gone before it can be read': {TIMELINE: [('T.Fast = {build = .3, burst = .15, settle = .5, tapGate = .5}', 'T.Fast = {build = .3, burst = .15, settle = .1, tapGate = .5}')]},
    'the fast splat keeps the long build-up': {TIMELINE: [('local f = if not motion then T.FastReduced elseif failed then T.FastSplat else T.Fast', 'local f = if not motion then T.FastReduced elseif failed then T.Splat else T.Fast')]},
    'the fast splat ends before the yolk lands': {TIMELINE: [('T.FastSplat = {build = .3, burst = .2, settle = .6, tapGate = .5}', 'T.FastSplat = {build = .3, burst = .2, settle = .3, tapGate = .5}')]},
    'the fast path keeps the paint buckets': {TIMELINE: [('tapGate = f.tapGate, paint = T.paintPlan(false), fast = true,', 'tapGate = f.tapGate, paint = T.paintPlan(motion), fast = true,')]},
    'fast is on for every egg': {TIMELINE: [('    if fast == true then -- BD-1164', '    if fast ~= false then -- BD-1164')]},
    'the fast path keeps all rattle cues': {TIMELINE: [('if build > 0 and durs.fast ~= true then', 'if build > 0 then')]},
    'a full-show egg moves on by itself': {TIMELINE: [('return if auto == true and durs.fast == true then "advance" else "hint"', 'return if auto == true then "advance" else "hint"')]},
    'a fast egg never moves on': {TIMELINE: [('return if auto == true and durs.fast == true then "advance" else "hint"', 'return "hint"')]},
    'a fast egg moves on before the reveal settled': {TIMELINE: [('    if t < durs.readyAt + lag then return "wait" end\n', '    if t < durs.build then return "wait" end\n')]},
    'the lead-in runs the build-up clock': {TIMELINE: [('            state.idle += used\n            dt -= used\n', '            state.idle += used\n')]},
    'the lead-in never ends': {TIMELINE: [('            state.lead -= used\n', '')]},
    'a fast egg gets a lead-in': {TIMELINE: [('local hold = if state.motion and fast ~= true and type(lead) == "number" and lead > 0 then lead else 0', 'local hold = if state.motion and type(lead) == "number" and lead > 0 then lead else 0')]},
    'Reduce Motion gets a lead-in': {TIMELINE: [('local hold = if state.motion and fast ~= true and type(lead) == "number" and lead > 0 then lead else 0', 'local hold = if fast ~= true and type(lead) == "number" and lead > 0 then lead else 0')]},
    'Skip the rest waits for the lead-in': {TIMELINE: [('        state.t, state.fastForwarded, state.lead = state.durs.build, true, 0\n        return "fastforward"', '        state.t, state.fastForwarded = state.durs.build, true\n        return "fastforward"')]},
    'the glow leaves its bounds': {TIMELINE: [('return math.sin(math.pi * math.clamp(1 - state.lead / state.leadTotal, 0, 1))', 'return 2 * math.sin(math.pi * math.clamp(1 - state.lead / state.leadTotal, 0, 1))')]},
    'the full show got shorter': {TIMELINE: [('T.Motion = {build = 3.6, burst = .6, settle = .8, tapGate = .5}', 'T.Motion = {build = 1.6, burst = .6, settle = .8, tapGate = .5}')]},
}

SCREEN_MUTANTS = {
    'screen: the fast egg shows the tap hint and waits': {SEQUENCE: [('if action == "advance" then advance() elseif action == "hint" then showHint() end', 'if action ~= "wait" then showHint() end')]},
    'screen: the plan ignores the flag': {SEQUENCE: [('local pace = Pacing.plan(Config.HatchFastCommonsEnabled == true, batch,', 'local pace = Pacing.plan(true, batch,')]},
    'screen: a fast cracked egg keeps its NEXT EGG button': {SEQUENCE: [('local kinds = if autoNext then {} else Copy.hatchButtons(failed, r.remaining)', 'local kinds = Copy.hatchButtons(failed, r.remaining)')]},
    'screen: the last egg moves on by itself': {SEQUENCE: [('        autoNext = pace.auto\n', '        autoNext = pace.fast\n')]},
    'screen: the fast timing is not handed to the timeline': {SEQUENCE: [('Timeline.supply(state, rarity, failed, pace.fast, if pace.special then Pacing.SpecialLead else nil)', 'Timeline.supply(state, rarity, failed, false, if pace.special then Pacing.SpecialLead else nil)')]},
    'screen: no lead-in line': {SEQUENCE: [('if pace.special and motion and state.lead > 0 then', 'if false then')]},
    'screen: the lead-in line stays on the card': {SEQUENCE: [('                    if state.lead <= 0 then specialLine:Destroy() specialLine = nil end\n', '')]},
    'screen: the lead-in has no cue': {SEQUENCE: [('            Sfx.play(Pacing.SpecialCue)\n', '')]},
    'screen: every party counts as brand-new': {SEQUENCE: [('Pacing.begin(batch, if ok then require(Shared.FtueRules).collectionCopies(collection) else nil)', 'Pacing.begin(batch, 1)')]},
    'screen: the brand-new check is skipped': {SEQUENCE: [('        Pacing.begin(batch, if ok then require(Shared.FtueRules).collectionCopies(collection) else nil)\n', '')]},
    'screen: the next egg is asked for on every frame': {SEQUENCE: [('    local function advance()\n        if finished then return end\n        finish()\n', '    local function advance()\n')]},
}

SEQ_NEEDLES = (
    'local Pacing = require(Shared.HatchPacing)',
    'if Config.HatchFastCommonsEnabled == true then -- the first egg of a party decides',
    'Pacing.begin(batch, if ok then require(Shared.FtueRules).collectionCopies(collection) else nil)',
    'local pace = Pacing.plan(Config.HatchFastCommonsEnabled == true, batch, {rarity = rarity, failed = failed, remaining = r.remaining,',
    'outcome = {failed = failed, shiny = r.shiny, big = r.big, eventMutationId = r.mutationId, genes = r.genes,',
    'secret = Config.HatchFastCommonsEnabled == true and require(Shared.SecretSpeciesConfig).isSecret(r.speciesId)}})',
    'fastEgg = pace.fast',
    'Timeline.supply(state, rarity, failed, pace.fast, if pace.special then Pacing.SpecialLead else nil)',
    'autoNext = pace.auto',
    'local kinds = if autoNext then {} else Copy.hatchButtons(failed, r.remaining)',
    'if pace.special and motion and state.lead > 0 then',
    'Sfx.play(Pacing.SpecialCue)',
    'Pacing.SpecialText',
    'if not motion or fastEgg then a.paint.finish() end',
    'if not state.pending and not fastEgg then updatePaint(t) end',
    'local lead = Timeline.leadGlow(state)',
    'if not revealStarted and modelReady and t >= durs.build + durs.revealLag then revealT = since startReveal() end',
    'local action = Timeline.readyAction(durs, t, revealT, autoNext)',
    'if action == "advance" then advance() elseif action == "hint" then showHint() end',
    'a.onSkipAll()',
    'if Timeline.skipAll(state) == "advance" then advance() end',
)

SOURCE_MUTANTS = {
    'the flag is on in the source': (CONFIG, 'HatchFastCommonsEnabled = false,', 'HatchFastCommonsEnabled = true,'),
    'the client plans the fast path without the flag': (SEQUENCE, 'local pace = Pacing.plan(Config.HatchFastCommonsEnabled == true, batch,', 'local pace = Pacing.plan(true, batch,'),
    'the client marks a party brand-new without the flag': (SEQUENCE, 'if Config.HatchFastCommonsEnabled == true then -- the first egg of a party decides', 'if true then -- the first egg of a party decides'),
    'the client drops the notable facts': (SEQUENCE, 'outcome = {failed = failed, shiny = r.shiny, big = r.big, eventMutationId = r.mutationId, genes = r.genes,', 'outcome = {failed = failed,'),
    'the client never moves on by itself': (SEQUENCE, 'if action == "advance" then advance() elseif action == "hint" then showHint() end', 'if action ~= "wait" then showHint() end'),
    'the client moves on without the timeline rule': (SEQUENCE, 'local action = Timeline.readyAction(durs, t, revealT, autoNext)', 'local action = if autoNext then "advance" else "hint"'),
    'a fast cracked egg still waits on NEXT EGG': (SEQUENCE, 'local kinds = if autoNext then {} else Copy.hatchButtons(failed, r.remaining)', 'local kinds = Copy.hatchButtons(failed, r.remaining)'),
    'the fast egg still pours the paint buckets': (SEQUENCE, 'if not state.pending and not fastEgg then updatePaint(t) end', 'if not state.pending then updatePaint(t) end'),
    'the fast egg stays colourless': (SEQUENCE, 'if not motion or fastEgg then a.paint.finish() end', 'if not motion then a.paint.finish() end'),
    'the lead-in has a new sound id': (SEQUENCE, 'Sfx.play(Pacing.SpecialCue)', 'Sfx.play("rbxassetid://1234")'),
    'Skip the rest lost its button action': (SEQUENCE, 'if Timeline.skipAll(state) == "advance" then advance() end', ''),
    'the server knows the flag': ('src/server/ProfileEggs.luau', 'local Config', 'local HatchFast = "HatchFastCommonsEnabled"\nlocal Config'),
    'the default profile does not pin the flag off': (PROFILES, '_flag_off("HatchFastCommonsEnabled",', '_flag_off("HatchFastCommonsEnabledX",'),
    'the playtest profile does not switch it on': (PROFILES, 'Rule("HatchFastCommonsEnabled", "set", True,', 'Rule("HatchFastCommonsEnabled", "set", False,'),
    'the flag is missing from the rehearsal list': (PROFILES, '("HatchFastCommonsEnabled", "BD-1164', '("HatchFastCommonsEnabledX", "BD-1164'),
    'the verifier left the workflow': (WORKFLOW, 'python tools/verify_hatch_pacing.py --runner /tmp/luau/luau', 'true'),
}


def check_sources(overrides=None):
    """overrides: {path: source} for a source mutant. Returns the first problem or None."""
    def src(path):
        if overrides and path in overrides:
            return overrides[path]
        return read(path)
    if src(CONFIG).count('    HatchFastCommonsEnabled = false,') != 1:
        return 'the flag must be false in source'
    prof = src(PROFILES)
    for needle in ('_flag_off("HatchFastCommonsEnabled",', 'Rule("HatchFastCommonsEnabled", "set", True,', '("HatchFastCommonsEnabled", "BD-1164'):
        if needle not in prof:
            return 'release_profiles lost: ' + needle
    seq = src(SEQUENCE)
    for needle in SEQ_NEEDLES:
        if needle not in seq:
            return 'HatchSequence lost: ' + needle
    if seq.count('Config.HatchFastCommonsEnabled == true') != 3:
        return 'HatchSequence reads the flag in exactly three places (party start, plan, secret lookup)'
    if seq.count('rbxassetid') != 0:
        return 'HatchSequence holds no asset id (sounds go through Sfx names)'
    pacing = src(PACING)
    code = '\n'.join(line for line in pacing.splitlines() if not line.strip().startswith('--'))
    for word in ('Instance.new', 'FireServer', 'InvokeServer', 'rbxassetid', 'os.clock', 'tick(', 'math.random', 'game:'):
        if word in code:
            return 'HatchPacing is pure (no Instances, remotes, ids, clock or dice): ' + word
    for path in sorted((ROOT / 'src/server').glob('*.luau')):
        rel = 'src/server/' + path.name
        text = src(rel)
        if 'HatchFastCommons' in text or 'HatchPacing' in text:
            return 'presentation only: no server file knows the fast path: ' + rel
    if src(WORKFLOW).count('python tools/verify_hatch_pacing.py --runner /tmp/luau/luau') != 1:
        return 'the workflow runs this verifier once'
    return None


def run(runner, replacements=None, report=False):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'hatch_pacing.luau'
        path.write_text(script(replacements, report), encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    out = result.stdout + result.stderr
    if result.returncode != 0 or 'hatch pacing rules passed' not in result.stdout:
        return False, out
    ok, screen_out = run_screen(runner, replacements)
    return ok, out + ''.join(line + '\n' for line in screen_out.splitlines() if not ok or 'hatch pacing screen' in line)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    parser.add_argument('--report', action='store_true', help='print the before/after table of docs/226')
    args = parser.parse_args()
    problem = check_sources()
    if problem:
        print('FAIL', problem)
        sys.exit(1)
    ok, out = run(args.runner, report=args.report)
    print(out, end='')
    if not ok:
        sys.exit(1)
    if not args.no_mutants:
        for name, replacements in MUTANTS.items():
            passed, _ = run(args.runner, replacements)
            assert not passed, 'MUTANT SURVIVED: ' + name
            print('  mutant caught: ' + name)
        for name, replacements in SCREEN_MUTANTS.items():
            passed, _ = run_screen(args.runner, replacements)
            assert not passed, 'MUTANT SURVIVED: ' + name
            print('  mutant caught: ' + name)
        for name, (path, old, new) in SOURCE_MUTANTS.items():
            source = read(path)
            assert old in source, 'mutant target missing in %s: %s' % (path, old)
            assert check_sources({path: source.replace(old, new, 1)}) is not None, 'SOURCE MUTANT SURVIVED: ' + name
            print('  source mutant caught: ' + name)
    print('Hatch pacing passed: flag off unchanged, which eggs are fast, first-3 rule, ordering and the lead-in, fast timeline, taps and Skip the rest, the real hatch screen in the mock (flag off and on), '
          'measurement, wiring, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS) + len(SCREEN_MUTANTS) + len(SOURCE_MUTANTS)))


if __name__ == '__main__':
    main()
