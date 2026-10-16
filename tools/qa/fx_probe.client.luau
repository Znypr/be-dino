--!nocheck
-- BD-429 FX probe (docs/124, docs/117). The cosmetic, weather and mutation FX are built on the CLIENT, so run this in the CLIENT
-- datamodel in Play mode (Studio MCP execute_luau with the client datamodel, or paste into the command bar after pressing Play and
-- switching the command bar to Client) in YOUR OWN temp Studio copy. Trigger the moment first (hatch a Legendary, force a weather
-- event, equip auras with friends/bots), then run it. It samples for SECONDS (default 6) and prints TSV; save as fx.tsv and run
--   python tools/fx_budget_report.py --runner <luau> --input fx.tsv
-- Set DEVICE to "phone", "tablet" or "desktop" (use Studio's device emulator for phone) and MOMENT to a short name.
-- Rows:
--   MOMENT <device> <name> live3d=<alive particles> big=<alive sprites >= 6 studs> beams=<n> trails=<n> lights=<n> ui=<n> fps=<avg> worstMs=<max frame ms>
-- live3d is ESTIMATED from enabled emitters (Rate x mean Lifetime, capped by Rate==0 emitters' last Emit counts are NOT visible to a script,
-- so one-shot bursts are listed as burstEmitters=<n> instead). fps and worstMs are REAL (RunService.Heartbeat).
local DEVICE = "desktop"
local MOMENT = "unnamed"
local SECONDS = 6

local RunService = game:GetService("RunService")
local Players = game:GetService("Players")

local function snapshot()
    local live, big, beams, trails, lights, burst = 0, 0, 0, 0, 0, 0
    local function scan(root)
        for _, d in root:GetDescendants() do
            if d:IsA("ParticleEmitter") then
                if d.Enabled and d.Rate > 0 then
                    local alive = d.Rate * (d.Lifetime.Min + d.Lifetime.Max) / 2
                    live += alive
                    local peak = 0
                    for _, k in d.Size.Keypoints do peak = math.max(peak, k.Value) end
                    if peak >= 6 then big += alive end
                elseif d.Rate == 0 then
                    burst += 1
                end
            elseif d:IsA("Beam") or d:IsA("Trail") then
                if d.Enabled then
                    if d:IsA("Beam") then beams += 1 else trails += 1 end
                end
            elseif d:IsA("PointLight") or d:IsA("SpotLight") or d:IsA("SurfaceLight") then
                if d.Enabled and d.Brightness > 0 then lights += 1 end
            end
        end
    end
    scan(workspace)
    local ui = 0
    local gui = Players.LocalPlayer and Players.LocalPlayer:FindFirstChildOfClass("PlayerGui")
    if gui then
        for _, d in gui:GetDescendants() do
            if d:IsA("GuiObject") and d.Visible and (d.Name:find("Sparkle") or d.Name:find("Shock") or d.Name:find("LightRay") or d.Name:find("Motif")
                or d.Name:find("Puff") or d.Name:find("Firework") or d.Name:find("Rain") or d.Name:find("Drip") or d.Name:find("Orbit")) then
                ui += 1
            end
        end
    end
    return live, big, beams, trails, lights, ui, burst
end

local frames, worst, peak = 0, 0, {0, 0, 0, 0, 0, 0, 0}
local start = os.clock()
local conn = RunService.Heartbeat:Connect(function(dt)
    frames += 1
    worst = math.max(worst, dt * 1000)
    local vals = {snapshot()}
    for i, v in vals do peak[i] = math.max(peak[i], v) end
end)
while os.clock() - start < SECONDS do task.wait(0.25) end
conn:Disconnect()
local elapsed = os.clock() - start
print(string.format("MOMENT\t%s\t%s\tlive3d=%.0f\tbig=%.0f\tbeams=%d\ttrails=%d\tlights=%d\tui=%d\tburstEmitters=%d\tfps=%.1f\tworstMs=%.1f",
    DEVICE, MOMENT, peak[1], peak[2], peak[3], peak[4], peak[5], peak[6], peak[7], frames / elapsed, worst))
