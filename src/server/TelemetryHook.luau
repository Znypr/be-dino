--!strict
-- BD-649..653 (docs/167): the one-line way for a server service to report a counted event ("rate_limited", "hatches", "shop_purchases",
-- "fusions") to TelemetryService. With Config.RunTelemetryEnabled off (default build) this is one boolean test: TelemetryService is
-- never required, nothing is stored. It never throws, never touches a profile, an attribute or a remote, and carries no user id.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)

local TelemetryHook = {}
local service: any = nil

-- name: a RunTelemetry.CountNames entry; label: short service label (letters and digits, "Chest"); player: optional, marks the funnel step.
function TelemetryHook.count(name: string, label: string?, player: any?)
    if (Config :: any).RunTelemetryEnabled ~= true then return end
    if service == nil then
        local ok, found = pcall(require, script.Parent.TelemetryService)
        if not ok then return end
        service = found
    end
    pcall(service.count, name, label, player)
end

return TelemetryHook
