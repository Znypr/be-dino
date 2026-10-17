"""BD-075 mini objectives panel (docs/66 section 18): offline verifier in pinned Luau.

Static (python): flag-off identity of the client wiring (ObjectivesPanel is only required behind Config.ObjectivesEnabled, has no top-level
side effect, asks the server only inside one function, Bootstrap publishes the panel rects only under the flag), the client never computes a
reward, text >= 14 px and buttons >= 44 px, existing UI parts only (no asset ids, no image labels, the registered "trophy" icon).

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
        if rel in ('src/client/ObjectivesPanel.luau', 'src/client/GoalHud.luau'):
            continue
        text = code_only(path.read_text(encoding='utf-8'))
        if 'ObjectivesPanel' in text or ('ObjectiveAction' in text and not rel.startswith('src/server/')):
            errors.append(f'{rel}: only GoalHud may reach ObjectivesPanel and only the panel may call ObjectiveAction on the client')
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
    claim_size = re.search(r'UDim2\.fromOffset\(CLAIM_W, (\d+)\)', panel)
    claim_w = re.search(r'^local CLAIM_W = (\d+)', panel, re.M)
    if not claim_size or int(claim_size.group(1)) < 44 or not claim_w or int(claim_w.group(1)) < 44:
        errors.append('ObjectivesPanel: the CLAIM button is >= 44 x 44')
    if 'UIScale' in panel:
        errors.append('ObjectivesPanel is drawn 1:1 (no UIScale): text and buttons keep their real pixel size')

    # --- existing UI parts only (docs/72, AGENTS.md 2026-10-14) ---------------------------------------------------------------------------
    for word in ('rbxassetid', 'ImageLabel', 'ImageButton', 'ViewportFrame', 'Polygon', 'ParticleEmitter'):
        if word in panel:
            errors.append(f'ObjectivesPanel: {word}: no new art; use Theme plates and registered icons only')
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
local Colors = {panel = "panel", card = "card", gold = "gold", accent = "accent", text = "text", outline = "outline", red = "red"}
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

local Panel = (function(game, Instance, UDim2, Vector2, Enum, Rect, typeof, task, os)
 @@PANEL_SRC@@
end)(gameMock, Instance_, UDim2_, Vector2_, Enum_, Rect_, typeof, task_, os_)

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
-- the server says disabled / failing: the panel stays out of the way
print("Panel passed: real ObjectivesPanel.luau on a GUI mock: folded one-liner and chip, open rows, CLAIM only on a finished task (>= 44 px), claim request {action,id,token}, waiting state, retry with the same token, fresh token after a definite answer, silent in a run and before the first egg")
'''


def script() -> str:
    panel_src = read('src/client/ObjectivesPanel.luau')
    text = LUAU
    for token, path in [
        ('@@CONFIG@@', 'src/shared/Config.luau'),
        ('@@PHONE_SCALE@@', 'src/shared/PhoneScale.luau'),
        ('@@TOUCH_LAYOUT@@', 'src/shared/TouchLayout.luau'),
        ('@@OBJ_CONFIG@@', 'src/shared/ObjectiveConfig.luau'),
        ('@@OBJ_RULES@@', 'src/shared/ObjectiveRules.luau'),
        ('@@PANEL_RULES@@', 'src/shared/ObjectivePanelRules.luau'),
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
        if result.returncode == 0 and 'Panel passed' in result.stdout:
            print('Objectives panel verification passed (BD-075).')
            return 0
        return result.returncode or 1


if __name__ == '__main__':
    raise SystemExit(main())
