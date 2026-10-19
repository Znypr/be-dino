--!strict
-- BD-1130 (docs/205 pictures 434, 435, 440): ONE answer to "is a game menu open?" for the playtest tools that lie in the bottom-left corner
-- (the "Tell us!" button of FeedbackClient and the Admin button of AdminPanel). Studio round 8 at 516 x 481: both lay over the Fusion menu.
-- Why they did not hide: the Fusion menu is its own ScreenGui, BeDinoFusionUI, and it is created only the first time the Fusion menu opens, so a
-- one-time WaitForChild at start-up timed out (30 s, and held the rest of the set-up back with it). This module hooks PlayerGui.ChildAdded instead, so a
-- ScreenGui that appears later is picked up, and it keeps its own state (no Bootstrap local).
--   scrimOpen():  the BeDinoUI ModalScrim is visible (Index, shops, Eggs, Settings ...)
--   fusionOpen(): BeDinoFusionUI exists and is enabled
--   anyOpen():    either
-- `onChange` runs after anything that may have changed the answer. Nothing here draws or moves anything.
local MenuWatch = {}

export type Watch = {scrimOpen: () -> boolean, fusionOpen: () -> boolean, anyOpen: () -> boolean}

function MenuWatch.watch(playerGui: Instance, onChange: () -> ()): Watch
    local scrim: any = nil
    local fusion: any = nil

    local function hookFusion(child: any)
        if child == fusion or child.Name ~= "BeDinoFusionUI" or not child:IsA("ScreenGui") then return end
        fusion = child
        child:GetPropertyChangedSignal("Enabled"):Connect(onChange)
        onChange()
    end
    local function hookUi(ui: any)
        task.spawn(function()
            local found = ui:WaitForChild("ModalScrim", 30)
            if found == nil or scrim == found or not found:IsA("GuiObject") then return end
            scrim = found
            found:GetPropertyChangedSignal("Visible"):Connect(onChange)
            onChange()
        end)
    end
    local function look(child: any)
        hookFusion(child)
        if child.Name == "BeDinoUI" then hookUi(child) end
    end

    playerGui.ChildAdded:Connect(look)
    for _, child in playerGui:GetChildren() do look(child) end

    local function scrimOpen(): boolean return scrim ~= nil and scrim.Visible == true end
    local function fusionOpen(): boolean return fusion ~= nil and fusion.Enabled == true end
    return {scrimOpen = scrimOpen, fusionOpen = fusionOpen, anyOpen = function() return scrimOpen() or fusionOpen() end}
end

return MenuWatch
