"""BD-1039 / docs/186 s7: the Pattern Index and the Colour Index (the Patterns and Colours tabs of the Index screen), offline, in the pinned Luau runtime.

1. LOGIC (src/shared/PatternColourIndex.luau with the REAL config tables): found sets from owned dinos (main AND accent colour both count) merged with the
   server's discovery log (a fused-away find stays found), "backfill" without any profile rewrite (the input is never touched), card order (tier, then
   table order), header counts "Patterns 5 / 8", boost pips from the tier points (Common 0 .. Mythic 5, no percent), "Found on" lines (two species, then
   +N), the dot rule, the hatch ribbon words, flag-off = the old single NEW! ribbon, the dimmed tier colour.
2. BOOST WORDS (GeneBoost.itemPips / dinoPips / dinoText, ColourBonus.text): the hatch card says "Boost 3 of 5" instead of the BD-172 percent only while
   Config.GeneBoostEnabled is true; flag off = the old text, byte for byte.
3. DISCOVERY (ProgressionRules.discover / backfillDiscovered / discoveryIds): the accent colour is recorded ONLY when the server passes the flag; without it
   the BD-436 behaviour is unchanged. Add-only, capped, and no new saved field: the existing progression.discovered log is reused.
4. SMOKE (tools/pattern_colour_index_smoke.luau): the REAL IndexTabs and PatternColourCards in a mock GUI (see that file).
5. WIRING (source): the flag ships false and is on in the playtest profile only; Bootstrap has the one-line hook; the server passes the flag; the
   client never hard-codes a pattern or colour id; every card text is kid copy.
Not Studio evidence: nothing here shows layout, drawing, touch or a phone. Usage: python tools/verify_pattern_colour_index.py --runner luau.exe
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def module(path):
    return '(function()\n' + read(path) + '\nend)()'


LOGIC = r'''
local PC = ProgressionConfig
local P, C = PC.EggPatterns, PC.EggColors
local function names(id) return ({compy = "Compy", raptor = "Raptor", triceratops = "Triceratops", stegosaurus = "Stegosaurus", tyrannosaurus = "T-Rex"})[id] or id end
local order = {"compy", "raptor", "triceratops", "stegosaurus", "tyrannosaurus"}
local function variant(pattern, main, accent, count) return {count = count or 1, genes = {patternId = pattern, primaryColorId = main, secondaryColorId = accent}} end
local function deepEqual(a, b)
    if type(a) ~= type(b) then return false end
    if type(a) ~= "table" then return a == b end
    for k, v in a do if not deepEqual(v, b[k]) then return false end end
    for k in b do if a[k] == nil then return false end end
    return true
end
local function clone(t) if type(t) ~= "table" then return t end local o = {} for k, v in t do o[k] = clone(v) end return o end

-- 1. tabs
assert(Index.validTab("patterns") == "patterns" and Index.validTab("colours") == "colours" and Index.validTab("dinos") == "dinos")
for _, bad in {"x", 5, true, {}} do assert(Index.validTab(bad) == "dinos", "a bad remembered tab opens the Dinos tab") end
assert(Index.validTab(nil) == "dinos" and #Index.Tabs == 3 and Index.TabNames.dinos == "Dinos" and Index.TabNames.patterns == "Patterns" and Index.TabNames.colours == "Colours")

-- 2. found sets: owned dinos (main AND accent colour), count 0 = not owned, species named in Index order
local collection = {
    compy = {base = 3, variants = {a = variant("03_round_spots", "blue", "red", 2), b = variant("07_diamond_scales", "white", "white"), z = variant("06_wavy_stripes", "teal", "pink", 0)}},
    raptor = {base = 0, variants = {c = variant("03_round_spots", "blue", "blue"), d = variant("04_bold_patches", "green", "blue")}},
    stegosaurus = {base = 1, variants = {}},
    mystery = {variants = {q = variant("08_freckles", "black", "black")}}, -- not in the species order: ignored
}
local before = clone(collection)
local f = Index.foundSets(collection, nil, order)
assert(deepEqual(collection, before), "the saved data is read, never rewritten (no profile rewrite)")
assert(f.patterns["03_round_spots"] and f.patterns["07_diamond_scales"] and f.patterns["04_bold_patches"] and not f.patterns["06_wavy_stripes"] and not f.patterns["08_freckles"])
assert(f.colours.blue and f.colours.red and f.colours.white and f.colours.green and not f.colours.teal and not f.colours.pink and not f.colours.black, "main and accent both count")
assert(table.concat(f.patternSpecies["03_round_spots"], ",") == "compy,raptor" and table.concat(f.colourSpecies.blue, ",") == "compy,raptor" and table.concat(f.colourSpecies.red, ",") == "compy")
local f2 = Index.foundSets(collection, {colours = 4, patterns = 3, ids = {patterns = {"02_emerald_islands", 5, ""}, colours = {"black", false}}}, order)
assert(f2.patterns["02_emerald_islands"] and f2.colours.black, "the discovery log adds finds (fused-away dinos stay found)")
assert(f2.patternSpecies["02_emerald_islands"] == nil, "a log-only find names no species")
for _, junk in {nil, {}, "x", 5, {ids = "x"}, {ids = {patterns = 5, colours = "x"}}} do
    local g = Index.foundSets(junk, junk, junk)
    assert(next(g.patterns) == nil and next(g.colours) == nil, "junk in, nothing found, no error")
end
local g0 = Index.foundSets({}, {}, order)
assert(next(g0.patterns) == nil and next(g0.colours) == nil)
-- first load of an old save: dinos already owned count, nothing else is needed (backfill without a saved field)
local old = Index.foundSets({compy = {base = 5, variants = {a = variant("08_freckles", "pink", "gold")}}}, {colours = 0, patterns = 0, mutations = 0}, order)
assert(old.patterns["08_freckles"] and old.colours.pink and old.colours.gold)

-- 3. cards: one per config row, tier order then table order, names are kid names
local pc = Index.cards("patterns", P, f2, names)
assert(#pc == #P and #pc == 8, "one card per EggPatterns row")
local expectOrder = {}
for tier = 0, 5 do for _, row in P do if Curve.index(row.rarity) == tier then table.insert(expectOrder, row.id) end end end
for i, card in pc do assert(card.id == expectOrder[i], "order " .. i .. " " .. card.id) end
assert(pc[1].tier <= pc[#pc].tier and pc[#pc].rarity == "Legendary" and pc[#pc].name == "Diamonds")
local byId = {}
for _, card in pc do byId[card.id] = card assert(card.name ~= "" and not string.find(card.name, "%d") and not string.find(card.name, "_"), "kid name, never an id: " .. card.name) end
assert(byId["03_round_spots"].found and byId["03_round_spots"].line == "Found on: Compy, Raptor")
assert(byId["07_diamond_scales"].line == "Found on: Compy" and byId["02_emerald_islands"].line == "Found before")
assert(not byId["06_wavy_stripes"].found and byId["06_wavy_stripes"].line == "Not found yet" and Index.NotFoundLine == "Not found yet")
assert(byId["01_blank"].rgb == nil, "patterns have no swatch")
-- the card list does not reshuffle when a find is made (same order found or not)
local pcNone = Index.cards("patterns", P, g0, names)
for i, card in pcNone do assert(card.id == pc[i].id and not card.found) end
-- never hard-coded: an extra row in the table appears as a card
local extra = clone(P) table.insert(extra, {id = "09_new", name = "Stars", rarity = "Mythic", weight = 1})
local pe = Index.cards("patterns", extra, g0, names)
assert(#pe == 9 and pe[#pe].id == "09_new" and pe[#pe].pips == 5 and pe[#pe].rarity == "Mythic")
-- a row without a name gets a calm generic word
assert(Index.displayName("patterns", {id = "x"}) == "Pattern" and Index.displayName("colours", {id = "x"}) == "Colour" and Index.displayName("colours", {id = "x", name = "Sky"}) == "Sky")
-- colours: same, with the real rgb
local cc = Index.cards("colours", C, f2, names)
assert(#cc == 9 and cc[1].tier == 0 and cc[#cc].tier == 5)
local cById = {}
for _, card in cc do cById[card.id] = card end
assert(cById.blue.rgb[1] == 36 and cById.blue.rgb[2] == 132 and cById.blue.rgb[3] == 211, "the real colour")
assert(cById.red.line == "Found on: Compy" and cById.black.line == "Found before" and cById.teal.line == "Not found yet")
-- 'Found on': two species, then +N
local many = {compy = {variants = {a = variant("01_blank", "blue", "blue")}}, raptor = {variants = {a = variant("01_blank", "blue", "blue")}},
    triceratops = {variants = {a = variant("01_blank", "blue", "blue")}}, stegosaurus = {variants = {a = variant("01_blank", "blue", "blue")}},
    tyrannosaurus = {variants = {a = variant("01_blank", "blue", "blue")}}}
local fm = Index.foundSets(many, nil, order)
assert(Index.cards("patterns", P, fm, names)[1].line == "Found on: Compy, Raptor +3", Index.cards("patterns", P, fm, names)[1].line)
assert(Index.foundOnText({"compy", "raptor"}, names) == "Compy, Raptor" and Index.foundOnText({"compy"}, names) == "Compy" and Index.foundOnText({}, names) == nil and Index.foundOnText(nil, names) == nil)
assert(Index.foundOnText({"a", "b", "c"}, nil) == "a, b +1", "no name function: the id is the last resort")

-- 4. header counts and pips
assert(Index.header("patterns", pcNone).text == "Patterns 0 / 8" and Index.header("patterns", pc).text == "Patterns 4 / 8")
assert(Index.header("colours", cc).text == "Colours 5 / 9", Index.header("colours", cc).text) -- blue, red, white, green + black (log)
assert(Index.header("colours", nil).text == "Colours 0 / 0" and Index.header("patterns", {}).text == "Patterns 0 / 0")
local want = {Common = 0, Uncommon = 1, Rare = 2, Epic = 3, Legendary = 4, Mythic = 5}
for _, card in pc do assert(card.pips == want[card.rarity], card.id .. " pips") end
for _, card in cc do assert(card.pips == want[card.rarity], card.id .. " pips") end
assert(Index.boostText(0) == "No boost" and Index.boostText(3) == "Boost 3 of 5" and Index.boostText(5) == "Boost 5 of 5")
for _, card in pc do assert(not string.find(card.boostText, "%%") and not string.find(card.boostText, "x"), "no percent, no multiplier") end
-- pips never exceed the tier ladder, rarer never fewer
local last = -1
for _, card in pc do assert(card.pips >= last and card.pips >= 0 and card.pips <= 5) last = card.pips end

-- 5. the dot
assert(Index.foundTotal(f2, P, C) == 4 + 5)
assert(Index.foundTotal(nil, P, C) == 0)
assert(Index.dotVisible(8, nil) == false, "no baseline yet: no dot")
assert(Index.dotVisible(8, 8) == false and Index.dotVisible(9, 8) == true and Index.dotVisible(3, 8) == false)

-- 6. ribbons on the hatch reveal
assert(table.concat(Index.ribbons({pattern = true}, true), "|") == "New pattern!")
assert(table.concat(Index.ribbons({colour = true}, true), "|") == "New colour!")
assert(table.concat(Index.ribbons({pattern = true, colour = true}, true), "|") == "New pattern!|New colour!")
assert(table.concat(Index.ribbons({pattern = true, colour = true, mutation = true}, true), "|") == "New pattern!|New colour!")
assert(table.concat(Index.ribbons({mutation = true}, true), "|") == "NEW!", "a mutation-only find keeps NEW!")
assert(#Index.ribbons({}, true) == 0 and #Index.ribbons(nil, true) == 0 and #Index.ribbons("x", true) == 0)
for _, off in {false, nil, 1, "true"} do
    assert(table.concat(Index.ribbons({pattern = true, colour = true}, off), "|") == "NEW!", "flag off: the old single ribbon")
    assert(#Index.ribbons({}, off) == 0)
end
for _, word in {"New pattern!", "New colour!"} do assert(#word <= 12) end

-- 7. the dimmed tier colour keeps its hue and stays visible
local legendary = {1, 0.8, 0.2}
local dark = {46 / 255, 46 / 255, 58 / 255}
local dimmed = Index.dim(legendary, dark)
for i = 1, 3 do assert(dimmed[i] >= math.min(legendary[i], dark[i]) - 1e-9 and dimmed[i] <= math.max(legendary[i], dark[i]) + 1e-9) end
assert(dimmed[1] > dimmed[3], "still reads as the warm tier colour, not grey")
assert(dimmed[1] < legendary[1] - 0.05 and dimmed[2] < legendary[2] - 0.05, "visibly dimmer than the full tier colour")
local same = Index.dim(dark, dark)
assert(math.abs(same[1] - dark[1]) < 1e-9)

-- 8. boost pips from the tier points
assert(Boost.itemPips(0) == 0 and Boost.itemPips(1) == 1 and Boost.itemPips(2) == 2 and Boost.itemPips(4) == 3 and Boost.itemPips(6) == 4 and Boost.itemPips(10) == 5 and Boost.itemPips(99) == 5)
assert(Boost.itemPips(nil) == 0 and Boost.itemPips(-3) == 0 and Boost.itemPips(0 / 0) == 0 and Boost.itemPips("x") == 0)
assert(Boost.itemPips(3) == 2 and Boost.itemPips(5) == 3, "between levels: the lower rank")
assert(Boost.dinoPips(0) == 0 and Boost.dinoPips(0.5) == 1 and Boost.dinoPips(3) == 1 and Boost.dinoPips(3.01) == 2 and Boost.dinoPips(15) == 5 and Boost.dinoPips(100) == 5 and Boost.dinoPips(nil) == 0)
local lastPips = 0
for n = 0, 60 do local p = Boost.dinoPips(n * .5) assert(p >= lastPips and p <= 5) lastPips = p end
local top = {patternId = "07_diamond_scales", primaryColorId = "black", secondaryColorId = "red"}
assert(Boost.dinoText(P, C, top) == "Boost 5 of 5")
assert(Boost.dinoText(P, C, {patternId = "01_blank", primaryColorId = "white", secondaryColorId = "blue"}) == nil, "no boost: no line")
assert(Boost.dinoText(P, C, {patternId = "06_wavy_stripes", primaryColorId = "green", secondaryColorId = "gold"}) == "Boost 3 of 5", Boost.dinoText(P, C, {patternId = "06_wavy_stripes", primaryColorId = "green", secondaryColorId = "gold"})) -- 2 + .7 + 4 = 6.7 points
assert(Boost.dinoText(P, C, nil) == nil and Boost.dinoText(nil, nil, top) == nil)

-- 9. BD-1065: the dot baseline survives a rejoin, and the small detail of a card
assert(Index.seenBaseline(5, 3, 8) == 5, "a tab looked at in this session wins")
assert(Index.seenBaseline(nil, 3, 8) == 3 and Index.seenBaseline(nil, 3.0, nil) == 3, "the saved total beats the first reading, so a find before a rejoin still shows its dot")
assert(Index.seenBaseline(nil, 0, 8) == 8 and Index.seenBaseline(nil, nil, 8) == 8 and Index.seenBaseline(nil, -2, 8) == 8 and Index.seenBaseline(nil, 0 / 0, 8) == 8, "nothing saved: the first reading is the baseline")
assert(Index.seenBaseline(nil, nil, nil) == nil and Index.seenBaseline("x", "y", "z") == nil, "junk gives no baseline")
assert(Index.dotVisible(9, Index.seenBaseline(nil, 7, 9)) == true and Index.dotVisible(9, Index.seenBaseline(nil, 9, 9)) == false)
local fullFound = Index.foundSets({compy = {variants = {a = variant("03_round_spots", "blue", "red")}}, raptor = {variants = {b = variant("03_round_spots", "blue", "blue")}},
    triceratops = {variants = {c = variant("03_round_spots", "white", "white")}}, stegosaurus = {variants = {d = variant("03_round_spots", "blue", "white")}},
    tyrannosaurus = {variants = {e = variant("03_round_spots", "blue", "white")}}}, nil, order)
local pcards = Index.cards("patterns", P, fullFound, names)
local ccards = Index.cards("colours", C, fullFound, names)
local function cardOf(list, id) for _, card in list do if card.id == id then return card end end end
local dots = Index.detail("patterns", cardOf(pcards, "03_round_spots"), fullFound, names)
assert(dots.found and dots.title == "Dots" and dots.tier == "Common" and dots.pips == 0 and dots.boostText == "No boost" and dots.hint == nil, "a pattern detail has no colour hint")
assert(#dots.lines == 3 and dots.lines[1] == "Compy, Raptor" and dots.lines[2] == "Triceratops, Stegosaurus" and dots.lines[3] == "T-Rex", "the full Found on list, two names to a line")
local blue = Index.detail("colours", cardOf(ccards, "blue"), fullFound, names)
assert(blue.found and blue.title == "Blue" and blue.hint == "The accent colour counts more", "the colour detail carries the accent hint")
assert(Index.detail("colours", cardOf(ccards, "red"), fullFound, names).hint == "The accent colour counts more", "also on a colour not found yet")
local unknown = Index.detail("patterns", cardOf(pcards, "07_diamond_scales"), fullFound, names)
assert(not unknown.found and unknown.title == "???" and unknown.tier == "Legendary" and unknown.pips == 4 and unknown.boostText == "Boost 4 of 5", "tier and pips stay visible on a card not found")
assert(#unknown.lines == 2 and unknown.lines[1] == "Not found yet" and unknown.lines[2] == "Hatch eggs to find it!")
local before2 = Index.detail("patterns", {id = "02_emerald_islands", name = "Islands", rarity = "Epic", found = true, pips = 3, boostText = "Boost 3 of 5"}, fullFound, names)
assert(before2.lines[1] == "Found before" and #before2.lines == 1, "found, but no dino of it is left")
-- a long list is kept whole (every dino the game has), and the tail is counted past the cap
local many, ids = {}, {}
for i = 1, 30 do table.insert(ids, "dino" .. i) end
many["03_round_spots"] = ids
local longList = Index.detail("patterns", {id = "03_round_spots", name = "Dots", rarity = "Common", found = true, pips = 0, boostText = "No boost"}, {patternSpecies = many}, function(id) return id end)
assert(#longList.lines == Index.MaxDetailLines + 1 and longList.lines[#longList.lines] == "+6 more" and longList.lines[1] == "dino1, dino2", "24 shown, the rest counted")
local twentytwo = {}
for i = 1, 22 do table.insert(twentytwo, "d" .. i) end
assert(#Index.detail("patterns", {id = "x", name = "X", rarity = "Common", found = true, pips = 0}, {patternSpecies = {x = twentytwo}}, function(id) return id end).lines == 11, "all 22 dinos of the game fit without a +N")
for _, junk in {nil, 5, "x", {}} do
    local d = Index.detail("colours", junk, junk, junk)
    assert(d.title == "???" and not d.found and d.hint == "The accent colour counts more" or d.title == "???", "junk in, a calm empty detail, no error")
end

print("Pattern and Colour Index logic passed: found sets (main + accent colour, log merge, no rewrite), cards in tier order from the real tables, kid names, Found on +N, header counts, pips Common 0 .. Mythic 5, dot rule, ribbons, flag-off ribbon, dim colour, dino boost words")
'''

BONUS = r'''
-- ColourBonus.text: the old BD-172 percent with the gene boost off, the pips wording with it on.
local genes = {patternId = "07_diamond_scales", primaryColorId = "red", secondaryColorId = "white"}
configMock.GeneBoostEnabled = false
assert(Bonus.text(PC.EggColors, genes) == "Colour bonus +5% growth", "flag off: unchanged")
assert(Bonus.text(PC.EggColors, {primaryColorId = "white", secondaryColorId = "white"}) == nil)
configMock.GeneBoostEnabled = nil
assert(Bonus.text(PC.EggColors, genes) == "Colour bonus +5% growth", "flag unset: unchanged")
configMock.GeneBoostEnabled = true
-- 6 (Legendary pattern) + 0.7 * 10 (red) + 0 = 13 points -> ceil(13 / 3) = 5 pips? no: 13 / 3 = 4.33 -> 5
assert(Bonus.text(PC.EggColors, genes) == "Boost 5 of 5", Bonus.text(PC.EggColors, genes))
assert(Bonus.text(PC.EggColors, {patternId = "01_blank", primaryColorId = "white", secondaryColorId = "white"}) == nil, "no boost: no line")
assert(not string.find(Bonus.text(PC.EggColors, genes), "%%") and not string.find(Bonus.text(PC.EggColors, genes), "growth"), "no percent once the boost replaces the colour bonus")
configMock.GeneBoostEnabled = "true"
assert(Bonus.text(PC.EggColors, genes) == "Colour bonus +5% growth", "only a literal true switches it on")
print("Boost words passed: Colour bonus text with the flag off, 'Boost N of 5' with the gene boost on")
'''

DISCOVERY = r'''
local function count(t) local n = 0 for _ in t do n += 1 end return n end
local profile = {collection = {
    compy = {base = 1, events = {}, variants = {a = {count = 1, mutationId = "", genes = {primaryColorId = "green", secondaryColorId = "red", patternId = "p1"}}}},
}}
-- flag off (the server passes nothing): the BD-436 behaviour, main colour only
local log = Rules.backfillDiscovered(profile)
assert(log.colours.green and not log.colours.red, "flag off: the accent colour is not recorded")
local fresh = Rules.discover(profile, {primaryColorId = "blue", secondaryColorId = "pink", patternId = "p2"}, "")
assert(fresh.colour and fresh.pattern and not log.colours.pink)
-- flag on: the accent colour counts too
local p2 = {collection = profile.collection}
local log2 = Rules.backfillDiscovered(p2, true)
assert(log2.colours.green and log2.colours.red, "flag on: backfill records the accent colour of dinos already owned")
local f1 = Rules.discover(p2, {primaryColorId = "green", secondaryColorId = "pink", patternId = "p1"}, "", true)
assert(f1.colour and not f1.pattern and log2.colours.pink, "a new ACCENT colour is a first-time find")
local f2 = Rules.discover(p2, {primaryColorId = "green", secondaryColorId = "pink", patternId = "p1"}, "", true)
assert(next(f2) == nil, "second time is not new")
local f3 = Rules.discover(p2, {primaryColorId = "teal", secondaryColorId = "teal", patternId = "p1"}, "", true)
assert(f3.colour and count(p2.progression.discovered.colours) == 4, "same colour twice is one entry")
assert(next(Rules.discover(p2, {primaryColorId = "teal", secondaryColorId = 5, patternId = 7}, "none", true)) == nil, "junk is ignored")
for _, off in {false, nil, 1, "true"} do
    local p3 = {collection = {}}
    Rules.discover(p3, {primaryColorId = "green", secondaryColorId = "red", patternId = "p1"}, "", off)
    assert(p3.progression.discovered.colours.green and not p3.progression.discovered.colours.red, "only a literal true records the accent")
end
-- ids for the client: sorted lists, only the player's own, bounded
local ids = Rules.discoveryIds(p2)
assert(table.concat(ids.colours, ",") == "green,pink,red,teal" and table.concat(ids.patterns, ",") == "p1", table.concat(ids.colours, ","))
assert(#Rules.discoveryIds({collection = {}}).colours == 0 and #Rules.discoveryIds({progression = {discovered = "junk"}}).patterns == 0, "absent or junk log reads as empty")
local big = {collection = {}}
for i = 1, 100 do Rules.discover(big, {primaryColorId = "c" .. i, secondaryColorId = "d" .. i}, "", true) end
assert(count(big.progression.discovered.colours) == Rules.DiscoveredMaxPerKind and #Rules.discoveryIds(big).colours == Rules.DiscoveredMaxPerKind, "capped")
assert(Rules.valid(p2.progression), "progression stays valid with the log")
print("Discovery passed: accent colour only with the flag, first-time flags, add-only and capped, ids sorted, flag off = BD-436")
'''


def logic_script():
    return ('local Curve=' + module('src/shared/RarityCurve.luau') + '\n'
            'local ProgressionConfig=' + module('src/shared/ProgressionConfig.luau') + '\n'
            'local script={Parent={RarityCurve=Curve}}\nlocal require=function(x) return x end\n'
            'local Boost=' + module('src/shared/GeneBoost.luau') + '\n'
            'script={Parent={RarityCurve=Curve,GeneBoost=Boost}}\n'
            'local Index=' + module('src/shared/PatternColourIndex.luau') + '\n' + LOGIC)


def bonus_script():
    return ('local Curve=' + module('src/shared/RarityCurve.luau') + '\n'
            'local PC=' + module('src/shared/ProgressionConfig.luau') + '\n'
            'local script={Parent={RarityCurve=Curve}}\nlocal require=function(x) return x end\n'
            'local Boost=' + module('src/shared/GeneBoost.luau') + '\n'
            'local configMock={}\n'
            'script={Parent={RarityCurve=Curve,Config=configMock,GeneBoost=Boost,ProgressionConfig=PC}}\n'
            'local Bonus=' + module('src/shared/ColourBonus.luau') + '\n' + BONUS)


def discovery_script():
    s = 'local ProgressionConfig=' + module('src/shared/ProgressionConfig.luau') + '\n'
    s += 'local script={Parent={ProgressionConfig="ProgressionConfig",EggGenetics="Genetics"}}\n'
    s += 'local require=function(_) return ProgressionConfig end\n'
    s += 'local Genetics=' + module('src/shared/EggGenetics.luau') + '\n'
    s += 'local require=function(id) return if id=="Genetics" then Genetics else ProgressionConfig end\n'
    s += 'local Rules=' + module('src/shared/ProgressionRules.luau') + '\n' + DISCOVERY
    return s


SMOKE_MODULES = {
    'Config': None,  # stubbed by the smoke
    'ProgressionConfig': 'src/shared/ProgressionConfig.luau',
    'RarityCurve': 'src/shared/RarityCurve.luau',
    'GeneBoost': 'src/shared/GeneBoost.luau',
    'PatternColourIndex': 'src/shared/PatternColourIndex.luau',
    'AssetSlots': 'src/shared/AssetSlots.luau',
    'SettingsModel': 'src/shared/SettingsModel.luau',
    'PatternColourCards': 'src/client/PatternColourCards.luau',
    'PatternColourDetail': 'src/client/PatternColourDetail.luau',
    'IndexTabs': 'src/client/IndexTabs.luau',
}


def smoke_script():
    parts = []
    for name, path in SMOKE_MODULES.items():
        if path is None:
            continue
        parts.append(name + '=function(script, require)\n' + read(path) + '\nend,\n')
    table = '{\n' + ''.join(parts) + '}'
    harness = read('tools/pattern_colour_index_smoke.luau')
    assert harness.count('local sources = MODULE_SOURCES') == 1
    return harness.replace('local sources = MODULE_SOURCES', 'local sources = ' + table)


def run(runner, source, name):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        path.write_text(source, encoding='utf-8')
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)


def mutants(runner):
    """The checks must FAIL when the rules are broken on purpose (so a green run means something)."""
    index = read('src/shared/PatternColourIndex.luau')
    cases = [
        ('accent colour ignored', 'for _, colourId in {g.primaryColorId, g.secondaryColorId} do', 'for _, colourId in {g.primaryColorId} do'),
        ('a count of 0 still owned', 'and whole(variant.count) > 0 and', 'and'),
        ('dimming removed', 'Index.DimBlend = 0.55', 'Index.DimBlend = 0'),
        ('log ignored', 'local ids = if type(discovered) == "table" and type(discovered.ids) == "table" then discovered.ids else nil', 'local ids = nil'),
        ('saved total ignored (the dot forgets a rejoin)', 'if type(saved) == "number" and saved == saved and saved > 0 then return saved end', ''),
        ('the accent hint shows on a pattern too', 'hint = if isColour then Index.AccentHint else nil', 'hint = Index.AccentHint'),
        ('the Found on list is cut to one line', 'local shown = math.min(#names, perLine * maxLines)', 'local shown = math.min(#names, perLine)'),
        ('a card not found gives away its name', 'local out: any = {title = "???"', 'local out: any = {title = (if type(card) == "table" and card.name then card.name else "???")'),
    ]
    for label, old, new in cases:
        assert old in index, 'mutant target missing: ' + label
        broken = index.replace(old, new)
        script = ('local Curve=' + module('src/shared/RarityCurve.luau') + '\n' +
                  'local ProgressionConfig=' + module('src/shared/ProgressionConfig.luau') + '\n' +
                  'local script={Parent={RarityCurve=Curve}}' + '\n' + 'local require=function(x) return x end' + '\n' +
                  'local Boost=' + module('src/shared/GeneBoost.luau') + '\n' +
                  'script={Parent={RarityCurve=Curve,GeneBoost=Boost}}' + '\n' +
                  'local Index=(function()' + '\n' + broken + '\n' + 'end)()' + '\n' + LOGIC)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'mutant.luau'
            path.write_text(script, encoding='utf-8')
            result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        assert result.returncode != 0, 'mutant survived: ' + label
    print('Mutants passed: %d broken versions of the rules were all caught' % len(cases))


def check_wiring():
    """Source-level wiring (Roblox services cannot run in plain Luau)."""
    config = read('src/shared/Config.luau')
    assert re.search(r'^\s*PatternColourIndexEnabled = false,', config, re.M), 'Config.PatternColourIndexEnabled must ship false'
    profiles = read('tools/release_profiles.py')
    assert '_flag_off("PatternColourIndexEnabled"' in profiles, 'the default profile pins the flag off'
    assert 'Rule("PatternColourIndexEnabled", "set", True' in profiles, 'the playtest profile turns it on (docs/157)'
    assert '("PatternColourIndexEnabled",' in profiles, 'the rehearsal list has it'
    # Bootstrap: one hook on the collection screen, nothing else; the byte ratchet is respected by verify_server_module_size
    boot = read('src/client/Bootstrap.client.luau')
    assert boot.count('require(script.Parent.IndexTabs).mount(open)') == 1, 'one hook in the collection branch'
    branch = boot[boot.index('elseif name=="collection" then'):]
    assert branch.index('IndexTabs).mount(open)') < branch.index('local unlocked=0'), 'the hook comes before the Dino Index is built, so Patterns / Colours never pay for it'
    assert 'IndexTabs' not in boot.replace('require(script.Parent.IndexTabs).mount(open)', ''), 'Bootstrap knows nothing else about the tabs'
    rail = read('src/client/FtueRail.luau')
    assert 'PatternColourIndexEnabled == true then require(script.Parent.IndexTabs).attachDot(buttons)' in rail, 'the dot hook is behind the flag'
    # the server passes the flag to the discovery log and sends ids only with it
    assert 'ProgressionRules.discover(profileValue,chest.genes,mutationId,Config.PatternColourIndexEnabled==true)' in read('src/server/ProfileEggs.luau')
    assert 'Config.PatternColourIndexEnabled == true' in read('src/server/ProfileFusion.luau')
    repo = read('src/server/ProfileRepository.luau')
    assert 'ProgressionRules.backfillDiscovered(profileValue, Config.PatternColourIndexEnabled == true)' in repo
    assert 'if Config.PatternColourIndexEnabled == true then discovery.ids = ProgressionRules.discoveryIds(profile) end' in repo, 'ids only with the flag'
    # the hatch ribbons
    hatch = read('src/client/HatchSequence.luau')
    assert 'NewFinds.ribbons(' in hatch and 'Config.PatternColourIndexEnabled' in hatch, 'the hatch reads the ribbon words from the shared rules, behind the flag'
    assert 'if #words == 0 then words = {"NEW!"} end' in hatch, 'flag off: still the old NEW! ribbon'
    # the old colour bonus line is replaced by the pips wording through ColourBonus.text (hatch card, Index card, Fusion and Dino details)
    bonus = read('src/shared/ColourBonus.luau')
    assert 'config.GeneBoostEnabled == true' in bonus and 'boost.dinoText' in bonus
    # no pattern or colour id is typed into the client modules; the tables are read from the config
    for path in ('src/client/IndexTabs.luau', 'src/client/PatternColourCards.luau', 'src/shared/PatternColourIndex.luau'):
        text = read(path)
        code = '\n'.join(line for line in text.split('\n') if not line.strip().startswith('--'))
        assert not re.search(r'"0\d_[a-z_]+"', code), path + ': a pattern id is typed in the code'
        for colour in ('"white"', '"teal"', '"violet"', '"black"'):
            assert colour not in code, path + ': a colour id is typed in the code'
    assert 'ProgressionConfig.EggPatterns' in read('src/client/IndexTabs.luau') and 'ProgressionConfig.EggColors' in read('src/client/IndexTabs.luau')
    # the shared rules are pure
    pure = read('src/shared/PatternColourIndex.luau')
    assert 'Instance.new' not in pure and 'game:GetService' not in pure and 'HttpService' not in pure, 'PatternColourIndex is pure'
    # no new saved field: the existing discovery log is reused
    rules = read('src/shared/ProgressionRules.luau')
    assert 'DiscoveredMaxPerKind=64' in rules and 'indexSeen' not in rules, 'still the one capped discovery log, no new saved field in the progression'
    # BD-1065: the dot's total is the ONE additive saved field, inside the existing settings (written only after a look, off with the flag)
    settings = read('src/shared/SettingsModel.luau')
    assert 'if s.indexSeen > 0 then out.indexSeen = s.indexSeen end' in settings, 'indexSeen is stored lazily: never in a profile that never looked'
    assert 'Settings.set("indexSeen", total)' in read('src/client/IndexTabs.luau') and 'indexSeen' not in read('src/client/FtueRail.luau')
    assert 'PatternColourIndexEnabled ~= true' in read('src/client/IndexTabs.luau'), 'IndexTabs does nothing with the flag off, so nothing is ever written'
    # asset slots: one per pattern id and the two tab icons, all unbound
    slots = read('src/shared/AssetSlots.luau')
    for row_id in re.findall(r'\{id="(0\d_[a-z_]+)"', read('src/shared/ProgressionConfig.luau')):
        assert re.search(r'^\s*pattern_%s = "",' % row_id, slots, re.M), 'AssetSlots.Images.pattern_' + row_id
    for name in ('index_tab_patterns', 'index_tab_colours'):
        assert re.search(r'^\s*%s = "",' % name, slots, re.M), name
    # close paths: nothing full-screen was added, the tabs sit left of X inside the header
    tabs = read('src/client/IndexTabs.luau')
    assert 'Active = true' not in tabs and tabs.count('Instance.new("TextButton")') == 1 and 'UDim2.new(1 / 3, -6, 1, 0)' in tabs, 'the only buttons are the three tabs inside the tab bar: no full-screen button or Active frame over the menu'
    assert "close.Size.X.Offset + 22" in tabs, 'the tab bar stops short of X'
    cards = read('src/client/PatternColourCards.luau')
    # BD-1065: a card is tappable. The ONE button per card sits inside the card (Parent = the card frame), so it can never cover X or the backdrop.
    assert cards.count('Instance.new("TextButton")') == 1 and 'hit.Size, hit.ZIndex, hit.Parent = UDim2.fromScale(1, 1), f.ZIndex + 8, f' in cards, 'one button per card, inside its own card'
    detail = read('src/client/PatternColourDetail.luau')
    assert detail.count('Instance.new("TextButton")') == 3, 'the detail has exactly the backdrop, X and OK'
    for needle in ('scrim.Activated:Connect(function() scrim:Destroy() end)', 'x.Activated:Connect(function() scrim:Destroy() end)', 'ok.Activated:Connect(function() scrim:Destroy() end)'):
        assert needle in detail, 'every way out of the detail: ' + needle
    assert 'UDim2.fromOffset(56, 56)' in detail and 'UDim2.fromOffset(140, 48)' in detail, 'X and OK are at least 44 px'
    assert 'Active = true' not in detail and 'TweenService' not in detail and 'Theme.animate' not in detail, 'no extra cover, no motion'
    assert 'Detail.open(body, tab, card, found, speciesName)' in tabs, 'IndexTabs opens the detail inside the screen body'
    assert 'TweenService' not in cards and 'Theme.animate' not in cards and 'TweenService' not in tabs, 'static: Reduce Motion needs no special case'
    print('Wiring passed: flag ships false and is on in the playtest profile only, one Bootstrap hook before the Dino Index is built, the server passes the flag and sends ids only with it, '
          'no typed ids, pure rules, asset slots for the 8 pattern icons and 2 tab icons, no full-screen control, no motion')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    check_wiring()
    run(args.runner, logic_script(), 'index_logic.luau')
    run(args.runner, bonus_script(), 'index_bonus.luau')
    run(args.runner, discovery_script(), 'index_discovery.luau')
    run(args.runner, smoke_script(), 'index_smoke.luau')
    mutants(args.runner)
