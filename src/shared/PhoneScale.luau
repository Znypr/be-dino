--!strict
-- BD-333/BD-334: pure scale policy for modals and HUD pieces on short (phone landscape) viewports.
-- No Roblox services: Bootstrap/ModalCompact apply the numbers, tools/verify_phone_scale.py checks them offline.
-- Input is the ScreenGui AbsoluteSize in pixels (safe insets and the Roblox top bar are already excluded).
-- Desktop (tall) viewports keep the old one-canvas rule exactly: scale = min(1, (w-40)/860, (h-40)/520) on an 860x520 panel.
-- Short viewports use a "compact" mode: the panel fills the viewport, the UIScale never drops under CompactFloor, and the
-- body scrolls instead of shrinking, so text and buttons stay readable (docs/72 floors: text >= 14 px, buttons >= 44 px).
local PhoneScale = {}

PhoneScale.MinText = 14 -- px on screen
PhoneScale.MinButton = 44 -- px on screen (touch target edge)
PhoneScale.DesktopW, PhoneScale.DesktopH = 860, 520
PhoneScale.CompactBelow = 500 -- gui height under this is "compact" (phone landscape; 1080x720 and bigger stay desktop)
PhoneScale.CompactFloor = 0.8 -- never shrink a compact modal under this
PhoneScale.Margin = 8 -- px gap between the compact panel and the screen edge
PhoneScale.HeaderH = 48 -- compact header height (design px), desktop is 78 (BD-531: was 56; the close button still floors to 44 px)
PhoneScale.ModalRailGap = 12 -- BD-546: px between the desktop left rail and a desktop modal panel
PhoneScale.ModalRightMargin = 20 -- px between a desktop modal and the right screen edge (the old (w - 40) / 860 rule is 20 on each side)
PhoneScale.RailLabelW = 60 -- px a rail button needs for a 14 px label (SETTINGS is about 58 px), else icon-only
PhoneScale.BodyTop = 56 -- compact body scroller top inside the panel (design px) (BD-531: was 66, 8 px more body on a 332 px phone canvas)

export type Modal = {
    mode: string, scale: number, panelW: number, panelH: number, -- panelW/H in design px (before UIScale)
    bodyW: number, bodyH: number, scrollX: boolean, headerH: number, bodyTop: number,
    centerDx: number, -- BD-546: px the panel centre sits right of the screen centre (desktop, to keep clear of the left rail); 0 elsewhere
    minText: number, minButton: number,
}

function PhoneScale.isCompact(h: number): boolean
    return h < PhoneScale.CompactBelow
end

-- Old rule, kept as one function so desktop is provably unchanged.
function PhoneScale.desktopScale(w: number, h: number): number
    return math.max(0.05, math.min(1, (w - 40) / PhoneScale.DesktopW, (h - 40) / PhoneScale.DesktopH))
end

-- BD-546: `clearLeft` (optional) is the x in px that a DESKTOP modal must stay right of (the left rail's right edge plus ModalRailGap, from
-- TouchLayout.modalClearLeft). Without it, or in compact mode (phones), nothing changes. With it the panel is centred on the screen when it
-- clears, else slid right by `centerDx`, and shrunk only as far as needed to stay on screen.
function PhoneScale.modal(w: number, h: number, clearLeft: number?): Modal
    if not PhoneScale.isCompact(h) then
        local scale, dx = PhoneScale.desktopScale(w, h), 0
        if clearLeft and clearLeft > 0 then
            local room = w - PhoneScale.ModalRightMargin - clearLeft
            scale = math.max(0.05, math.min(scale, room / PhoneScale.DesktopW))
            dx = math.max(0, clearLeft + PhoneScale.DesktopW * scale / 2 - w / 2)
        end
        return {mode = "desktop", scale = scale, panelW = 860, panelH = 520, bodyW = 824, bodyH = 402,
            scrollX = false, headerH = 78, bodyTop = 98, centerDx = dx, minText = PhoneScale.MinText, minButton = PhoneScale.MinButton}
    end
    local scale = math.clamp((w - 2 * PhoneScale.Margin) / PhoneScale.DesktopW, PhoneScale.CompactFloor, 1)
    local panelW = (w - 2 * PhoneScale.Margin) / scale
    local panelH = (h - PhoneScale.Margin) / scale
    return {mode = "compact", scale = scale, panelW = panelW, panelH = panelH, bodyW = math.min(panelW - 8, 842),
        bodyH = panelH - PhoneScale.BodyTop - 4, scrollX = panelW < 850, headerH = PhoneScale.HeaderH,
        bodyTop = PhoneScale.BodyTop, centerDx = 0, minText = PhoneScale.MinText, minButton = PhoneScale.MinButton}
