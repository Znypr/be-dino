--!strict
-- BD-1212: drives the full-screen hatch stage (Client/HatchStage.luau) from OUTSIDE Bootstrap (Bootstrap is at its size ceiling, docs/150):
-- it watches the shared menu window and
--   * applies the stage while a hatch runs (the hatch builds its HatchFxBack layer in the panel) and restores the window when it ends,
--   * on the burst (the heading changes away from "An egg is hatching...") reads the name / odds / detail lines the hatch wrote and the
--     rarity from the name colour, and shows the rarity word, chips and confetti,
--   * shows the end-of-batch card ("Auto-opened eggs") on the same stage.
-- Config.HatchStageEnabled false = this script returns at once; nothing is watched.
local Players = game:GetService("Players")
local GuiService = game:GetService("GuiService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Shared = ReplicatedStorage:WaitForChild("Shared")
if require(Shared:WaitForChild("Config")).HatchStageEnabled ~= true then return end
local Theme = require(Shared:WaitForChild("UITheme"))
local Stage = require(script.Parent:WaitForChild("HatchStage"))

local player = Players.LocalPlayer
local gui = player:WaitForChild("PlayerGui"):WaitForChild("BeDinoUI") :: ScreenGui
local shade = gui:WaitForChild("ModalScrim") :: GuiObject
local panel = shade:FindFirstChildWhichIsA("Frame") :: Frame
-- the header strip sits at the top of the panel, the body under it (Bootstrap builds them in that order)
local header, body
for _, child in panel:GetChildren() do
    -- Bootstrap: header = box(panel, 4, 4, ...), body at (18, 98); both keep the default name "Frame" (FossilTexture / HatchFx* do not)
    if child:IsA("Frame") and child.Name == "Frame" then
        if child.Position.Y.Offset == 4 then header = child elseif child.Position.Y.Offset == 98 then body = child end
    end
end
assert(header and body, "hatch stage: menu window not found")
local heading = header:FindFirstChildWhichIsA("TextLabel") :: TextLabel

local function reduceMotion(): boolean
    return GuiService.ReducedMotionEnabled == true or player:GetAttribute("ReduceMotion") == true
end
local function parts(): any
    return {gui = gui, shade = shade, panel = panel, header = header, heading = heading, body = body, reduceMotion = reduceMotion()}
end
-- the three lines the hatch writes under the dino: name (rarity colour), odds, detail (top to bottom, 660 px wide)
local function lines(): {TextLabel}
    local found = {}
    for _, o in body:GetChildren() do
        -- Bootstrap places them at y 236 / 288 / 316 (the hatch may resize the name line, so match the band, not the width)
        if o:IsA("TextLabel") and o.Name == "TextLabel" and o.Position.Y.Offset >= 230 and o.Position.Y.Offset <= 330 then table.insert(found, o) end
    end
    table.sort(found, function(a, b) return a.Position.Y.Offset < b.Position.Y.Offset end)
    return found
end
local function rarityOf(color: Color3): number
    local best, bestD = 1, math.huge
    for i = 1, 6 do
        local c = Theme.RarityColors[i]
        local d = (c.R - color.R) ^ 2 + (c.G - color.G) ^ 2 + (c.B - color.B) ^ 2
        if d < bestD then best, bestD = i, d end
    end
    return best
end

local current: Instance? = nil -- the HatchFxBack of the egg on stage
local mode = "" -- "", "hatch" or "summary"
local WAITING = "An egg is hatching..."
heading:GetPropertyChangedSignal("Text"):Connect(function()
    if mode == "hatch" and heading.Text ~= WAITING and heading.Text ~= "" then
        local l = lines()
        if #l >= 3 then
            -- the rarity WORD in the odds line is the truth ("Common • 36% of eggs"); the name colour can be tinted by traits
            local odds = string.gsub(l[2].Text, "<[^>]->", "")
            local rank = nil
            for i, word in {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"} do
                if string.find(odds, "^%s*" .. word) then rank = i end
            end
            rank = rank or rarityOf(l[1].TextColor3)
            Stage.prepare({rarity = rank, color = Theme.RarityColors[rank], failed = heading.Text == "Oops! Splat!",
                nameLabel = l[1], oddsLabel = l[2], detailLabel = l[3]})
            pcall(Stage.reveal)
        end
    end
end)
RunService.Heartbeat:Connect(function()
    local fx = if shade.Visible then panel:FindFirstChild("HatchFxBack") else nil
    if fx then
        if fx ~= current then
            current, mode = fx, "hatch"
            local ok, err = pcall(Stage.apply, parts())
            if not ok then Stage.restore() warn("[Be Dino] hatch stage skipped: " .. tostring(err)) end
        end
    elseif mode == "hatch" then
        current, mode = nil, ""
        Stage.restore()
    end
    local summary = shade.Visible and heading.Text == "Auto-opened eggs" and not fx
    if summary and mode ~= "summary" then
        mode = "summary"
        pcall(Stage.summary, parts())
    elseif not summary and mode == "summary" then
        mode = ""
        Stage.restore()
    end
end)
