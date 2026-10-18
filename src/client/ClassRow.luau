--!strict
-- BD-1099 (owner 2026-10-18: "class icons wherever the class is shown, not only on the reveal card"): the class badge (the owner's icon from
-- AssetSlots, drawn by Shared/ClassBadge) in the places that list a dino's facts: the Dino Index cards, the My dinos details and the inspect details.
-- The class WORD stays next to the icon where there is room. One module so every place looks the same.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local ClassBadge = require(Shared:WaitForChild("ClassBadge"))
local ClassInfo = require(Shared:WaitForChild("ClassInfo"))
local ClassMovement = require(Shared:WaitForChild("ClassMovement"))

local M = {}
M.IconSize = 26 -- design px: a card corner and a details row

-- Puts the badge into `parent` at (x, y) above everything in it (the 3D picture, the cards). Returns the badge frame.
function M.badge(parent: GuiObject, speciesId: any, x: number, y: number, withWord: boolean, z: number): Frame
    local badge = ClassBadge.create(parent, speciesId, M.IconSize, withWord)
    badge.Position = UDim2.fromOffset(x, y)
    badge.ZIndex = z
    for _, d in badge:GetDescendants() do if d:IsA("GuiObject") then d.ZIndex = z end end
    return badge
end

-- A row of a details list (UIListLayout, LayoutOrder `order`): icon and word, left aligned. Replaces an older row with the same name.
function M.row(list: GuiObject, speciesId: any, order: number): Frame
    local old = list:FindFirstChild("ClassRow")
    if old then old:Destroy() end
    local row = Instance.new("Frame")
    row.Name, row.BackgroundTransparency, row.BorderSizePixel = "ClassRow", 1, 0
    row.Size, row.LayoutOrder, row.ZIndex = UDim2.new(1, -10, 0, M.IconSize + 4), order, list.ZIndex + 1
    row:SetAttribute("Class", ClassInfo.forSpecies(speciesId).class)
    row.Parent = list
    M.badge(row, speciesId, 0, 2, true, row.ZIndex + 1)
    return row
end

-- The line of a card under the picture, as the Dino Index drew it inline before (Bootstrap): an event mutation shows nothing here (its badge does), a
-- dino with chosen traits the colour boost, else the class word and how many copies are found. `label` is Bootstrap's label helper.
function M.card(label: any, card: GuiObject, id: string, detail: string, detailY: number, compact: boolean, heroY: number)
    label(card, detail, 5, detailY, 254, if compact then 22 else 25, if compact then 14 else 16)
    -- the class icon in the top-left corner of the picture (icon only on a short card; the word is on the line below when no variant text replaces it)
    return M.badge(card, id, 8, heroY + 2, not compact, card.ZIndex + 8)
end

M.label = function(speciesId: any): string return ClassInfo.Labels[ClassMovement.classForSpecies(speciesId)] end

return M
