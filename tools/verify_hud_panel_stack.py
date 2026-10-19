#!/usr/bin/env python3
"""BD-1095 (docs/197 pictures 347 and 348): the hub Goals panel and the Tasks panel must never draw over each other.

Studio round 5 at 500 x 465: opening Goals put its card over the Tasks pill, opening Tasks put its sheet over the Goals header, and the text was
unreadable. The rule (src/shared/HudPanelStack.luau, wired in GoalsPanel.luau and ObjectivesPanel.luau): one panel is open at a time, and a folded
panel that sits where the open one needs the room is hidden until the open one folds. Goals stays fold-only (BD-1074, docs/115): no tap-outside close.

This runs the REAL TouchLayout (the rects the game gives both panels) and the REAL HudPanelStack on many canvases, touch and mouse, and checks that no two
VISIBLE panels overlap in any state (Goals open, Tasks open, both folded). A probe proves the canvases do contain overlaps without the rule, and the
mutants (rule off, wrong open rect, never folding the other panel) must fail the check.
BD-1108 (docs/200 pictures 391, 393): an OPEN panel also keeps off the HUD rail. The open Goals card opens leftwards and lay over the right column of the
rail. HudPanelStack.clearRail moves an open panel under the rail (the rect HudV2.layout publishes as RailRect: the six-button rail at home, the two-button
rail in a run) when it would cover it, and leaves it where it was only when the canvas has no room under the rail (those canvases are listed in the output).
Not Studio evidence: nothing here is drawn. A Studio look at 500 x 465 and 848 x 423 is still needed (the P1 row added with this change).
Usage: python tools/verify_hud_panel_stack.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def wrapped(path, replacements=None):
    source = read(path)
    for old, new in replacements or []:
        assert old in source, 'mutant target missing in %s: %s' % (path, old)
        source = source.replace(old, new)
    return '(function()\n' + source + '\nend)()'


LUAU = r'''
local Mods = {}
local script = {Parent = {Config = "Config", PhoneScale = "PhoneScale", TouchLayout = "TouchLayout"}}
local require = function(name) return Mods[name] end
Rect = nil
typeof = function(v) return type(v) end
Mods.Config = @CONFIG@
Mods.PhoneScale = @PHONE@
Mods.TouchLayout = @TOUCH@
local Stack = @STACK@
local TouchLayout, Config = Mods.TouchLayout, Mods.Config

-- ---- the protocol on the shared attribute
local cur = ""
cur = Stack.after(cur, "goals", true) assert(cur == "goals")
assert(Stack.mustFold(cur, "tasks") and not Stack.mustFold(cur, "goals"), "Tasks folds when Goals is the open one")
cur = Stack.after(cur, "tasks", true) assert(cur == "tasks" and Stack.mustFold(cur, "goals") and not Stack.mustFold(cur, "tasks"), "the panel touched last stays open")
assert(Stack.after("tasks", "goals", false) == "tasks", "folding Goals never clears what Tasks set")
assert(Stack.after("tasks", "tasks", false) == "" and Stack.after("", "goals", false) == "", "folding the open panel clears it")
assert(not Stack.mustFold("", "goals") and not Stack.mustFold(nil, "tasks") and not Stack.mustFold(5, "tasks"), "nothing open (or junk): nothing folds")
assert(not Stack.hidden("tasks", "", {x = 0, y = 0, w = 1, h = 1}, {x = 0, y = 0, w = 9, h = 9}) and not Stack.hidden("tasks", "tasks", {x = 0, y = 0, w = 1, h = 1}, {x = 0, y = 0, w = 9, h = 9}), "the open panel itself is never hidden")
assert(not Stack.hidden("tasks", "goals", nil, {x = 0, y = 0, w = 9, h = 9}) and not Stack.hidden("tasks", "goals", {x = 0, y = 0, w = 1, h = 1}, nil), "an unknown rect hides nothing")
assert(Stack.hidden("tasks", "goals", {x = 0, y = 0, w = 5, h = 5}, {x = 4, y = 4, w = 9, h = 9}) and not Stack.hidden("tasks", "goals", {x = 0, y = 0, w = 4, h = 4}, {x = 4, y = 4, w = 9, h = 9}), "touching edges do not overlap")

-- ---- geometry on many canvases
local function inside(r, w, h) return r.x >= -1e-6 and r.y >= -1e-6 and r.x + r.w <= w + 1e-6 and r.y + r.h <= h + 1e-6 end
local function describe(r) return string.format("%d,%d %dx%d", r.x + .5, r.y + .5, r.w + .5, r.h + .5) end
local canvases = {
 {500, 465}, {500, 400}, {500, 300}, {516, 481}, {498, 463}, {667, 375}, {667, 339}, {667, 317}, {800, 360}, {836, 390}, {844, 390}, {844, 354}, {848, 423}, {848, 481}, {740, 340}, {640, 360}, {732, 412}, {915, 412},
 {760, 360}, {800, 302}, {800, 600}, {1024, 768}, {1156, 793}, {1156, 841}, {1280, 720}, {1366, 768}, {1445, 841}, {1920, 1080}, {2400, 1080},
}
-- the two rails the layout gets: HUB = the six buttons at home, RUN = POTIONS and SETTINGS only (RailRun, BD-1105)
local RAILS = {{name = "hub", count = 6}, {name = "run", count = 2}}
local probeOverlaps, states, checked, railProbe, railMoved = 0, 0, 0, 0, 0
local noRoom = {}
local function railOf(layout) local r = layout.rail return {x = r.x, y = r.y, w = r.w * r.scale, h = r.h * r.scale} end -- what HudV2.layout publishes as RailRect
local function visibleRects(layout)
    local goalsFolded = if layout.touch then layout.goals else layout.goalsPanel
    -- what GoalsPanel.luau really draws when open: 260 design px wide and 214 tall at the header's scale, the right edge where the folded header's right edge is
    local goalsOpen = layout.goalsPanelOpen
    if layout.touch then
        local s = goalsFolded.h / 44
        goalsOpen = {x = goalsFolded.x + goalsFolded.w - 260 * s, y = goalsFolded.y, w = 260 * s, h = 214 * s}
    end
    local derived = Stack.goalsOpen(goalsFolded) -- the rule the panels share must say the same
    assert(math.abs(derived.x - goalsOpen.x) < 1e-6 and math.abs(derived.y - goalsOpen.y) < 1e-6 and math.abs(derived.h - goalsOpen.h) < 1e-6 and math.abs(derived.w - goalsOpen.w) < 1e-6,
        string.format("Stack.goalsOpen %s is not the open Goals card %s", describe(derived), describe(goalsOpen)))
    return goalsFolded, goalsOpen, layout.objectives, layout.objectivesOpen
end
local function moved(r, dy) return {x = r.x, y = r.y + dy, w = r.w, h = r.h} end
for _, v in canvases do
    for _, touch in {true, false} do
        for _, railKind in RAILS do
            local w, h = v[1], v[2]
            local layout = TouchLayout.compute({width = w, height = h, touch = touch, navCount = railKind.count, goals = true, objectives = true})
            local goalsFolded, goalsOpen0, tasksFolded, tasksOpen0 = visibleRects(layout)
            local rail = railOf(layout)
            local label = string.format("%dx%d %s, %s rail", w, h, if layout.touch then "phone layout" else "desktop layout", railKind.name)
            assert(goalsFolded and goalsOpen0 and tasksFolded and tasksOpen0, label .. ": the layout gives all four rects")
            -- state A: nothing open (the layout keeps the folded pieces apart from each other and from the rail: the existing guarantee)
            assert(not Stack.overlaps(goalsFolded, tasksFolded), label .. ": the folded Goals header and the folded Tasks pill overlap")
            assert(not Stack.overlaps(goalsFolded, rail) and not Stack.overlaps(tasksFolded, rail), label .. ": a folded panel lies over the rail")
            -- BD-1108: an open panel opens under the rail when it would cover it (what GoalsPanel / ObjectivesPanel do with the same rule)
            local goalsDy, goalsClear = Stack.clearRail(goalsOpen0, rail, h)
            local tasksDy, tasksClear = Stack.clearRail(tasksOpen0, rail, h)
            local goalsOpen, tasksOpen = moved(goalsOpen0, goalsDy), moved(tasksOpen0, tasksDy)
            if Stack.overlaps(goalsOpen0, rail) or Stack.overlaps(tasksOpen0, rail) then railProbe += 1 end -- what the player saw without the rule
            if goalsDy > 0 or tasksDy > 0 then railMoved += 1 end
            for _, entry in {{"Goals", goalsOpen0, goalsOpen, goalsDy, goalsClear}, {"Tasks", tasksOpen0, tasksOpen, tasksDy, tasksClear}} do
                local name, before, after, dy, clear = entry[1], entry[2], entry[3], entry[4], entry[5]
                if clear then
                    assert(not Stack.overlaps(after, rail), string.format("%s: the open %s panel %s still lies over the rail %s", label, name, describe(after), describe(rail)))
                    if dy > 0 then assert(after.y + after.h <= h + 1e-6, string.format("%s: the open %s panel %s was moved off the bottom of the canvas", label, name, describe(after))) end
                else
                    -- no room under the rail: it stays where it was, and that really is a canvas without room (rail bottom + gap + panel taller than the canvas)
                    assert(dy == 0 and Stack.overlaps(before, rail), label .. ": a panel with no room must stay put")
                    assert(rail.y + rail.h + Stack.RailGap + before.h > h - Stack.RailGap - 1e-6, string.format("%s: the %s panel was left over the rail although there is room under it", label, name))
                    table.insert(noRoom, label .. " " .. name)
                end
            end
            -- state B: Goals open, state C: Tasks open
            for _, openName in {"goals", "tasks"} do
                states += 1
                local openRect, other = if openName == "goals" then goalsOpen else tasksOpen, if openName == "goals" then tasksFolded else goalsFolded
                local otherName = if openName == "goals" then "tasks" else "goals"
                if Stack.overlaps(if openName == "goals" then goalsOpen0 else tasksOpen0, other) then probeOverlaps += 1 end -- what the player saw without the rule
                local hiddenOther = Stack.hidden(otherName, openName, other, openRect)
                local shown = {{name = openName .. " (open)", r = openRect}}
                if not hiddenOther then table.insert(shown, {name = otherName .. " (folded)", r = other}) end
                for i = 1, #shown do
                    for j = i + 1, #shown do
                        assert(not Stack.overlaps(shown[i].r, shown[j].r), string.format("%s: %s %s is drawn over %s %s", label, shown[i].name, describe(shown[i].r), shown[j].name, describe(shown[j].r)))
                    end
                end
                checked += 1
            end
            -- the open panels themselves stay readable: a Goals card and a Tasks sheet that fit the canvas (reported, not asserted for the tiniest windows)
            if w >= 640 then
                assert(inside(goalsOpen, w, h) or goalsOpen.y + goalsOpen.h > h, label .. ": the open Goals card leaves the canvas sideways " .. describe(goalsOpen))
            end
        end
    end
end
assert(probeOverlaps > 0, "probe lost sensitivity: without the rule no canvas has an open panel over the other one")
assert(railProbe > 0 and railMoved > 0, "probe lost sensitivity: without the rail rule no canvas has an open panel over the rail")
table.sort(noRoom)
print(string.format("Hud panel stack passed: %d states on %d canvases x 2 rails (touch and mouse; six-button rail at home, two-button rail in a run); without the stack rule %d of them draw one panel over the other, without the rail rule %d layouts have an open panel over the rail, %d of those open under it; no room under the rail (left where it was): %d (%s)",
    checked, #canvases * 2, probeOverlaps, railProbe, railMoved, #noRoom, table.concat(noRoom, "; ")))
'''


def build_script(stack_replacements=None):
    source = LUAU
    source = source.replace('@CONFIG@', wrapped('src/shared/Config.luau'))
    source = source.replace('@PHONE@', wrapped('src/shared/PhoneScale.luau'))
    source = source.replace('@TOUCH@', wrapped('src/shared/TouchLayout.luau'))
    source = source.replace('@STACK@', wrapped('src/shared/HudPanelStack.luau', stack_replacements))
    return source


def run(runner, source):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'hud_panel_stack.luau'
        path.write_text(source, encoding='utf-8')
        return subprocess.run([runner, str(path)], capture_output=True, text=True, encoding='utf-8')


MUTANTS = {
    'the rule never hides a folded panel (both can be drawn over each other)': [
        ('    return overlaps(own, otherOpen)', '    return false')],
    'the Goals open rect is only as wide as its folded header': [
        ('    local w = G.w * s', '    local w = folded.w')],
    'the Goals open card is as short as its header': [
        ('h = TouchLayout.GOALS_OPEN_H * s}', 'h = folded.h}')],
    'a panel that is the open one hides itself': [
        ('current == panel or own == nil', 'own == nil')],
    # BD-1108: the open panel keeps off the rail
    'an open panel never moves off the rail (the old behaviour, pictures 391 and 393)': [
        ('    local dy = rail.y + rail.h + Stack.RailGap - open.y', '    local dy = 0')],
    'an open panel moves to the top of the rail, not under it': [
        ('    local dy = rail.y + rail.h + Stack.RailGap - open.y', '    local dy = rail.y - open.y + 1')],
    'an open panel moves under the rail even when it then leaves the canvas': [
        ('    if dy > 0 and open.y + dy + open.h <= canvasH - Stack.RailGap then return dy, true end', '    if dy > 0 then return dy, true end')],
    'the rail rule ignores the rail (it moves every open panel)': [
        ('    if rail == nil or not overlaps(open, rail) then return 0, true end', '    if rail == nil then return 0, true end')],
    'the rail rule gives up when there is room (it reports no room)': [
        ('    if dy > 0 and open.y + dy + open.h <= canvasH - Stack.RailGap then return dy, true end', '    if dy > 0 and open.y + dy + open.h <= 0 then return dy, true end')],
}


def static_checks():
    stack = read('src/shared/HudPanelStack.luau')
    for banned in ('Instance.new', 'game:GetService', 'workspace', 'os.clock', 'task.'):
        assert banned not in stack, 'HudPanelStack stays pure: ' + banned
    goals = read('src/client/GoalsPanel.luau')
    tasks = read('src/client/ObjectivesPanel.luau')
    for name, text, who in (('GoalsPanel', goals, 'Goals'), ('ObjectivesPanel', tasks, 'Tasks')):
        assert 'HudPanelStack' in text, name + ': does not use HudPanelStack'
        assert 'Stack.after(gui:GetAttribute(Stack.Attribute), Stack.%s,' % who in text, name + ': opening / folding does not set the shared attribute'
        assert 'GetAttributeChangedSignal(Stack.Attribute)' in text and 'Stack.mustFold(' in text, name + ': does not fold when the other panel opens'
        assert 'Stack.hidden(' in text, name + ': does not hide when the other panel needs its spot'
    # BD-1108: both open panels keep off the rail (the rect HudV2 publishes), and the Tasks panel hides under the REAL open Goals rect
    assert 'Stack.clearRail(' in goals and 'GetAttribute("RailRect")' in goals, 'GoalsPanel: the open card does not keep off the rail (BD-1108)'
    assert 'Stack.clearRail(' in tasks and 'GetAttribute("RailRect")' in tasks, 'ObjectivesPanel: the open sheet does not keep off the rail (BD-1108)'
    assert 'SetAttribute("GoalsOpenRect"' in goals and 'GetAttribute("GoalsOpenRect")' in tasks, 'the Goals panel publishes where its open card really is and the Tasks panel reads it'
    assert 'SetAttribute("RailRect"' in read('src/client/HudV2.luau'), 'HudV2.layout publishes the rail rect (one rect for the toasts and the panels)'
    assert 'SetAttribute("GoalsFoldedRect"' in goals and 'GetAttribute("GoalsFoldedRect")' in tasks, 'the Goals panel publishes its folded rect and the Tasks panel reads it'
    assert 'ObjectivesOpenRect' in goals, 'the Goals panel reads the open Tasks rect'
    # BD-1074: Goals stays fold-only. No tap-outside close, no catcher.
    for banned in ('UserInputService', 'InputBegan', 'InputEnded', 'ModalScrim'):
        assert banned not in goals, 'GoalsPanel must stay fold-only (BD-1074): ' + banned


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    static_checks()
    result = run(args.runner, build_script())
    print(result.stdout, end='')
    if result.returncode != 0 or 'passed' not in result.stdout:
        print(result.stderr)
        sys.exit(result.returncode or 1)
    if not args.no_mutants:
        for name, replacements in MUTANTS.items():
            outcome = run(args.runner, build_script(replacements))
            assert outcome.returncode != 0, 'MUTANT SURVIVED (the check did not notice): ' + name
            print('  mutant caught: ' + name)
    print('Hud panel stack: static wiring ok, %d mutants caught' % (0 if args.no_mutants else len(MUTANTS)))


if __name__ == '__main__':
    main()
