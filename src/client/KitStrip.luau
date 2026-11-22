--!strict
-- BD-1287 (docs/246): the shop menu kit effect strip, as on the owner-approved Aura Shop card: the dark studded kit 2 strip with one short
-- line in white outlined words, the number green ("x1.15 Growth": rich = the RichText copy, text = the same without tags). While the kit 2
-- strip is not bound it is the Toybox dark button. Screens pass only data: KitStrip.draw(parent, name, x, y, w, h, z, spec).
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Kit2 = require(Shared.ShopKit2)
local Rules = require(Shared.SaeFrameRules)
local Art = require(script.Parent.KitArt)

local S = {}

export type Spec = {text: string, rich: string?, textSize: number}

function S.draw(parent: Instance, name: string, x: number, y: number, w: number, h: number, z: number, spec: Spec): Frame
    local holder = Art.box(parent, name, x, y, w, h, z)
    local k = h / Kit2.Studded[Kit2.StripSlot].h
    if not Art.studded(holder, "Face", Kit2.StripSlot, 0, 0, w, h, z, k, k) then
        Art.kit(holder, "Face", "toybox_button_dark", 0, 0, w, h, z)
    end
    local size = Rules.fitSize(spec.text, w - 14, spec.textSize)
    Art.words(holder, "Line", spec.rich or spec.text, 0, -math.floor(h * 0.05), w, h, size, z + 1, nil, if spec.rich then spec.text else nil)
    return holder
end

return S
