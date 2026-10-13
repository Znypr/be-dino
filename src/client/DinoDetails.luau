--!strict
-- BD-062 Dino Details for ONE individual dinosaur instance. Content comes from the
-- server's `details` action and the pure FusionSelection.details view model:
-- hatched -> original egg (genes, condition, event, source); fused -> parent list,
-- parent eggs, recipe/odds versions and "Crafted Gold (earned)". Never a fake Gold
-- drop %, and bought cosmetics are listed separately and never count toward rarity.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Preview = require(Shared.DinosaurPreview)
local Sel = require(Shared.FusionSelection)
local PreviewTraits = require(script.Parent.PreviewTraits)
local W = require(script.Parent.FusionWidgets)
local C = W.Colors

local DinoDetails = {}

-- call(payload) -> response|nil (already pcall/timeout wrapped by the caller).
function DinoDetails.show(container: GuiObject, instanceId: string, catalog, call, onBack: () -> ())
    local root = Instance.new("Frame")
    root.Name, root.Size, root.BackgroundColor3, root.Active = "DinoDetails", UDim2.fromScale(1, 1), C.panel, true
    root.Parent = container
    local header = W.box(root, UDim2.new(1, 0, 0, W.Touch + 8), UDim2.new(), C.blue)
    local title = W.label(header, "Loading dino...", UDim2.new(1, -(W.Touch * 2 + 40), 1, -8), UDim2.fromOffset(12, 4), 28, nil, true)
    W.button(header, "BACK", UDim2.new(0, W.Touch * 2, 0, W.Touch), UDim2.new(1, -(W.Touch * 2 + 4), 0, 4), C.red, function()
        root:Destroy()
        onBack()
    end)
    local status = W.label(root, "Loading details...", UDim2.new(1, -24, 0, 40), UDim2.new(0, 12, 0, W.Touch + 20), 22, C.gold)
    task.spawn(function()
        local response = call({action = "details", instanceId = instanceId})
        if not root.Parent then return end
        if type(response) ~= "table" or response.ok ~= true or type(response.dinosaur) ~= "table" then
            status.Text = "Details unavailable: " .. (if type(response) == "table" then tostring(response.reason or "unknown") else "connection problem")
            status.TextColor3 = C.red
            return
        end
        status:Destroy()
        local d = response.dinosaur
        local view = Sel.details(d, catalog)
        title.Text = view.title
        -- Left: preview (stage material + shiny/BIG badges). Right: scrolling facts.
        local stage = W.box(root, UDim2.new(.38, -18, 1, -(W.Touch + 26)), UDim2.new(0, 12, 0, W.Touch + 16), W.StageColors[d.stage or "base"] or C.card)
        local preview = Preview.add(stage, d.speciesId or "compy", if d.stage == "base" or d.stage == nil then "base" else d.stage)
        preview.Size, preview.Position = UDim2.fromScale(1, .72), UDim2.fromScale(0, .02)
        -- Gold/Diamond keep their stage material; Base shows the actual gene colors.
        PreviewTraits.add(preview, {shiny = d.shiny, big = d.big, genes = if d.stage == "base" then d.genes else nil})
        W.label(stage, view.prestige or "", UDim2.new(1, -12, .12, 0), UDim2.new(0, 6, .74, 0), 22, C.text)
        W.swatch(stage, d.genes, UDim2.new(1, -24, .08, 0), UDim2.new(0, 12, .88, 0))
        local facts = W.scroll(root, UDim2.new(.62, -18, 1, -(W.Touch + 26)), UDim2.new(.38, 6, 0, W.Touch + 16))
        W.list(facts, 4)
        local order = 0
        local function line(text: string, color: Color3?, height: number?)
            order += 1
            local l = W.label(facts, text, UDim2.new(1, -14, 0, height or 28), UDim2.new(), 20, color, true)
            l.LayoutOrder = order
            return l
        end
        line("TRAITS", C.gold)
        for _, row in view.traits do line(row.label .. ": " .. row.value) end
        line("PRESTIGE: " .. (view.prestige or ""), C.gold)
        line(if view.origin.kind == "fused" then "FUSION LINEAGE" elseif view.origin.kind == "hatched" then "ORIGINAL EGG" else "ORIGIN", C.gold)
        for _, text in view.origin.lines do line(text, nil, if #text > 48 then 46 else 28) end
        for i, parent in view.origin.parents do
            line(i .. ". " .. parent.text, C.blue)
            line("   Egg: " .. parent.egg, nil, if #parent.egg > 44 then 46 else 28)
        end
        line("COSMETICS (THIS DINO ONLY)", C.purple)
        for _, text in view.cosmetics do line(text, nil, if #text > 48 then 46 else 28) end
    end)
    return root
end

return DinoDetails
