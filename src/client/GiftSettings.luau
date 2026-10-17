--!strict
-- BD-570 (docs/134 s13): the client's one connection to the GiftAction remote, shared by the Settings row "Gifts from" (SettingsMenu) and the
-- gift popup (GiftPopup.client). The rules and the exact requests live in Shared/GiftUiModel (pure, verified offline by tools/verify_gift_ui.py);
-- this file only owns the remote and the one controller. Nothing here runs unless Config.GiftClaimEnabled is on: both callers check the flag
-- BEFORE they require this module, so with the flag off no remote is looked up and nothing is invoked.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Model = require(Shared:WaitForChild("GiftUiModel"))

local M = {}
local remote: RemoteFunction? = nil
local controller: Model.Controller? = nil
local loading = false

-- Non-blocking: the remote exists once the server's GiftService started. nil = this server has gifts off (the row then stays hidden).
local function findRemote(): RemoteFunction?
    if remote ~= nil and (remote :: RemoteFunction).Parent ~= nil then return remote end
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    local found = if folder then folder:FindFirstChild("GiftAction") else nil
    remote = if found ~= nil and found:IsA("RemoteFunction") then found else nil
    return remote
end
function M.available(): boolean
    return findRemote() ~= nil
end
-- The remote call behind the controller. Yields; nil when the call failed or there is no remote.
local function invoke(request: {[string]: any}): any
    local target = findRemote()
    if target == nil then return nil end
    local ok, response = pcall(function() return (target :: RemoteFunction):InvokeServer(request) end)
    return if ok then response else nil
end
function M.controller(): Model.Controller
    if controller == nil then controller = Model.controller(invoke) end
    return controller :: Model.Controller
end

-- Reads the saved value once per menu draw until it has loaded. `changed` runs (on the calling thread's behalf) only when the shown value moved.
function M.refresh(changed: () -> ())
    local c = M.controller()
    if c.loaded() or loading then return end
    loading = true
    task.spawn(function()
        local moved = c.refresh()
        loading = false
        if moved then changed() end
    end)
end

-- True while the Settings row is on screen inside an open menu, so a late answer never reopens a menu the player closed or switched.
function M.rowShowing(): boolean
    local playerGui = Players.LocalPlayer:FindFirstChild("PlayerGui")
    local gui = if playerGui then playerGui:FindFirstChild("BeDinoUI") else nil
    local scrim = if gui then gui:FindFirstChild("ModalScrim") else nil
    local button = if gui then gui:FindFirstChild("Choice_" .. Model.RowLabel .. "_" .. Model.Default, true) else nil
    return scrim ~= nil and scrim:IsA("GuiObject") and scrim.Visible and button ~= nil
end

return M
