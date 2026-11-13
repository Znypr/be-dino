--!strict
-- BD-1182 (docs/228 board 6, docs/229): the window open / close presets of the Bootstrap modal. Bootstrap calls this only while
-- Config.MotionPresetsEnabled is true (default false, on only in the playtest profile); with the flag off this file is never required.
-- The numbers and the Reduce Motion rule come from Shared/UIMotion (pure, tested offline by tools/verify_ui_motion.py); this file only
-- hands them to Theme.animate, which itself jumps to the end state while Reduce Motion is on.
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Theme = require(Shared:WaitForChild("UITheme"))
local UIMotion = require(Shared:WaitForChild("UIMotion"))

local M = {}

-- A closed window opens: the panel scale pops from small past `target` (103%) and rests at `target` in 0.3 s.
-- Bootstrap has already started its own .16 s tween on `scale`; Theme.animate keeps one tween per target, so this one replaces it.
function M.open(scale: UIScale, target: number)
    local plan = UIMotion.windowOpen(not Theme.MotionEnabled)
    if plan.seconds <= 0 then return end -- Reduce Motion: Bootstrap's own call already put the window at its end state
    Theme.cancel(scale)
    scale.Scale = target * plan.from
    Theme.animate(scale, plan.seconds, {Scale = target * plan.to}, Enum.EasingStyle.Back)
end

-- The window closes in 0.15 s (scrim fade, the same small shrink and slide as before). Returns the seconds after which Bootstrap hides it.
-- The settled panel scale and the place the slide ends at come from ModalCompact, as in Bootstrap.
function M.close(scale: UIScale, shade: GuiObject, panel: GuiObject): number
    local plan = UIMotion.windowClose(not Theme.MotionEnabled)
    if plan.seconds <= 0 then return plan.hideAfter end -- Reduce Motion: Bootstrap's own calls already set the end state
    local ModalCompact = require(script.Parent.ModalCompact)
    Theme.animate(scale, plan.seconds, {Scale = ModalCompact.model().scale * plan.shrink})
    Theme.animate(shade, plan.seconds, {BackgroundTransparency = 1})
    Theme.animate(panel, plan.seconds, {Position = ModalCompact.home(.52)})
    return plan.hideAfter
end

return M
