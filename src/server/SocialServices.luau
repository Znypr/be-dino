--!strict
-- BD-1227 / BD-1228 / BD-1229 / BD-1233 (docs/242 gaps 17 and 18): one start line in Bootstrap.server for the social and return-hook services.
-- Each part checks its own flag and is required only while that flag is on, so with every flag off this file loads nothing else and does nothing.
-- (The rare hatch news itself lives in RareHatchService, which Bootstrap already starts.)
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config) :: any

local Social = {}

function Social.start()
    if Config.FriendBonusEnabled == true then require(script.Parent.FriendBonusService).start() end -- BD-1228
    if Config.BadgesEnabled == true then require(script.Parent.BadgeAwardService).start() end -- BD-1229
    if Config.CodesEnabled == true then require(script.Parent.CodeService).start(require(script.Parent.ProfileRepository)) end -- BD-1233
end

return Social
