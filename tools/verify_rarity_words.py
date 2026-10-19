#!/usr/bin/env python3
"""BD-1120 (docs/202 R5): coloured rarity words everywhere a rarity is named.

One helper, Shared/RarityWord: RarityWord(tier) -> word, colour (the colour is Theme.RarityColors, docs/114 s5.2; this file fails on a colour literal in the helper
and on a second palette in ShopPreview). Mixed text goes through RarityWord.paint / set / paintLabel (RichText, whole words only, the rest escaped).
Checks:
  1. pure Luau tests of RarityWord with a stub palette read from docs/114 s5.2 (hex round trip, whole words, "Uncommon" is one word, "Rarer" is not "Rare", escaping),
  2. source guards (no colour literal in RarityWord, no second palette, the screens that name a rarity call it),
  3. the grep: every place in src/client that prints a tier word uses RarityWord, or is listed in tools/rarity_words_allow.json with a reason
     (a tier FILL already carries the colour; the white word stays),
  4. the geometry mock (tools/text_floor_smoke.luau): the REAL Toasts and EggsScreen paint the words, plain text stays plain,
  5. mutants: each old defect put back must fail a check.
NOT Studio evidence: it proves the words and colours that are asked for, not how the RichText draws.
Usage: python tools/verify_rarity_words.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rarity_word_sites as rs  # noqa: E402
import text_style_floors as tf  # noqa: E402


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def palette():
    """The six hex colours of docs/114 s5.2, in tier order."""
    doc = read('docs/114-handbook.md')
    block = doc[doc.index('### 5.2 Rarity'):doc.index('### 5.3')]
    pairs = re.findall(r'(Common|Uncommon|Rare|Epic|Legendary|Mythic) #([0-9A-Fa-f]{6})', block)
    assert [p[0] for p in pairs] == ['Common', 'Uncommon', 'Rare', 'Epic', 'Legendary', 'Mythic'], 'docs/114 s5.2 lost a tier colour: %s' % pairs
    return [p[1].upper() for p in pairs]


PURE = r'''
local hexes = {@HEXES@}
local colours = {}
for i, h in hexes do
    colours[i] = {R = tonumber(string.sub(h, 1, 2), 16) / 255, G = tonumber(string.sub(h, 3, 4), 16) / 255, B = tonumber(string.sub(h, 5, 6), 16) / 255}
end
local fakeScript = {Parent = {UITheme = {RarityColors = colours}}}
local function require(x) return x end
local RW = (function(script)
@SRC@
end)(fakeScript)

assert(#RW.Names == 6 and RW.Names[1] == "Common" and RW.Names[2] == "Uncommon" and RW.Names[6] == "Mythic", "six tiers")
-- index: rank or name, any case; nothing else
assert(RW.index(1) == 1 and RW.index(5) == 5 and RW.index(6) == 6 and RW.index(0) == nil and RW.index(7) == nil and RW.index(nil) == nil and RW.index(2.7) == 2, "index by rank")
assert(RW.index("Rare") == 3 and RW.index("rare") == 3 and RW.index("LEGENDARY") == 5 and RW.index("Secret") == nil and RW.index("") == nil, "index by name")
-- the word and its colour (the colour is the palette entry itself, never a copy)
for i, name in RW.Names do
    local word, colour = RW.get(i)
    assert(word == name and colour == colours[i], "get(" .. i .. ")")
    local word2, colour2 = RW(name)
    assert(word2 == name and colour2 == colours[i], "callable: RarityWord(" .. name .. ")")
    assert(RW.hex(i) == "#" .. hexes[i], "hex(" .. i .. ") is " .. RW.hex(i) .. ", the palette says #" .. hexes[i])
    assert(RW.rich(i) == '<font color="#' .. hexes[i] .. '">' .. name .. '</font>', "rich(" .. i .. ")")
end
local unknownWord, unknownColour = RW.get("Secret")
assert(unknownWord == "Common" and unknownColour == colours[1], "an unknown tier answers Common")
-- has / paint: whole words only
assert(RW.has("Best: Legendary Compy") and RW.has("Common") and RW.has("Uncommon dino") and RW.has("x Epic.") and RW.has("Mythic!"), "has finds a tier word")
assert(not RW.has("Rarer potions show up less often.") and not RW.has("Uncommonly good") and not RW.has("Epicenter") and not RW.has("common") and not RW.has(""), "has ignores part-words and lower case")
local function rich(i) return RW.rich(i) end
assert(RW.paint("Best: Legendary Compy") == "Best: " .. rich(5) .. " Compy", "paint one word")
assert(RW.paint("Uncommon") == rich(2), "Uncommon is ONE word, never Common inside it")
assert(RW.paint("Common, Uncommon & Rare") == rich(1) .. ", " .. rich(2) .. " &amp; " .. rich(3), "paint three words, escape &")
assert(RW.paint("Rarer potions") == "Rarer potions" and RW.paint("Rare.") == rich(3) .. ".", "Rarer is not Rare, punctuation stays")
assert(RW.paint("<b>Rare</b> \"x\" 'y'") == "&lt;b&gt;" .. rich(3) .. "&lt;/b&gt; &quot;x&quot; &apos;y&apos;", "markup in the text is escaped, never becomes markup")
assert(RW.paint("Epic Epic") == rich(4) .. " " .. rich(4) and RW.paint("") == "", "repeats and empty")
assert(RW.paint("Mythic find") == rich(6) .. " find", "Mythic")
-- set / paintLabel / apply on a label
local label = {Text = "", RichText = false, TextColor3 = false}
RW.set(label, "A Legendary Compy")
assert(label.RichText == true and label.Text == "A " .. rich(5) .. " Compy", "set paints a label with a tier word")
RW.set(label, "Follow the glow")
assert(label.RichText == false and label.Text == "Follow the glow", "set leaves a plain text plain (and turns RichText off again)")
label.Text = "Auto-open: Common, Rare"
RW.paintLabel(label)
assert(label.RichText == true and label.Text == "Auto-open: " .. rich(1) .. ", " .. rich(3), "paintLabel uses the text already on the label")
RW.apply(label, 4)
assert(label.RichText == false and label.Text == "Epic" and label.TextColor3 == colours[4], "apply: the word alone, in its colour")
colours[6] = {R = 0.5, G = 0, B = 1}
assert(RW.hex(6) == "#8000FF", "hex rounds to the nearest byte (0.5 is 128), got " .. RW.hex(6))
print("RarityWord passed: six tiers, colour = palette entry, whole words, Uncommon is one word, Rarer is not Rare, text escaped")
'''


def pure(runner, replacements=None):
    source = read('src/shared/RarityWord.luau').replace('--!strict', '')
    for old, new in replacements or []:
        assert old in source, 'mutant target missing in RarityWord: ' + old
        source = source.replace(old, new)
    hexes = ', '.join('"%s"' % h for h in palette())
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / 'rarity_word.luau'
        f.write_text(PURE.replace('@HEXES@', hexes).replace('@SRC@', source), encoding='utf-8')
        r = subprocess.run([runner, str(f)], capture_output=True, text=True, encoding='utf-8')
        return r.returncode == 0 and 'passed' in r.stdout, r.stdout + r.stderr


PURE_MUTANTS = {
    'Uncommon is painted as Common inside it': [('if not string.find(before, "^%a$") and not string.find(after, "^%a$") then best = name end', 'best = name')],
    'a part-word counts as a tier word (Rarer is painted)': [('"%f[%a]" .. name .. "%f[%A]"', 'name')],
    'the text is not escaped': [('table.insert(out, escape(string.sub(text, i, i)))', 'table.insert(out, string.sub(text, i, i))')],
    'RichText stays on for a plain text': [('        label.RichText = false\n        label.Text = text\n    end\nend', '        label.Text = text\n    end\nend')],
    'an unknown tier answers nothing': [('local rank = RarityWord.index(tier) or 1\n    return RarityWord.Names[rank], (palette())[rank]', 'local rank = RarityWord.index(tier) or 99\n    return RarityWord.Names[rank], (palette())[rank]')],
    'the hex is rounded down': [('return math.clamp(math.floor(v * 255 + 0.5), 0, 255)', 'return math.clamp(math.floor(v * 255), 0, 255)')],
    'apply forgets the colour': [('    label.TextColor3 = colour\n', '')],
    'the callable helper is gone': [('setmetatable(RarityWord, {__call = function(_, tier: any): (string, Color3) return RarityWord.get(tier) end})', '')],
}

SMOKE_MUTANTS = {
    'toasts show the plain text again': {
        'Toasts': [('RarityWord.set(slot.title,entry.text) RarityWord.set(slot.detail,entry.body or "")', 'slot.title.Text,slot.detail.Text=entry.text,entry.body or ""')],
    },
    'the toast detail line is not painted': {
        'Toasts': [('RarityWord.set(slot.detail,entry.body or "")', 'slot.detail.Text=entry.body or ""')],
    },
    'the auto-open line of the Eggs screen is not painted': {
        'EggsScreen': [('require(Shared.RarityWord).paintLabel(autoLine)', '')],
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    ok, out = pure(args.runner)
    print(out, end='')
    if not ok:
        raise SystemExit('RarityWord tests failed')
    # one colour source
    word = read('src/shared/RarityWord.luau')
    code = '\n'.join(l.split('--')[0] for l in word.splitlines())
    assert not re.search(r'Color3\.(fromRGB|new|fromHex)|#[0-9A-Fa-f]{6}\b|\{\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\}', code), 'RarityWord must not hold a colour: it reads Theme.RarityColors'
    assert 'Theme.RarityColors' in word or 'RarityColors' in word, 'RarityWord must read RarityColors'
    preview_code = '\n'.join(l.split('--')[0] for l in read('src/shared/ShopPreview.luau').splitlines())
    assert 'RarityColors' not in preview_code, 'ShopPreview must not hold a second rarity palette (BD-1120)'
    theme = read('src/shared/UITheme.luau')
    assert 'Theme.RarityColors = {' in theme and 'Config.SpeciesRarityNames' in theme, 'UITheme keeps the one palette (docs/114 s5.2, tools/verify_handbook.py checks the numbers)'
    # the sites
    allow = rs.load_allow()
    problems = rs.check(allow)
    for p in problems:
        print('FAIL', p)
    if problems:
        raise SystemExit('%d rarity-word site problem(s)' % len(problems))
    found = rs.sites()
    total = sum(len(v) for v in found.values())
    painted = sum(1 for v in found.values() for r in v if r[1])
    print('Rarity sites passed: %d places print a tier word in src/client, %d use RarityWord, %d are filled chips or builders listed with a reason' % (total, painted, total - painted))
    # the mock: the real Toasts and EggsScreen paint the words (part of the text-floor smoke)
    passed, out = tf.run_smoke(args.runner, None, [])
    if not passed or 'Rarity words ok' not in out:
        print(out[-1500:])
        raise SystemExit('the mock check of the coloured rarity words failed')
    print('Rarity words in the mock passed: Toasts (title and line), Eggs auto-open line, plain text stays plain')
    if args.no_mutants:
        return
    from concurrent.futures import ThreadPoolExecutor
    names = list(SMOKE_MUTANTS)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda n: tf.run_smoke(args.runner, SMOKE_MUTANTS[n], []), names))
    for name, (passed, _out) in zip(names, results):
        assert not passed, 'MUTANT SURVIVED (the mock did not notice): ' + name
        print('  mutant caught: ' + name)
    for name, replacements in PURE_MUTANTS.items():
        passed, _out = pure(args.runner, replacements)
        assert not passed, 'MUTANT SURVIVED (the RarityWord tests did not notice): ' + name
        print('  mutant caught: ' + name)
    # the site check itself, on synthetic files
    with tempfile.TemporaryDirectory() as d:
        client = Path(d) / 'src' / 'client'
        client.mkdir(parents=True)
        (client / 'A.luau').write_text('label(card, rarityNames[r], 1, 2, 3, 4, 20)\n', encoding='utf-8')
        (client / 'B.luau').write_text('local R = require(Shared.RarityWord)\nR.set(l, rarityNames[r])\n', encoding='utf-8')
        (client / 'C.luau').write_text('-- rarityNames[r] in a comment\nlocal x = 1\n', encoding='utf-8')
        found = rs.sites(d)
        assert 'src/client/A.luau' in found and 'src/client/B.luau' in found and 'src/client/C.luau' not in found, 'the scan finds code, not comments'
        assert rs.check({'unpainted': {}}, found), 'an unpainted site with no allowance fails'
        assert not rs.check({'unpainted': {'src/client/A.luau': {'count': 1, 'reason': 'x'}}}, found), 'an allowed site passes'
        assert rs.check({'unpainted': {'src/client/A.luau': {'count': 2, 'reason': 'x'}}}, found), 'a stale count fails'
        assert rs.check({'unpainted': {'src/client/B.luau': {'count': 1, 'reason': 'x'}, 'src/client/A.luau': {'count': 1, 'reason': 'x'}}}, found), 'an entry for a painted file fails'
    print('  site rules caught: unpainted site, stale count, entry for a painted file; comments ignored')
    print('Rarity words passed: %d mutants caught' % (len(SMOKE_MUTANTS) + len(PURE_MUTANTS)))


if __name__ == '__main__':
    main()
