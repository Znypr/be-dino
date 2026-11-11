--!strict
-- BD-1163 (docs/225): the client half of the starter run, the first run of a brand-new player. Behind Config.StarterRunEnabled (default
-- false, on only in the playtest profile): with the flag off attach returns at once (no listener, no thread) and resultsMode says "normal".
-- The SERVER decides who is a starter (owner-only value StarterRun = 1 while the save has no settled run), starts the run by itself and
-- gives the eggs; this file only shows things:
--   * no "Welcome" lecture at join for a starter (it stays under Settings > Help > How to play);
--   * the happy card "You found 3 eggs!" with ONE button, "Take them home!", when StarterRunEggs eggs are caught. The button asks the
--     server to end the run through the existing RequestEndRun remote (no "Go home?" confirm); the X still closes the card, so a child
--     who wants to keep playing is never trapped;
--   * Run Complete of the starter run: OPEN EGGS is the only big button;
--   * one toast "Run again to find new dinos!" after the starter eggs were opened.
-- All words are in Shared/FtueCopy, all decisions in the pure Shared/FtueRules (tools/verify_starter_run.py). No new art, no new sound.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config) :: any
local Rules = require(Shared.FtueRules)
local Copy = require(Shared.FtueCopy)
local Theme = require(Shared.UITheme)
local PrivateState = require(script.Parent.PrivateState)

local Starter = {}
local player = Players.LocalPlayer
local d: any = nil -- SmallScreens' helper table (body, heading, header, label, button, art, open, close, notify, decoded, markTutorialSeen)
local screens: any = nil
local attached = false
local latched = false -- this join began as a starter; stays true for the session so Run Complete and the hatch know
local starterRunId: any = nil -- the run that ended the starter state (set when StarterRun goes back to 0)
local cardShown: {[Model]: boolean} = setmetatable({}, {__mode = "k"}) :: any
local againShown = false

local function enabled(): boolean
    return Config.StarterRunEnabled == true
end

local function noteSettled()
    if latched and starterRunId == nil and PrivateState.num("StarterRun") == 0 then starterRunId = player:GetAttribute("LastRunId") end
end

-- Run Complete buttons: "normal" (Back home, and OPEN EGGS when there are eggs), "openOnly" (the starter run: OPEN EGGS alone) or
-- "wait" (the starter run found eggs and its settlement has not arrived yet: no Back home to press by mistake; the X still closes).
function Starter.resultsMode(hasEggs: boolean): string
    if not enabled() or not latched then return "normal" end
    noteSettled()
    local runId = player:GetAttribute("LastRunId")
    if starterRunId ~= nil then
        return if runId == starterRunId and Rules.starterOnlyOpenEggs(true, hasEggs) then "openOnly" else "normal"
    end
    local found = player:GetAttribute("LastRunCatchScore")
    return if typeof(found) == "number" and found > 0 then "wait" else "normal"
end

local function checkCard()
    local character = player.Character
    if not character then return end
    if Rules.starterCardNow({starter = latched and PrivateState.num("StarterRun") == 1, runState = character:GetAttribute("RunState"),
        eggs = character:GetAttribute("CatchScore"), shown = cardShown[character] == true, cardEggs = Config.StarterRunEggs}) then
        cardShown[character] = true -- once per run
        d.open("starter")
    end
end

local function checkRunAgain()
    noteSettled()
    if Rules.starterRunAgainNow({starter = latched, settled = starterRunId ~= nil, shown = againShown,
        eggsLeft = PrivateState.num("ActiveChestCount") + PrivateState.num("QueuedEggsWaiting") + PrivateState.num("BufferedRevealCount"),
        copies = Rules.collectionCopies(d.decoded("CollectionJson", "{}"))}) then
        againShown = true -- once
        d.notify(Copy.starterRunAgain, Theme.Colors.gold, {kind = "major", key = "starter_again", icon = "egg", seconds = 8})
    end
end

local function latch()
    if latched or PrivateState.num("StarterRun") ~= 1 then return end
    latched = true
    d.markTutorialSeen() -- no lecture before the first run; How to play stays in Settings
    if screens.shown == "tutorial" and d.heading.Text == "Welcome to Be Dino!" then d.close() end -- it opened before the save facts arrived
    checkCard()
end

-- The starter card (screen name "starter", opened by checkCard, drawn through SmallScreens.render).
function Starter.render()
    local body, C = d.body, Theme.Colors
    d.heading.Text, d.header.BackgroundColor3 = Copy.starterCardHeading, C.gold
    local visibleH = require(script.Parent.ModalCompact).bodyHeight() -- phone landscape shows less than the 402 px body
    local artSize = math.clamp(visibleH - 176, 60, 200)
    d.art(body, "egg", (824 - artSize) / 2, 0, artSize)
    local character = player.Character
    local eggs = if character then character:GetAttribute("CatchScore") else nil
    d.label(body, Copy.starterCardTitle(if typeof(eggs) == "number" and eggs >= 1 then eggs else Config.StarterRunEggs), 62, artSize + 4, 700, 56, 40, C.gold)
    local go = d.button(body, Copy.starterCardButton, 212, visibleH - 72, 400, 68, C.accent, function()
        local current = player.Character
        d.close()
        if current and current:GetAttribute("RunState") == "Active" then d.endRun:FireServer() d.notify("Going home...", C.gold) end
    end)
    go.TextSize = 30
end

-- helpers = the table SmallScreens.attach got from Bootstrap (plus endRun); owner = SmallScreens (owner.shown = the last screen it drew).
function Starter.attach(helpers: any, owner: any)
    if not enabled() or attached then return end
    attached = true
    d, screens = helpers, owner
    PrivateState.onChanged("StarterRun", function()
        latch()
        noteSettled()
        checkRunAgain()
    end)
    for _, name in {"ActiveChestCount", "QueuedEggsWaiting", "BufferedRevealCount", "CollectionJson"} do PrivateState.onChanged(name, checkRunAgain) end
    local function watch(character: Model)
        character:GetAttributeChangedSignal("CatchScore"):Connect(checkCard)
        character:GetAttributeChangedSignal("RunState"):Connect(checkCard)
        checkCard()
    end
    player.CharacterAdded:Connect(watch)
    if player.Character then watch(player.Character) end
    -- the server refused Home because a bigger dinosaur is close: offer the card again a little later
    player:GetAttributeChangedSignal("LastExitStatusAt"):Connect(function()
        local character = player.Character
        if not character or player:GetAttribute("LastExitStatus") ~= "predator_nearby" or not cardShown[character] then return end
        task.delay(6, function()
            if player.Character == character then cardShown[character] = nil checkCard() end
        end)
    end)
    latch()
end

return Starter
