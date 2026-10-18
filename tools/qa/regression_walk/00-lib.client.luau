--!nocheck
-- BD-541 / docs/145 s9: first-session regression walk, CLIENT library. Run this FIRST (Studio MCP execute_luau, CLIENT datamodel, Play mode).
-- It only installs helpers into shared.BDWalk and prints the capabilities it found. Nothing here writes game state: the steps tap the
-- real buttons (VirtualInputManager) or fire the very remotes those buttons fire. Order and meaning: tools/qa/regression_walk/README.md.
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")
local LogService = game:GetService("LogService")
local GuiService = game:GetService("GuiService")
local HttpService = game:GetService("HttpService")
local player = Players.LocalPlayer
local W = {lib = 2, results = {}, mem = {}, steps = {}, needs = {}, keep = {}} -- keep: facts later steps compare against (eggs caught, species, run ids)
shared.BDWalk = W
W.player = player

-- ---------------------------------------------------------------- time, waiting, one call's time budget
function W.wait(cond, timeout, step)
    local stop = time() + (timeout or 5)
    while true do
        local ok, v = pcall(cond)
        if ok and v then return v end
        if time() >= stop then return nil end
        task.wait(step or 0.1)
    end
end
function W.left() return (W.deadline or math.huge) - time() end -- seconds left in THIS execute_luau call (steps hand back CONTINUE when it runs low)

-- ---------------------------------------------------------------- game handles
function W.gui() local pg = player:FindFirstChild("PlayerGui") return pg and pg:FindFirstChild("BeDinoUI") end
function W.root() local c = player.Character return c and c:FindFirstChild("HumanoidRootPart") end
function W.hum() local c = player.Character return c and c:FindFirstChildOfClass("Humanoid") end
function W.rs() local c = player.Character return c and c:GetAttribute("RunState") end
function W.cattr(name) local c = player.Character return c and c:GetAttribute(name) end
function W.remotes() return RS:FindFirstChild("BeDinoRemotes") end
function W.remote(name) local f = W.remotes() return f and f:FindFirstChild(name) end
local PS = nil -- the game's own client cache of the owner-only values (Client/PrivateState.luau); public names fall through to attributes
pcall(function() PS = require(player.PlayerScripts.Client.PrivateState) end)
W.privOk = PS ~= nil
function W.priv(name)
    if PS then
        local ok, v = pcall(PS.get, name)
        if ok and v ~= nil then return v end
    end
    return player:GetAttribute(name)
end
function W.num(name) local v = W.priv(name) return type(v) == "number" and v or 0 end
function W.json(name)
    local v = W.priv(name)
    if type(v) ~= "string" or v == "" then return nil end
    local ok, d = pcall(function() return HttpService:JSONDecode(v) end)
    return ok and d or nil
end
function W.mod(path) -- require a game module by "Shared.Name" or "Client.Name"; nil when it is not there
    local a, b = string.match(path, "^(%w+)%.(%w+)$")
    local root = if a == "Shared" then RS:FindFirstChild("Shared") else player:FindFirstChild("PlayerScripts") and player.PlayerScripts:FindFirstChild("Client")
    local m = root and root:FindFirstChild(b)
    if not m then return nil end
    local ok, v = pcall(require, m)
    return ok and v or nil
end
function W.admin(...) -- the admin panel's own RemoteFunction (unpublished Studio: everyone is admin)
    local r = W.remote("AdminAction")
    if not r then return nil, "no AdminAction remote" end
    local ok, a, b = pcall(function(...) return r:InvokeServer(...) end, ...)
    if not ok then return nil, tostring(a) end
    return a, b
end

-- ---------------------------------------------------------------- gui helpers
function W.visible(o)
    local cur = o
    while cur and cur ~= game do
        if cur:IsA("GuiObject") and not cur.Visible then return false end
        if cur:IsA("ScreenGui") and not cur.Enabled then return false end
        cur = cur.Parent
    end
    return o.AbsoluteSize.X > 0 and o.AbsoluteSize.Y > 0
end
function W.find(root, pred)
    if not root then return nil end
    for _, d in root:GetDescendants() do if pred(d) then return d end end
    return nil
end
function W.texts(root)
    local out = {}
    if not root then return out end
    for _, d in root:GetDescendants() do
        if (d:IsA("TextLabel") or d:IsA("TextButton")) and d.Text ~= "" and W.visible(d) then table.insert(out, d.Text) end
    end
    return out
