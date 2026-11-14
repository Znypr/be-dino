--!strict
-- BD-1192 (docs/234, polish finding P-9283ac): the crystal icon and the price on a shop button are ONE group, centred on the button, measured from the real text.
-- On the Aura cards "3700 Crystals" ran into the icon: the icon sat at a fixed spot and the text was centred by the button on its own. Here the group is
-- icon + gap + text; its left edge is (button width - group) / 2, the text starts after the icon. When the group is wider than the button less the margins the
-- text size steps down (never under minSize); at the smallest size the group still starts at the margin. Pure maths, no Instances: tools/verify_price_group.py.
local PriceGroup = {}

export type Layout = {size: number, iconX: number, textLeft: number, groupW: number, fits: boolean}

-- measure(size) -> the text width in px at that size (TextService on a client, an estimate in a test).
function PriceGroup.layout(measure: (number) -> number, startSize: number, minSize: number, buttonW: number, iconSize: number, gap: number, margin: number): Layout
    local size = startSize
    local room = buttonW - 2 * margin
    while true do
        local textW = measure(size)
        local groupW = iconSize + gap + textW
        if groupW <= room or size <= minSize then
            local iconX = math.max(margin, (buttonW - groupW) / 2)
            return {size = size, iconX = iconX, textLeft = iconX + iconSize + gap, groupW = groupW, fits = groupW <= room}
        end
        size -= 1
    end
end

return PriceGroup
