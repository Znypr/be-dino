--!strict
-- BD-1221 (Config.PlazaHubEnabled, Shared/PlazaHubLayout): walk-up prompts at the four plaza stalls. A press goes through the rail's own
-- path: HubTravelClient.press(screen, true) first (so a run keeps its "At home" rule, BD-1105 / docs/104 s7.7, exactly like the rail),
-- then HubTravelClient.openScreen(screen) when the rail would open the screen. Client presentation only: nothing is sent or stored here.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Layout = require(Shared:WaitForChild("PlazaHubLayout"))
if not Layout.enabled(Config) then return end
local SignCopy = require(Shared:WaitForChild("HubSignCopy"))
local Travel = require(script.Parent:WaitForChild("HubTravelClient"))

local function attach(anchor: Instance)
    if not anchor:IsA("BasePart") or anchor:FindFirstChild("PlazaOpen") then return end
    local station, screen = anchor:GetAttribute("PlazaStation"), anchor:GetAttribute("PlazaScreen")
    if typeof(station) ~= "string" or typeof(screen) ~= "string" then return end
    local prompt = Instance.new("ProximityPrompt")
    prompt.Name, prompt.ActionText, prompt.ObjectText = "PlazaOpen", "Open", SignCopy.sign(station) or ""
    prompt.KeyboardKeyCode, prompt.GamepadKeyCode = Enum.KeyCode[Layout.PromptKey], Enum.KeyCode[Layout.PromptGamepad]
    prompt.HoldDuration, prompt.MaxActivationDistance, prompt.RequiresLineOfSight = 0, Layout.PromptDistance, false
    prompt.Triggered:Connect(function()
        if Travel.press(screen, true) then return end -- blocked ("At home" in a run) or travelling: the rail's own answer
        Travel.openScreen(screen)
    end)
    prompt.Parent = anchor
end

local arena = workspace:WaitForChild("BeDinoArena")
local folder = arena:WaitForChild("PlazaHub", 60)
if not folder then return end
for _, d in folder:GetDescendants() do if d.Name == "PlazaPrompt" then attach(d) end end
folder.DescendantAdded:Connect(function(d) if d.Name == "PlazaPrompt" then task.defer(attach, d) end end)
