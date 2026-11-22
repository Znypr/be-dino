#!/usr/bin/env python3
"""BD-1288 slice 1 (owner OK 2026-11-22, docs/evidence/2026-11-22-hatch-storyboard): the hatch on storyboard 1 behind
Config.HatchStoryboardEnabled.

Runs with the pinned Luau runtime:
  1. RULES (src/shared/HatchStoryboardRules.luau): the egg is 35-45 % of the screen, the colour and pattern names are each held 0.8-1 s and
     the crack build-up is 0.5-0.8 s, every word on the stage is >= 19 px on four screens (phone landscape to 1080p), the splash plates stay
     on screen right of the egg, the TAP sits under the egg, the reveal stack (dino, name plate, chips, NEXT) never overlaps, the BEST FIND!
     cards stay inside the screen, never overlap each other, the best dino or the buttons, kid words only;
  2. TIMELINE (src/shared/HatchTimeline.luau): flag off = every number and state as shipped; storyboard on = the paint plan of the rules, the
     egg WAITS at t = 0 for a tap (only the idle wobble moves), a tap / Skip the rest / a fast egg / TapWaitMax seconds open it;
  3. SCREEN: the REAL hatch screen (src/client/HatchSequence.luau) in the engine mock of verify_close_paths with the flag on: the egg waits
     for the tap (HatchTapWait on the body), the tap starts it, the dinosaur comes, Skip the rest still works, Reduce Motion waits too;
     flag off (the base smoke) is unchanged;
  4. WIRING: flag false in source, off in default / on in playtest / rehearsal list / playtest manifest, the watcher requires the client
     module only under the flag, the CI runs this file;
then puts each defect back (mutants). NOT Studio, phone or eyes evidence (the pictures are docs/evidence/2026-11-22-hatch-slice1).
Usage: python tools/verify_hatch_storyboard.py --runner luau.exe [--no-mutants]"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_close_paths  # noqa: E402  (the engine mock that runs the REAL HatchSequence)

RULES = 'src/shared/HatchStoryboardRules.luau'
TIMELINE = 'src/shared/HatchTimeline.luau'
SEQUENCE = 'src/client/HatchSequence.luau'


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
local function overlap(a, b) return a.bottom > b.top + .5 and b.bottom > a.top + .5 end
local function boxes(a, b)
    return math.abs(a.cx - b.cx) * 2 < a.w + b.w - 1 and math.abs(a.cy - b.cy) * 2 < a.h + b.h - 1
end
local SCREENS = {{844, 390, "phone landscape"}, {667, 375, "small phone"}, {1280, 720, "desktop"}, {1920, 1080, "1080p"}}

-- 1. RULES
do
    assert(R.MinText >= 19)
    assert(R.EggShare.want >= .35 and R.EggShare.want <= .45, "the egg is 35-45 % of the screen")
    for _, s in SCREENS do
        local w, h = s[1], s[2]
        -- the boost brings any drawn egg to the wanted share
        for _, drawn in {h * .2, h * .3, h * .38} do
            local tall = drawn * R.eggBoost(drawn, h)
            assert(tall >= h * .35 and tall <= h * .45, s[3] .. ": the boosted egg is 35-45 % of the screen")
        end
        assert(R.eggBoost(0, h) == 1 and R.eggBoost(100, 0) == 1, "no geometry yet = no boost")
        local eggH, cx, cy = h * R.EggShare.want, w / 2, h * R.EggCentreY
        -- the splash plates: right of the egg, inside the screen, words >= 19 px
        for _, word in {"BLUE", "TURQUOISE", "SPOTS", "LEOPARD", "PLAIN"} do
            local L = R.label(w, h, cx, cy, eggH, word)
            assert(L.plate.text >= R.MinText and L.chip.text >= R.MinText, s[3] .. ": plate words >= 19 px")
            assert(L.plate.cx - L.plate.w / 2 >= 0 and L.plate.cx + L.plate.w / 2 <= w, s[3] .. ": the plate stays on screen (" .. word .. ")")
            assert(L.chip.cx + L.chip.w / 2 <= w and L.chip.cy + L.chip.h / 2 <= h, s[3] .. ": the rarity chip stays on screen")
            assert(L.plate.w >= R.wordWidth(word, L.plate.text) + L.plate.text * .5 or L.plate.cx + L.plate.w / 2 >= w - 17, s[3] .. ": the word fits its plate")
            assert(L.chip.cy > L.plate.cy, "the rarity chip is under the name")
            assert(L.plate.cx - L.plate.w / 2 >= cx + eggH * .3, s[3] .. ": the plate is right of the egg, not over it (" .. word .. ")")
            assert(L.plate.text >= h * .07, s[3] .. ": the name is BIG")
        end
        -- the TAP under the egg, inside the screen, its word >= 19 px
        local tap = R.tapButton(w, h, cy, eggH)
        assert(tap.text >= R.MinText and tap.cy + tap.h / 2 <= h and tap.cy > cy + eggH * .3, s[3] .. ": TAP under the egg, on screen")
        assert(tap.h >= 44, s[3] .. ": TAP is a big target")
        -- the bar
        local bar = R.topBar(w, h)
        assert(bar.text >= R.MinText and bar.titleText >= R.MinText and bar.chipH < bar.h and bar.h <= h * .15, s[3] .. ": the bar")
        assert(cy - eggH / 2 >= bar.h - 2, s[3] .. ": the egg starts under the bar")
        -- the reveal stack: dino 40-50 %, nothing overlaps, everything on screen
        assert(R.Reveal.dinoH * R.DinoFill >= .38 and R.Reveal.dinoH * R.DinoFill <= .5 and R.Reveal.dinoHBig * R.DinoFill >= .38 and R.Reveal.dinoHBig * R.DinoFill <= .5, "the dino itself is about 40-50 % of the stage")
        local st = R.revealStack(w, h)
        assert(not overlap(st.plate, st.chips), s[3] .. ": the name plate and the chips do not overlap")
        assert(not overlap(st.chips, st.next), s[3] .. ": the chips and NEXT do not overlap")
        assert(st.dino.bottom <= st.plate.top + h * .03, s[3] .. ": the dino stands above the name plate")
        assert(st.next.bottom <= h, s[3] .. ": NEXT is on screen")
        local chips = R.revealChips(w, h)
        assert(chips.text >= R.MinText, s[3] .. ": chip words >= 19 px")
        -- the summary
        for others = 1, 9 do
            local S = R.summary(w, h, others)
            assert(S.cardText >= R.MinText and S.chipText >= R.MinText, s[3] .. ": card words >= 19 px")
            assert(#S.cards == math.min(others, #S.cards) and #S.cards >= 1, s[3] .. ": at least one card")
            assert(S.shown + (if S.more > 0 then 1 else 0) == #S.cards and S.shown + S.more == others, s[3] .. ": every other dino is a card or counted in +N")
            local bigBox = {cx = S.big.cx, cy = S.big.cy, w = S.big.h * 1.1, h = S.big.h}
            for i, c in S.cards do
                assert(c.w >= 128, s[3] .. ": a card is at least 128 px wide (a dino name at 19 px fits)")
                local K = R.cardStack(c.w, c.h, S.cardText, S.chipText)
                assert(K.dinoH >= c.h * .35, s[3] .. ": the dino keeps at least a third of its card")
                assert(K.nameCy + K.nameH / 2 <= K.chipCy - K.chipH / 2 and K.dinoCy + K.dinoH / 2 <= K.nameCy - K.nameH / 2, s[3] .. ": dino, name and chip never overlap in a card")
                assert(K.chipCy + K.chipH / 2 <= c.h, s[3] .. ": the chip stays in its card")
                assert(c.cx - c.w / 2 >= 0 and c.cx + c.w / 2 <= w and c.cy - c.h / 2 >= S.bar.h and c.cy + c.h / 2 <= S.buttonsY - 24, s[3] .. ": card " .. i .. " on screen, under the bar, over the buttons (" .. others .. ")")
                assert(not boxes(c, bigBox), s[3] .. ": card " .. i .. " is not over the best dino")
                for j, d in S.cards do if j ~= i then assert(not boxes(c, d), s[3] .. ": cards do not overlap") end end
            end
            assert(S.big.cy - S.big.h / 2 >= S.bar.h - 1 and S.big.cy + S.big.h / 2 <= S.buttonsY, s[3] .. ": the best dino sits between the bar and the buttons")
        end
    end
    -- pace: each name held 0.8-1 s, the build-up 0.5-0.8 s
    local plan = R.plan()
    assert(plan.colourHold >= .8 and plan.colourHold <= 1, "the colour name is held 0.8-1 s")
    assert(plan.patternHold >= .8 and plan.patternHold <= 1, "the pattern name is held 0.8-1 s")
    assert(plan.buildUp >= .5 and plan.buildUp <= .8, "the build-up is 0.5-0.8 s")
    assert(plan.build <= 3.6, "the storyboard egg is never slower than today's 3.6 s build")
    assert(R.TapWaitMax >= 5 and R.TapWaitMax <= 15, "a batch never stalls on an untouched TAP")
    -- words
    assert(R.colourWord("Blue") == "BLUE" and R.patternWord("Spots") == "SPOTS" and R.patternWord("", true) == "PLAIN" and R.patternWord(nil) == "PLAIN")
    assert(R.tierWord("Rare") == "RARE" and R.Words.tap == "TAP!" and R.Words.best == "BEST FIND!" and R.Words.next == "NEXT")
    for _, word in R.Words do assert(not string.find(word, "%d"), "kid words: no numbers in " .. word) end
    local i, n = R.counter("Egg 2 of 5")
    assert(i == 2 and n == 5 and R.counter("") == nil and R.counter(nil) == nil)
    -- best find and when the summary shows
    assert(R.best({}) == 0)
    assert(R.best({{rarity = 1}, {rarity = 5}, {rarity = 3}}) == 2, "the highest rarity is the best find")
    assert(R.best({{rarity = 3}, {rarity = 3}, {rarity = 1}}) == 1, "a tie: the first one hatched")
    assert(R.best({{rarity = 0}, {rarity = 1}}) == 2, "a splat is never the best find")
    assert(R.wantsSummary(2) and R.wantsSummary(10) and not R.wantsSummary(1) and not R.wantsSummary(nil), "BEST FIND! only for 2+ eggs")
    assert(R.isNew(true, false) and R.isNew(false, true) and not R.isNew(false, false) and not R.isNew(nil, nil))
    -- build-up look: rarity tint, no shake with Reduce Motion, Legendary and up keep the gold build-up
    assert(R.buildUpLook(3, false).shake and not R.buildUpLook(3, true).shake, "Reduce Motion: no shake")
    assert(R.buildUpLook(3, true).glowGrow == 1, "Reduce Motion: no growing pulse")
    assert(R.buildUpLook(4, false).own and not R.buildUpLook(5, false).own and not R.buildUpLook(6, false).own)
end

-- 2. TIMELINE
do
    -- flag off: as shipped
    local m = T.durations(true)
    assert(near(m.build, 3.6) and near(m.readyAt, 5.0) and near(m.paint.leftImpact, .8) and near(m.paint.rightImpact, 1.55), "flag off: the shipped build-up")
    local s = T.new(true, 1, false, false)
    assert(s.gate == nil and T.tapAction(s) == "ignore", "flag off: no wait for a tap")
    for _ = 1, 30 do T.step(s, 1 / 30) end
    assert(near(s.t, 1), "flag off: the clock runs at once")
    -- storyboard on: the paint plan of the rules
    local d = T.durations(true, 1, false, false, false, R)
    local plan = R.plan()
    assert(near(d.paint.leftImpact, plan.leftImpact) and near(d.paint.rightImpact, plan.rightImpact) and near(d.build, plan.build), "storyboard: the rules' pace")
    assert(d.paint.patternEnd <= d.build, "the pattern washes in before the build-up ends")
    assert(near(T.durations(true, 3, false, false, false, R).build, plan.build + T.anticipation(3)), "rarer eggs keep their anticipation")
    assert(T.durations(true, 1, false, true, false, R).build == T.durations(true, 1, false, true).build, "a v2 egg keeps the v2 beat sheet")
    assert(T.durations(false, 1, false, false, false, R).build == 0, "Reduce Motion: no build-up, as before")
    local f = T.durations(true, 1, false, false, true, R)
    assert(f.fast and near(f.build, T.Fast.build), "a fast egg keeps the fast path")
    -- the egg waits for the TAP
    s = T.storyboard(T.new(true, 1, false, false), R, true)
    for _ = 1, 90 do T.step(s, 1 / 30) end
    assert(s.t == 0 and s.idle > 2.9 and s.gate, "the waiting egg holds the clock at 0 (only the wobble moves)")
    assert(T.tapAction(s) == "start" and T.tap(s) == "start" and not s.gate, "the TAP starts the egg")
    T.step(s, .5)
    assert(near(s.t, .5), "then the clock runs")
    -- a tap while the answer is still on its way starts the egg; it then holds at the first bucket as before
    s = T.storyboard(T.new(true, 1, false, true), R, true)
    T.tap(s)
    for _ = 1, 60 do T.step(s, 1 / 30) end
    assert(not s.gate and near(s.t, T.holdAt(s)), "pending after the tap: the egg waits for the answer at the first bucket")
    T.supply(s, 1, false)
    assert(near(s.durs.build, plan.build), "the answer keeps the storyboard pace")
    -- Skip the rest, a fast egg and the time limit open the wait
    s = T.storyboard(T.new(true, 1, false, false), R, true)
    assert(T.skipAll(s) == "fastforward" and not s.gate and s.t == s.durs.build, "Skip the rest never waits for the TAP")
    s = T.storyboard(T.new(true, 1, false, true), R, true)
    T.supply(s, 1, false, true)
    assert(not s.gate, "a fast egg never waits for the TAP")
    s = T.storyboard(T.new(true, 1, false, false), R, true)
    for _ = 1, math.ceil(R.TapWaitMax * 30) + 2 do T.step(s, 1 / 30) end
    assert(not s.gate, "an untouched TAP opens by itself after TapWaitMax")
    s = T.storyboard(T.new(false, 1, false, false), R, true)
    assert(s.gate and T.tap(s) == "start", "Reduce Motion waits for the TAP too (no pulse, the same tap)")
    -- no wait without the gate (the storyboard pace alone)
    s = T.storyboard(T.new(true, 1, false, false), R, false)
    T.step(s, .25)
    assert(near(s.t, .25), "gate off: the clock runs")
end
print("storyboard rules passed")
'''


def script(replacements=None):
    return ('local RS=' + module('src/shared/RevealSkip.luau') + '\n'
            'local V2=' + module('src/shared/HatchV2Plan.luau') + '\n'
            'local script={Parent={RevealSkip=RS,HatchV2Plan=V2}}\nlocal function require(x) return x end\n'
            'local T=' + module(TIMELINE, replacements) + '\n'
            'local R=' + module(RULES, replacements) + '\n' + BODY)


def run(runner, replacements=None):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'storyboard.luau'
        path.write_text(script(replacements), encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    out = result.stdout + result.stderr
    return result.returncode == 0 and 'storyboard rules passed' in result.stdout, out


SCREEN = r'''
do -- BD-1288: the real hatch screen with the storyboard flag on. The base smoke above ran with it off (as shipped).
    local Config = requireModule(SharedFolder.Config)
    local TL = requireModule(SharedFolder.HatchTimeline)
    stubs.FtueRules = {collectionCopies = function() return 9 end}
    stubs.SecretSpeciesConfig = {isSecret = function() return false end}
    register("FtueRules") register("SecretSpeciesConfig")
    assert(Config.HatchStoryboardEnabled == false, "the mock starts with the flag off")
    local function start(opts)
        local menu = buildMenu(1280, 720, 860, 520, 1)
        local handle = playHatch(menu, opts)
        return menu, handle
    end
    local function revealed(menu) local d = menu.body:FindFirstChild("Dino") return d ~= nil and d.Visible == true and d.ImageTransparency == 0 end -- the view is visible but clear while it loads
    local function untilReveal(menu, limit)
        local n = 0
        while not revealed(menu) and n < limit * 30 do frames(1) n += 1 end
        return n / 30
    end
    -- flag off: the egg starts at once, no attribute is written
    TL.batchReset(TL.session)
    local m = start({rarity = 1, remaining = 3})
    local took = untilReveal(m, 9)
    check(revealed(m) and took < 4.5, "flag off: the dinosaur comes without a tap, took " .. took)
    check(m.body:GetAttribute("HatchTapWait") == nil and m.body:GetAttribute("HatchColourName") == nil, "flag off: no storyboard attributes")
    m.gui:Destroy()

    Config.HatchStoryboardEnabled, Config.HatchStageEnabled = true, true
    TL.batchReset(TL.session)
    m = start({rarity = 1, remaining = 3})
    frames(90)
    check(not revealed(m) and m.body:GetAttribute("HatchTapWait") == true, "flag on: the egg waits for the TAP")
    check(m.body:GetAttribute("HatchSpeciesId") == "compy" and m.body:GetAttribute("HatchNewFind") == false, "the reveal words are on the body")
    tapOn(m, m.body)
    frames(2)
    check(m.body:GetAttribute("HatchTapWait") == false, "the tap starts the egg")
    local SBR = requireModule(SharedFolder.HatchStoryboardRules)
    local seen, at = false, 0
    for f = 1, 150 do
        frames(1)
        if m.body:GetAttribute("HatchBuildUp") == true and not seen then seen, at = true, f / 30 end
    end
    check(seen and math.abs(at - SBR.plan().buildUpAt) < .15, "the build-up starts on the sequence clock at the end of the pattern hold, at " .. at)
    took = untilReveal(m, 9)
    check(revealed(m) and took <= 4.2, "then the dinosaur comes, took " .. took)
    check(m.nexts == 0, "the start tap never skips to the next egg")
    check(m.body:GetAttribute("HatchBuildUp") == false, "the build-up flag is off again after the burst")
    m.gui:Destroy()
    -- the waiting egg: Skip the rest still works
    m = start({rarity = 1, remaining = 3})
    frames(10)
    local skip = m.gui:FindFirstChild("SkipAll", true)
    check(skip ~= nil, "Skip the rest is on the waiting egg")
    if skip then skip.Activated:Fire() end
    frames(30)
    check(m.skipAlls == 1 and revealed(m), "Skip the rest opens the waiting egg at once")
    m.gui:Destroy()
    -- nobody taps: the egg opens by itself
    m = start({rarity = 1, remaining = 3})
    took = untilReveal(m, 20)
    check(revealed(m) and took >= 10 and took <= 15, "an untouched TAP opens by itself, took " .. took)
    m.gui:Destroy()
    -- Reduce Motion waits for the same tap
    m = start({rarity = 1, remaining = 3, motion = false})
    frames(60)
    check(not revealed(m) and m.body:GetAttribute("HatchTapWait") == true, "Reduce Motion: the egg waits for the TAP")
    tapOn(m, m.body)
    took = untilReveal(m, 5)
    check(revealed(m), "Reduce Motion: the tap opens it")
    m.gui:Destroy()
    TL.batchReset(TL.session)
    Config.HatchStoryboardEnabled, Config.HatchStageEnabled = false, false
    print("hatch storyboard screen passed")
end
'''
END_LINE = 'if failures > 0 then error(failures .. " close-path checks failed") end'


def screen_script(replacements=None):
    reps = {}
    for path, pairs in (replacements or {}).items():
        reps.setdefault(Path(path).stem, []).extend(pairs)
    modules = dict(verify_close_paths.MODULES)
    verify_close_paths.MODULES['HatchStoryboardRules'] = RULES
    try:
        source = verify_close_paths.build_script(reps)
    finally:
        verify_close_paths.MODULES.clear()
        verify_close_paths.MODULES.update(modules)
    assert source.count(END_LINE) == 1
    return source.replace(END_LINE, SCREEN + END_LINE)


def run_screen(runner, replacements=None):
    result = verify_close_paths.run(runner, screen_script(replacements))
    out = result.stdout + result.stderr
    return result.returncode == 0 and 'hatch storyboard screen passed' in result.stdout, out


def check_sources(overrides=None):
    def src(path):
        return (overrides or {}).get(path) or read(path)
    if '    HatchStoryboardEnabled = false,\n' not in src('src/shared/Config.luau'):
        return 'Config.HatchStoryboardEnabled must ship false'
    profiles = src('tools/release_profiles.py')
    if ('_flag_off("HatchStoryboardEnabled"' not in profiles or 'Rule("HatchStoryboardEnabled", "set", True' not in profiles
            or '("HatchStoryboardEnabled", "BD-1288' not in profiles):
        return 'HatchStoryboardEnabled: off in default, on in playtest, in the rehearsal list'
    if '"HatchStoryboardEnabled"' not in src('tools/release_playtest.py'):
        return 'the playtest manifest records HatchStoryboardEnabled'
    watch = src('src/client/HatchStageWatch.client.luau')
    if 'local Storyboard = if Config.HatchStoryboardEnabled == true then require(script.Parent:WaitForChild("HatchStoryboard")) else nil' not in watch:
        return 'the stage watcher requires the storyboard only under the flag'
    seq = src(SEQUENCE)
    if 'local SB = if Config.HatchStoryboardEnabled == true and Config.HatchStageEnabled == true then require(Shared.HatchStoryboardRules) else nil' not in seq:
        return 'HatchSequence reads the storyboard rules only under both flags'
    if 'if state.gate then Timeline.tap(state) return end' not in seq:
        return 'the tap on the waiting egg starts it'
    if 'copy.HatchStoryboardEnabled = false' not in src('tools/verify_close_paths.py'):
        return 'the close-path smokes keep measuring the shipped hatch'
    if 'python tools/verify_hatch_storyboard.py --runner /tmp/luau/luau' not in src('.github/workflows/build-generated-place.yml'):
        return 'CI runs tools/verify_hatch_storyboard.py'
    for path in ('src/shared/HatchStoryboardRules.luau', 'src/client/HatchStoryboard.luau'):
        text = src(path)
        for bad in ('Robux', 'MarketplaceService', 'DataStore', 'RemoteEvent', ':FireServer'):
            if bad in text:
                return '%s: presentation only, no %s' % (path, bad)
    for path in Path(ROOT / 'src/server').rglob('*.luau'):
        if 'HatchStoryboard' in path.read_text(encoding='utf-8'):
            return 'no server file knows the storyboard (%s)' % path.name
    return None


MUTANTS = {
    'the egg is small again': {RULES: [('R.EggShare = {min = .35, max = .45, want = .42}', 'R.EggShare = {min = .35, max = .45, want = .28}')]},
    'the colour name flashes by': {RULES: [('R.Paint = {leftStart = .35, rightStart = 1.25,', 'R.Paint = {leftStart = .35, rightStart = .9,')]},
    'the build-up drags': {RULES: [('R.BuildUp = .7', 'R.BuildUp = 1.4')]},
    'phone words under 19 px': {RULES: [('R.MinText = 19', 'R.MinText = 14')]},
    'the plate covers the egg': {RULES: [('local left = eggCx + eggH * .42 + math.max(12, eggH * .08)', 'local left = eggCx - eggH * .2')]},
    'chips sit on the name plate': {RULES: [('chipsY = .79', 'chipsY = .72')]},
    'the card name sits on the chip': {RULES: [('local nameCy = chipCy - chipH / 2 - 3 - nameH / 2', 'local nameCy = chipCy - nameH / 4')]},
    'the summary cards spill off the screen': {RULES: [('local areaL, areaR = w * .54, w - 16', 'local areaL, areaR = w * .54, w + 120')]},
    'the best find is the last egg': {RULES: [('if r > rank then best, rank = i, r end', 'if r >= rank then best, rank = i, r end')]},
    'one egg gets a summary': {RULES: [('return type(total) == "number" and total >= 2', 'return type(total) == "number" and total >= 1')]},
    'Reduce Motion shakes': {RULES: [('shake = not reduceMotion', 'shake = true')]},
    'the TAP never opens the egg': {TIMELINE: [('    if action == "start" then\n        state.gate = false\n', '    if action == "start" then\n')]},
    'the waiting egg runs its clock': {TIMELINE: [('        state.idle += dt\n        if state.gateWait', '        state.t += dt\n        if state.gateWait')]},
    'Skip the rest waits for the TAP': {TIMELINE: [('    state.gate = false -- BD-1288: Skip the rest never waits for a TAP\n', '')]},
    'a fast egg waits for the TAP': {TIMELINE: [('    if fast == true then state.gate = false end', '')]},
    'the egg waits forever': {TIMELINE: [('if state.gateWait >= ((state.sb and state.sb.TapWaitMax) or 0) then state.gate = false end', '')]},
    'flag off changes the pace': {TIMELINE: [('local p = paint or T.Paint', 'local p = paint or {leftStart = .35, rightStart = 1.25, window = .75, impact = .6, wash = .35, patternDelay = .05, patternWash = .4}')]},
}

SCREEN_MUTANTS = {
    'screen: the tap on the waiting egg is ignored': {SEQUENCE: [('        if state.gate then Timeline.tap(state) return end -- BD-1288', '        if state.gate then return end -- BD-1288')]},
    'screen: the storyboard runs with the flag off': {SEQUENCE: [('local SB = if Config.HatchStoryboardEnabled == true and Config.HatchStageEnabled == true then', 'local SB = if true then')]},
    'screen: the build-up never starts': {SEQUENCE: [('state.t >= SB.plan().buildUpAt and state.t < state.durs.build', 'false')]},
    'screen: no TAP attribute': {SEQUENCE: [('a.body:SetAttribute("HatchTapWait", state.gate == true)', 'a.body:SetAttribute("HatchTapWait", false)')]},
}

SOURCE_MUTANTS = {
    'the flag ships on': ('src/shared/Config.luau', '    HatchStoryboardEnabled = false,\n', '    HatchStoryboardEnabled = true,\n'),
    'the watcher always loads the storyboard': ('src/client/HatchStageWatch.client.luau', 'if Config.HatchStoryboardEnabled == true then require(script.Parent:WaitForChild("HatchStoryboard")) else nil', 'require(script.Parent:WaitForChild("HatchStoryboard"))'),
    'the storyboard sends to the server': ('src/client/HatchStoryboard.luau', 'local SB = {}', 'local SB = {} local _ = game:GetService("ReplicatedStorage").X:FireServer()'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    problem = check_sources()
    if problem:
        print('FAIL', problem)
        sys.exit(1)
    ok, out = run(args.runner)
    print(out, end='')
    if not ok:
        sys.exit(1)
    ok, out = run_screen(args.runner)
    print('\n'.join(line for line in out.splitlines() if 'storyboard' in line or line.startswith('FAIL') or 'error' in line.lower()))
    if not ok:
        print(out[-3000:])
        sys.exit(1)
    count = 0
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
        count = len(MUTANTS) + len(SCREEN_MUTANTS) + len(SOURCE_MUTANTS)
    print('Hatch storyboard passed: rules on four screens, the storyboard pace and the TAP wait, the real hatch screen in the mock (flag off and on), wiring, %d mutants caught' % count)


if __name__ == '__main__':
    main()