end
function W.hasExact(root, text) for _, t in W.texts(root) do if t == text then return true end end return false end
function W.hasMatch(root, pat) for _, t in W.texts(root) do if string.find(t, pat) then return t end end return nil end
function W.btn(root, text, prefix) -- a visible TextButton by its text (exact, or prefix)
    return W.find(root, function(d)
        return d:IsA("TextButton") and W.visible(d) and (d.Text == text or (prefix and string.sub(d.Text, 1, #text) == text))
    end)
end
function W.rail(dest) -- a rail button (Bootstrap tags each with the attribute Destination)
    local g = W.gui()
    return g and W.find(g, function(d) return d:IsA("TextButton") and d:GetAttribute("Destination") == dest end)
end
function W.leapLabel() -- the LEAP button has no Text of its own: its label starts with "LEAP"
    local g = W.gui()
    return g and W.find(g, function(d) return d:IsA("TextLabel") and string.find(d.Text, "^LEAP") ~= nil end)
end
function W.scrim() local g = W.gui() return g and g:FindFirstChild("ModalScrim") end
function W.modalOpen(title) -- a menu is open (and its heading is `title`, when given)
    local s = W.scrim()
    return s ~= nil and W.visible(s) and (title == nil or W.hasExact(s, title))
end
function W.closeModal() -- Bootstrap's own close() through its documented client hook (docs/133 DemoCloseModal)
    player:SetAttribute("DemoCloseModal", true)
    return W.wait(function() return not W.modalOpen() end, 2)
end

-- BD-1019 (docs/181): is `o` reachable by a tap? The engine's own hit test lists what sits at o's centre, topmost first; the first object that
-- takes input (a button, or Active) must be o or something inside it. Returns nil when o is reachable, else the object that covers it.
-- Owner bug 2026-10-18: a full-screen tap catcher sat above the hatch menu, so X did nothing. AbsolutePosition may or may not include the top
-- bar (same doubt as W.tap), so the centre is tried both ways: reachable if either answer is o.
function W.cover(o)
    local pg = player:FindFirstChild("PlayerGui")
    if not pg then return nil end
    local c = W.center(o)
    local inset = GuiService:GetGuiInset()
    local first = nil
    for _, pos in {c, c + inset} do
        local ok, list = pcall(function() return pg:GetGuiObjectsAtPosition(pos.X, pos.Y) end)
        if ok then
            for _, d in list do
                if d:IsA("GuiButton") or d.Active then
                    if d == o or d:IsDescendantOf(o) then return nil end
                    first = first or d
                    break
                end
            end
        end
    end
    return first
end
-- Adds the "X is reachable on the open menu" check when a menu is open (called for every step at report time and by the hatch step).
function W.closeCheck(list)
    local s = W.scrim()
    if not (s and W.visible(s)) then return end
    local x = W.btn(s, "X")
    if not x then W.add(list, false, "the open menu has no X button") return end
    local blocker = W.cover(x)
    local a = x.AbsoluteSize
    W.add(list, blocker == nil, if blocker == nil then "X is reachable on the open menu" else "X is COVERED by " .. blocker.Name .. " (" .. blocker.ClassName .. ", ZIndex " .. blocker.ZIndex .. ")")
    W.add(list, a.X >= 44 and a.Y >= 44, string.format("X is %.0fx%.0f px (44 minimum)", a.X, a.Y))
end

-- HUD rectangles that must never overlap each other (BD-531 / BD-524 are exactly such overlaps)
function W.hudRects()
    local g = W.gui()
    local r = {}
    if not g then return r end
    local railButton = W.find(g, function(d) return d:IsA("TextButton") and d:GetAttribute("Destination") ~= nil end)
    if railButton then r.rail = railButton.Parent end
    local shop = g:FindFirstChild("OpenShop", true)
    if shop then r.crystals = shop.Parent end
    r.eggs = g:FindFirstChild("EggsPlate", true)
    r.sizeBar, r.goalHint, r.home = g:FindFirstChild("SizeBar"), g:FindFirstChild("GoalHint"), g:FindFirstChild("HomeButton")
    r.nextGoal = g:FindFirstChild("NextGoal", true)
    local leap = W.leapLabel()
    if leap and leap.Parent and leap.Parent.Parent then r.timers = leap.Parent.Parent end
    local pg = player:FindFirstChild("PlayerGui")
    local feedback = pg and W.find(pg, function(d) return d:IsA("TextButton") and string.find(d.Text, "Tell us") ~= nil end)
    if feedback then r.feedback = feedback end
    return r
end
function W.overlaps(rects) -- list of "a/b WxH" for every visible pair that overlaps by more than 4 px both ways, plus off-screen ones
    local names, bad = {}, {}
    for k in rects do table.insert(names, k) end
    table.sort(names)
    local g = W.gui()
    for i = 1, #names do
        local a = rects[names[i]]
        if W.visible(a) then
            if g then
                local gp, gs = g.AbsolutePosition, g.AbsoluteSize
                local ap, as = a.AbsolutePosition, a.AbsoluteSize
                if ap.X < gp.X - 2 or ap.Y < gp.Y - 2 or ap.X + as.X > gp.X + gs.X + 2 or ap.Y + as.Y > gp.Y + gs.Y + 2 then table.insert(bad, names[i] .. " off screen") end
            end
            for j = i + 1, #names do
                local b = rects[names[j]]
                if W.visible(b) then
                    local ap, as, bp, bs = a.AbsolutePosition, a.AbsoluteSize, b.AbsolutePosition, b.AbsoluteSize
                    local ox = math.min(ap.X + as.X, bp.X + bs.X) - math.max(ap.X, bp.X)
                    local oy = math.min(ap.Y + as.Y, bp.Y + bs.Y) - math.max(ap.Y, bp.Y)
                    if ox > 4 and oy > 4 then table.insert(bad, string.format("%s/%s %.0fx%.0f", names[i], names[j], ox, oy)) end
                end
            end
        end
    end
    return bad
end

-- ---------------------------------------------------------------- input: real taps through VirtualInputManager
local VIM = nil
pcall(function() VIM = game:GetService("VirtualInputManager") end)
W.vimNote = if VIM then "found" else "service missing"
if VIM then -- the service can exist yet refuse to run for a script: probe with a harmless mouse move
    local ok, err = pcall(function() VIM:SendMouseMoveEvent(5, 5, game) end)
    if not ok then VIM = nil W.vimNote = "blocked: " .. string.sub(tostring(err), 1, 60) end
end
W.vim = VIM
function W.center(o) return o.AbsolutePosition + o.AbsoluteSize / 2 end
local function sendMouse(x, y)
    return pcall(function()
        VIM:SendMouseMoveEvent(x, y, game)
        VIM:SendMouseButtonEvent(x, y, 0, true, game, 0)
        task.wait(0.06)
        VIM:SendMouseButtonEvent(x, y, 0, false, game, 0)
    end)
end
-- "ok" (the effect showed up, or no effect was asked for) | "noeffect" (clicked, nothing changed) | "novim" (no input service here)
function W.tap(o, effect, timeout)
    if not VIM then return "novim" end
    local c = W.center(o)
    local inset = GuiService:GetGuiInset() -- the click position is screen space; AbsolutePosition may or may not include the top bar, so try both
    for _, pos in {c + inset, c} do
        local sent = sendMouse(pos.X, pos.Y)
        if not sent then return "novim" end
        if not effect then return "ok" end
        if W.wait(effect, timeout or 1.5, 0.1) then return "ok" end
    end
    return "noeffect"
end
function W.key(code)
    if not VIM then return false end
    return pcall(function()
        VIM:SendKeyEvent(true, code, false, game)
        task.wait(0.05)
        VIM:SendKeyEvent(false, code, false, game)
    end)
end
-- Make `effect()` true: already true -> nothing; else tap `getObj()`. Returns ok, why. A failed tap is recorded in W.needs so the
-- lead can click it by hand (user_mouse_input) and simply re-run the same snippet: every step is safe to repeat.
function W.ensure(effect, getObj, what, timeout)
    if effect() then return true end
    local o = getObj()
    if not o then return false, "no " .. what .. " on screen" end
    local r = W.tap(o, effect, timeout)
    if r == "ok" then return true end
    local p = W.center(o)
    local why = if r == "novim" then string.format("cannot click %s (no VirtualInputManager)", what) else string.format("clicked %s but nothing changed", what)
    table.insert(W.needs, string.format("click %s at viewport (%.0f,%.0f), then re-run the step", what, p.X, p.Y))
    return false, why .. string.format(": click it by hand at viewport (%.0f,%.0f) and re-run", p.X, p.Y)
end

-- ---------------------------------------------------------------- checks, errors, report
function W.add(list, ok, text) -- ok: true = pass, false = fail, nil = odd (cannot judge). The same text again (a step resumed after CONTINUE) updates its line.
    for _, c in list do
        if c[2] == text then c[1] = ok return ok end
    end
    table.insert(list, {ok, text})
    return ok
end
-- BD-596: Studio itself (not the game) prints about 40 "Failed to upload TexturePack ... HTTP 429" lines at each Play in an unpublished
-- place (one per SurfaceAppearance under Resources). They are counted and named in the report, never mixed into the game's errors.
W.StudioNoise = "Failed to upload TexturePack"
function W.isStudioNoise(message)
    return string.sub(message, 1, #W.StudioNoise) == W.StudioNoise
end
function W.errors(since)
    local out = {}
    for _, e in LogService:GetLogHistory() do
        if e.messageType == Enum.MessageType.MessageError and e.timestamp >= since and not W.isStudioNoise(e.message) then table.insert(out, e.message) end
    end
    return out
end
function W.studioNoise(since)
    local n = 0
    for _, e in LogService:GetLogHistory() do
        if e.messageType == Enum.MessageType.MessageError and e.timestamp >= since and W.isStudioNoise(e.message) then n += 1 end
    end
    return n
end
function W.errCheck(list, since)
    local e = W.errors(since)
    W.add(list, #e == 0, if #e == 0 then "no new errors" else string.format("%d new error(s): %s", #e, string.sub(e[1], 1, 90)))
    local noise = W.studioNoise(since)
    if noise > 0 then W.add(list, true, "Studio TexturePack upload lines not counted: " .. noise .. " (BD-596)") end
end
function W.capture(n, note)
    local cam = workspace.CurrentCamera
    if not cam then print(string.format("CAPTURE %02d no camera", n)) return end
    local p = cam.CFrame.Position
    local look = p + cam.CFrame.LookVector * 30
    local root = W.root()
    print(string.format("CAPTURE %02d screen_capture now: %s | cam (%.0f,%.0f,%.0f) looking at (%.0f,%.0f,%.0f) | dino %.0f studs away | viewport %.0fx%.0f",
        n, note or "the whole screen", p.X, p.Y, p.Z, look.X, look.Y, look.Z, if root then (root.Position - p).Magnitude else 0, cam.ViewportSize.X, cam.ViewportSize.Y))
end
local function line(n, verdict, name, list)
    local fails, odds, passes = {}, {}, {}
    for _, c in list do
        if c[1] == false then table.insert(fails, "FAIL " .. c[2]) elseif c[1] == nil then table.insert(odds, "ODD " .. c[2]) else table.insert(passes, c[2]) end
    end
    local parts = {}
    for _, group in {fails, odds, passes} do for _, s in group do table.insert(parts, s) end end
    return string.format("WALK %02d %s %s :: %s", n, verdict, name, table.concat(parts, " | "))
end
function W.report(n, name, list, note)
    local verdict = "PASS"
    for _, c in list do
        if c[1] == false then verdict = "FAIL" elseif c[1] == nil and verdict == "PASS" then verdict = "ODD" end
    end
    local text = line(n, verdict, name, list)
    W.results[n] = {verdict = verdict, line = text}
    print(text)
    W.capture(n, note)
    return verdict
end

-- Runs the listed steps in order. A step returns name, checks, captureNote and optionally "CONTINUE", progress text (call the snippet again).
function W.run(list)
    local only = shared.BDWalkOnly
    W.deadline = time() + (shared.BDWalkBudget or 24)
    W.needs = {}
    local from = 1
    if only == nil and W.resume ~= nil and table.find(list, W.resume) then from = table.find(list, W.resume) end -- a CONTINUE earlier: pick up there, do not repeat the finished steps
    for i = from, #list do
        local n = list[i]
        if only == nil or only == n then
            local f = W.steps[n]
            local m = W.mem[n]
            if not m then m = {since = os.time() - 1} W.mem[n] = m end
            if not f then
                W.results[n] = {verdict = "ODD", line = string.format("WALK %02d ODD step not loaded :: run its chunk file first", n)}
                print(W.results[n].line)
            else
                local ok, name, checks, note, status, progress = xpcall(f, debug.traceback, {mem = m, since = m.since})
                if not ok then
                    W.mem[n] = nil
                    W.resume = nil
                    W.report(n, "step crashed", {{false, string.sub(tostring(name), 1, 300)}}, nil)
                elseif status == "CONTINUE" then
                    W.resume = n
                    print(string.format("WALK %02d CONTINUE %s :: %s | run this snippet again (the step resumes)", n, name or "?", progress or "working"))
                    return "CONTINUE " .. n
                else
                    W.mem[n] = nil
                    if W.resume == n then W.resume = nil end
                    pcall(W.closeCheck, checks)
                    W.errCheck(checks, m.since)
                    W.report(n, name, checks, note)
                end
            end
            if #W.needs > 0 then print("NEEDS " .. table.concat(W.needs, " ; ")) end
        end
    end
    return W.summary()
end
function W.summary()
    local keys = {}
    for n in W.results do table.insert(keys, n) end
    table.sort(keys)
    local out = {}
    for _, n in keys do table.insert(out, string.format("%02d %s", n, W.results[n].verdict)) end
    local s = "SUMMARY " .. table.concat(out, ", ")
    print(s)
    return s
end

-- ---------------------------------------------------------------- capabilities
local cam = workspace.CurrentCamera
print(string.format("WALK lib ready | VirtualInputManager %s | PrivateState cache %s | viewport %.0fx%.0f | player %s", if VIM then "works (taps are tried)" else "NOT usable (" .. W.vimNote .. "): steps print where to click",
    if W.privOk then "found" else "NOT found (public attributes only)", cam and cam.ViewportSize.X or 0, cam and cam.ViewportSize.Y or 0, player.Name))
return "lib ready"
