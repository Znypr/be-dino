--!strict
-- BD-075 (docs/66 section 18): the collapsible objectives panel. CLIENT ONLY and shown ONLY while Config.ObjectivesEnabled is true (GoalHud calls
-- attach() behind that flag, so with the flag off this module is never required: no Instances, no remote lookup, no request).
-- It reads the server view through the ObjectiveAction RemoteFunction ({action="view"}) and sends {action="claim", id, token} when a
-- CLAIM button is tapped. It never computes a reward, a progress value or a window: every number comes from the server view.
-- Pure choices (which 3 rows, the folded line, the words, claim answers) live in Shared/ObjectivePanelRules (tools/verify_objectives_panel.py).
-- Pattern: GoalsPanel (existing UI parts only: Theme.decorate plates, the registered "trophy" icon, no new art, no asset ids).
-- Folded: ONE 44 px line (trophy, nearest task, progress chip). Open: header + the 3 tasks (name, progress bar, CLAIM when done) + "New tasks soon".
-- BD-561 (docs/109 section 9): four OPTIONAL icons (chevron, tutorial arrow, crystal, star), each read from Theme.ImageIds. An empty id = no Instance and no
-- reserved space, so with all four empty the panel is exactly the one without icons; geometry comes from the pure ObjectivePanelRules.headerLayout /
-- prizeLayout / fitWords (tools/verify_objectives_panel.py checks both states).
-- Placement comes from TouchLayout (published by Bootstrap as the ObjectivesRect / ObjectivesOpenRect attributes of the BeDinoUI gui), at 1:1
-- so text is >= 14 px and every button >= 44 px. Hidden during a run, like the Goals panel (the hub is where tasks are read and claimed).
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rules = require(Shared:WaitForChild("ObjectivePanelRules"))
local Theme = require(Shared:WaitForChild("UITheme"))
local TouchLayout = require(Shared:WaitForChild("TouchLayout"))
local PhoneScale = require(Shared:WaitForChild("PhoneScale"))

local Panel = {}
local state = {playActive = true, onTop = nil :: (() -> ())?, view = nil :: any, fetchedAt = 0, fetching = false, nextFetch = 0}

-- GoalHud feeds the Goals panel PLAY state through this (true = "play new dinos" is on screen and not finished, so an unfinished T8 is hidden).
function Panel.setPlayActive(active: boolean) state.playActive = active end

-- BD-076 (docs/66 s19): the top objective for the one-line goal. Pure choice (ObjectivePanelRules.select = the same rows the panel shows, so an
-- unfinished T8 stays hidden next to the Goals PLAY line); nil until the server has answered. fit = {width, font} of the goal line.
function Panel.goalLine(fit: any): any?
    if state.view == nil then return nil end
    return Rules.goalLine(Rules.select(state.view, {playGoalActive = state.playActive}), fit)
end
-- GoalHud listens here: called only when what the goal line would say about the top row changed (not on every 20 s poll).
function Panel.onTopChanged(fn: () -> ()) state.onTop = fn end
local function topKey(): string
    local top = Rules.select(state.view, {playGoalActive = state.playActive})[1]
    if top == nil then return "" end
    return string.format("%s|%d|%s", top.id, top.progress, tostring(top.claimable))
end
local function setView(view: any)
    local before = topKey()
    state.view, state.fetchedAt = view, os.clock()
    if state.onTop and topKey() ~= before then state.onTop() end
end

local HEADER_H = TouchLayout.OBJECTIVES.h -- 44: the header is a button (docs/114 s4.4 tap-target floor)
local ROW_H = TouchLayout.OBJECTIVES.rowH
local ROWS = TouchLayout.OBJECTIVES.rows
local ROW_GAP = TouchLayout.OBJECTIVES.rowGap
local PITCH = ROW_H + ROW_GAP -- one row plus its gap (the divider sits in the gap)
local CANVAS_H = ROWS * ROW_H + (ROWS - 1) * ROW_GAP
local CLAIM_W = 100
local CLAIM_H = 44
local TEXT = 15 -- row text; the smallest text anywhere in the panel is PhoneScale.MinText (14)

