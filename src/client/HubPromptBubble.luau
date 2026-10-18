--!strict
-- BD-1017 (docs/180 option A, owner 2026-10-18: "the shop interactions should be like messages with buttons to click, like E to interact").
-- The friendly message bubble above a cave stall (and the Heart "Show off" spot): the stall name, one warm line and a big key button
-- ("E  Open" on a keyboard, "Tap to open" on a phone, the controller button on a gamepad). The whole bubble is the button (at least 96 x 96 px).
-- One press opens the existing window (the prompt's own Triggered handler does that: HubWalkUpClient for the stalls, CaveShowOff on the server for
-- the Heart). NO hold, NO auto-open when walking near (docs/114 s6.2). Only called while Config.ShopPromptBubbleEnabled is true (HubWalkUpClient decides).
--   * a prompt takes part when it carries the attribute BubbleStation (the station id, a key of HubSignCopy.BubbleLines); its Style is Custom
--   * one bubble at a time: the nearest (Rules.step). Hidden while any window is open, while the stall cannot open, for a moment after a press and
--     after a window closes (so a tap can never fall through to the world). The KEY keeps working while a window is open: pressing it again closes
--     the window (BD-1074, ModalCloseRules.keyAction), only the picture is hidden.
--   * calm: a soft fade (instant with Reduce Motion), a small squash on a press, no bob. One existing soft cue (ui_click), no new sound.
-- Look: the handbook chip style (docs/114 s4, ChipStyle: rounded rectangle, 3 px dark outline, flat palette fill, FredokaOne). No pictures, no code art.
local Players = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")
local ContextActionService = game:GetService("ContextActionService")
local ProximityPromptService = game:GetService("ProximityPromptService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Rules = require(Shared:WaitForChild("HubPromptBubbleRules"))
local Walk = require(Shared:WaitForChild("HubWalkUpRules"))
local Theme = require(Shared:WaitForChild("UITheme"))
local Chip = require(Shared:WaitForChild("ChipStyle"))
local Sfx = require(Shared:WaitForChild("Sfx"))

local Bubble = {}
local ACTION = "HubPromptBubbleKey"
local TICK = 0.2 -- seconds between two looks at the player's distance and the open windows
local LIFT = 3.5 -- studs above the prompt anchor (the stall sign)

local function inputName(): string
    local ok, name = pcall(function() return UserInputService:GetLastInputType().Name end)
    if not ok or name == "None" or name == "Focus" then
        return if UserInputService.TouchEnabled and not UserInputService.KeyboardEnabled then "Touch" else "Keyboard"
    end
    return name
end

local function label(parent: Instance, name: string, text: string, size: number, color: Color3, y: number, height: number, pad: number, stroke: boolean): TextLabel
    local l = Instance.new("TextLabel")
    l.Name, l.BackgroundTransparency, l.Position, l.Size = name, 1, UDim2.fromOffset(pad, y), UDim2.new(1, -2 * pad, 0, height)
    l.Font, l.Text, l.TextColor3, l.TextScaled, l.TextWrapped = Enum.Font.FredokaOne, text, color, true, false
    l.TextXAlignment = Enum.TextXAlignment.Center
    if stroke then l.TextStrokeTransparency, l.TextStrokeColor3 = 0.4, Theme.Colors.outline end
    local limit = Instance.new("UITextSizeConstraint")
    limit.MinTextSize, limit.MaxTextSize, limit.Parent = Rules.MinText, size, l
    l.Parent = parent
    return l
end

-- ctx = {canShow = function() -> boolean (the stall can open now: at home, no hub trip), windowOpen = function() -> boolean (any window on screen)}.
function Bubble.attach(ctx: any): any
    local player = Players.LocalPlayer
    local state = Rules.newState()
    local active: {[ProximityPrompt]: boolean} = {}
    local looping = false
    local shown: any = nil -- {board, group, scale, id, kind, prompt}

    local function rootPart(): BasePart?
        local character = player.Character
        local root = character and character:FindFirstChild("HumanoidRootPart")
        return if root and root:IsA("BasePart") then root else nil
    end

    local function hide(immediate: boolean)
        local s = shown
        if s == nil then return end
        shown = nil
        if immediate or not Theme.MotionEnabled then
            s.board:Destroy()
            return
        end
        Theme.animate(s.group, Rules.FadeOut, {GroupTransparency = 1})
        task.delay(Rules.FadeOut + 0.02, function() s.board:Destroy() end)
    end

    local refresh: () -> ()

    local function press(prompt: ProximityPrompt)
        Sfx.play("ui_click")
        if shown and Theme.MotionEnabled then Theme.animate(shown.scale, Rules.SquashSeconds, {Scale = Rules.Squash}) end
        Rules.pressed(state, os.clock())
        prompt:InputHoldBegin()
        prompt:InputHoldEnd()
        refresh()
    end

    local function show(prompt: ProximityPrompt, id: string, kind: string)
        local anchor = prompt.Parent
        if anchor == nil then return end
        local viewport = workspace.CurrentCamera
        local layout = Rules.layout(if viewport then viewport.ViewportSize.Y else nil)
        local keyName = if kind == "Gamepad" then prompt.GamepadKeyCode.Name else prompt.KeyboardKeyCode.Name
        local okLabel, engineLabel = pcall(function() return UserInputService:GetStringForKeyCode(prompt.KeyboardKeyCode) end)
        local words = Rules.words(id, kind, keyName, if okLabel then engineLabel else nil)
        if words == nil then return end

        local board = Instance.new("BillboardGui")
        board.Name, board.Adornee, board.Size, board.AlwaysOnTop = "HubPromptBubble", anchor, UDim2.fromOffset(layout.w, layout.h), true
        board.StudsOffset, board.ResetOnSpawn, board.LightInfluence = Vector3.new(0, LIFT, 0), false, 0
        local group = Instance.new("CanvasGroup")
        group.Name, group.Size, group.BackgroundTransparency, group.GroupTransparency = "Fade", UDim2.fromScale(1, 1), 1, 1
        group.Parent = board

        -- The whole bubble is the button: one big, easy tap (a world button, never a screen overlay).
        local button = Instance.new("TextButton")
        button.Size, button.Text, button.AutoButtonColor, button.Name = UDim2.fromScale(1, 1), "", false, "Bubble"
        Chip.apply(button, Theme.Colors.panel, nil)
        button.Parent = group
        label(button, "Title", words.title, layout.titleSize, Theme.Colors.gold, layout.titleY, layout.titleH, layout.pad, true)
        label(button, "Line", words.line, layout.lineSize, Theme.Colors.text, layout.lineY, layout.lineH, layout.pad, false)

        local action = Instance.new("Frame")
        action.Name, action.Position, action.Size = "Action", UDim2.fromOffset(layout.pad, layout.buttonY), UDim2.new(1, -2 * layout.pad, 0, layout.buttonH)
        Chip.apply(action, Theme.Colors.gold, nil)
        action.Parent = button
        local scale = Instance.new("UIScale")
        scale.Parent = action
        local row = Instance.new("UIListLayout")
        row.FillDirection, row.HorizontalAlignment, row.VerticalAlignment = Enum.FillDirection.Horizontal, Enum.HorizontalAlignment.Center, Enum.VerticalAlignment.Center
        row.Padding, row.SortOrder, row.Parent = UDim.new(0, 8), Enum.SortOrder.LayoutOrder, action
        if words.keyLabel then
            local key = Instance.new("Frame")
            key.Name, key.Size, key.LayoutOrder = "Key", UDim2.fromOffset(36, layout.buttonH - 14), 1
            Chip.apply(key, Theme.Colors.panel, nil, true)
            key.Parent = action
            local letter = Instance.new("TextLabel")
            letter.Name, letter.BackgroundTransparency, letter.Size, letter.Text = "Letter", 1, UDim2.fromScale(1, 1), words.keyLabel
            letter.Font, letter.TextColor3, letter.TextScaled = Enum.Font.FredokaOne, Theme.Colors.text, true
            local letterLimit = Instance.new("UITextSizeConstraint")
            letterLimit.MinTextSize, letterLimit.MaxTextSize, letterLimit.Parent = Rules.MinText, layout.buttonSize, letter
            letter.Parent = key
        end
        local open = Instance.new("TextLabel")
        open.Name, open.BackgroundTransparency, open.LayoutOrder, open.Text = "Words", 1, 2, words.buttonText
        open.Size = UDim2.fromOffset(math.ceil(Rules.textWidth(words.buttonText, layout.buttonSize)) + 4, layout.buttonH - 8)
        open.Font, open.TextColor3, open.TextSize = Enum.Font.FredokaOne, Theme.Colors.outline, layout.buttonSize
        open.Parent = action

        button.Activated:Connect(function()
            press(prompt)
        end)
        board.Parent = player:WaitForChild("PlayerGui")
        shown = {board = board, group = group, scale = scale, id = id, kind = kind, prompt = prompt}
        Theme.animate(group, Rules.FadeIn, {GroupTransparency = 0})
    end

    refresh = function()
        local root = rootPart()
        local candidates, byId = {}, {}
        for prompt in active do
            local anchor = prompt.Parent
            local id = prompt:GetAttribute("BubbleStation")
            if root and anchor and anchor:IsA("BasePart") and typeof(id) == "string" then
                candidates[#candidates + 1] = {id = id, distance = (anchor.Position - root.Position).Magnitude, range = prompt.MaxActivationDistance}
                byId[id] = prompt
            end
        end
        local id = Rules.step(state, {candidates = candidates, canShow = ctx.canShow() == true, windowOpen = ctx.windowOpen() == true}, os.clock())
        if id == nil then hide(false) return end
        local kind = Rules.inputKind(inputName())
        if shown and shown.id == id and shown.kind == kind and shown.board.Parent ~= nil then return end
        hide(true)
        local prompt = byId[id]
        if prompt then show(prompt, id, kind) end
    end

    local function nearestPrompt(): ProximityPrompt?
        local root = rootPart()
        if root == nil then return nil end
        local best: ProximityPrompt? = nil
        local bestDistance = math.huge
        for prompt in active do
            local anchor = prompt.Parent
            if anchor and anchor:IsA("BasePart") then
                local d = (anchor.Position - root.Position).Magnitude
                if d < bestDistance then best, bestDistance = prompt, d end
            end
        end
        return best
    end

    -- ONE key binding for all prompts of the bubble (they share the key): it presses the nearest one, also while its window is open (key twice = closed).
    local function bindKey()
        ContextActionService:BindAction(ACTION, function(_, inputState)
            if inputState == Enum.UserInputState.Begin then
                local prompt = nearestPrompt()
                if prompt then press(prompt) end
            end
            return Enum.ContextActionResult.Sink
        end, false, Enum.KeyCode[Walk.keyFor(true)], Enum.KeyCode[Walk.gamepadFor(true)])
    end

    local function startLoop()
        if looping then return end
        looping = true
        task.spawn(function()
            while next(active) ~= nil do
                refresh()
                task.wait(TICK)
            end
            looping = false
            hide(true)
        end)
    end

    ProximityPromptService.PromptShown:Connect(function(prompt: ProximityPrompt)
        if typeof(prompt:GetAttribute("BubbleStation")) ~= "string" or active[prompt] then return end
        if next(active) == nil then bindKey() end
        active[prompt] = true
        refresh()
        startLoop()
        prompt.PromptHidden:Once(function()
            active[prompt] = nil
            if next(active) == nil then ContextActionService:UnbindAction(ACTION) end
            refresh()
        end)
    end)

    return {refresh = function() refresh() end}
end

return Bubble
