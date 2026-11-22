--!strict
-- BD-1287 (docs/246): the shop menu kit tabs OUTSIDE the window on the right, as on the owner-approved Aura Shop: an illustrated icon with a
-- white outlined word under it, no box; the selected one a little bigger on a lime kit tile (BD-1296). Screens pass only data:
-- KitRail.draw(holder, rail, {tabs, words, selected, icon(tab) -> id?, onTab(tab)}); rail = SaeFrameRules.layout(...).rail.
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Kit2 = require(Shared.ShopKit2)
local Art = require(script.Parent.KitArt)

local R = {}

export type Spec = {tabs: {string}, words: {[string]: string}, selected: string?, icon: (string) -> string?, onTab: (string) -> ()}

function R.draw(holder: Instance, rail: any, spec: Spec)
    for i, tab in spec.tabs do
        local s = rail.slots[i]
        if not s then break end
        local selected = tab == spec.selected
        local size = if selected then math.floor(rail.icon * 0.95 + 0.5) else rail.icon -- the selected icon sits inside its lime tile (BD-1296)
        local icon = spec.icon(tab)
        local cx = s.x + math.floor(s.w / 2)
        local tile = math.floor(rail.icon * 1.15 + 0.5)
        local iconY = s.y + rail.icon - size - (if selected then math.floor((tile - size) / 2) else 0) -- the tile clears the word under it
        if selected then
            -- BD-1296 (lead polish 2026-11-23, ChatGPT: "the active tab must read as selected"): a lime backing tile behind the active
            -- icon, the kit 2 green button piece (lime, dark outline) as a square about 1.15 x the icon
            local k = tile / Kit2.Studded[Kit2.buttonSlot(false)].h
            Art.studded(holder, "KitTabTile_" .. tab, Kit2.buttonSlot(false), cx - math.floor(tile / 2), iconY + math.floor((size - tile) / 2), tile, tile, 31, k * 0.9, k * 0.6)
        end
        if icon then Art.picture(holder, "KitTabIcon_" .. tab, icon, cx - math.floor(size / 2), iconY, size, size, 32) end
        Art.words(holder, "KitTabWord_" .. tab, spec.words[tab] or tab, s.x - 6, s.y + rail.icon, s.w + 12, rail.labelSize + 2, rail.labelSize, 32)
        Art.tap(holder, "KitTab_" .. tab, s.x, s.y, s.w, s.h, 34, function() spec.onTab(tab) end)
    end
end

return R