function Panel.attach(gui: ScreenGui, anchor: GuiObject)
    local C = Theme.Colors
    local root = Instance.new("Frame")
    root.Name, root.Size, root.BackgroundColor3, root.BackgroundTransparency, root.ZIndex = "ObjectivesPanel", UDim2.fromOffset(TouchLayout.OBJECTIVES.w, HEADER_H), C.panel, 0.15, 3
    root.ClipsDescendants = true
    Theme.decorate(root, 5)
    root.Visible, root.Parent = false, gui

    local function text(parent: GuiObject, name: string, size: number, color: Color3, align: Enum.TextXAlignment): TextLabel
        local l = Instance.new("TextLabel")
        l.Name, l.Font, l.TextSize, l.TextColor3, l.TextXAlignment = name, Enum.Font.FredokaOne, size, color, align
        l.BackgroundTransparency, l.ZIndex, l.Parent = 1, root.ZIndex + 2, parent
        Theme.TextStyle.apply(l)
        return l
    end

    -- Header: one tappable line. Folded = trophy + nearest task + chip; open = trophy + TASKS + "New tasks soon".
    local header = Instance.new("TextButton")
    header.Name, header.Text, header.AutoButtonColor, header.BackgroundTransparency = "Header", "", false, 1
    header.Size, header.ZIndex, header.Parent = UDim2.new(1, 0, 0, HEADER_H), root.ZIndex + 1, root
    local trophy = Theme.icon(header, "trophy")
    if trophy then trophy.Position, trophy.Size, trophy.ZIndex = UDim2.fromOffset(8, 8), UDim2.fromOffset(28, 28), root.ZIndex + 2 end
    local title = text(header, "Title", 17, C.gold, Enum.TextXAlignment.Left)
    title.TextTruncate = Enum.TextTruncate.AtEnd
    local wait = text(header, "Wait", PhoneScale.MinText, C.gold, Enum.TextXAlignment.Right) -- "New tasks soon" (open)
    wait.TextTruncate = Enum.TextTruncate.AtEnd
    local chip = Instance.new("Frame")
    chip.Name, chip.BackgroundColor3, chip.ZIndex, chip.Parent = "Chip", C.card, root.ZIndex + 1, header
    Theme.decorate(chip, 6)
    chip.Position, chip.Size = UDim2.new(1, -64, 0, 8), UDim2.fromOffset(56, 28)
    local chipText = text(chip, "ChipText", 16, C.text, Enum.TextXAlignment.Center) -- progress "3/10" or "Done!" (folded)
    chipText.Position, chipText.Size = UDim2.fromOffset(0, 0), UDim2.fromScale(1, 1)

    -- BD-561: icon slots. Rules.Slots names the Theme.ImageIds keys; a key with no id gets nothing at all (makeIcon returns nil).
    local P = Rules.IconPx
    local art: {[string]: boolean} = {}
    for which, key in Rules.Slots do
        local ids = (Theme :: any).ImageIds
        local id = if type(ids) == "table" then ids[key] else nil
        art[which] = type(id) == "string" and id ~= ""
    end
    local anyArt = art.chevron or art.arrow or art.crystal or art.star
    local function makeIcon(parent: GuiObject, which: string, px: number): GuiObject?
        if not art[which] then return nil end
        local icon = Theme.icon(parent, Rules.Slots[which])
        if icon then icon.Size, icon.Visible = UDim2.fromOffset(px, px), false end
        return icon
    end
    local chevronIcon, arrowIcon = makeIcon(header, "chevron", P.chevron), makeIcon(header, "arrow", P.arrow)
    local starIcon, gemIcon = makeIcon(header, "star", P.star), makeIcon(header, "crystal", P.crystal)
    -- The arrow bobs 3 px every half second (a tween, ~2 updates a second); Reduce Motion (Theme.MotionEnabled false) keeps it still.
    local function bobTo(icon: GuiObject, x: number, y: number)
        local bob = if (Theme :: any).MotionEnabled ~= false and math.floor(os.clock() / 0.5) % 2 == 1 then 3 else 0
        local at = UDim2.fromOffset(x, y + bob)
        if icon.Visible then Theme.animate(icon, 0.4, {Position = at}) else icon.Position = at end
        icon.Visible = true
    end

    -- Body: the 3 rows (pooled, updated on data changes only, never per frame).
    local body = Instance.new("ScrollingFrame")
    body.Name, body.BackgroundTransparency, body.BorderSizePixel, body.ScrollBarThickness = "Body", 1, 0, 6
    body.ScrollBarImageColor3, body.ScrollingDirection, body.ZIndex = C.gold, Enum.ScrollingDirection.Y, root.ZIndex + 1
    body.Position, body.Size, body.CanvasSize, body.Parent = UDim2.fromOffset(0, HEADER_H + 2), UDim2.new(1, 0, 1, -(HEADER_H + 2)), UDim2.fromOffset(0, CANVAS_H), root
    pcall(function() body.ElasticBehavior = Enum.ElasticBehavior.Never end)
    local rows = {}
    for i = 1, ROWS do
        local row = Instance.new("Frame")
        row.Name, row.BackgroundTransparency, row.Position, row.Size, row.ZIndex, row.Parent = "Row" .. i, 1, UDim2.fromOffset(0, (i - 1) * PITCH), UDim2.new(1, 0, 0, ROW_H), body.ZIndex, body
        local name = text(row, "Name", TEXT, C.text, Enum.TextXAlignment.Left)
        name.TextWrapped, name.TextTruncate, name.TextYAlignment = true, Enum.TextTruncate.AtEnd, Enum.TextYAlignment.Top
        local note = text(row, "Note", PhoneScale.MinText, C.text:Lerp(C.card, 0.3), Enum.TextXAlignment.Left) -- optional hint: UITheme text colour toned toward the card colour
        note.TextTruncate, note.Visible = Enum.TextTruncate.AtEnd, false
        local bar = Instance.new("Frame")
        bar.Name, bar.BackgroundColor3, bar.ZIndex, bar.Parent = "Bar", C.card, body.ZIndex + 1, row
        Theme.decorate(bar, 3)
        local fill = Instance.new("Frame")
        fill.Name, fill.BackgroundColor3, fill.BorderSizePixel, fill.Size, fill.ZIndex, fill.Parent = "Fill", C.accent, 0, UDim2.fromScale(0, 1), bar.ZIndex + 1, bar
        Theme.decorate(fill, 3)
        local count = text(row, "Count", 16, C.gold, Enum.TextXAlignment.Right)
        local reward = text(row, "Reward", PhoneScale.MinText, C.gold, Enum.TextXAlignment.Right)
        local claim = Instance.new("TextButton")
        claim.Name, claim.Text, claim.TextSize, claim.TextColor3, claim.BackgroundColor3, claim.ZIndex = "Claim", "CLAIM", 18, C.text, C.accent, body.ZIndex + 2
        claim.Visible, claim.Parent = false, row
        Theme.decorate(claim, 6)
        local divider = Instance.new("Frame") -- 2 px line in the gap under the row (UITheme card colour, no art); hidden under the last shown row
        divider.Name, divider.BackgroundColor3, divider.BorderSizePixel, divider.ZIndex = "Divider", C.card, 0, body.ZIndex
        divider.Position, divider.Size, divider.Parent = UDim2.fromOffset(8, ROW_H + ROW_GAP / 2 - 1), UDim2.new(1, -16, 0, 2), row
        rows[i] = {frame = row, divider = divider, name = name, note = note, bar = bar, fill = fill, count = count, reward = reward, claim = claim, id = nil :: string?, fraction = -1,
            arrow = makeIcon(row, "arrow", P.arrow), star = makeIcon(row, "star", P.row), gem = makeIcon(row, "crystal", P.row)}
    end

    local open = false
    local busy: {[string]: boolean} = {}
    local tokens: {[string]: string} = {}
    local message, messageUntil = "", 0
    local messageGrant: any = nil -- the grant behind `message` (so the crystal icon can follow the number); nil for any other answer
    local panelWidth = TouchLayout.OBJECTIVES.w -- the width the rect gives the panel (the tween may still be on its way)
    local shown: {any} = {}
    local lastRects = ""

    -- Server calls (only ever from here). The remote is looked up per call: it exists only while the server flag is on.
    local function remote(): RemoteFunction?
        local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
        local fn = folder and folder:FindFirstChild("ObjectiveAction")
        if fn and fn:IsA("RemoteFunction") then return fn end
        return nil
    end
    local function call(request: any): any
        local fn = remote()
        if not fn then return nil end
        local ok, response = pcall(function() return (fn :: RemoteFunction):InvokeServer(request) end)
        if ok and typeof(response) == "table" then return response end
        return nil
    end

    local function remaining(): number?
        local seconds = Rules.resetSeconds(state.view, shown)
        if seconds == nil then return nil end
        return seconds - (os.clock() - state.fetchedAt)
    end

    local function render()
        shown = Rules.select(state.view, {playGoalActive = state.playActive})
        local folded = Rules.folded(shown)
        local now = os.clock()
        local showMessage = message ~= "" and now < messageUntil
        local left = remaining()
        -- Header text: icon (8..36), title, then the chip (folded) or the "New tasks soon" words (open).
        title.Position = UDim2.fromOffset(42, 0)
        if open then
            title.Text = Rules.Title
            -- The claim answer takes the wide right-hand label for 2.5 s (the 38% title slot cut "+10 crystals" to "+10 crys..." in Studio).
            wait.Text = if showMessage then message elseif left ~= nil then Rules.resetText(left) elseif folded.empty then Rules.resetText(0) else ""
            wait.TextColor3 = if showMessage then C.accent else C.gold
            wait.Visible, chip.Visible = true, false
            wait.AnchorPoint, wait.Position, wait.Size = Vector2.new(1, 0.5), UDim2.new(1, -10, 0.5, 0), UDim2.new(0.62, -10, 1, 0)
            title.Size = UDim2.new(0.38, -42, 1, 0)
        else
            title.Text = folded.text
            chipText.Text = folded.chip
            wait.Visible, chip.Visible = false, folded.chip ~= ""
            chip.BackgroundColor3 = if folded.claimable then C.accent else C.card
            title.Size = UDim2.new(1, -42 - (if folded.chip ~= "" then 68 else 8), 1, 0)
        end
        title.TextSize = if open then 17 else TEXT
        title.TextColor3 = if folded.claimable and not open then C.accent else C.gold
        if anyArt then -- BD-561: re-place the header pieces around the icons that exist; icons that do not exist change nothing
            local lay = Rules.headerLayout(panelWidth, {
                chevron = chevronIcon ~= nil, arrow = arrowIcon ~= nil and folded.tutorial == true, star = starIcon ~= nil and folded.claimable,
                chip = chip.Visible, open = open,
            })
            if chevronIcon then
                chevronIcon.Position, chevronIcon.Rotation, chevronIcon.Visible = UDim2.fromOffset(lay.chevronX, (HEADER_H - P.chevron) // 2), if open then 180 else 0, true
            end
            local gemShown = false
            if open then
                -- The claim answer sits in the right-hand words; with the crystal icon it is "+10" and the gem at the very end (number, then gem).
                local inset = lay.waitInset
                local words = if showMessage and messageGrant ~= nil and gemIcon ~= nil then Rules.rewardWords(messageGrant, true) else nil
                if words and gemIcon and Rules.textWidth(words, PhoneScale.MinText) <= lay.waitW - P.crystal - 2 then
                    gemShown = true
                    gemIcon.Position = UDim2.new(1, -(inset + P.crystal), 0, (HEADER_H - P.crystal) // 2)
                    inset += P.crystal + 2
                    wait.Text = words
                else
                    wait.Text = Rules.fitWords(wait.Text, lay.waitW, PhoneScale.MinText) or "Soon"
                end
                wait.Position, wait.Size = UDim2.new(1, -inset, 0.5, 0), UDim2.new(0.62, -inset, 1, 0)
                title.Text = Rules.fitWords(title.Text, lay.titleW, 17) or title.Text
            else
                title.Position, title.Size = UDim2.fromOffset(lay.titleX, 0), UDim2.new(0, lay.titleW, 1, 0)
                title.Text = Rules.fitWords(title.Text, lay.titleW, TEXT) or "Task"
                if lay.chipX then chip.Position = UDim2.fromOffset(lay.chipX, 8) end
            end
            if gemIcon then gemIcon.Visible = gemShown end
            if arrowIcon then
                if lay.arrowX then bobTo(arrowIcon, lay.arrowX, (HEADER_H - P.arrow) // 2) else arrowIcon.Visible = false end
            end
            if starIcon then
                if lay.starX then starIcon.Position, starIcon.Visible = UDim2.fromOffset(lay.starX, (HEADER_H - P.star) // 2), true else starIcon.Visible = false end
            end
        end
        -- Rows.
        body.Visible = open
        for i, r in rows do
            local data = shown[i]
            r.frame.Visible = open and data ~= nil
            r.id = if data then data.id else nil
            if data then
                local width = body.AbsoluteSize.X
                if width <= 0 then width = root.Size.X.Offset end
                local leftW = width - CLAIM_W - 24
                local rightX = -(CLAIM_W + 8)
                -- Fixed row (ROW_H). No note: name 3..35 (two lines at most), bar 43..51 or the prize 38..58 (finished). With a note: name 3..23 (one
                -- line), note 23..41, bar 46..54 or the prize 41..59. On the right: count 8..30 + prize 30..52, or a 44 px CLAIM centred in the row.
                -- Nothing shares a pixel with another label (tools/verify_objectives_panel.py).
                local hasNote = data.note ~= nil
                r.divider.Visible = i < #shown
                r.name.Position, r.name.Size, r.name.Text = UDim2.fromOffset(8, 3), UDim2.fromOffset(leftW, if hasNote then 20 else 32), data.name
                r.note.Visible = hasNote
                if hasNote then
                    r.note.Position, r.note.Size, r.note.Text = UDim2.fromOffset(8, 23), UDim2.fromOffset(leftW, 18), data.note
                end
                r.bar.Position, r.bar.Size = UDim2.fromOffset(8, if hasNote then 46 else 43), UDim2.fromOffset(leftW, 8)
                if r.fraction ~= data.fraction then
                    r.fraction = data.fraction
                    Theme.animate(r.fill, 0.2, {Size = UDim2.fromScale(math.clamp(data.fraction, 0, 1), 1)})
                end
                r.fill.BackgroundColor3 = if data.claimable then C.gold else C.accent
                local mode = Rules.buttonState(data, busy[data.id] == true)
                r.claim.Visible = mode ~= "none"
                r.claim.Position, r.claim.Size = UDim2.new(1, rightX, 0, (ROW_H - CLAIM_H) / 2), UDim2.fromOffset(CLAIM_W, CLAIM_H)
                r.claim.Text = if mode == "wait" then "..." else "CLAIM"
                r.claim.BackgroundColor3 = if mode == "wait" then C.card else C.accent
                r.claim.Active = mode == "claim"
                -- Progress: bar + "3/10" + the prize on the right. Finished: the full bar gives way to the prize under the name, next to CLAIM.
                r.bar.Visible, r.count.Visible = not data.claimable, not data.claimable
                r.count.Position, r.count.Size, r.count.Text = UDim2.new(1, rightX, 0, 8), UDim2.fromOffset(CLAIM_W, 22), Rules.progressText(data)
                r.reward.Text = Rules.rewardText(data.reward)
                if data.claimable then
                    r.reward.Position, r.reward.Size, r.reward.TextXAlignment = UDim2.fromOffset(8, if hasNote then 41 else 38), UDim2.fromOffset(leftW, if hasNote then 18 else 20), Enum.TextXAlignment.Left
                else
                    r.reward.Position, r.reward.Size, r.reward.TextXAlignment = UDim2.new(1, rightX, 0, 30), UDim2.fromOffset(CLAIM_W, 22), Enum.TextXAlignment.Right
                end
                if anyArt then -- BD-561: arrow on the open tutorial task, star + gem on the prize line; each only where it fits
                    local arrowRoom = P.arrow + Rules.IconGap
                    if r.arrow then
                        if data.group == "tutorial" and not data.claimable and Rules.wrapLines(data.name, leftW - arrowRoom, TEXT) <= (if hasNote then 1 else 2) then
                            r.name.Position, r.name.Size = UDim2.fromOffset(8 + arrowRoom, 3), UDim2.fromOffset(leftW - arrowRoom, if hasNote then 20 else 32)
                            if hasNote then -- the hint is indented too, and cut at a whole word if it no longer fits
                                r.note.Position, r.note.Size = UDim2.fromOffset(8 + arrowRoom, 23), UDim2.fromOffset(leftW - arrowRoom, 18)
                                r.note.Text = Rules.fitWords(data.note, leftW - arrowRoom, PhoneScale.MinText) or data.note
                            end
                            bobTo(r.arrow, 8, 3)
                        else
                            r.arrow.Visible = false
                        end
                    end
                    local lay = Rules.prizeLayout(data.reward, if data.claimable then leftW else CLAIM_W, data.claimable, {star = r.star ~= nil, gem = r.gem ~= nil})
                    r.reward.Text = lay.words
                    if data.claimable then
                        local lineY, lineH = if hasNote then 41 else 38, if hasNote then 18 else 20
                        r.reward.Position, r.reward.Size = UDim2.fromOffset(8 + lay.text.x, lineY), UDim2.fromOffset(lay.text.w, lineH)
                        if r.star then
                            r.star.Visible = lay.star ~= nil
                            if lay.star then r.star.Position = UDim2.fromOffset(8 + lay.star, lineY + (lineH - P.row) // 2) end
                        end
                        if r.gem then
                            r.gem.Visible = lay.gem ~= nil
                            if lay.gem then r.gem.Position = UDim2.fromOffset(8 + lay.gem, lineY + (lineH - P.row) // 2) end
                        end
                    else
                        r.reward.Size = UDim2.fromOffset(lay.text.w, 22)
                        if r.star then r.star.Visible = false end
                        if r.gem then
                            r.gem.Visible = lay.gem ~= nil
                            if lay.gem then r.gem.Position = UDim2.new(1, rightX + lay.gem, 0, 31) end
                        end
                    end
                end
            end
        end
    end

    local function fetch(force: boolean?)
        local now = os.clock()
        if state.fetching or (not force and now < state.nextFetch) then return end
        state.fetching, state.nextFetch = true, now + 2
        task.spawn(function()
            local response = call({action = "view"})
            state.fetching = false
            if response and response.ok == true and typeof(response.view) == "table" then
                setView(response.view)
                render()
            end
        end)
    end

    local function claim(id: string)
        if busy[id] then return end
        local current
        for _, r in shown do if r.id == id then current = r end end
        if not current or not current.claimable then return end
        busy[id] = true
        render()
        local token = tokens[id] or HttpService:GenerateGUID(false)
        tokens[id] = token
        task.spawn(function()
            local response = call({action = "claim", id = id, token = token})
            busy[id] = nil
            local code = if response == nil then "error" elseif response.ok == true then response.status else response.reason
            if not Rules.keepToken(code) then tokens[id] = nil end -- a definite answer frees the id; a lost one retries with the SAME token (claim-once)
            if response and typeof(response.view) == "table" then setView(response.view) end
            if code == "claimed" and response and typeof(response.grant) == "table" then
                message, messageGrant = Rules.rewardText(response.grant), response.grant
            else
                message, messageGrant = Rules.claimMessage(code), nil
            end
            messageUntil = os.clock() + 2.5
            render()
            if not (response and response.ok == true) then fetch(true) end -- e.g. the window rolled over: show what the server says now
        end)
    end
    for _, r in rows do
        r.claim.Activated:Connect(function() if r.id then claim(r.id) end end)
    end

    header.Activated:Connect(function()
        open = not open
        if open then fetch(true) end
        render()
        lastRects = "" -- re-place at once
    end)

    local elapsed, sinceFetch = 0, 0
    RunService.Heartbeat:Connect(function(dt)
        elapsed += dt
        if elapsed < 0.5 then return end
        sinceFetch += elapsed
        elapsed = 0
        local character = Players.LocalPlayer.Character
        local inRun = character ~= nil and character:GetAttribute("RunState") == "Active"
        local folded = gui:GetAttribute("ObjectivesRect")
        local openRect = gui:GetAttribute("ObjectivesOpenRect")
        local hub = not inRun and anchor.Visible
        -- A view that cannot be fetched (server flag off, not loaded yet) keeps the panel hidden until the first answer.
        local visible = hub and typeof(folded) == "Rect" and state.view ~= nil
        root.Visible = visible
        if not hub then
            if open then open = false lastRects = "" render() end
            return
        end
        if sinceFetch >= Rules.PollSeconds or state.view == nil or ((remaining() or 1) <= 0 and os.clock() - state.fetchedAt > 5) then
            sinceFetch = 0
            fetch(state.view == nil)
        end
        if not visible then return end
        local rect: Rect = if open and typeof(openRect) == "Rect" then openRect else folded
        local key = tostring(rect) .. tostring(open)
        if key ~= lastRects then
            lastRects = key
            local height = if open then rect.Height else HEADER_H
            panelWidth = rect.Width
            root.Position = UDim2.fromOffset(rect.Min.X, rect.Min.Y)
            Theme.animate(root, 0.15, {Size = UDim2.fromOffset(rect.Width, height)})
            body.CanvasSize = UDim2.fromOffset(0, CANVAS_H)
            render()
        end
        render() -- countdown words and the message timeout; ~2 text updates a second, no allocation
    end)
    render()
end

return Panel
