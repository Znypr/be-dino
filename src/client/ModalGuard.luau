--!strict
-- BD-1196 (docs/234, polish finding P-43bc51): rules of the shared menu window that Bootstrap's open() asks.
--  * routed: a name that has its own menu ("fusion" = FusionMenu) is handed to that menu and the shared window is left alone. It used to open the shared window, which
--    has no "fusion" screen: an empty window under the title of the screen before ("Potion Shop").
--  * fill: after a screen drew, a window with NO content at all gets its own title (from the name) and one calm line, never the last screen's title over nothing.
-- Pure rules + two small Instance writes; tools/verify_fusion_route.py runs both.
local Guard = {}

Guard.OwnMenus = {fusion = true}
Guard.EmptyText = "Nothing here yet"

-- BD-1266 (docs/244 s2.14): screens that moved onto the standard window register here (ShopScreens.attach, only while
-- Config.StandardMenuEnabled is on): route() opens that window and returns true. Any other screen first calls onOther (it closes the
-- standard window), so two windows never stack. Both stay empty with the flag off.
Guard.Routes = {} :: {[string]: () -> boolean}
Guard.onOther = nil :: (() -> ())?

-- openOwn: the function that opens the own menu (Bootstrap's openFusion; nil while it is not set up yet).
function Guard.routed(name: string, openOwn: (() -> ())?): boolean
    local route = Guard.Routes[name]
    if route and route() then return true end
    if Guard.onOther then Guard.onOther() end
    if Guard.OwnMenus[name] and openOwn then
        openOwn()
        return true
    end
    return false
end

function Guard.title(name: string): string
    return string.upper(string.sub(name, 1, 1)) .. string.sub(name, 2)
end

-- ui: {body, heading, header, label(parent, text, x, y, w, h, size, color), color, gold}. The hatch body fills itself while the egg opens: left alone.
function Guard.fill(name: string, ui: any)
    if name == "hatch" or #ui.body:GetChildren() > 0 then return false end
    ui.heading.Text, ui.header.BackgroundColor3 = Guard.title(name), ui.color
    ui.label(ui.body, Guard.EmptyText, 0, 120, 824, 60, 32, ui.gold)
    return true
end

return Guard