end

-- Design-space size that renders at least `floor` px on screen under `scale`.
function PhoneScale.floorSize(size: number, scale: number, floor: number): number
    if scale <= 0 then return size end
    return math.max(size, math.ceil(floor / scale))
end

function PhoneScale.floorText(size: number, scale: number): number
    return PhoneScale.floorSize(size, scale, PhoneScale.MinText)
end

function PhoneScale.floorButton(height: number, scale: number): number
    return PhoneScale.floorSize(height, scale, PhoneScale.MinButton)
end

-- BD-507: a free-standing panel under its own UIScale (no modal floor pass). The smallest scale at which a `designButton` px tall tap target
-- renders >= MinButton and a `designText` px label >= MinText, never under `base` and never above 1 (a floor is only ever raised to 1:1).
function PhoneScale.floorScale(base: number, designButton: number, designText: number): number
    return math.min(1, math.max(base, PhoneScale.MinButton / math.max(designButton, 1), PhoneScale.MinText / math.max(designText, 1)))
end

-- HUD pieces: the smallest UIScale at which a text of `designText` design px reads >= MinText, capped at `ceiling`.
function PhoneScale.hudScale(base: number, designText: number, ceiling: number): number
    return math.min(ceiling, math.max(base, PhoneScale.MinText / math.max(designText, 1)))
end

-- BD-531: phone-landscape layouts (design px inside the visible compact body, `bodyH` = Modal.bodyH) of the two screens that used to need a
-- scroll for their main action. Pure numbers, used by EggsScreen / Bootstrap's Go home confirm and asserted in tools/verify_phone_scale.py:
-- everything lies inside [0, bodyH], buttons are >= MinButton / CompactFloor tall so they stay >= 44 px on screen, nothing overlaps.
function PhoneScale.eggsLayout(bodyH: number, hint: boolean, scale: number)
    local slotY, nestH = 30, 68
    local cardY = slotY + nestH + 6
    local cardH = bodyH - cardY
    local hintH = if hint then 22 else 0
    local openY = 46 + hintH
    local buttonH = PhoneScale.floorButton(0, scale) + 2 -- renders >= 44 px; Bootstrap's floor pass would only grow a smaller one
    local gearY = cardH - 8 - buttonH
    return {slotY = slotY, nestH = nestH, cardY = cardY, cardH = cardH, hintH = hintH, hintY = 46, openY = openY,
        openH = math.max(buttonH, gearY - 4 - openY), gearY = gearY, gearH = buttonH, rowH = 34}
end

function PhoneScale.exitLayout(bodyH: number, scale: number)
    local buttonH = PhoneScale.floorButton(0, scale) + 2
    return {artY = 10, artSize = 150, lineY = 4, lineH = 84, totalsY = 92, totalsH = 48, buttonH = buttonH, buttonsY = bodyH - buttonH - 8}
end

-- Toasts sit under the top bar on phones so they never cover the bottom action row (Fill/Clear/FUSE, Home).
function PhoneScale.toastAnchor(h: number): string
    return if PhoneScale.isCompact(h) then "top" else "default"
end

return PhoneScale
