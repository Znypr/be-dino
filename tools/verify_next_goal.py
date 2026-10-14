"""Execute the pure next-goal HUD logic (src/shared/NextGoal.luau) and the pure helpers of
src/shared/Sfx.luau with the pinned Luau runtime. Covers fusion-progress selection, the level-XP
fallback, deterministic ties, placeholder-id safety (no-op) and throttling/pooling math.
Roblox Instances are not executed here; Studio/phone checks are tracked in docs/62.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
local function dino(species, pattern, stage, locked)
 return {speciesId = species, stage = stage or "base", locked = locked, genes = {patternId = pattern}}
end
local function many(n, species, pattern, stage)
 local t = {} for i = 1, n do table.insert(t, dino(species, pattern, stage)) end return t
end
local function join(...) local out = {} for _, list in {...} do for _, d in list do table.insert(out, d) end end return out end
local function opts(dinos) return {dinos = dinos, level = 3, xp = 450, perLevel = 100, maxLevel = 60,
 speciesName = function(id) return id == "compy" and "Compy" or id end,
 patternName = function(id) return id == "06_wavy_stripes" and "Wavy" or id end} end

-- Best fusion progress across species + pattern wins.
local goal = Goal.pick(opts(join(many(9, "compy", "06_wavy_stripes"), many(4, "compy", "03_round_spots"), many(2, "rex", "06_wavy_stripes"))))
assert(goal.kind == "fusion" and goal.text == "Gold: 9/50 Compy Wavy", goal.text)
assert(math.abs(goal.fraction - 9 / 50) < 1e-9)
-- A higher tier with a higher fraction wins (2/3 Diamond beats 9/50 Gold).
goal = Goal.pick(opts(join(many(9, "compy", "06_wavy_stripes"), many(2, "rex", "03_round_spots", "emerald"))))
assert(goal.text == "Diamond: 2/3 rex 03_round_spots", goal.text)
-- Ready recipes win and say so; the count is capped at the recipe.
goal = Goal.pick(opts(join(many(60, "compy", "06_wavy_stripes"), many(2, "rex", "03_round_spots", "emerald"))))
assert(goal.ready == true and goal.text == "Gold ready: fuse Compy Wavy", goal.text)
-- Locked dinos do not count; diamonds have no next stage -> level fallback.
goal = Goal.pick(opts({dino("compy", "06_wavy_stripes", "base", true), dino("compy", "06_wavy_stripes", "diamond")}))
assert(goal.kind == "level", "nothing eligible -> level fallback")
-- Fallback when the fusion list is unavailable (nil) or empty.
assert(Goal.pick(opts(nil)).text == "Level 3: 50/500 XP")
assert(Goal.pick(opts({})).text == "Level 3: 50/500 XP")
assert(Goal.level({xp = 0}).text == "Level 1: 0/100 XP")
assert(Goal.level({xp = 10 ^ 9, level = 60, maxLevel = 60}).fraction == 1)
assert(Goal.level({xp = "bad"}).fraction == 0)
-- Deterministic: reversed input gives the same text; garbage entries are ignored.
local mixed = join({5, "x", {}}, many(3, "compy", "06_wavy_stripes"), many(3, "rex", "06_wavy_stripes"))
local reversed = {} for i = #mixed, 1, -1 do table.insert(reversed, mixed[i]) end
assert(Goal.pick(opts(mixed)).text == Goal.pick(opts(reversed)).text)

-- Sfx pure helpers: placeholder ids are inert and never invented.
local required = {"hatch_crack","hatch_common","hatch_rare","hatch_legendary","shiny_bang","big_thud","pickup","run_start","run_end","shop_buy","shop_refresh","weather_start","level_up","fusion_reveal","ui_click"}
for _, name in required do assert(Sfx.Sounds[name], name) end
for name, entry in Sfx.Sounds do
 assert(entry.id == "" or Sfx.normalizeId(entry.id) ~= nil, name .. " must be empty or a valid rbxassetid (never invented: only uploaded ids)")
 assert(entry.volume > 0 and entry.volume <= 1 and entry.rate > 0 and entry.gap >= 0, name)
 if entry.id == "" then assert(Sfx.play(name) == false, "empty id must be a no-op") end
end
for _, name in {"hatch_crack","hatch_common","hatch_rare","hatch_legendary","shiny_bang","big_thud","pickup","pickup_hi","pickup_lo","run_start","run_end","shop_buy","shop_refresh","weather_start","level_up","fusion_reveal","ui_click"} do
 assert(Sfx.normalizeId(Sfx.Sounds[name].id) ~= nil, name .. ": the uploaded sound pack must be bound (2026-10-15)")
end
assert(Sfx.Sounds.hatch_rattle.id == "" and Sfx.Sounds.hatch_burst.id == "", "no sound exists yet for the rattle and burst cues")
assert(Sfx.play("not_a_sound") == false)
assert(Sfx.normalizeId("") == nil and Sfx.normalizeId("rbxassetid://") == nil and Sfx.normalizeId("abc") == nil)
assert(Sfx.normalizeId(0) == nil and Sfx.normalizeId(1.5) == nil and Sfx.normalizeId(nil) == nil and Sfx.normalizeId({}) == nil)
assert(Sfx.normalizeId("rbxassetid://123") == "rbxassetid://123" and Sfx.normalizeId("123") == "rbxassetid://123" and Sfx.normalizeId(123) == "rbxassetid://123")
assert(Sfx.normalizeId("rbxassetid://0") == nil)
local e = {gap = .1}
assert(not Sfx.throttled(e, nil, 0) and Sfx.throttled(e, 0, .05) and not Sfx.throttled(e, 0, .1) and Sfx.throttled(nil, 0, 5))
local slot = 0 local seen = {} for _ = 1, 7 do slot = Sfx.nextSlot(slot, 3) seen[slot] = true end
assert(seen[1] and seen[2] and seen[3] and not seen[4] and slot == 1)
assert(Sfx.hatchName(1) == "hatch_common" and Sfx.hatchName(2) == "hatch_common" and Sfx.hatchName(3) == "hatch_rare" and Sfx.hatchName(4) == "hatch_legendary" and Sfx.hatchName(5) == "hatch_legendary" and Sfx.hatchName(nil) == "hatch_common")
print("Next goal and Sfx helper checks passed")
'''


def script():
    return ('local Goal=' + module('src/shared/NextGoal.luau') + '\n'
            + 'local Sfx=' + module('src/shared/Sfx.luau') + '\n' + BODY)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'next_goal.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
