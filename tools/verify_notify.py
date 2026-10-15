"""Execute the pure notification queue (src/shared/NotifyQueue.luau, BD-066) with the pinned Luau
runtime and fake time: cap, priority, merge by key, info throttle, key gap, waiting overflow,
major cards held while a menu is open and bumping info cards, expiry, the hatch-batch summary and
the status-code copy table. Drawing (pooled cards, tweens) is Studio-only; see docs/80.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
local function texts(q) local t = {} for _, c in q.visible do table.insert(t, c.text) end return table.concat(t, ",") end

-- Cap and info throttle: three info cards need 3 s (one per 1.5 s), never more than 3 visible.
local q = Q.new()
for i = 1, 5 do assert(Q.push(q, 0, {text = "i" .. i, kind = "info"}) == "queued") end
Q.update(q, 0) assert(texts(q) == "i1", "one info card per 1.5 s")
Q.update(q, 1) assert(texts(q) == "i1")
Q.update(q, 1.5) assert(texts(q) == "i1,i2")
Q.update(q, 2.4) assert(texts(q) == "i1,i2", "i1 lasts 2.5 s")
Q.update(q, 2.6) assert(texts(q) == "i2", "i1 expired after 2.5 s")
Q.update(q, 3) Q.update(q, 4.5) assert(#q.visible <= 3)

-- Priority: warnings jump the info line and skip the info throttle.
q = Q.new()
Q.push(q, 0, {text = "a", kind = "info"}) Q.update(q, 0)
Q.push(q, 0.1, {text = "b", kind = "info"}) Q.push(q, 0.1, {text = "w", kind = "warning"})
Q.update(q, 0.1) assert(texts(q) == "a,w", "warning first, no info gap")

-- Merge by key: one card with a counter and a refreshed timer.
q = Q.new()
Q.push(q, 0, {text = "+5 Crystals", kind = "good", key = "crystals"}) Q.update(q, 0)
assert(Q.push(q, 2, {text = "+12 Crystals", kind = "good", key = "crystals"}) == "merged")
assert(#q.visible == 1 and q.visible[1].count == 2 and q.visible[1].text == "+12 Crystals" and q.visible[1].expiresAt == 5)
Q.update(q, 4) assert(#q.visible == 1, "timer refreshed")
-- Counters add up instead of replacing: "+5" then "+12" reads "+17 Crystals".
q = Q.new()
Q.push(q, 0, {text = "+5 Crystals", kind = "good", key = "crystals", amount = 5, format = "+%d Crystals"}) Q.update(q, 0)
Q.push(q, 1, {text = "+12 Crystals", kind = "good", key = "crystals", amount = 12, format = "+%d Crystals"})
assert(texts(q) == "+17 Crystals" and q.visible[1].count == 2)
-- Key gap: the same info key right after it expired is dropped; later it shows again.
q = Q.new()
Q.push(q, 0, {text = "Restock", key = "shop"}) Q.update(q, 0) Q.update(q, 2.6)
assert(#q.visible == 0 and Q.push(q, 3, {text = "Restock", key = "shop"}) == "dropped")
assert(Q.push(q, 6, {text = "Restock", key = "shop"}) == "queued")

-- Waiting overflow drops the lowest priority, oldest card, never a warning for an info.
q = Q.new()
Q.push(q, 0, {text = "w0", kind = "warning"})
for i = 1, 7 do Q.push(q, 0, {text = "i" .. i}) end
assert(#q.waiting == 8)
assert(Q.push(q, 0, {text = "w1", kind = "warning"}) == "queued" and #q.waiting == 8 and q.waiting[1].text == "w0")
for _, c in q.waiting do assert(c.text ~= "i1", "oldest info dropped") end
assert(Q.push(q, 0, {text = "i9"}) == "queued" and q.stats.dropped == 2)
for _, c in q.waiting do assert(c.text ~= "i2", "next oldest info dropped, newest kept") end

-- Major cards wait while a menu/hatch reveal is open, then bump the oldest info card.
q = Q.new()
Q.push(q, 0, {text = "i1"}) Q.update(q, 0)
Q.push(q, 0, {text = "w", kind = "warning"}) Q.update(q, 0)
Q.push(q, 1.5, {text = "i2"}) Q.update(q, 1.5)
assert(texts(q) == "i1,w,i2")
Q.push(q, 1.6, {text = "Level 5!", kind = "major"})
Q.update(q, 1.6, true) assert(not string.find(texts(q), "Level"), "majors wait while blocked")
Q.update(q, 1.7, false) assert(texts(q) == "w,i2,Level 5!", "major bumps oldest info")
-- Three warnings fill the stack: a major cannot bump them and waits.
q = Q.new()
for i = 1, 3 do Q.push(q, 0, {text = "w" .. i, kind = "warning"}) end Q.update(q, 0)
Q.push(q, 0, {text = "M", kind = "major"}) Q.update(q, 0) assert(#q.visible == 3 and #q.waiting == 1)
Q.update(q, 4) assert(texts(q) == "M", "shows after the warnings expire")
assert(Q.dismissTop(q) and #q.visible == 0 and not Q.dismissTop(q))
-- Bad input never shows.
assert(Q.push(q, 0, nil) == "dropped" and Q.push(q, 0, {text = ""}) == "dropped" and Q.push(q, 0, {text = 5}) == "dropped")
assert(Q.push(Q.new(), 0, {text = "x", kind = "weird"}) == "queued")

-- Hatch batch summary: one card, best find by rarity then Shiny/BIG.
local names = {"Common", "Uncommon", "Rare", "Epic", "Legendary"}
assert(Q.hatchSummary({{rarity = 1, name = "Compy"}}, names) == nil, "single egg: the reveal is enough")
local s = Q.hatchSummary({{rarity = 1, name = "Compy"}, {rarity = 3, name = "Triceratops"}, {rarity = 2, name = "Stegosaurus", shiny = true}, {failed = true}}, names)
assert(s.text == "3 dinos hatched" and s.body == "Best: Rare Triceratops" and s.kind == "good" and s.key == "hatch_summary" and s.tint == "Rare")
s = Q.hatchSummary({{rarity = 5, name = "Tyrannosaurus", big = true}, {rarity = 1, name = "Compy"}}, names)
assert(s.kind == "major" and s.body == "Best: BIG Legendary Tyrannosaurus")
s = Q.hatchSummary({{failed = true}, {failed = true}}, names)
assert(s.text == "0 dinos hatched" and s.body == "The cracked eggs crumbled")

-- Long copy is clipped at a word boundary so it fits the 440 px card (title 30, second line 44 characters).
assert(Q.clip("Short", 30) == "Short")
local long = Q.clip("Fusion is not available on this server yet", Q.MaxText)
assert(#long <= Q.MaxText and string.sub(long, -3) == "..." and not string.find(long, " %.%.%."), long)
q = Q.new()
Q.push(q, 0, {text = string.rep("word ", 20), body = string.rep("x", 100), kind = "warning"}) Q.update(q, 0)
assert(#q.visible[1].text <= Q.MaxText and #q.visible[1].body <= Q.MaxBody, "push clips title and body")
assert(Q.MaxVisible == 3, "never more than 3 cards")

-- Status codes become short copy; raw codes never reach the screen.
assert(Q.statusText("insufficient_crystals") == "Not enough Crystals" and Q.statusText("some_new_code") == "Something went wrong. Try again" and Q.statusText(nil) == "Something went wrong. Try again")
for code, text in Q.StatusText do assert(not string.find(text, "_") and #text <= 44, code) end
print("Notification queue checks passed: cap 3, priority, key merge, info throttle, key gap, overflow, held majors, bump, expiry, hatch summary, status copy")
'''


def script():
    return 'local Q=' + module('src/shared/NotifyQueue.luau') + '\n' + BODY


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'notify.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
