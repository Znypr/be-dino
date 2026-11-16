--!strict
-- BD-1226 (docs/242 benchmark gap 11, "hits teach by a chip on the object, not windows"): ONLY while Config.PlayCuesEnabled is on (flag off: this
-- script returns on its first lines and nothing changes). A bobbing chip in the handbook chip style (Shared/ChipStyle) points at the thing to do:
--   * "Eat me!" on the nearest food in a new player's first run, until a few bites or the first minutes are over;
--   * "Eggs ready!" (with the registered nest icon) on the nests at home while a nest egg is ready and the eggs screen was not opened yet;
--   * "Shop!" / "Potions!" on the nearest stall at home for a new player, until a stall was opened or after a short while.
-- Each marker is gone for the session once it was used. Words and decisions: Shared/PlayCuesRules (tools/verify_play_cues.py). Calm: a slow bob,
-- none with Reduce Motion. Hidden while a window is open. Client presentation only: nothing is stored, sent or decided.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local GuiService = game:GetService("GuiService")
local HttpService = game:GetService("HttpService")
local ProximityPromptService = game:GetService("ProximityPromptService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
if (Config :: any).PlayCuesEnabled ~= true then return end

local Rules = require(Shared:WaitForChild("PlayCuesRules"))
local Chip = require(Shared:WaitForChild("ChipStyle"))
local Theme = require(Shared:WaitForChild("UITheme"))
local Kit = require(Shared:WaitForChild("ToyboxKit"))
local NestQueue = require(Shared:WaitForChild("NestQueue"))
local PrivateState = require(script.Parent:WaitForChild("PrivateState"))

local player = Players.LocalPlayer
local playerGui = player:WaitForChild("PlayerGui")
local gui = playerGui:WaitForChild("BeDinoUI")
local CREAM = Color3.fromRGB(Kit.Tone.panel[1], Kit.Tone.panel[2], Kit.Tone.panel[3])
local INK = Color3.fromRGB(Kit.Tone.value[1], Kit.Tone.value[2], Kit.Tone.value[3])
local TICK = 0.25

local function motion(): boolean
    return Theme.MotionEnabled ~= false and GuiService.ReducedMotionEnabled ~= true and player:GetAttribute("ReduceMotion") ~= true
end
local function menuOpen(): boolean
    local scrim = gui:FindFirstChild("ModalScrim")
    return scrim ~= nil and scrim:IsA("GuiObject") and scrim.Visible
end
local function runState(): any
    local character = player.Character
    return if character then character:GetAttribute("RunState") else nil
end
local function rootPosition(): Vector3?
    local character = player.Character
    local root = if character then character:FindFirstChild("HumanoidRootPart") else nil
    return if root and root:IsA("BasePart") then root.Position else nil
end

-- One marker: a billboard with a cream chip (ink words, ink outline: style rules R1 / R2), optional registered icon on its left.
type Marker = {board: BillboardGui, label: TextLabel, lift: number, target: BasePart?}
local function marker(name: string, icon: string?): Marker
    local board = Instance.new("BillboardGui")
    board.Name, board.Size, board.LightInfluence, board.MaxDistance, board.Enabled = "PointAt_" .. name, UDim2.fromOffset(170, 52), 0, 400, false
    board.AlwaysOnTop = false -- Studio's screen capture does not draw AlwaysOnTop billboards; the chip floats above the thing, in view
    board.ResetOnSpawn = false
    local chip, label = Chip.new(board :: any, {name = "Chip", fill = CREAM, size = UDim2.new(1, -4, 1, -4), position = UDim2.fromOffset(2, 2), z = 1,
        text = "", textInset = if icon then 44 else 8})
    label.TextColor3, label.TextStrokeTransparency = INK, 1
    if icon then
        local art = Theme.icon(chip, icon)
        if art then art.Position, art.Size, art.ZIndex = UDim2.fromOffset(4, 4), UDim2.fromOffset(40, 40), 3 end
    end
    board.Parent = playerGui
    return {board = board, label = label, lift = 0, target = nil}
end

local food = marker("Food", nil)
local nest = marker("Nest", "egg_nest")
local stall = marker("Stall", nil)
food.label.Text, nest.label.Text = Rules.Words.food, Rules.Words.nest

local function partOf(item: Instance): BasePart?
    if item:IsA("BasePart") then return item end
    if item:IsA("Model") then return item.PrimaryPart or item:FindFirstChildWhichIsA("BasePart", true) end
    return nil
end
local function point(m: Marker, target: BasePart?)
    if target ~= m.target then
        m.target = target
        m.board.Adornee = target
        m.lift = if target then target.Size.Y * 0.5 + Rules.Lift else 0
    end
    m.board.Enabled = target ~= nil
end

-- Session facts.
local bites, played, home = 0, 0, 0
local usedStall, openedAt = false, -1 -- openedAt = the ready count when the eggs screen was last opened (-1 never)
local function watch(character: Model)
    local last = character:GetAttribute("GrowthScore")
    character:GetAttributeChangedSignal("GrowthScore"):Connect(function()
        local now = character:GetAttribute("GrowthScore")
        if typeof(now) == "number" and typeof(last) == "number" and now > last and character:GetAttribute("RunState") == "Active" then bites += 1 end
        last = now
    end)
end
player.CharacterAdded:Connect(watch)
if player.Character then watch(player.Character) end
ProximityPromptService.PromptTriggered:Connect(function(prompt: ProximityPrompt)
    if prompt:GetAttribute("HubWalkUp") == true then
        local anchor = prompt.Parent
        if anchor and anchor.Name ~= "Prompt_nests" then usedStall = true end
    end
end)

local function readyNests(): number
    local ok, list = pcall(function() return HttpService:JSONDecode(PrivateState.str("NestsJson", "[]")) end)
    if not ok or typeof(list) ~= "table" then return 0 end
    return Rules.readyCount(NestQueue.project(list, math.floor(workspace:GetServerTimeNow()), Config.NestIncubationSeconds))
end

local legacyNest: BasePart? = nil
local function nestTarget(): BasePart?
    local prompts = workspace:FindFirstChild("HubWalkUpPrompts")
    local pad = if prompts then prompts:FindFirstChild("Prompt_nests") else nil
    if pad and pad:IsA("BasePart") then return pad end
    if legacyNest and legacyNest.Parent then return legacyNest end
    local found = workspace:FindFirstChild("EggNest", true) -- the legacy Sanctuary (cave hub off): looked up once, then cached
    legacyNest = if found and found:IsA("BasePart") then found else nil
    return legacyNest
end

local function stallTarget(from: Vector3): (BasePart?, string?)
    local prompts = workspace:FindFirstChild("HubWalkUpPrompts")
    if not prompts then return nil, nil end
    local list, parts = {}, {}
    for _, id in Rules.StallStations do
        local pad = prompts:FindFirstChild("Prompt_" .. id)
        if pad and pad:IsA("BasePart") then
            table.insert(list, {distance = (pad.Position - from).Magnitude})
            table.insert(parts, {pad, id})
        end
    end
    local best = Rules.nearest(list)
    if not best then return nil, nil end
    return parts[best][1], parts[best][2]
end

local function foodTarget(from: Vector3): BasePart?
    local folder = workspace:FindFirstChild("Food")
    if not folder then return nil end
    local best, bestD = nil, 120 -- only food within reach of the screen
    for _, item in folder:GetChildren() do
        local owner = item:GetAttribute("OwnerUserId")
        if owner == nil or owner == player.UserId then
            local part = partOf(item)
            if part and part.Transparency < 1 then
                local d = (part.Position - from).Magnitude
                if d < bestD then best, bestD = part, d end
            end
        end
    end
    return best
end

local clock = 0
task.spawn(function()
    while gui.Parent do
        local state = runState()
        if state == "Active" then played += TICK elseif state == "Sanctuary" then home += TICK end
        local new = Rules.isNew(player:GetAttribute("AccountLevel"), PrivateState.get("StarterRun"))
        local ready = readyNests()
        if gui:GetAttribute("Screen") == "eggs" then openedAt = ready end
        local opened = openedAt >= ready and openedAt >= 0
        if ready == 0 then openedAt = -1 end
        local from = rootPosition()
        local blocked = menuOpen() or from == nil
        point(food, if not blocked and Rules.foodOn({new = new, runState = state, bites = bites, played = played}) then foodTarget(from :: Vector3) else nil)
        point(nest, if not blocked and Rules.nestOn({readyNests = ready, runState = state, opened = opened}) then nestTarget() else nil)
        local stallPart, stallId = nil, nil
        if not blocked and Rules.stallOn({new = new, runState = state, usedStall = usedStall, home = home}) then stallPart, stallId = stallTarget(from :: Vector3) end
        if stallId then stall.label.Text = if stallId == "potions" then Rules.Words.potions else Rules.Words.stall end
        point(stall, stallPart)
        task.wait(TICK)
    end
end)

RunService.RenderStepped:Connect(function(dt)
    clock += dt
    local bob = Rules.bob(clock, motion())
    for _, m in {food, nest, stall} do
        if m.board.Enabled then m.board.StudsOffset = Vector3.new(0, m.lift + bob, 0) end
    end
end)
