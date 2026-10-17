--!strict
-- BD-075 (docs/66 section 18): the collapsible objectives panel. CLIENT ONLY and shown ONLY while Config.ObjectivesEnabled is true (GoalHud calls
-- attach() behind that flag, so with the flag off this module is never required: no Instances, no remote lookup, no request).
-- It reads the server view through the ObjectiveAction RemoteFunction ({action="view"}) and sends {action="claim", id, token} when a
-- CLAIM button is tapped. It never computes a reward, a progress value or a window: every number comes from the server view.
-- Pure choices (which 3 rows, the folded line, the words, claim answers) live in Shared/ObjectivePanelRules (tools/verify_objectives_panel.py).
-- Pattern: GoalsPanel (existing UI parts only: Theme.decorate plates, the registered "trophy" icon, no new art, no asset ids).
-- Folded: ONE 44 px line (trophy, nearest task, progress chip). Open: header + the 3 tasks (name, progress bar, CLAIM when done) + "New tasks soon".
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
local state = {playActive = true, view = nil :: any, fetchedAt = 0, fetching = false, nextFetch = 0}

-- GoalHud feeds the Goals panel PLAY state through this (true = "play new dinos" is on screen and not finished, so an unfinished T8 is hidden).
function Panel.setPlayActive(active: boolean) state.playActive = active end

local HEADER_H = TouchLayout.OBJECTIVES.h -- 44: the header is a button (docs/114 s4.4 tap-target floor)
local ROW_H = TouchLayout.OBJECTIVES.rowH
local ROWS = TouchLayout.OBJECTIVES.rows
local CLAIM_W = 100
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

    -- Body: the 3 rows (pooled, updated on data changes only, never per frame).
    local body = Instance.new("ScrollingFrame")
    body.Name, body.BackgroundTransparency, body.BorderSizePixel, body.ScrollBarThickness = "Body", 1, 0, 6
    body.ScrollBarImageColor3, body.ScrollingDirection, body.ZIndex = C.gold, Enum.ScrollingDirection.Y, root.ZIndex + 1
    body.Position, body.Size, body.CanvasSize, body.Parent = UDim2.fromOffset(0, HEADER_H + 2), UDim2.new(1, 0, 1, -(HEADER_H + 2)), UDim2.fromOffset(0, ROWS * ROW_H), root
    pcall(function() body.ElasticBehavior = Enum.ElasticBehavior.Never end)
    local rows = {}
    for i = 1, ROWS do
        local row = Instance.new("Frame")
        row.Name, row.BackgroundTransparency, row.Position, row.Size, row.ZIndex, row.Parent = "Row" .. i, 1, UDim2.fromOffset(0, (i - 1) * ROW_H), UDim2.new(1, 0, 0, ROW_H), body.ZIndex, body
        local name = text(row, "Name", TEXT, C.text, Enum.TextXAlignment.Left)
        name.TextWrapped, name.TextTruncate, name.TextYAlignment = true, Enum.TextTruncate.AtEnd, Enum.TextYAlignment.Top
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
        rows[i] = {frame = row, name = name, bar = bar, fill = fill, count = count, reward = reward, claim = claim, id = nil :: string?, fraction = -1}
    end

    local open = false
    local busy: {[string]: boolean} = {}
    local tokens: {[string]: string} = {}
    local message, messageUntil = "", 0
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
                r.name.Position, r.name.Size, r.name.Text = UDim2.fromOffset(8, 2), UDim2.fromOffset(leftW, 32), data.name
                r.bar.Position, r.bar.Size = UDim2.fromOffset(8, 38), UDim2.fromOffset(leftW, 8)
                if r.fraction ~= data.fraction then
                    r.fraction = data.fraction
                    Theme.animate(r.fill, 0.2, {Size = UDim2.fromScale(math.clamp(data.fraction, 0, 1), 1)})
                end
                r.fill.BackgroundColor3 = if data.claimable then C.gold else C.accent
                local mode = Rules.buttonState(data, busy[data.id] == true)
                r.claim.Visible = mode ~= "none"
                r.claim.Position, r.claim.Size = UDim2.new(1, -(CLAIM_W + 8), 0, 4), UDim2.fromOffset(CLAIM_W, 44)
                r.claim.Text = if mode == "wait" then "..." else "CLAIM"
                r.claim.BackgroundColor3 = if mode == "wait" then C.card else C.accent
                r.claim.Active = mode == "claim"
                -- Progress: bar + "3/10" + the prize on the right. Finished: the full bar gives way to the prize under the name, next to CLAIM.
                r.bar.Visible, r.count.Visible = not data.claimable, not data.claimable
                r.count.Position, r.count.Size, r.count.Text = UDim2.new(1, -(CLAIM_W + 8), 0, 2), UDim2.fromOffset(CLAIM_W, 22), Rules.progressText(data)
                r.reward.Text = Rules.rewardText(data.reward)
                if data.claimable then
                    r.reward.Position, r.reward.Size, r.reward.TextXAlignment = UDim2.fromOffset(8, 34), UDim2.fromOffset(leftW, 18), Enum.TextXAlignment.Left
                else
                    r.reward.Position, r.reward.Size, r.reward.TextXAlignment = UDim2.new(1, -(CLAIM_W + 8), 0, 24), UDim2.fromOffset(CLAIM_W, 22), Enum.TextXAlignment.Right
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
                state.view, state.fetchedAt = response.view, os.clock()
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
            if response and typeof(response.view) == "table" then state.view, state.fetchedAt = response.view, os.clock() end
            if code == "claimed" and response and typeof(response.grant) == "table" then message = Rules.rewardText(response.grant) else message = Rules.claimMessage(code) end
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
            root.Position = UDim2.fromOffset(rect.Min.X, rect.Min.Y)
            Theme.animate(root, 0.15, {Size = UDim2.fromOffset(rect.Width, height)})
            body.CanvasSize = UDim2.fromOffset(0, ROWS * ROW_H)
            render()
        end
        render() -- countdown words and the message timeout; ~2 text updates a second, no allocation
    end)
    render()
end

return Panel
