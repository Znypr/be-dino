--!strict
-- BD-1287 (docs/246): the shop menu kit tabs OUTSIDE the window on the right, as on the owner-approved Aura Shop: an illustrated icon with a
-- white outlined word under it, no box; the selected one a little bigger. Screens pass only data:
-- KitRail.draw(holder, rail, {tabs, words, selected, icon(tab) -> id?, onTab(tab)}); rail = SaeFrameRules.layout(...).rail.
local Art = require(script.Parent.KitArt)

local R = {}

export type Spec = {tabs: {string}, words: {[string]: string}, selected: string?, icon: (string) -> string?, onTab: (string) -> ()}

function R.draw(holder: Instance, rail: any, spec: Spec)
    for i, tab in spec.tabs do
        local s = rail.slots[i]
        if not s then break end
        local selected = tab == spec.selected
        local size = if selected then rail.selectedIcon else rail.icon
        local icon = spec.icon(tab)
        local cx = s.x + math.floor(s.w / 2)
        if icon then Art.picture(holder, "KitTabIcon_" .. tab, icon, cx - math.floor(size / 2), s.y + rail.icon - size, size, size, 32) end
        Art.words(holder, "KitTabWord_" .. tab, spec.words[tab] or tab, s.x - 6, s.y + rail.icon, s.w + 12, rail.labelSize + 2, rail.labelSize, 32)
        Art.tap(holder, "KitTab_" .. tab, s.x, s.y, s.w, s.h, 34, function() spec.onTab(tab) end)
    end
end

return R
