--!strict
-- BD-503 (docs/147 s4 item 5): the ONE helper every server-side teleport of a dinosaur goes through. With workspace.StreamingEnabled the client only holds
-- the world near its character, so a dino moved across the map could land where Terrain voxels (not Models, so not Persistent) are not loaded yet.
-- request() asks the engine to stream the area around the target to this client first. INERT while StreamingEnabled is false (today's shipped
-- profiles): it returns at once and touches nothing. Never blocks a teleport for long and never throws: pcall + a short timeout.
local Players = game:GetService("Players")

local StreamingTeleport = {}
StreamingTeleport.DefaultTimeout = 3 -- seconds RequestStreamAroundAsync may wait; a failure or timeout only means "go anyway"
StreamingTeleport.NearStuds = 64 -- a target this close to where the dino stands is inside the streaming min radius already: no request, no wait

-- Returns true when a stream request was made and finished without an error (a timeout counts: the teleport proceeds either way).
function StreamingTeleport.request(player: Player, position: Vector3, timeout: number?): boolean
    if not workspace.StreamingEnabled then return false end
    if player.Parent ~= Players then return false end
    local ok = pcall(function() player:RequestStreamAroundAsync(position, timeout or StreamingTeleport.DefaultTimeout) end)
    return ok
end

-- True when a teleport of `character` to `position` should ask for streaming first (streaming on and the target is not right here).
function StreamingTeleport.needed(character: Model, position: Vector3): boolean
    if not workspace.StreamingEnabled then return false end
    local root = character:FindFirstChild("HumanoidRootPart")
    if not root or not root:IsA("BasePart") then return true end
    return ((root :: BasePart).Position - position).Magnitude > StreamingTeleport.NearStuds
end

return StreamingTeleport
