--!strict
-- BD-495 (docs/146 s10, risk 3): the cave hub is built with 30 point lights and 8 shaft beams. A phone gets only the 12 lights nearest to
-- the camera and 4 beams (one per shaft). CLIENT ONLY: the server still builds the same lights; this just flips `Enabled` on this client's copy,
-- re-evaluated on a calm interval (PhoneGuards.Phone.evalSeconds, 0.5 s) with hysteresis in PhoneGuards.selectLights so lights never flicker.
-- Desktop and tablet: step() returns at once and nothing is touched. CaveAtmosphere.step calls this only after its own Config.CaveHub check.
-- Reduce Motion needs no special case: the lights are static data, no motion is involved.
local Players = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local Guards = require(Shared:WaitForChild("PhoneGuards"))
local Recipes = require(Shared:WaitForChild("FxRecipes"))

local Guard = {}
local device: string? = nil
local accumulated = 1 -- evaluate on the first call
local state: {[PointLight]: boolean} = {} -- last Enabled answer per light

local function deviceClass(): string
    if device then return device end
    local camera = workspace.CurrentCamera
    if not camera or camera.ViewportSize.Magnitude < 1 then return "desktop" end -- not sized yet: do not cache a guess
    device = Recipes.deviceClass(UserInputService.TouchEnabled, UserInputService.MouseEnabled, math.min(camera.ViewportSize.X, camera.ViewportSize.Y))
    return device :: string
end

local function caveLights(): ({PointLight}, {Vector3})
    local lights, where = {}, {}
    for _, holder in workspace.Terrain:GetChildren() do
        if holder:IsA("Attachment") and string.sub(holder.Name, 1, 10) == "CaveLight_" then
            local light = holder:FindFirstChildOfClass("PointLight")
            if light then
                table.insert(lights, light)
                table.insert(where, holder.WorldPosition)
            end
        end
    end
    return lights, where
end

local function evaluate(dev: string)
    local camera = workspace.CurrentCamera
    if not camera then return end
    local eye = camera.CFrame.Position
    local lights, where = caveLights()
    local dists: {number} = {}
    local was: {[number]: boolean} = {}
    for i, light in lights do
        dists[i] = (where[i] - eye).Magnitude
        was[i] = state[light] == true
    end
    local on = Guards.selectLights(Guards.caveLightCap(dev), dists, was, Guards.Phone.lightMargin)
    local nextState: {[PointLight]: boolean} = {}
    local enabled = 0
    for i, light in lights do
        local want = on[i] == true
        nextState[light] = want
        if want then enabled += 1 end
        if light.Enabled ~= want then light.Enabled = want end
    end
    state = nextState
    local folder = if workspace:FindFirstChild("Sanctuary") then (workspace.Sanctuary :: Instance):FindFirstChild("CaveLighting") else nil
    if folder then
        local shafts = {}
        local beams: {Beam} = {}
        for _, d in folder:GetDescendants() do
            if d:IsA("Beam") and d:GetAttribute("IsLightingFx") then
                table.insert(beams, d)
                shafts[d.Parent :: Instance] = true
            end
        end
        local shaftCount = 0
        for _ in shafts do shaftCount += 1 end
        local keep = Guards.beamsPerShaft(dev, shaftCount, if shaftCount > 0 then #beams // shaftCount else 0)
        for _, beam in beams do
            local core = string.find(beam.Name, "Core", 1, true) ~= nil -- haze first, core second: the first `keep` per shaft stay
            local want = keep >= 2 or (keep == 1 and not core)
            if beam.Enabled ~= want then beam.Enabled = want end
        end
    end
    Players.LocalPlayer:SetAttribute("CaveLightsOn", enabled) -- QA: how many cave lights this phone keeps on (at most 12)
end

function Guard.step(dt: number)
    local dev = deviceClass()
    if not Guards.isPhone(dev) then return end
    accumulated += dt
    if accumulated < Guards.Phone.evalSeconds then return end
    accumulated = 0
    evaluate(dev)
end

return Guard
