--!strict
-- BD-296: the full-screen modal blur (Lighting.BeDinoModalBlur, built in Bootstrap) belongs to a modal that is actually visible. The old
-- guard only looked at `active` and `shade.Visible`; both stay true when the whole BeDinoUI ScreenGui is disabled (Enabled = false, e.g. a
-- debug sweep or a UI toggle) or removed while a menu was open, so the blur (Size 8) stayed on with nothing on screen. This module is the one
-- rule for "should the blur be on", pure data so tools/verify_modal_blur.py can run it. Bootstrap feeds it the live state and re-checks it on
-- every change of ScreenGui.Enabled / ancestry / shade.Visible, plus a slow poll as a backstop.
local Guard = {}
Guard.Size = 8 -- blur radius while a modal is showing (PROVISIONAL, was inline in Bootstrap)

-- state: active = open menu name ("" = none), shadeVisible = ModalScrim.Visible, guiEnabled = ScreenGui.Enabled,
--        guiAttached = the ScreenGui and the scrim are still inside the PlayerGui (not destroyed / unparented).
export type State = {active: string, shadeVisible: boolean, guiEnabled: boolean, guiAttached: boolean}

function Guard.modalShowing(s: State): boolean
    return s.active ~= "" and s.shadeVisible and s.guiEnabled and s.guiAttached
end

-- Blur size to aim for: Guard.Size only while a modal is showing and motion is allowed (Calm / Reduce Motion = no blur), else 0.
function Guard.target(s: State, motion: boolean): number
    return if motion and Guard.modalShowing(s) then Guard.Size else 0
end

-- true when the blur has to be forced back down now (it is above 0 but no modal is showing).
function Guard.mustClear(s: State, blurSize: number): boolean
    return blurSize > 0 and not Guard.modalShowing(s)
end

return Guard
