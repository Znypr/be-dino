"""BD-075 mini objectives panel (docs/66 section 18): offline verifier in pinned Luau.

Static (python): flag-off identity of the client wiring (ObjectivesPanel is only required behind Config.ObjectivesEnabled, has no top-level
side effect, asks the server only inside one function, Bootstrap publishes the panel rects only under the flag), the client never computes a
reward, text >= 14 px and buttons >= 44 px, existing UI parts only (no asset ids, no image labels, the registered "trophy" icon).

BD-561 (docs/109 section 9): four OPTIONAL icons (objective_chevron, objective_arrow, notify_crystal, notify_star), each behind an empty-id gate. Static: the
slots exist and are empty in source, the panel creates icons only through one gated helper. Luau: the pure geometry (fitWords, wrapLines, headerLayout,
prizeLayout) and the REAL panel with the ids empty (the Instance tree and every number identical to a panel without the feature, whatever else is in
Theme.ImageIds) and with fake ids (icons in their documented spots, no overlap, text inside its box, whole-word cuts) on desktop, 836 x 390, 667 x 375
and at the 190 / 220 / 250 / 300 px pills.

Luau (real modules): the pure ObjectivePanelRules (which 3 rows, T8 versus the Goals PLAY line, the folded line, "New tasks soon" words,
claim answers, token reuse, docs/72 copy rules on every string it can produce) and the REAL src/client/ObjectivesPanel.luau executed against a
small mock of the Roblox GUI classes and a fake ObjectiveAction remote fed by the REAL ObjectiveRules view: folded and open states, the CLAIM
button only on a finished task, the claim request {action="claim", id, token}, the waiting state, a lost answer retried with the SAME token,
a definite answer freeing the id, and zero remote calls while the panel is not shown. Offline only: no Studio, no real GUI, no phone.

  python tools/verify_objectives_panel.py --runner C:/path/to/luau.exe
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import release_profiles  # noqa: E402


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def code_only(text: str) -> str:
    """Luau source without -- comments (a comment may name a module it does not use)."""
    return re.sub(r'--.*$', '', text, flags=re.M)


def module(path: str) -> str:
    return '(function()\n' + read(path) + '\nend)()'


def static_errors() -> list[str]:
    errors: list[str] = []
    entries = release_profiles.config_entries(read('src/shared/Config.luau'))
    found = entries.get('ObjectivesEnabled')
    if not found or found[-1][1] is not False:
        errors.append('Config.ObjectivesEnabled must stay false in source (the panel is behind it)')

    panel = code_only(read('src/client/ObjectivesPanel.luau'))
    goal_hud = read('src/client/GoalHud.luau')
    boot = read('src/client/Bootstrap.client.luau')
    layout = read('src/shared/TouchLayout.luau')

    # --- flag-off identity -------------------------------------------------------------------------------------------------------------
    gate = re.search(r'if Config\.ObjectivesEnabled==true then[^\n]*\n(.*?)\n    end\n', goal_hud, re.S)
    if not gate or 'require(script.Parent.ObjectivesPanel)' not in gate.group(1) or 'objectives.attach(gui,goalHUD)' not in gate.group(1):
        errors.append('GoalHud must require and attach ObjectivesPanel only inside `if Config.ObjectivesEnabled==true then`')
    if len(re.findall(r'require\(script\.Parent\.ObjectivesPanel\)', goal_hud)) != 1:
        errors.append('GoalHud: exactly one require of ObjectivesPanel')
    for path in sorted((ROOT / 'src').rglob('*.luau')):
        rel = path.relative_to(ROOT).as_posix()
        if rel in ('src/client/ObjectivesPanel.luau', 'src/client/GoalHud.luau', 'src/client/ObjectiveSeen.luau', 'src/client/FusionMenu.luau'):
            continue
        text = code_only(path.read_text(encoding='utf-8'))
        if 'ObjectivesPanel' in text or ('ObjectiveAction' in text and not rel.startswith('src/server/')):
            errors.append(f'{rel}: only GoalHud may reach ObjectivesPanel and only the panel may call ObjectiveAction on the client')
    # --- OB2 (docs/115): the one-time "seen" report. Only FusionMenu calls it, behind the flag; it sends one shape; flag off = silent ---------------
    seen = code_only(read('src/client/ObjectiveSeen.luau'))
    menu = code_only(read('src/client/FusionMenu.luau'))
    if 'ObjectiveAction' in menu or 'InvokeServer({action' in menu:
        errors.append('FusionMenu must not call ObjectiveAction itself (it calls ObjectiveSeen.report)')
    if len(re.findall(r'^.*ObjectiveSeen.*$', menu, re.M)) != 1 or             'if Config.ObjectivesEnabled == true then require(script.Parent.ObjectiveSeen).report("fusion_menu") end' not in menu:
        errors.append('FusionMenu: exactly one use of ObjectiveSeen, `if Config.ObjectivesEnabled == true then require(script.Parent.ObjectiveSeen).report("fusion_menu") end`')
    # two sends of one shape: the report and the single BD-616 retry after "not_opened"
    if re.findall(r'action\s*=\s*"([a-z_]+)"', seen) != ['seen', 'seen'] or seen.count('InvokeServer') != 2 or seen.count('{action = "seen", id = seenId}') != 2:
        errors.append('ObjectiveSeen: the only request is {action = "seen", id = seenId}')
    if not re.search(r'function ObjectiveSeen\.report\(seenId: string\)\n    if Config\.ObjectivesEnabled ~= true then return end\n', seen):
        errors.append('ObjectiveSeen.report must return first thing while the flag is not true (flag off sends nothing)')
    for number, line in enumerate(seen.splitlines(), 1):
        if line and not line[0].isspace() and not re.match(r'(local |function |return|end\b|--!)', line):
            errors.append(f'ObjectiveSeen.luau:{number}: top-level statement runs on require: {line[:60]}')
    if 'FindFirstChild("ObjectiveAction")' not in seen or 'WaitForChild' in seen:
        errors.append('ObjectiveSeen: the remote is looked up with FindFirstChild (it exists only while the server flag is on)')
    # no top-level statement besides local/function/return (nothing runs when the module is required)
    for number, line in enumerate(panel.splitlines(), 1):
        if line and not line[0].isspace() and not re.match(r'(local |function |return|end\b|--!)', line):
            errors.append(f'ObjectivesPanel.luau:{number}: top-level statement runs on require: {line[:60]}')
    if panel.count('InvokeServer') != 1 or panel.count('"ObjectiveAction"') != 1:
        errors.append('ObjectivesPanel: the server is called from exactly one place (call -> InvokeServer on ObjectiveAction)')
    if panel.count('call({action = "view"})') != 1 or panel.count('call({action = "claim", id = id, token = token})') != 1:
        errors.append('ObjectivesPanel: only {action="view"} and {action="claim", id, token} are ever sent')
    remote_fn = re.search(r'local function remote\(\).*?\n    end\n', panel, re.S)
    if not remote_fn or 'FindFirstChild("ObjectiveAction")' not in remote_fn.group(0) or 'WaitForChild("ObjectiveAction")' in panel:
        errors.append('ObjectivesPanel: the remote is looked up with FindFirstChild per call (it exists only while the server flag is on); never WaitForChild')
    if 'objectives=Config.ObjectivesEnabled==true and goalHUD.Visible' not in boot:
        errors.append('Bootstrap: TouchLayout.compute gets objectives only while Config.ObjectivesEnabled')
    publish = re.search(r'if Config\.ObjectivesEnabled==true then[^\n]*\n(.*?)\n    end\n', boot, re.S)
    if (not publish or boot.count('SetAttribute("ObjectivesRect"') != 1 or boot.count('SetAttribute("ObjectivesOpenRect"') != 1
            or 'SetAttribute("ObjectivesRect"' not in publish.group(1) or 'SetAttribute("ObjectivesOpenRect"' not in publish.group(1)):
        errors.append('Bootstrap: ObjectivesRect / ObjectivesOpenRect are published once, only inside the flag check')
    if len(re.findall(r'^local ', boot, re.M)) > 195:
        errors.append('Bootstrap: no new top-level local (limit)')

    # --- BD-076: the goal line follows the top objective, and with the flag off it is the old line ----------------------------------------
    hud_code = code_only(goal_hud)
    if hud_code.count('objectives=require(') != 1 or hud_code.count('local objectives: any=nil') != 1:
        errors.append('GoalHud: `objectives` is nil until the one require inside the flag check')
    if hud_code.count('objectives.goalLine(') != 1 or not re.search(r'if objectives then\n(?:(?!\n        end\n).)*objectives\.goalLine\(', hud_code, re.S):
        errors.append('GoalHud: objectives.goalLine is called once, only inside `if objectives then` (flag off: objective stays nil)')
    if 'local objective=nil' not in hud_code or 'objective=objective' not in hud_code or 'prefix..goal.text' not in hud_code:
        errors.append('GoalHud: NextGoal.pick gets objective=nil unless the flag is on; the text is prefix..goal.text as before')
    if hud_code.count('objectives.onTopChanged(') != 1 or hud_code.find('objectives.onTopChanged(') < hud_code.find('Config.ObjectivesEnabled==true then'):
        errors.append('GoalHud: onTopChanged is wired once, inside the flag check')
    next_goal = code_only(read('src/shared/NextGoal.luau'))
    for word in ('Config', 'ObjectivesEnabled', 'ObjectivePanelRules', 'ObjectivesPanel', 'game:GetService', 'Instance.new'):
        if word in next_goal:
            errors.append(f'NextGoal must stay pure and flag-free, found {word} (the flag lives in GoalHud only)')
    if panel.count('Rules.goalLine(') != 1 or panel.count('onTop') < 2:
        errors.append('ObjectivesPanel: goalLine and onTopChanged are the only BD-076 hooks')
    min_font = re.search(r'local MIN_FONT = (\d+)', read('src/shared/ObjectivePanelRules.luau'))
    min_text = re.search(r'PhoneScale\.MinText = (\d+)', read('src/shared/PhoneScale.luau'))
    if not min_font or not min_text or min_font.group(1) != min_text.group(1):
        errors.append('ObjectivePanelRules.MIN_FONT must equal PhoneScale.MinText')
    # The width maths in the Luau part assumes how Bootstrap styles the line; if these lines change, the fit table must be revisited.
    for needle in ('floorText(17,layout.crystal.scale) else 17', 'goalLimit.MaxTextSize,goalLimit.MinTextSize=goalFloor,if layout.touch then goalFloor else require(Shared.PhoneScale).MinText',
                   'goalText.TextScaled,goalText.TextSize=not layout.touch,goalFloor', 'local goalText=label(goalHUD,"",8,0,244,30,17,C.gold)'):
        if needle not in boot and needle not in goal_hud:
            errors.append('goal line styling changed (' + needle[:50] + '...): re-check the BD-076 width table')

    # --- the client never computes a reward ----------------------------------------------------------------------------------------------
    for word in ('PrivateState', 'AccountXP', 'AccountLevel', 'MarketplaceService', 'Robux', 'DeveloperProduct', 'Crystals"'):
        if word in panel:
            errors.append(f'ObjectivesPanel must not touch {word}: rewards are the server\'s (it only shows the view)')
    if re.search(r'(crystals|reward|xp)\s*[-+*/]=', panel, re.I) or re.search(r'\.(crystals|xp)\s*[-+*/]\s*\w', panel):
        errors.append('ObjectivesPanel does arithmetic on a reward')
    rules = code_only(read('src/shared/ObjectivePanelRules.luau'))
    for word in ('Instance.new', 'game:GetService', 'os.time', 'os.clock', 'RemoteFunction', 'RemoteEvent', 'task.'):
        if word in rules:
            errors.append(f'ObjectivePanelRules must stay pure, found {word}')

    # --- floors: text >= 14 px, buttons >= 44 px ------------------------------------------------------------------------------------------
    floor_text = 14
    for match in re.finditer(r'text\(\w+, "\w+", (\d+|\w+\.\w+)', panel):
        size = match.group(1)
        if size.isdigit() and int(size) < floor_text:
            errors.append(f'ObjectivesPanel: text size {size} < {floor_text}')
    for size in re.findall(r'^local TEXT = (\d+)', panel, re.M):
        if int(size) < floor_text:
            errors.append('ObjectivesPanel: TEXT < 14')
    if 'PhoneScale.MinText' not in panel:
        errors.append('ObjectivesPanel: small text uses PhoneScale.MinText')
    o = re.search(r'TouchLayout\.OBJECTIVES = \{w = (\d+), minW = (\d+), h = (\d+), rowH = (\d+), rows = (\d+)', layout)
    if not o or int(o.group(3)) < 44:
        errors.append('TouchLayout.OBJECTIVES.h (the header button) must be >= 44')
    elif int(o.group(4)) < 44 + 4:
        errors.append('TouchLayout.OBJECTIVES.rowH must hold a 44 px CLAIM button')
    claim_size = re.search(r'^local CLAIM_H = (\d+)', panel, re.M)
    claim_w = re.search(r'^local CLAIM_W = (\d+)', panel, re.M)
    if not claim_size or int(claim_size.group(1)) < 44 or not claim_w or int(claim_w.group(1)) < 44:
        errors.append('ObjectivesPanel: the CLAIM button is >= 44 x 44')
    # --- BD-075 row layout (docs/66 s18): fixed row height, gap 4..6 px, a divider in the UITheme card colour, CLAIM centred in its row ------
    gaps = re.search(r'rowGap = (\d+)\}', layout)
    if not gaps or not 4 <= int(gaps.group(1)) <= 6:
        errors.append('TouchLayout.OBJECTIVES.rowGap must be 4..6 px')
    if '(O.rows - 1) * O.rowGap' not in layout:
        errors.append('TouchLayout.objectivesOpenH must count the row gaps')
    if 'divider.Name, divider.BackgroundColor3, divider.BorderSizePixel, divider.ZIndex = "Divider", C.card, 0, body.ZIndex' not in panel:
        errors.append('ObjectivesPanel: each row has a Divider in the UITheme card colour (no art)')
    if '(ROW_H - CLAIM_H) / 2' not in panel:
        errors.append('ObjectivesPanel: CLAIM is vertically centred in its row ((ROW_H - CLAIM_H) / 2)')
    if 'C.text:Lerp(C.card' not in panel:
        errors.append('ObjectivesPanel: the row note uses UITheme colours only (text toned toward card)')
    if 'UIScale' in panel:
        errors.append('ObjectivesPanel is drawn 1:1 (no UIScale): text and buttons keep their real pixel size')

    # --- existing UI parts only (docs/72, AGENTS.md 2026-10-14) ---------------------------------------------------------------------------
    for word in ('rbxassetid', 'ImageLabel', 'ImageButton', 'ViewportFrame', 'Polygon', 'ParticleEmitter'):
        if word in panel:
            errors.append(f'ObjectivesPanel: {word}: no new art; use Theme plates and registered icons only')
    # BD-561: every other icon goes through ONE gated helper (empty id = no Instance); the slots exist and are empty in source
    if panel.count('Theme.icon(') != 2 or not re.search(r'local function makeIcon\(.*?\n        if not art\[which\] then return nil end\n        local icon = Theme\.icon\(parent, Rules\.Slots\[which\]\)', panel, re.S):
        errors.append('ObjectivesPanel: Theme.icon is called twice only (the trophy, and makeIcon behind `if not art[which] then return nil end`)')
    slots = read('src/shared/AssetSlots.luau')
    for key in ('objective_chevron', 'objective_arrow', 'notify_crystal', 'notify_star'):
        if not re.search(rf'^\s*{key} = "",', slots, re.M):
            errors.append(f'AssetSlots.Images.{key} must exist and be empty in source (art pending, never an invented id)')
    if 'Rules.Slots' not in panel or 'chevron = "objective_chevron", arrow = "objective_arrow", crystal = "notify_crystal", star = "notify_star"' not in read('src/shared/ObjectivePanelRules.luau'):
        errors.append('ObjectivePanelRules.Slots must name the four Theme.ImageIds keys of docs/109 section 9')
    if 'Theme.icon(header, "trophy")' not in panel or not re.search(r'^\s*trophy = "rbxassetid://\d+"', read('src/shared/UIIconAssets.luau'), re.M):
        errors.append('ObjectivesPanel: the header icon is the already-registered "trophy"')
    return errors


# ---------------------------------------------------------------------------------------------------------------------------------------
LUAU = r'''
local realOs = os
local modules = {}
local script = {Parent = setmetatable({}, {__index = function(_, key) return key end})}
local function require(name) return assert(modules[name], "unknown module " .. tostring(name)) end
modules.Config = @@CONFIG@@
modules.PhoneScale = @@PHONE_SCALE@@
modules.TouchLayout = @@TOUCH_LAYOUT@@
modules.ObjectiveConfig = @@OBJ_CONFIG@@
modules.ObjectiveRules = @@OBJ_RULES@@
modules.ObjectivePanelRules = @@PANEL_RULES@@
modules.NextGoal = @@NEXT_GOAL@@
local Rules, ServerRules, Cfg, TouchLayout = modules.ObjectivePanelRules, modules.ObjectiveRules, modules.ObjectiveConfig, modules.TouchLayout

local function copy(t) if type(t) ~= "table" then return t end local r = {} for k, v in t do r[k] = copy(v) end return r end
local NOW = 20833 * 86400 + 100 -- a UTC midnight + 100 s: the server clock the fixtures are rolled at
local function realView(events, claimIds)
 local s = ServerRules.fresh()
 ServerRules.advance(s, NOW)
 if events then ServerRules.applyEvents(s, events, NOW) end
 for _, id in claimIds or {} do assert(ServerRules.claim(s, id, NOW, {crystals = 0}, 2000000000), "fixture claim " .. id) end
 local view = ServerRules.view(s, NOW)
 return view, s
end
local function ids(rows) local r = {} for _, row in rows do table.insert(r, row.id) end return table.concat(r, ",") end

---------------------------------------------------------------- 1. which rows (pure rules, real server view)
local v0 = realView()
local rows = Rules.select(v0, {playGoalActive = false})
assert(#rows == 3 and rows[1].id == "T1" and rows[1].group == "tutorial", "fresh: tutorial first, then one short, one daily: " .. ids(rows))
assert(rows[2].group == "short" and rows[3].group == "daily", "short and daily are shown in turns, so a daily is never starved")
for _, r in rows do
 assert(not r.claimable and r.progress == 0 and r.fraction == 0 and r.goal >= 1 and r.reward.crystals >= 1 and r.name ~= "")
end
assert(#Rules.select(v0, {max = 2}) == 2 and #Rules.select(v0, {max = 99}) <= 6 and #Rules.select(nil) == 0 and #Rules.select("x") == 0 and #Rules.select({}) == 0)

-- a finished short row jumps to the front and is claimable; closest-to-done order inside a group
local v1, s1 = realView({{kind = "food_eaten", amount = 10}})
rows = Rules.select(v1, {playGoalActive = false})
assert(rows[1].id == "T1" and rows[1].claimable and Rules.claimableCount(rows) >= 1, "finished tutorial row is claimable and first")
local shortIds = s1.short.ids
local entry = Cfg.ById[shortIds[2]]
local v2 = realView({{kind = entry.event, amount = entry.goal, value = entry.minValue}})
rows = Rules.select(v2, {playGoalActive = false})
local claimables = 0 for _, r in rows do if r.claimable then claimables += 1 assert(rows[claimables].claimable, "claimable rows come first") end end
assert(claimables >= 1)
-- claimed rows leave the list
local v3 = realView({{kind = "food_eaten", amount = 10}}, {"T1"})
for _, r in Rules.select(v3, {playGoalActive = false}) do assert(r.id ~= "T1", "claimed rows are not shown") end
assert(v3.tutorial and v3.tutorial.id == "T2")

-- carried rows (finished last window, still claimable) show and claim
local carryView = {tutorialDone = true, short = {}, daily = {}, carry = {{id = "S3", name = "Finish a run", progress = 1, goal = 1, reward = {crystals = 15, xp = 0}, done = true, claimed = false, carried = true}}}
rows = Rules.select(carryView)
assert(#rows == 1 and rows[1].claimable and rows[1].carried and rows[1].group == "carry")

-- many claimable: only 3, the rest after claiming
local many = {tutorialDone = true, short = {}, daily = {}, carry = {}}
for i, id in {"S1", "S2", "S3", "S4", "S5"} do table.insert(many.short, {id = id, name = Cfg.ById[id].name, progress = Cfg.ById[id].goal, goal = Cfg.ById[id].goal, reward = {crystals = 5}, done = true, claimed = false}) end
assert(#Rules.select(many) == 3)

---------------------------------------------------------------- 2. T8 "second species" versus the Goals PLAY line (docs/66 s16 watch item)
local function t8(progress)
 return {tutorial = {id = "T8", name = Cfg.ById.T8.name, progress = progress, goal = 1, reward = {crystals = 30, xp = 0}, done = progress >= 1, claimed = false}, tutorialDone = false,
  short = {}, daily = {}, carry = {}}
end
assert(ids(Rules.select(t8(0), {playGoalActive = true})) == "", "PLAY line on screen: an unfinished T8 is NOT shown (one species nudge, not two)")
assert(ids(Rules.select(t8(0), {playGoalActive = false})) == "T8", "PLAY line finished: T8 shows")
assert(ids(Rules.select(t8(1), {playGoalActive = true})) == "T8" and Rules.select(t8(1), {playGoalActive = true})[1].claimable, "a finished T8 is a reward to claim, not a nudge: shown")
local other = t8(0) other.tutorial.id = "T9" other.tutorial.name = Cfg.ById.T9.name
assert(ids(Rules.select(other, {playGoalActive = true})) == "T9", "only T8 is hidden")

---------------------------------------------------------------- 3. folded line, chips, words
local f = Rules.folded({})
assert(f.empty and f.chip == "" and f.text == "All done!")
f = Rules.folded(Rules.select(v0, {playGoalActive = false}))
assert(f.text == "Eat 10 food" and f.chip == "0/10" and not f.claimable and not f.empty)
f = Rules.folded(Rules.select(v1, {playGoalActive = false}))
assert(f.chip == "Done!" and f.claimable and f.claimableCount >= 1)
assert(Rules.progressText({progress = 3, goal = 10}) == "3/10" and Rules.progressText({progress = 99, goal = 10}) == "99/10" and Rules.progressText({}) == "0/1")
assert(Rules.rewardText({crystals = 10}) == "+10 crystals" and Rules.rewardText({crystals = 10, xp = 5}) == "+10 crystals +5 XP" and Rules.rewardText(nil) == "+0 crystals")
-- docs/72: "New tasks soon", never "5m 0s"
assert(Rules.resetText(0) == "New tasks soon" and Rules.resetText(60) == "New tasks soon" and Rules.resetText(nil) == "New tasks soon" and Rules.resetText(-5) == "New tasks soon" and Rules.resetText(0 / 0) == "New tasks soon")
assert(Rules.resetText(61) == "New tasks in 2 min" and Rules.resetText(300) == "New tasks in 5 min" and Rules.resetText(1800) == "New tasks in 30 min" and Rules.resetText(3481) == "New tasks in 59 min" and Rules.resetText(3541) == "New tasks in 1 h")
assert(Rules.resetText(3600) == "New tasks in 1 h" and Rules.resetText(3601) == "New tasks in 2 h" and Rules.resetText(86400) == "New tasks in 24 h")
for _, sec in {0, 1, 59, 60, 61, 299, 300, 1799, 1800, 3599, 3600, 7200, 86399, 86400} do assert(Rules.copyOk(Rules.resetText(sec)), "copy: " .. sec) end
assert(not Rules.copyOk("5m 0s") and not Rules.copyOk("2h 0m") and not Rules.copyOk("Speed 1.25x") and not Rules.copyOk("Resets in 12m") and not Rules.copyOk("window") and Rules.copyOk("Hatch 3 eggs"), "the copy checker has teeth")
-- the clock shown is the soonest of the groups on screen; the tutorial has no clock
local clockView = {shortResetsIn = 600, dailyResetsIn = 40000}
assert(Rules.resetSeconds(clockView, {{group = "short"}, {group = "daily"}}) == 600 and Rules.resetSeconds(clockView, {{group = "daily"}}) == 40000)
assert(Rules.resetSeconds(clockView, {{group = "tutorial"}}) == nil and Rules.resetSeconds(clockView, {}) == nil and Rules.resetSeconds(nil, {{group = "short"}}) == nil)
assert(Rules.resetSeconds(clockView, {{group = "carry"}}) == 600, "a carried short row follows the short clock")

---------------------------------------------------------------- 4. claim answers, tokens, button state
for _, code in {"claimed", "claimed_capped", "duplicate", "already_claimed", "not_done", "not_active", "rate_limited", "save_failed", "lease_lost", "error",
 "disabled", "bad_request", "unknown_objective", "invalid_token", "token_conflict", "newer_version", "profile_not_loaded", "xyz", nil} do
 local text = Rules.claimMessage(code)
 assert(type(text) == "string" and #text >= 3 and #text <= 40 and Rules.copyOk(text), "claim copy: " .. tostring(code))
end
assert(Rules.claimMessage("not_done") == "Not done yet" and Rules.claimMessage("save_failed") == "Try again" and Rules.claimMessage("zzz") == "Try again later")
for _, code in {"rate_limited", "save_failed", "lease_lost", "error"} do assert(Rules.keepToken(code), code .. ": nothing was decided, retry with the same token") end
for _, code in {"claimed", "claimed_capped", "duplicate", "already_claimed", "not_done", "not_active", "unknown_objective", "token_conflict", "disabled", nil} do assert(not Rules.keepToken(code), tostring(code) .. ": a definite answer frees the id") end
assert(Rules.paid("claimed") and Rules.paid("duplicate") and Rules.paid("already_claimed") and not Rules.paid("not_done") and not Rules.paid("error"))
assert(Rules.buttonState({claimable = true}, false) == "claim" and Rules.buttonState({claimable = true}, true) == "wait" and Rules.buttonState({claimable = false}, false) == "none" and Rules.buttonState({claimable = false}, true) == "none")
-- every catalogue name is panel copy: short, plain, fits two lines
for _, e in Cfg.Catalogue do assert(#e.name <= Rules.MaxName and Rules.copyOk(e.name) and Rules.copyOk(Rules.rewardText(e.reward)) and Rules.copyOk(Rules.progressText({progress = e.goal, goal = e.goal})), e.id) end
assert(Rules.copyOk(Rules.Title) and Rules.MaxShown == 3 and Rules.PollSeconds >= 5)
print("Rules passed: 3 rows (claimable first, tutorial, short and daily in turns), T8 hidden next to the PLAY line until finished, folded line, 'New tasks soon' words, claim answers and token reuse, docs/72 copy")

---------------------------------------------------------------- 6. BD-076: the one-line goal (priority table, flag-off identity, copy and width)
local NextGoal = modules.NextGoal
local function dino(species, pattern, stage) return {speciesId = species, stage = stage or "base", genes = {patternId = pattern}} end
local function many(n, species, pattern, stage) local t = {} for _ = 1, n do table.insert(t, dino(species, pattern, stage)) end return t end
local FUSION = {none = nil, progress = many(3, "compy", "06_wavy_stripes"), ready = many(6, "compy", "06_wavy_stripes")}
local function goalOpts(dinos, objective)
 return {dinos = dinos, level = 3, xp = 450, perLevel = 100, maxLevel = 60, objective = objective,
  speciesName = function(id) return id == "compy" and "Compy" or id end, patternName = function(id) return id end}
end
local WIDE = {width = 600, font = 14, prefix = ""} -- plenty of room: the words, not the width, are under test here
local function line(rowsView, fit, play)
 return Rules.goalLine(Rules.select(rowsView, {playGoalActive = play == true}), fit or WIDE)
end
local freshLine = line(v0)
local doneLine = line(v1)
assert(freshLine and not freshLine.claimable and freshLine.text == "Eat 10 food: 0/10", freshLine and freshLine.text)
assert(doneLine and doneLine.claimable and doneLine.ready and doneLine.text == "Done! Claim at the objectives panel", doneLine and doneLine.text)
local TABLE = {} -- the priority table: objective (none / unfinished / claimable) x fusion (none / in progress / ready) -> the winner
local function expect(objective, fusion)
 if objective == "claimable" then return "objective" end
 if fusion ~= "none" then return "fusion" end
 if objective == "unfinished" then return "objective" end
 return "level"
end
for _, objective in {"none", "unfinished", "claimable"} do
 for _, fusion in {"none", "progress", "ready"} do
  local o = if objective == "none" then nil elseif objective == "unfinished" then freshLine else doneLine
  local goal = NextGoal.pick(goalOpts(FUSION[fusion], o))
  assert(goal.kind == expect(objective, fusion), "priority " .. objective .. " + fusion " .. fusion .. " -> " .. goal.kind)
  if goal.kind == "objective" then assert(goal.text == o.text and goal.ready == (objective == "claimable") and goal.claimable == (objective == "claimable")) end
  if goal.kind == "fusion" then assert(goal.text == (if fusion == "ready" then "Gold ready: fuse Compy" else "Gold: 3/6 Compy")) end
  if goal.kind == "level" then assert(goal.text == "Level 3: 50/500 XP") end
  table.insert(TABLE, objective .. "+" .. fusion .. "=" .. goal.kind)
 end
end
assert(#TABLE == 9)
-- the three rules one by one, in words
assert(NextGoal.pick(goalOpts(FUSION.ready, doneLine)).kind == "objective", "1. a claimable objective beats everything (even a ready fusion)")
assert(NextGoal.pick(goalOpts(FUSION.progress, freshLine)).kind == "fusion", "2. the fusion goal beats an unfinished objective")
assert(NextGoal.pick(goalOpts(nil, freshLine)).kind == "objective" and NextGoal.pick(goalOpts({}, freshLine)).kind == "objective", "3. any active objective beats the level fallback (list unavailable or empty)")
-- a nonsense objective is ignored, never a blank line
for _, bad in {"x", 5, {}, {text = ""}, {text = 5}, {claimable = true}} do assert(NextGoal.pick(goalOpts(nil, bad)).kind == "level", "unusable objective -> the old line") end

-- flag-off identity: without an objective NextGoal.pick IS the old `fusion or level` for every input, field for field
local function legacy(o) return NextGoal.fusion(o.dinos, o) or NextGoal.level(o) end
local function same(a, b) for k, v in a do if b[k] ~= v then return false end end for k in b do if a[k] == nil then return false end end return true end
local checked = 0
for _, dinos in {FUSION.progress, FUSION.ready, {}, many(1, "rex", "03_round_spots", "emerald"), many(2, "compy", "06_wavy_stripes", "gold")} do
 for _, xp in {0, 450, 10 ^ 9} do
  local o = goalOpts(dinos, nil)
  o.xp = xp
  assert(same(NextGoal.pick(o), legacy(o)), "flag off: byte-identical to the old line")
  checked += 1
 end
end
assert(same(NextGoal.pick({level = 2, xp = 120}), legacy({level = 2, xp = 120})) and checked >= 15)

-- copy and width on EVERY canvas: phone, tablet, desktop, and the real 836 x 390 / 667 x 375 minus the top bar, mouse and touch
local canvases = {}
for _, v in {{800, 360}, {640, 360}, {667, 375}, {732, 412}, {844, 390}, {915, 412}, {800, 302}, {760, 360}, {1024, 768}, {1280, 720}, {1280, 800}, {1366, 1024}, {1920, 1080}, {2400, 1080},
 {667, 317}, {836, 332}, {1000, 700}, {1156, 841}, {1080, 720}, {1440, 900}} do table.insert(canvases, {v[1], v[2], true}) table.insert(canvases, {v[1], v[2], false}) end
for _, v in {{836, 390}, {667, 375}} do for _, bar in {0, 36, 44, 58} do for _, touch in {true, false} do table.insert(canvases, {v[1], v[2] - bar, touch}) end end end
local PHONE = modules.PhoneScale
local function wordsOf(text) local w = {} for word in string.gmatch(text, "%S+") do table.insert(w, word) end return w end
local longReady, shortReady, fullNames, cutNames, bareProgress = 0, 0, 0, 0, 0
for _, c in canvases do
 local layout = TouchLayout.compute({width = c[1], height = c[2], touch = c[3], navCount = 7})
 local scale = layout.crystal.scale
 -- exactly what Bootstrap does: the phone layout draws a fixed floorText(17) size and truncates; desktop scales between MinText and 17
 local font = if layout.touch then PHONE.floorText(17, scale) else PHONE.MinText
 local prefix = if c[3] or PHONE.isCompact(c[2]) then "" else "Goal  "
 assert((prefix == "") == layout.touch, "the prefix rule matches the layout: " .. c[1] .. "x" .. c[2])
 assert(not layout.touch or font * scale >= PHONE.MinText - 1e-6, "the touch line renders >= 14 px at " .. c[1] .. "x" .. c[2])
 local fit = {width = 244, font = font, prefix = prefix}
 -- finished: the longest fixed phrase that fits (the bare "Done!" always does)
 local ready = line(v1, fit)
 assert(ready.claimable and Rules.fitsLine(ready.text, fit) and Rules.copyOk(ready.text), "ready text fits at " .. c[1] .. "x" .. c[2] .. ": " .. ready.text)
 assert(string.sub(ready.text, 1, 5) == "Done!", "a finished task always starts with Done!")
 for _, candidate in Rules.GoalReadyText do
  if candidate == ready.text then break end
  assert(not Rules.fitsLine(candidate, fit), "a longer phrase that fits is preferred: " .. candidate)
 end
 if ready.text == Rules.GoalReadyText[1] then longReady += 1 else shortReady += 1 end
 -- unfinished: every catalogue task at progress 0 and goal - 1
 for _, e in Cfg.Catalogue do
  for _, p in {0, math.max(0, e.goal - 1)} do
   local row = {id = e.id, name = e.name, progress = p, goal = e.goal, reward = e.reward, fraction = p / e.goal, claimable = false}
   local l = Rules.goalLine({row}, fit)
   local pText = if e.goal > 1 then Rules.progressText(row) else ""
   assert(l and not l.claimable and not l.ready and l.id == e.id, e.id)
   assert(Rules.fitsLine(l.text, fit) or l.text == pText, "fits: " .. l.text .. " at " .. c[1] .. "x" .. c[2])
   assert(Rules.copyOk(l.text) and #l.text <= 48, "copy: " .. l.text)
   assert(pText == (if e.goal > 1 then Rules.progressText(row) else "") and (pText == "" or string.sub(l.text, -#pText) == pText), "a counted task keeps its count: " .. l.text)
   -- never a word cut in half: the name part is a whole-word prefix of the name
   local namePart = string.gsub(string.sub(l.text, 1, #l.text - #pText), "[:%.%s]+$", "")
   if namePart == "" then bareProgress += 1 elseif namePart ~= "Task" and namePart ~= "Next task" then
    local nameWords, partWords = wordsOf(e.name), wordsOf(namePart)
    for i, word in partWords do assert(word == nameWords[i], "whole words only: '" .. l.text .. "' from '" .. e.name .. "'") end
   end
   if l.text == e.name .. (if pText ~= "" then ": " .. pText else "") then fullNames += 1 else cutNames += 1 end
   -- the words never end on a dangling "a" / "toward" before the dots
   assert(not string.find(l.text, " a%.%.%.") and not string.find(l.text, " toward%.%.%.") and not string.find(l.text, " the%.%.%."), "no dangling word: " .. l.text)
  end
 end
end
assert(fullNames > 0 and cutNames > 0 and shortReady > 0, "the table covers both the full and the cut words")
assert(Rules.textWidth("", 17) == 0 and Rules.textWidth("Done!", 17) < Rules.textWidth("Done! Claim it", 17) and Rules.textWidth("WWWW", 14) > Rules.textWidth("iiii", 14))
-- degenerate input never errors, never a blank line
assert(Rules.goalLine({}, WIDE) == nil and Rules.goalLine({{claimable = false}}, nil) == nil)
local nameless = Rules.goalLine({{id = "X", name = "", progress = 1, goal = 2, claimable = false, fraction = 0.5}}, WIDE)
assert(nameless.text == "Task 1/2", nameless.text)
assert(Rules.goalLine({{id = "X", name = "Supercalifragilisticexpialidocious", progress = 1, goal = 2, claimable = false, fraction = 0.5}}, {width = 120, font = 23, prefix = ""}).text == "Task 1/2", "one over-long word is never cut: the progress stands in")
-- T8 versus the Goals PLAY line: the unfinished second-species task never reaches the goal line either
assert(line(t8(0), WIDE, true) == nil, "PLAY line on screen: no T8 on the goal line")
assert(line(t8(0), WIDE, false).text == "Collect a second species", "PLAY line done: T8 may show")
assert(line(t8(1), WIDE, true).claimable, "a finished T8 is a reward: it shows")
print(string.format("Goal line passed: priority table %s; flag-off identical on %d inputs; copy and width on %d canvases (%d full names, %d cut at a word, ready text long on %d / short on %d canvases)",
 table.concat(TABLE, " "), checked, #canvases, fullNames, cutNames, longReady, shortReady))

---------------------------------------------------------------- 5. the REAL ObjectivesPanel.luau against a mock of the GUI classes
local clockNow, tasks, calls, guidCount = 1000, {}, {}, 0
local function pump() while #tasks > 0 do local t = table.remove(tasks, 1) t[1](table.unpack(t, 2)) end end
local function signal()
 local s = {handlers = {}}
 function s:Connect(fn) table.insert(self.handlers, fn) return {Disconnect = function() end} end
 function s:fire(...) for _, h in self.handlers do h(...) end end
 return s
end
local function newInstance(class)
 local self = {ClassName = class, Children = {}, Name = class}
 local mt = {}
 mt.__index = function(t, key)
  if key == "Activated" then local s = signal() rawset(t, key, s) return s end
  if key == "AbsoluteSize" then return {X = 0, Y = 0} end
  if key == "FindFirstChild" then return function(_, name) for _, c in t.Children do if c.Name == name then return c end end return nil end end
  if key == "IsA" then return function(_, c) return c == class or c == "GuiObject" end end
  if key == "GetChildren" then return function() return t.Children end end
  if key == "Destroy" then return function() end end
  return nil
 end
 mt.__newindex = function(t, key, value)
  if key == "Parent" then rawset(t, key, value) if value then table.insert(value.Children, t) end return end
  rawset(t, key, value)
 end
 return setmetatable(self, mt)
end
local function find(node, name) for _, c in node.Children do if c.Name == name then return c end end return nil end
local Instance_ = {new = newInstance}
local function udim(sx, ox, sy, oy) return {X = {Scale = sx, Offset = ox}, Y = {Scale = sy, Offset = oy}} end
local UDim2_ = {new = udim, fromOffset = function(x, y) return udim(0, x, 0, y) end, fromScale = function(x, y) return udim(x, 0, y, 0) end}
local Vector2_ = {new = function(x, y) return {X = x, Y = y} end, zero = {X = 0, Y = 0}}
local Enum_ = setmetatable({}, {__index = function(_, k) return setmetatable({}, {__index = function(_, k2) return k .. "." .. k2 end}) end})
local Rect_ = {new = function(x0, y0, x1, y1) return {__type = "Rect", Min = {X = x0, Y = y0}, Max = {X = x1, Y = y1}, Width = x1 - x0, Height = y1 - y0} end}
local function typeof(v) if type(v) == "table" and rawget(v, "__type") then return v.__type end return type(v) end
local task_ = {spawn = function(fn, ...) table.insert(tasks, {fn, ...}) end, delay = function(_, fn) table.insert(tasks, {fn}) end}
local os_ = {clock = function() return clockNow end}
local Colors = {panel = "panel", card = "card", gold = "gold", accent = "accent", text = setmetatable({}, {__index = {Lerp = function() return "muted" end}}), outline = "outline", red = "red"}
modules.ChipStyle = {apply = function(frame, fill) frame.BackgroundColor3 = fill end} -- BD-1077
modules.UITheme = {Colors = Colors, decorate = function() end, TextStyle = {apply = function() end},
 icon = function(parent, id) local f = newInstance("Frame") f.Name = "Icon_" .. id f.Parent = parent return f end,
 animate = function(target, _, goals) for k, v in goals do target[k] = v end end}

local remoteHandler = function(_) return nil end
local remote = newInstance("RemoteFunction") remote.Name = "ObjectiveAction"
remote.InvokeServer = function(_, request) table.insert(calls, copy(request)) return remoteHandler(request) end
local remotesFolder = newInstance("Folder") remotesFolder.Name = "BeDinoRemotes" remote.Parent = remotesFolder
local sharedFolder = {WaitForChild = function(_, name) return name end}
local replicated = {WaitForChild = function() return sharedFolder end, FindFirstChild = function(_, name) if name == "BeDinoRemotes" then return remotesFolder end return nil end}
local runState = "Idle"
local character = {GetAttribute = function(_, name) if name == "RunState" then return runState end return nil end}
local player = {Character = character}
local heartbeat = signal()
local gameMock = {GetService = function(_, name)
 if name == "HttpService" then return {GenerateGUID = function() guidCount += 1 return "guid-" .. guidCount end} end
 if name == "Players" then return {LocalPlayer = player} end
 if name == "ReplicatedStorage" then return replicated end
 if name == "RunService" then return {Heartbeat = heartbeat} end
 error("service " .. tostring(name))
end}
local gui = newInstance("ScreenGui")
gui.attrs = {}
gui.GetAttribute = function(self, name) return self.attrs[name] end
local anchor = newInstance("Frame") anchor.Visible = true

local function loadPanel(gameObject)
 return (function(game, Instance, UDim2, Vector2, Enum, Rect, typeof, task, os)
 @@PANEL_SRC@@
 end)(gameObject, Instance_, UDim2_, Vector2_, Enum_, Rect_, typeof, task_, os_)
end
local Panel = loadPanel(gameMock)

-- Nothing is asked before attach, and attach alone sends nothing: with the panel not shown there are no remote calls.
assert(#calls == 0 and #tasks == 0, "attach has no side effect")
Panel.attach(gui, anchor)
assert(#calls == 0 and #tasks == 0, "attach asks nothing")
local root = find(gui, "ObjectivesPanel")
assert(root and root.Visible == false, "hidden until it has a layout rect and an answer")
local function tick() clockNow += 0.6 heartbeat:fire(0.6) pump() end
-- hub but no layout rect yet (flag on, Bootstrap has not published): still no request storm, panel hidden
local PILL, SHEET = Rect_.new(278, 72, 498, 116), Rect_.new(278, 72, 559, 261)
tick() tick()
assert(root.Visible == false)
gui.attrs.ObjectivesRect, gui.attrs.ObjectivesOpenRect = PILL, SHEET

local view = copy(v0)
local function respond(request)
 if request.action == "view" then return {ok = true, view = copy(view)} end
 return {ok = false, reason = "bad_request"}
end
remoteHandler = respond
Panel.setPlayActive(false)
tick() tick() -- the first tick asks, the next one shows the answer
assert(root.Visible == true, "shown once the server answered")
assert(calls[#calls].action == "view" and #calls[#calls] == 0, "view request shape")
for _, c in calls do assert(c.action == "view", "before any tap only views are sent") end
local header = find(root, "Header")
local title, chip = find(header, "Title"), find(header, "Chip")
local chipText = find(chip, "ChipText")
local wait = find(header, "Wait")
assert(title.Text == "Eat 10 food" and chipText.Text == "0/10" and chip.Visible == true, "folded: ONE line, the nearest task and a progress chip")
assert(root.Size.Y.Offset == 44 and root.Size.X.Offset == 220 and root.Position.X.Offset == 278 and root.Position.Y.Offset == 72, "folded rect = the layout rect, 44 px tall")
assert(title.TextSize >= 14 and chipText.TextSize >= 14 and wait.TextSize >= 14, "header text >= 14 px")
local body = find(root, "Body")
assert(body.Visible == false, "rows are hidden while folded")

-- polling: a fresh view every PollSeconds, never faster than the limiter allows
local viewsBefore = #calls
for _ = 1, 5 do tick() end
assert(#calls == viewsBefore, "3 s later: no new request")
for _ = 1, 40 do tick() end
assert(#calls > viewsBefore and #calls - viewsBefore <= 3, "about every 20 s while shown, not per frame: " .. (#calls - viewsBefore))

-- open: header + 3 rows, no CLAIM yet, "New tasks soon"-style words, sheet rect
header.Activated:fire() pump() tick()
assert(root.Size.Y.Offset == SHEET.Height and root.Size.X.Offset == SHEET.Width and root.Position.Y.Offset == SHEET.Min.Y, "open = the open sheet rect")
assert(body.Visible == true and title.Text == "TASKS" and chip.Visible == false and wait.Visible == true)
assert(wait.Text == "New tasks in 30 min" or string.match(wait.Text, "^New tasks in %d+ min$") or wait.Text == "New tasks soon", "child-friendly clock: " .. wait.Text)
assert(Rules.copyOk(wait.Text))
local function row(i) return find(body, "Row" .. i) end
local names = {}
for i = 1, 3 do
 local r = row(i)
 assert(r.Visible == true, "row " .. i)
 local claimB = find(r, "Claim")
 assert(claimB.Visible == false, "no CLAIM on an unfinished task")
 assert(find(r, "Name").TextSize >= 14 and find(r, "Count").TextSize >= 14 and find(r, "Reward").TextSize >= 14)
 assert(find(r, "Name").Text ~= "" and find(r, "Count").Visible and string.match(find(r, "Count").Text, "^%d+/%d+$"))
 table.insert(names, find(r, "Name").Text)
 assert(Rules.copyOk(find(r, "Name").Text) and Rules.copyOk(find(r, "Reward").Text))
end
assert(names[1] == "Eat 10 food")
header.Activated:fire() pump() tick()
assert(body.Visible == false and root.Size.Y.Offset == 44, "folds again")

-- a finished task: claimable state, CLAIM button >= 44, request shape, waiting state, answer
local doneView, doneState = realView({{kind = "food_eaten", amount = 10}})
view = doneView
header.Activated:fire() pump() -- opening asks the server for a fresh view
tick()
assert(title.Text == "TASKS")
local r1 = row(1)
local claim = find(r1, "Claim")
assert(find(r1, "Name").Text == "Eat 10 food" and claim.Visible == true and claim.Text == "CLAIM" and claim.Active == true, "finished task: CLAIM shown")
assert(claim.Size.X.Offset >= 44 and claim.Size.Y.Offset >= 44, "CLAIM is a >= 44 px target")
assert(find(r1, "Count").Visible == false and find(r1, "Reward").Visible ~= false and find(r1, "Reward").Text == "+10 crystals" and find(r1, "Reward").TextSize >= 14, "finished: the prize is shown next to CLAIM")
for i = 2, 3 do assert(find(row(i), "Claim").Visible == false) end
-- a lost answer (the call throws): the token is kept and reused
local attempts = 0
local afterClaimView, afterClaimState = realView({{kind = "food_eaten", amount = 10}}, {"T1"})
remote.InvokeServer = function(_, request)
 table.insert(calls, copy(request))
 if request.action == "view" then return {ok = true, view = copy(view)} end
 attempts += 1
 if attempts == 1 then error("lost") end
 if attempts == 2 then return {ok = true, status = "claimed", grant = {crystals = 10, xp = 0}, view = copy(afterClaimView)} end
 return {ok = false, reason = "already_claimed"}
end
local before = #calls
claim.Activated:fire()
assert(claim.Text == "..." and claim.Active == false, "waiting state while the answer is out")
claim.Activated:fire() -- a second tap while waiting sends nothing
assert(#tasks == 1, "one claim in flight")
pump()
local sent = {}
for i = before + 1, #calls do if calls[i].action == "claim" then table.insert(sent, calls[i]) end end
assert(#sent == 1 and sent[1].id == "T1" and type(sent[1].token) == "string" and #sent[1].token >= 1 and #sent[1].token <= Cfg.ClaimTokenMax, "claim request {action, id, token}")
for k in sent[1] do assert(k == "action" or k == "id" or k == "token", "no other field is ever sent (no amounts, no progress)") end
assert(wait.Text == "Try again" and Rules.copyOk(wait.Text) and title.Text == "TASKS", "a lost answer says what to do next")
assert(claim.Text == "CLAIM" and claim.Active == true, "the button is back")
local firstToken = sent[1].token
claim.Activated:fire() pump()
local retry
for i = #calls, 1, -1 do if calls[i].action == "claim" then retry = calls[i] break end end
assert(retry.token == firstToken, "the retry after a lost answer uses the SAME token (claim-once)")
assert(wait.Text == "+10 crystals", "paid: the grant the server answered, nothing computed here: " .. wait.Text)
view = afterClaimView
tick()
local claimsSoFar = 0 for _, c in calls do if c.action == "claim" then claimsSoFar += 1 end end
assert(claimsSoFar == 2)
for i = 1, 3 do if row(i).Visible then assert(find(row(i), "Name").Text ~= "Eat 10 food", "the claimed task left the list") end end

-- a definite answer frees the id: the next claim uses a NEW token
local t2view = realView({{kind = "food_eaten", amount = 10}, {kind = "run_end"}}, {"T1"})
view = t2view
header.Activated:fire() header.Activated:fire() pump() tick() -- close, open again: opening asks for a fresh view
local second = row(1)
local claim2 = find(second, "Claim")
assert(find(second, "Name").Text == "Finish your first run" and claim2.Visible, "next tutorial task, finished")
remote.InvokeServer = function(_, request)
 table.insert(calls, copy(request))
 if request.action == "view" then return {ok = true, view = copy(view)} end
 return {ok = false, reason = "not_done"}
end
claim2.Activated:fire() pump()
assert(wait.Text == "Not done yet")
local tokenA
for i = #calls, 1, -1 do if calls[i].action == "claim" then tokenA = calls[i].token break end end
assert(tokenA ~= firstToken, "a new task has its own token")
claim2.Activated:fire() pump()
local tokenB
for i = #calls, 1, -1 do if calls[i].action == "claim" then tokenB = calls[i].token break end end
assert(tokenA ~= tokenB, "after a definite answer (not_done) the id gets a fresh token")

-- during a run the panel hides, folds and sends nothing; the hub shows it again
runState = "Active"
local callsInRun = #calls
for _ = 1, 60 do tick() end
assert(root.Visible == false and #calls == callsInRun, "in a run: hidden, zero remote calls")
runState = "Idle"
tick() tick()
assert(root.Visible == true and body.Visible == false, "back in the hub: shown, folded")
-- Goals panel not shown (before the first egg): hidden and silent
anchor.Visible = false
local callsHidden = #calls
for _ = 1, 60 do tick() end
assert(root.Visible == false and #calls == callsHidden, "Goals hidden (first session): the panel is hidden and silent")
anchor.Visible = true
-- BD-076: the REAL panel answers the goal line and tells GoalHud only when the top row changed
local fitHub = {width = 244, font = 17, prefix = ""}
local g0 = Panel.goalLine(fitHub)
assert(g0 and g0.claimable and string.sub(g0.text, 1, 5) == "Done!", "view loaded (second tutorial task finished): the claimable row leads the goal line")
local topChanges = 0
Panel.onTopChanged(function() topChanges += 1 end)
local function refetch() header.Activated:fire() header.Activated:fire() pump() tick() end
remote.InvokeServer = function(_, request) table.insert(calls, copy(request)) if request.action == "view" then return {ok = true, view = copy(view)} end return {ok = false, reason = "bad_request"} end
view = copy(v0)
refetch()
local g1 = Panel.goalLine(fitHub)
assert(topChanges == 1 and g1 and not g1.claimable and g1.text == "Eat 10 food: 0/10", "a changed top row notifies once: " .. tostring(g1 and g1.text))
refetch() refetch()
assert(topChanges == 1, "the same answer again (every 20 s poll) does not wake the goal line")
view = copy(v1)
refetch()
assert(topChanges == 2 and Panel.goalLine(fitHub).claimable, "a finished task notifies and is claimable")
view = t8(0)
Panel.setPlayActive(true)
refetch()
assert(Panel.goalLine(fitHub) == nil, "PLAY line on screen: an unfinished T8 gives the goal line nothing")
Panel.setPlayActive(false)
assert(Panel.goalLine({width = 600, font = 17, prefix = ""}).text == "Collect a second species" and Panel.goalLine({width = 200, font = 17, prefix = ""}).text == "Collect a second...", Panel.goalLine({width = 200, font = 17, prefix = ""}).text)
-- the server says disabled / failing: the panel stays out of the way
---------------------------------------------------------------- 7. row layout: no text rect overlaps another (1..3 rows, with and without CLAIM and a note)
-- The mock has no layout engine, so the rects are computed from Position / Size / AnchorPoint exactly as Roblox does for UDim2 (offset + scale of the
-- parent), for a visible label, button or progress bar inside the panel. A label's rect is its whole box, which is stricter than its glyphs.
local function rectOf(node, parent)
 local pos, size, anchor = node.Position, node.Size, node.AnchorPoint or {X = 0, Y = 0}
 local w = size.X.Scale * parent.w + size.X.Offset
 local h = size.Y.Scale * parent.h + size.Y.Offset
 return {x = parent.x + pos.X.Scale * parent.w + pos.X.Offset - anchor.X * w, y = parent.y + pos.Y.Scale * parent.h + pos.Y.Offset - anchor.Y * h, w = w, h = h}
end
local function strictlyOverlap(a, b) return a.x < b.x + b.w - 0.01 and b.x < a.x + a.w - 0.01 and a.y < b.y + b.h - 0.01 and b.y < a.y + a.h - 0.01 end
local function collect(rootNode)
 local rootRect = {x = 0, y = 0, w = rootNode.Size.X.Offset, h = rootNode.Size.Y.Offset}
 local items, rowRects = {}, {}
 local function walk(node, rect, rowIndex)
  for _, child in node.Children do
   if child.Visible ~= false and child.Size ~= nil and child.Position ~= nil then
    local r = rectOf(child, rect)
    local row = rowIndex
    local index = string.match(child.Name, "^Row(%d)$")
    if index then row = tonumber(index) rowRects[row] = r end
    local isText = (child.ClassName == "TextLabel" or child.ClassName == "TextButton") and child.Text ~= nil and child.Text ~= ""
    if isText or child.Name == "Bar" then table.insert(items, {name = child.Name, r = r, row = row, node = child, text = isText}) end
    if child.Name ~= "Fill" then walk(child, r, row) end
   end
  end
 end
 walk(rootNode, rootRect, nil)
 return items, rowRects, rootRect
end
local function fakeRow(id, name, done, note)
 return {id = id, name = name, note = note, progress = if done then 5 else 2, goal = 5, reward = {crystals = 10, xp = 0}, done = done, claimed = false, carried = false}
end
local function fakeView(n, claimMode, withNote)
 local note = if withNote then "Cracked eggs count too" else nil
 local long = "Hatch five eggs from the very first nest" -- 40 characters: the catalogue maximum
 local function done(i) return claimMode == "all" or (claimMode == "first" and i == 1) end
 local v = {tutorial = fakeRow("T1", long, done(1), note), short = {}, daily = {}, carry = {}, shortResetsIn = 1800, dailyResetsIn = 7200}
 if n >= 2 then v.short = {fakeRow("S1", "Eat 40 food", done(2), note)} end
 if n >= 3 then v.daily = {fakeRow("D1", "Hatch a Rare or better", done(3), note)} end
 return v
end
local function layoutSheet(width, height, touch)
 local l = TouchLayout.compute({width = width, height = height, touch = touch, navCount = 7, goals = true, objectives = true})
 local o = l.objectivesOpen
 assert(o and l.objectives, "layout gives the objectives rects at " .. width .. "x" .. height)
 return Rect_.new(o.x, o.y, o.x + o.w, o.y + o.h), Rect_.new(l.objectives.x, l.objectives.y, l.objectives.x + l.objectives.w, l.objectives.y + l.objectives.h)
end
local O = TouchLayout.OBJECTIVES
assert(O.rowGap >= 4 and O.rowGap <= 6 and O.rowH >= 48 and TouchLayout.objectivesOpenH() == O.h + 2 + O.rows * O.rowH + (O.rows - 1) * O.rowGap + 4, "open height counts rows and gaps")
local sizes = {{"desktop 1156x783", 1156, 783, false}, {"phone 836x390", 836, 390, true}, {"phone 667x375", 667, 375, true}}
local checked = 0
for _, size in sizes do
 local sheet, pill = layoutSheet(size[2], size[3], size[4])
 gui.attrs.ObjectivesRect, gui.attrs.ObjectivesOpenRect = pill, sheet
 for n = 1, 3 do
  for _, claimMode in {"none", "first", "all"} do
   for _, withNote in {false, true} do
    local label = string.format("%s, %d rows, claim %s%s", size[1], n, claimMode, if withNote then ", note" else "")
    view = fakeView(n, claimMode, withNote)
    -- open (asks for the fresh view), inspect, then fold again so the next case opens it anew
    header.Activated:fire() pump() tick()
    assert(body.Visible == true and root.Size.X.Offset == sheet.Width, label .. ": open")
    local items, rowRects, rootRect = collect(root)
    local seenRows = 0
    for _ in rowRects do seenRows += 1 end
    assert(seenRows == n, label .. ": rows shown " .. seenRows)
    for i = 1, n do
     assert(rowRects[i].h == O.rowH, label .. ": every row has the same fixed height")
     if i > 1 then
      local gap = rowRects[i].y - (rowRects[i - 1].y + rowRects[i - 1].h)
      assert(gap >= 4 and gap <= 6, label .. ": gap between rows is 4..6 px, got " .. gap)
     end
     local divider = find(row(i), "Divider")
     assert(divider and divider.BackgroundColor3 == Colors.card and divider.Visible == (i < n), label .. ": divider under every row but the last, UITheme card colour")
     if divider.Visible then
      local d = rectOf(divider, rowRects[i])
      assert(d.y >= rowRects[i].y + rowRects[i].h - 0.01 and d.y + d.h <= rowRects[i].y + rowRects[i].h + O.rowGap + 0.01, label .. ": the divider sits in the gap")
     end
    end
    for a = 1, #items do
     local item = items[a]
     if item.text then
      assert(item.node.TextSize >= 14, label .. ": " .. item.name .. " text >= 14 px")
      assert(item.r.h >= item.node.TextSize, label .. ": " .. item.name .. " box is at least one line high")
      if item.name == "Claim" then assert(item.r.w >= 44 and item.r.h >= 44, label .. ": CLAIM >= 44 x 44") end
     end
     assert(item.r.x >= -0.01 and item.r.x + item.r.w <= rootRect.w + 0.01, label .. ": " .. item.name .. " inside the panel width")
     if item.row then
      local rr = rowRects[item.row]
      assert(item.r.y >= rr.y - 0.01 and item.r.y + item.r.h <= rr.y + rr.h + 0.01, label .. ": " .. item.name .. " inside its row (row " .. item.row .. ")")
      if item.name == "Claim" then
       assert(math.abs((item.r.y + item.r.h / 2) - (rr.y + rr.h / 2)) <= 0.5, label .. ": CLAIM vertically centred in its own row")
      end
     end
     for b = a + 1, #items do
      assert(not strictlyOverlap(item.r, items[b].r), string.format("%s: %s (%.0f,%.0f %.0fx%.0f) overlaps %s (%.0f,%.0f %.0fx%.0f)", label, item.name, item.r.x, item.r.y, item.r.w, item.r.h, items[b].name, items[b].r.x, items[b].r.y, items[b].r.w, items[b].r.h))
     end
    end
    for i = 1, n do
     local r = find(row(i), "Note")
     assert((r.Visible == true) == withNote, label .. ": the note shows exactly when the row has one")
     if withNote then assert(r.Text == "Cracked eggs count too" and r.TextSize >= 14 and r.TextColor3 ~= Colors.text, label .. ": note is small, >= 14 px and in the toned UITheme colour") end
    end
    -- the scroll canvas holds every row; the desktop sheet shows all of them without scrolling
    local bodyTop = O.h + 2
    assert(body.CanvasSize.Y.Offset >= rowRects[n].y + rowRects[n].h - bodyTop - 0.01, label .. ": canvas holds the rows")
    if not size[4] then
     assert(rowRects[n].y + rowRects[n].h <= rootRect.h + 0.01, label .. ": the desktop sheet is tall enough for " .. n .. " rows")
    end
    header.Activated:fire() pump() tick()
    assert(body.Visible == false, label .. ": folds")
    checked += 1
   end
  end
 end
end
assert(checked == 3 * 3 * 3 * 2)
print("Rows passed: " .. checked .. " layouts (1 to 3 rows, no / first / every CLAIM, with and without a note) at desktop, 836x390 and 667x375: no text or bar rect overlaps another, equal fixed row height, 4..6 px gaps with a divider, CLAIM centred and >= 44 px, text >= 14 px, note >= 14 px")
---------------------------------------------------------------- OB2: the real ObjectiveSeen.luau (FusionMenu's one-time T9 report)
do
 local seenCfg = {ObjectivesEnabled = false}
 local lookups, sent, queued = 0, {}, {}
 local seenAnswer = function(_) return {ok = true, status = "seen"} end
 local seenRemote = {IsA = function(_, c) return c == "RemoteFunction" end,
  InvokeServer = function(_, request) table.insert(sent, copy(request)) return seenAnswer(request) end}
 local hasRemote = true
 local seenFolder = {FindFirstChild = function(_, name) if name == "ObjectiveAction" and hasRemote then return seenRemote end return nil end}
 local seenRepl = {Shared = {Config = "Config"}, FindFirstChild = function(_, name) lookups += 1 if name == "BeDinoRemotes" then return seenFolder end return nil end}
 local seenGame = {GetService = function(_, name) assert(name == "ReplicatedStorage") return seenRepl end}
 local waited = 0
 local seenTask = {spawn = function(fn) table.insert(queued, fn) end, wait = function(s) waited += s return s end}
 local seenRequire = function(id) assert(id == "Config") return seenCfg end
 local function loadSeen() return (function(game, task, require) @@SEEN_SRC@@ end)(seenGame, seenTask, seenRequire) end
 local function drain() while #queued > 0 do table.remove(queued, 1)() end end
 local Seen = loadSeen()
 assert(lookups == 0 and #sent == 0, "requiring the module does nothing")
 -- flag off: nothing is looked up, nothing is spawned, nothing is sent, however often the menu opens
 for _ = 1, 5 do Seen.report("fusion_menu") end
 drain()
 assert(lookups == 0 and #sent == 0 and #queued == 0, "flag off: the client sends nothing and does not even look for the remote")
 -- flag on but the server flag is off (no remote): still nothing
 seenCfg.ObjectivesEnabled = true
 hasRemote = false
 Seen.report("fusion_menu") drain()
 assert(#sent == 0, "no ObjectiveAction remote: nothing sent")
 hasRemote = true
 -- flag on: exactly one request of exactly one shape, and the menu does not wait for it (it is spawned)
 Seen.report("fusion_menu")
 assert(#sent == 0 and #queued == 1, "the request is spawned, never made inline")
 Seen.report("fusion_menu")
 assert(#queued == 1, "a second open while the first is in flight sends nothing")
 drain()
 assert(#sent == 1 and sent[1].action == "seen" and sent[1].id == "fusion_menu", "the report")
 local keys = 0 for _ in sent[1] do keys += 1 end
 assert(keys == 2, "no amount, no objective id, no reward: only {action, id}")
 for _ = 1, 3 do Seen.report("fusion_menu") end drain()
 assert(#sent == 1, "after an answer it is never sent again this session")
 -- "not yet" answers are asked again on the next open; a definite refusal is not
 for _, reason in {"rate_limited", "no_dino"} do
  sent = {} Seen = loadSeen()
  seenAnswer = function(_) return {ok = false, reason = reason} end
  Seen.report("fusion_menu") drain() Seen.report("fusion_menu") drain()
  assert(#sent == 2, reason .. ": asked again on the next open")
 end
 -- BD-616: "not_opened" (the menu's own request had not landed yet) is asked once more after a short wait, then again on the next open
 sent = {} Seen = loadSeen() waited = 0
 seenAnswer = function(_) return {ok = false, reason = "not_opened"} end
 Seen.report("fusion_menu") drain()
 assert(#sent == 2 and waited > 0, "not_opened: one more try after a short wait (" .. #sent .. " sent)")
 Seen.report("fusion_menu") drain()
 assert(#sent == 4, "not_opened is not final: the next open asks again")
 local lateCalls = 0
 sent = {} Seen = loadSeen()
 seenAnswer = function(_) lateCalls += 1 if lateCalls == 1 then return {ok = false, reason = "not_opened"} end return {ok = true, status = "seen"} end
 Seen.report("fusion_menu") drain() Seen.report("fusion_menu") drain()
 assert(#sent == 2, "not_opened then seen: the retry succeeds and the report is final")
 sent = {} Seen = loadSeen()
 seenAnswer = function(_) return nil end
 Seen.report("fusion_menu") drain() Seen.report("fusion_menu") drain()
 assert(#sent == 2, "no answer: retry on the next open")
 sent = {} Seen = loadSeen()
 seenAnswer = function(_) return {ok = false, reason = "unknown_objective"} end
 Seen.report("fusion_menu") drain() Seen.report("fusion_menu") drain()
 assert(#sent == 1, "a definite refusal is final")
 print("Seen passed: real ObjectiveSeen.luau: flag off sends nothing and looks nothing up, one shape {action, id}, spawned, once per session, retries only on not-yet answers")
end
print("Panel passed: real ObjectivesPanel.luau on a GUI mock: folded one-liner and chip, open rows, CLAIM only on a finished task (>= 44 px), claim request {action,id,token}, waiting state, retry with the same token, fresh token after a definite answer, silent in a run and before the first egg")

---------------------------------------------------------------- 6. BD-561: the four optional icons (docs/109 section 9)
;(function()
local FAKE = "rbxassetid://1234567"
local ALL_FAKE = {objective_chevron = FAKE, objective_arrow = FAKE, notify_crystal = FAKE, notify_star = FAKE}
local P, GAP = Rules.IconPx, Rules.IconGap
local function boxOverlap(a, b) return a.x0 < b.x1 - 0.01 and b.x0 < a.x1 - 0.01 and a.y0 < b.y1 - 0.01 and b.y0 < a.y1 - 0.01 end

-- 6a. pure geometry
assert(Rules.Slots.chevron == "objective_chevron" and Rules.Slots.arrow == "objective_arrow" and Rules.Slots.crystal == "notify_crystal" and Rules.Slots.star == "notify_star")
for key, px in P do assert(px <= 44 and px >= 20, "docs/109 s9: icons are 20 to 44 px: " .. key) end
assert(Rules.fitWords("Equip a dino in the Index", 1000, 15) == "Equip a dino in the Index")
assert(Rules.fitWords("Equip a dino in the Index", 90, 15) == "Equip a dino..." or Rules.fitWords("Equip a dino in the Index", 90, 15) == "Equip...", "whole words")
assert(Rules.fitWords("Equip a dino in the Index", 5, 15) == nil and Rules.fitWords("", 0, 15) == "")
assert(Rules.wrapLines("Hatch 3 eggs", 1000, 15) == 1 and Rules.wrapLines("Hatch 3 eggs", 70, 15) == 2 and Rules.wrapLines("Supercalifragilisticexpialidocious", 60, 15) == math.huge)
local fitChecked = 0
for _, e in Cfg.Catalogue do
 for width = 20, 320, 7 do
  local out = Rules.fitWords(e.name, width, 15)
  if out ~= nil then
   fitChecked += 1
   assert(Rules.textWidth(out, 15) <= width, "fits: " .. out)
   local words, outWords = wordsOf(e.name), wordsOf((string.gsub(out, "%.%.%.$", "")))
   for i, word in outWords do assert(word == words[i], "whole words only: '" .. out .. "' from '" .. e.name .. "'") end
   assert(not string.find(out, " a%.%.%.") and not string.find(out, " the%.%.%.") and not string.find(out, " toward%.%.%.") and Rules.copyOk(out))
  end
 end
end
assert(fitChecked > 100)

-- The header geometry: no overlap, inside the panel, the chevron and the chip keep their places, the arrow / star yield first.
local function range(x, w) return {x0 = x, x1 = x + w, y0 = 0, y1 = 1} end
local legacy = Rules.headerLayout(220, {chip = true})
assert(legacy.chipX == 220 - 64 and legacy.titleX == 42 and legacy.titleW == 220 - 42 - 68 and legacy.chevronX == nil and legacy.arrowX == nil and legacy.starX == nil, "no icon: today's numbers")
local legacyOpen = Rules.headerLayout(300, {open = true})
assert(legacyOpen.waitInset == 10 and legacyOpen.titleW == 0.38 * 300 - 42 and legacyOpen.waitW == 0.62 * 300 - 10, "open, no icon: today's numbers")
local hdrCases = 0
for width = 150, 400, 5 do
 for mask = 0, 15 do
  local has = {chevron = mask % 2 == 1, arrow = mask // 2 % 2 == 1, star = mask // 4 % 2 == 1, chip = mask // 8 % 2 == 1}
  for _, isOpen in {false, true} do
   has.open = isOpen
   local lay = Rules.headerLayout(width, has)
   hdrCases += 1
   assert(lay.titleW >= 0 and (lay.chevronX ~= nil) == has.chevron, "chevron keeps its place")
   if has.chevron then assert(lay.chevronX + P.chevron <= width - 8 + 1e-9 and lay.chevronX >= 0) end
   if isOpen then
    assert(lay.starX == nil and lay.arrowX == nil and lay.chipX == nil)
    assert(math.abs(lay.titleX + lay.titleW - (width - lay.waitInset - lay.waitW)) < 1e-6, "open: the title ends where the words start")
    assert(not has.chevron or width - lay.waitInset <= lay.chevronX - GAP + 1e-9, "open: the words stop before the chevron")
   else
    assert((lay.chipX ~= nil) == has.chip)
    assert(not (lay.starX and lay.arrowX), "star and arrow never together")
    if lay.arrowX then assert(has.arrow and lay.titleW >= Rules.MinTitle, "arrow only with room") end
    if lay.starX then assert(has.star and has.chip and lay.titleW >= Rules.MinTitle, "star only with room, beside the chip") end
    local items = {range(8, 28), range(lay.titleX, lay.titleW)}
    if lay.arrowX then table.insert(items, range(lay.arrowX, P.arrow)) end
    if lay.starX then table.insert(items, range(lay.starX, P.star)) end
    if lay.chipX then table.insert(items, range(lay.chipX, Rules.ChipW)) end
    if lay.chevronX then table.insert(items, range(lay.chevronX, P.chevron)) end
    for i = 1, #items do
     assert(items[i].x0 >= 0 and items[i].x1 <= width + 1e-9, "inside the panel")
     for j = i + 1, #items do assert(not boxOverlap(items[i], items[j]), "no overlap in the folded header at " .. width .. " mask " .. mask) end
    end
   end
  end
 end
end

-- The prize line: every piece inside its span, nothing overlaps, the words always fit; the star leaves first, then the gem.
local plain = Rules.prizeLayout({crystals = 10}, 100, false, {})
assert(plain.words == "+10 crystals" and plain.text.x == 0 and plain.text.w == 100 and plain.gem == nil and plain.star == nil, "no icon: today's words")
local prizeCases, withBoth, withoutStar, withoutGem = 0, 0, 0, 0
for span = 30, 320, 2 do
 for _, claimable in {false, true} do
  for _, reward in {{crystals = 10}, {crystals = 150, xp = 5}} do
   for mask = 0, 3 do
    local lay = Rules.prizeLayout(reward, span, claimable, {star = mask % 2 == 1, gem = mask // 2 == 1})
    prizeCases += 1
    assert(lay.words ~= "" and Rules.copyOk(lay.words))
    local items = {{x0 = lay.text.x, x1 = lay.text.x + lay.text.w, y0 = 0, y1 = 1}}
    if lay.star then assert(claimable and mask % 2 == 1, "star only on a finished task") table.insert(items, {x0 = lay.star, x1 = lay.star + P.row, y0 = 0, y1 = 1}) end
    if lay.gem then assert(mask // 2 == 1) table.insert(items, {x0 = lay.gem, x1 = lay.gem + P.row, y0 = 0, y1 = 1}) end
    if lay.gem or lay.star then
     assert(Rules.textWidth(lay.words, 14) <= lay.text.w + 1e-9 or lay.words == Rules.rewardText(reward) and not lay.gem, "text inside its box")
    end
    for i = 1, #items do
     assert(items[i].x0 >= -1e-9 and items[i].x1 <= span + 1e-9, "inside the span " .. span)
     for j = i + 1, #items do assert(not boxOverlap(items[i], items[j]), "no overlap in the prize line, span " .. span) end
    end
    if lay.gem and lay.star then withBoth += 1 elseif lay.gem and mask % 2 == 1 and claimable then withoutStar += 1 elseif mask // 2 == 1 and not lay.gem then withoutGem += 1 end
   end
  end
 end
end
assert(withBoth > 0 and withoutStar > 0 and withoutGem > 0, "the table covers both icons, the star dropped first, then the gem")
assert(Rules.rewardWords({crystals = 10}, true) == "+10" and Rules.rewardWords({crystals = 10, xp = 5}, true) == "+5 XP +10" and Rules.rewardWords({crystals = 10}, false) == "+10 crystals")

-- 6b. the REAL panel in a fresh mock world per run
local DEFAULT = copy(v0)
local function makeEnv(ids)
 modules.UITheme.ImageIds = ids
 modules.UITheme.MotionEnabled = true
 local hb = signal()
 local rem = newInstance("RemoteFunction") rem.Name = "ObjectiveAction"
 local st = {view = copy(DEFAULT), after = copy(afterClaimView)}
 rem.InvokeServer = function(_, request)
  if request.action == "view" then return {ok = true, view = copy(st.view)} end
  return {ok = true, status = "claimed", grant = {crystals = 10, xp = 0}, view = copy(st.after)}
 end
 local folder = newInstance("Folder") folder.Name = "BeDinoRemotes" rem.Parent = folder
 local rep = {WaitForChild = function() return sharedFolder end, FindFirstChild = function(_, n) if n == "BeDinoRemotes" then return folder end return nil end}
 local g = {GetService = function(_, name)
  if name == "HttpService" then return {GenerateGUID = function() guidCount += 1 return "guid-" .. guidCount end} end
  if name == "Players" then return {LocalPlayer = {Character = {GetAttribute = function() return "Idle" end}}} end
  if name == "ReplicatedStorage" then return rep end
  if name == "RunService" then return {Heartbeat = hb} end
  error("service " .. tostring(name))
 end}
 local gui2 = newInstance("ScreenGui") gui2.attrs = {}
 gui2.GetAttribute = function(self, name) return self.attrs[name] end
 local anchor2 = newInstance("Frame") anchor2.Visible = true
 local panel2 = loadPanel(g)
 panel2.setPlayActive(false)
 panel2.attach(gui2, anchor2)
 local e = {gui = gui2, st = st}
 e.root = find(gui2, "ObjectivesPanel")
 e.header, e.body = find(e.root, "Header"), find(e.root, "Body")
 function e.tick() clockNow += 0.6 hb:fire(0.6) pump() end
 function e.place(pill, sheet) gui2.attrs.ObjectivesRect, gui2.attrs.ObjectivesOpenRect = pill, sheet end
 function e.toggle() e.header.Activated:fire() pump() e.tick() end
 return e
end

local function serialize(v)
 if type(v) ~= "table" then return tostring(v) end
 local keys = {}
 for k in v do table.insert(keys, tostring(k)) end
 table.sort(keys)
 local out = {}
 for _, k in keys do table.insert(out, k .. "=" .. serialize(v[k])) end
 return "{" .. table.concat(out, ",") .. "}"
end
local PROPS = {"Position", "Size", "AnchorPoint", "Rotation", "Text", "TextSize", "TextXAlignment", "Visible", "BackgroundTransparency", "ZIndex"}
local function dump(node, path, lines)
 local parts = {path .. "/" .. node.Name, node.ClassName}
 for _, key in PROPS do local v = rawget(node, key) if v ~= nil then table.insert(parts, key .. ":" .. serialize(v)) end end
 table.insert(lines, table.concat(parts, "|"))
 for _, child in node.Children do dump(child, path .. "/" .. node.Name, lines) end
end
local function treeText(e) local lines = {} dump(e.root, "", lines) return table.concat(lines, "\n") end

-- The same walk for every state: folded, open, a finished task (folded + open), the answer to a claim.
local function walk(e, pill, sheet, viewA, viewB, visit)
 e.st.view = viewA
 e.place(pill, sheet)
 e.tick() e.tick()
 visit(e, "folded")
 e.toggle() visit(e, "open")
 e.toggle()
 e.st.view = viewB
 e.toggle() visit(e, "open_ready")
 e.toggle() visit(e, "folded_ready")
 e.toggle()
 local claimButton = find(find(e.body, "Row1"), "Claim")
 if claimButton.Visible then claimButton.Activated:fire() pump() end
 visit(e, "message")
end

-- 6c. every id empty = the panel without the feature: whatever else sits in Theme.ImageIds, the tree and every number are the same, and no icon exists
local rectPill, rectSheet = Rect_.new(278, 72, 498, 116), Rect_.new(278, 72, 559, 261)
local function record(e, label, into) into[label] = treeText(e) end
local reference
for name, ids in {nothing = false, empty = {}, unrelated = {trophy = "rbxassetid://5", paint_bucket = "rbxassetid://7"}, blanks = {objective_chevron = "", objective_arrow = "", notify_crystal = "", notify_star = ""}} do
 local e = makeEnv(if ids == false then nil else ids)
 local seen = {}
 walk(e, rectPill, rectSheet, DEFAULT, v1, function(env, label) record(env, label, seen) end)
 local text = ""
 for _, label in {"folded", "open", "open_ready", "folded_ready", "message"} do text ..= "## " .. label .. "\n" .. seen[label] .. "\n" end
 local noted = copy(DEFAULT) noted.tutorial.name, noted.tutorial.note = "Hatch 3 eggs", "Cracked eggs count too" -- a row with a hint (OB3)
 local e2, seen2 = makeEnv(if ids == false then nil else ids), {}
 walk(e2, rectPill, rectSheet, noted, v1, function(env, label) record(env, label, seen2) end)
 for _, label in {"folded", "open", "open_ready", "folded_ready", "message"} do text ..= "## noted " .. label .. "\n" .. seen2[label] .. "\n" end
 reference = reference or text
 assert(text == reference, "ids " .. name .. ": the tree is not the one without the feature")
 for _, label in {"folded", "open", "message"} do assert(not string.find(seen[label], "objective_", 1, true) and not string.find(seen[label], "notify_", 1, true), "no icon Instance") end
 local count = 0 for _ in string.gmatch(seen.folded, "Icon_") do count += 1 end
 assert(count == 1 and string.find(seen.folded, "Icon_trophy", 1, true), "only the trophy exists")
end
-- today's numbers, spelled out
do
 local e = makeEnv(nil)
 e.place(rectPill, rectSheet)
 e.st.view = DEFAULT e.tick() e.tick()
 local title, chip, wait = find(e.header, "Title"), find(e.header, "Chip"), find(e.header, "Wait")
 assert(serialize(title.Position) == serialize(UDim2_.fromOffset(42, 0)) and serialize(title.Size) == serialize(UDim2_.new(1, -110, 1, 0)), "folded title as before")
 assert(serialize(chip.Position) == serialize(UDim2_.new(1, -64, 0, 8)) and serialize(chip.Size) == serialize(UDim2_.fromOffset(56, 28)) and title.Text == "Eat 10 food", "folded chip as before")
 e.toggle()
 assert(serialize(wait.Position) == serialize(UDim2_.new(1, -10, 0.5, 0)) and serialize(wait.Size) == serialize(UDim2_.new(0.62, -10, 1, 0)) and serialize(title.Size) == serialize(UDim2_.new(0.38, -42, 1, 0)), "open words as before")
 local r1 = find(e.body, "Row1")
 local leftW = 281 - 124
 assert(serialize(find(r1, "Name").Position) == serialize(UDim2_.fromOffset(8, 3)) and serialize(find(r1, "Name").Size) == serialize(UDim2_.fromOffset(leftW, 32)), "row name as before")
 assert(find(r1, "Reward").Text == "+10 crystals" and serialize(find(r1, "Reward").Position) == serialize(UDim2_.new(1, -108, 0, 30)) and serialize(find(r1, "Reward").Size) == serialize(UDim2_.fromOffset(100, 22)), "row prize as before")
end

-- 6d. fake ids: icons in their documented spots, no overlap, text inside its box
local function boxOf(inst, pw, ph)
 local ax, ay = 0, 0
 if inst.AnchorPoint then ax, ay = inst.AnchorPoint.X, inst.AnchorPoint.Y end
 local w, h = inst.Size.X.Scale * pw + inst.Size.X.Offset, inst.Size.Y.Scale * ph + inst.Size.Y.Offset
 local x, y = inst.Position.X.Scale * pw + inst.Position.X.Offset - ax * w, inst.Position.Y.Scale * ph + inst.Position.Y.Offset - ay * h
 return {x0 = x, y0 = y, x1 = x + w, y1 = y + h}
end
local function textBox(label, pw, ph)
 local b = boxOf(label, pw, ph)
 local w = math.min(Rules.textWidth(label.Text, label.TextSize), b.x1 - b.x0)
 if label.TextXAlignment == Enum_.TextXAlignment.Right then b.x0 = b.x1 - w
 elseif label.TextXAlignment == Enum_.TextXAlignment.Center then local c = (b.x0 + b.x1) / 2 b.x0, b.x1 = c - w / 2, c + w / 2
 else b.x1 = b.x0 + w end
 return b
end
local function icon(parent, key) return find(parent, "Icon_" .. key) end
local function shown(node) return node ~= nil and node.Visible == true end
local stats = {arrowNote = 0, noteCut = 0, arrowFolded = 0, starFolded = 0, arrowRow = 0, starRow = 0, gemRow = 0, gemMessage = 0, cuts = 0, canvases = 0}
local GROUP = {}
for _, e in Cfg.Catalogue do GROUP[e.name] = e.group end

local function checkNoOverlap(items, w, h, what)
 for i = 1, #items do
  local a = items[i]
  assert(a.x0 >= -0.01 and a.x1 <= w + 0.01 and a.y0 >= -0.01 and a.y1 <= h + 0.01, what .. ": " .. items[i].name .. " leaves the panel")
  for j = i + 1, #items do assert(not boxOverlap(a, items[j]), what .. ": " .. a.name .. " overlaps " .. items[j].name) end
 end
end

local function checkHeader(e, label)
 local W = e.root.Size.X.Offset
 local title, chip, wait = find(e.header, "Title"), find(e.header, "Chip"), find(e.header, "Wait")
 local chevron, arrow, star, gem = icon(e.header, "objective_chevron"), icon(e.header, "objective_arrow"), icon(e.header, "notify_star"), icon(e.header, "notify_crystal")
 local isOpen = e.body.Visible
 local items = {{name = "trophy", x0 = 8, y0 = 8, x1 = 36, y1 = 36}}
 local function add(name, b) b.name = name table.insert(items, b) end
 local t = textBox(title, W, 44) t.y0, t.y1 = 8, 36 add("title", t)
 if isOpen then local w = textBox(wait, W, 44) w.y0, w.y1 = 8, 36 add("words", w) end
 if chip.Visible then add("chip", boxOf(chip, W, 44)) end
 for name, node in {chevron = chevron, arrow = arrow, star = star, gem = gem} do
  if shown(node) then local b = boxOf(node, W, 44) add(name, b) end
 end
 checkNoOverlap(items, W, 44, label .. " header @" .. W)
 -- the chevron is always there and turns over when open; the arrow lives on a folded tutorial task, the star beside a Done chip
 assert(shown(chevron) and chevron.Rotation == (if isOpen then 180 else 0), label .. ": chevron at the right end, turned when open")
 assert(boxOf(chevron, W, 44).x1 == W - 8 and chevron.Size.X.Offset == P.chevron, "chevron 24 px, 8 px from the right edge")
 if isOpen then assert(not shown(arrow) and not shown(star), "open: arrow and star belong to the rows") end
 if shown(arrow) then assert(not isOpen and chip.Visible, "folded arrow beside the task") stats.arrowFolded += 1 end
 if shown(star) then assert(not isOpen and find(chip, "ChipText").Text == "Done!", "folded star beside the Done chip") stats.starFolded += 1 end
 if shown(gem) then assert(isOpen and wait.Text == "+10", "gem only after a reward number") stats.gemMessage += 1 end
 if not isOpen then
  local cut = find(chip, "ChipText").Text
  -- text fits its box by the pure estimate, or it is the single fallback word
  assert(Rules.textWidth(title.Text, title.TextSize) <= title.Size.X.Offset + 0.01 or title.Text == "Task", label .. ": folded text fits " .. title.Text)
  if string.sub(title.Text, -3) == "..." then stats.cuts += 1 end
 end
end

local ROW = TouchLayout.OBJECTIVES.rowH
local function glyph(label, pw, lines) -- the box of the glyphs: one text line is about 1.15 x the font size high (the label box is taller)
 local b = textBox(label, pw, ROW)
 b.y1 = b.y0 + math.ceil(label.TextSize * 1.15) * lines
 return b
end
local function checkRows(e, label)
 local W = e.root.Size.X.Offset
 for i = 1, 3 do
  local row = find(e.body, "Row" .. i)
  if row.Visible then
   local name, note, count, reward, claim, bar = find(row, "Name"), find(row, "Note"), find(row, "Count"), find(row, "Reward"), find(row, "Claim"), find(row, "Bar")
   local arrow, star, gem = icon(row, "objective_arrow"), icon(row, "notify_star"), icon(row, "notify_crystal")
   local items = {}
   local function add(n, b) b.name = n table.insert(items, b) end
   local nb = boxOf(name, W, ROW)
   local maxLines = if note.Visible then 1 else 2
   add("name", nb) -- the whole label box, as in the row-layout test above (stricter than its glyphs)
   if note.Visible then add("note", glyph(note, W, 1)) end
   if count.Visible then add("count", glyph(count, W, 1)) end
   add("prize", glyph(reward, W, 1))
   if claim.Visible then add("claim", boxOf(claim, W, ROW)) end
   if bar.Visible then add("bar", boxOf(bar, W, ROW)) end
   for n, node in {arrow = arrow, star = star, gem = gem} do if shown(node) then add(n, boxOf(node, W, ROW)) end end
   checkNoOverlap(items, W, ROW, label .. " row " .. i .. " @" .. W)
   if shown(arrow) then
    assert(GROUP[name.Text] == "tutorial" and not claim.Visible, "the arrow is only on an unfinished tutorial task")
    assert(Rules.wrapLines(name.Text, name.Size.X.Offset, 15) <= maxLines, "the name still fits beside the arrow: " .. name.Text)
    assert(not note.Visible or Rules.textWidth(note.Text, note.TextSize) <= note.Size.X.Offset + 0.01, "the hint still fits beside the arrow")
    assert(arrow.Size.X.Offset == P.arrow and boxOf(arrow, W, ROW).x0 == 8, "arrow 28 px at the row's left")
    stats.arrowRow += 1
    if note.Visible then stats.arrowNote += 1 if string.sub(note.Text, -3) == "..." then stats.noteCut += 1 end end
   end
   if GROUP[name.Text] ~= "tutorial" then assert(not shown(arrow), "never an arrow on a short or daily task") end
   if shown(star) then assert(claim.Visible, "the star only on a finished task") stats.starRow += 1 end
   if claim.Visible == false then assert(not shown(star)) end
   if shown(gem) then assert(Rules.copyOk(reward.Text) and not string.find(reward.Text, "crystals", 1, true), "the gem replaces the word") stats.gemRow += 1 end
  end
 end
end

local function visitor(e, label)
 checkHeader(e, label)
 if e.body.Visible then checkRows(e, label) end
end

local function rect(r) return Rect_.new(r.x, r.y, r.x + r.w, r.y + r.h) end
local function canvasRects(width, height, touch)
 local layout = TouchLayout.compute({width = width, height = height, touch = touch, navCount = 7, goals = true, objectives = true})
 assert(layout.objectives and layout.objectivesOpen, "layout gives the rects")
 return rect(layout.objectives), rect(layout.objectivesOpen)
end

local sets = {}
for _, v in {{1280, 720}, {1920, 1080}, {836, 390}, {667, 375}} do
 for _, bar in (if v[1] > 1000 then {0} else {0, 36, 58}) do
  for _, touch in {true, false} do
   local pill, sheet = canvasRects(v[1], v[2] - bar, touch)
   table.insert(sets, {label = v[1] .. "x" .. (v[2] - bar) .. (if touch then " touch" else " mouse"), pill = pill, sheet = sheet})
  end
 end
end
for _, w in {190, 220, 250, 300} do table.insert(sets, {label = "pill " .. w, pill = Rect_.new(10, 10, 10 + w, 54), sheet = Rect_.new(10, 10, 10 + w, 248)}) end

local pillWidths = {}
for _, s in sets do
 stats.canvases += 1
 pillWidths[s.pill.Width] = true
 walk(makeEnv(ALL_FAKE), s.pill, s.sheet, DEFAULT, v1, visitor)
end
local widths = {} for w in pillWidths do table.insert(widths, w) end table.sort(widths)

-- every catalogue task as the first / only task, at the narrow pills and the widest one
local function oneRowView(entry)
 local view = {tutorialDone = true, short = {}, daily = {}, carry = {}}
 local row = {id = entry.id, name = entry.name, note = entry.note, progress = 0, goal = entry.goal, reward = copy(entry.reward), done = false, claimed = false}
 if entry.group == "tutorial" then view.tutorial, view.tutorialDone = row, false else table.insert(view[entry.group], row) end
 return view
end
local doneView = function(entry) local view = oneRowView(entry) local r = view.tutorial or view[entry.group][1] r.progress, r.done = entry.goal, true return view end
local nameRuns = 0
for _, w in {190, 220, 250, 300} do
 for _, entry in Cfg.Catalogue do
  local pill, sheet = Rect_.new(10, 10, 10 + w, 54), Rect_.new(10, 10, 10 + w, 248)
  local e = makeEnv(ALL_FAKE)
  walk(e, pill, sheet, oneRowView(entry), doneView(entry), visitor)
  nameRuns += 1
  -- folded text: the full name, or a whole-word cut, or the one fallback word; at 190 nothing but trophy, title, chip and chevron
  local e2 = makeEnv(ALL_FAKE)
  e2.place(pill, sheet) e2.st.view = oneRowView(entry) e2.tick() e2.tick()
  local title = find(find(e2.root, "Header"), "Title")
  local words = wordsOf((string.gsub(title.Text, "%.%.%.$", "")))
  local nameWords = wordsOf(entry.name)
  if title.Text ~= "Task" then for i, word in words do assert(word == nameWords[i], "whole words only at " .. w .. ": '" .. title.Text .. "' from '" .. entry.name .. "'") end end
  if w == 190 then
   assert(not shown(icon(find(e2.root, "Header"), "objective_arrow")) and not shown(icon(find(e2.root, "Header"), "notify_star")), "190 px: no room for the arrow, the chevron and the chip stay")
   assert(shown(icon(find(e2.root, "Header"), "objective_chevron")) and find(find(e2.root, "Header"), "Chip").Visible)
  end
 end
end
assert(stats.arrowNote > 0 and stats.arrowFolded > 0 and stats.starFolded > 0 and stats.arrowRow > 0 and stats.starRow > 0 and stats.gemRow > 0 and stats.gemMessage > 0 and stats.cuts > 0, "the walk covers every icon: " .. serialize(stats))

-- the documented spots at the widest pill, and the arrow's rules
do
 local e = makeEnv(ALL_FAKE)
 local pill, sheet = Rect_.new(10, 10, 310, 54), Rect_.new(10, 10, 310, 248)
 e.place(pill, sheet) e.st.view = DEFAULT e.tick() e.tick()
 local header = e.header
 assert(shown(icon(header, "objective_arrow")) and find(header, "Title").Text == "Eat 10 food", "folded: the arrow beside the first tutorial task")
 assert(boxOf(icon(header, "objective_arrow"), 300, 44).x1 <= find(header, "Title").Position.X.Offset, "the arrow is left of the name")
 e.toggle()
 local r1, r2, r3 = find(e.body, "Row1"), find(e.body, "Row2"), find(e.body, "Row3")
 assert(shown(icon(r1, "objective_arrow")) and not shown(icon(r2, "objective_arrow")) and not shown(icon(r3, "objective_arrow")), "open: the arrow on the tutorial row only")
 assert(shown(icon(r1, "notify_crystal")) and shown(icon(r2, "notify_crystal")) and shown(icon(r3, "notify_crystal")) and find(r1, "Reward").Text == "+10", "the gem follows the prize number on every row")
 assert(not shown(icon(r1, "notify_star")), "no star before the task is finished")
 e.toggle() e.st.view = v1 e.toggle()
 local ready = find(e.body, "Row1")
 assert(find(ready, "Claim").Visible and shown(icon(ready, "notify_star")) and shown(icon(ready, "notify_crystal")) and not shown(icon(ready, "objective_arrow")), "finished: star + prize + gem, no arrow")
 assert(boxOf(icon(ready, "notify_star"), 300, 60).x1 <= boxOf(icon(ready, "notify_crystal"), 300, 60).x0, "star, then the prize, then the gem")
 e.toggle()
 assert(shown(icon(e.header, "notify_star")) and find(find(e.header, "Chip"), "ChipText").Text == "Done!" and not shown(icon(e.header, "objective_arrow")), "folded: the star left of the Done chip")
 assert(boxOf(icon(e.header, "notify_star"), 300, 44).x1 <= find(e.header, "Chip").Position.X.Offset, "the star is left of the chip")
 e.toggle()
 find(find(e.body, "Row1"), "Claim").Activated:fire() pump()
 local wait = find(e.header, "Wait")
 assert(wait.Text == "+10" and shown(icon(e.header, "notify_crystal")), "the answer to a claim: the number, then the gem")
 local gemBox, numberBox = boxOf(icon(e.header, "notify_crystal"), 300, 44), textBox(wait, 300, 44)
 assert(numberBox.x1 <= gemBox.x0 and gemBox.x0 - numberBox.x1 <= 4 and gemBox.x1 == 300 - 8 - P.chevron - GAP, "the gem sits right after the number, before the chevron")
end
do -- the bob: 3 px every half second, still when motion is off
 local e = makeEnv(ALL_FAKE)
 e.place(Rect_.new(10, 10, 310, 54), Rect_.new(10, 10, 310, 248)) e.st.view = DEFAULT e.tick() e.tick()
 local arrow = icon(e.header, "objective_arrow")
 local ys = {}
 for _ = 1, 6 do e.tick() ys[arrow.Position.Y.Offset] = true end
 local count = 0 for _ in ys do count += 1 end
 assert(count == 2 and ys[8] and ys[11], "the arrow bobs between two heights 3 px apart")
 modules.UITheme.MotionEnabled = false
 ys = {}
 for _ = 1, 6 do e.tick() ys[arrow.Position.Y.Offset] = true end
 count = 0 for _ in ys do count += 1 end
 assert(count == 1 and ys[8], "Reduce Motion: no bob")
 modules.UITheme.MotionEnabled = true
end

print(string.format("Icons passed: slots empty = the same Instance tree and numbers as a panel without icons (4 ImageIds variants, 5 states); fake ids on %d canvases and pills (%s px wide): header %d cases, prize line %d cases, no overlap, whole-word cuts (%d cut titles), %d name runs; arrows %d folded / %d rows, stars %d folded / %d rows, gems %d rows / %d answers",
 stats.canvases, table.concat(widths, "/"), hdrCases, prizeCases, stats.cuts, nameRuns, stats.arrowFolded, stats.arrowRow, stats.starFolded, stats.starRow, stats.gemRow, stats.gemMessage))
end)()
'''


def script() -> str:
    panel_src = read('src/client/ObjectivesPanel.luau')
    text = LUAU.replace('@@SEEN_SRC@@', read('src/client/ObjectiveSeen.luau'))
    for token, path in [
        ('@@CONFIG@@', 'src/shared/Config.luau'),
        ('@@PHONE_SCALE@@', 'src/shared/PhoneScale.luau'),
        ('@@TOUCH_LAYOUT@@', 'src/shared/TouchLayout.luau'),
        ('@@OBJ_CONFIG@@', 'src/shared/ObjectiveConfig.luau'),
        ('@@OBJ_RULES@@', 'src/shared/ObjectiveRules.luau'),
        ('@@PANEL_RULES@@', 'src/shared/ObjectivePanelRules.luau'),
        ('@@NEXT_GOAL@@', 'src/shared/NextGoal.luau'),
    ]:
        text = text.replace(token, module(path))
    return text.replace('@@PANEL_SRC@@', panel_src)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args(argv)
    errors = static_errors()
    for path in ('docs/66-intake-mini-objectives.md',):
        if '## 18.' not in read(path):
            errors.append(f'{path}: section 18 (BD-075 panel) missing')
    for error in errors:
        print('FAIL:', error)
    if errors:
        return 1
    print('Static passed: flag-off identity (module only behind the flag, no top-level effect, one server call site, rects published only under the flag), no client reward maths, floors, existing UI parts only')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'objectives_panel.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        print(result.stderr, end='')
        if result.returncode == 0 and 'Panel passed' in result.stdout and 'Goal line passed' in result.stdout and 'Icons passed' in result.stdout:
            print('Objectives panel verification passed (BD-075, BD-076, BD-561).')
            return 0
        return result.returncode or 1


if __name__ == '__main__':
    raise SystemExit(main())
