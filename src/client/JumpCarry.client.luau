--!strict
-- BD-212: a normal Space jump is a forward bound, not a straight hop. At take-off the local dino keeps
-- its run direction with a small horizontal boost (scaled by its speed, none when standing still)
-- until it lands. The E leap is separate (LeapService sets MovementSpeedLimit while it runs) and is
-- left alone. The boost stays far inside MovementGuard's horizontal envelope (WalkSpeed x tolerance).
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local Config = require(game:GetService("ReplicatedStorage"):WaitForChild("Shared"):WaitForChild("Config"))

local CARRY = Config.JumpForwardCarry -- PROVISIONAL horizontal speed multiplier while airborne
local MIN_SPEED = 4 -- below this the jump stays a plain hop

local carry: Vector3? = nil
local humanoid: Humanoid? = nil
local root: BasePart? = nil

local function bind(character: Model)
    carry = nil
    local h = character:WaitForChild("Humanoid", 10)
    local r = character:WaitForChild("HumanoidRootPart", 10)
    if not h or not h:IsA("Humanoid") or not r or not r:IsA("BasePart") then return end
    humanoid, root = h, r
    h.StateChanged:Connect(function(_, new)
        if new == Enum.HumanoidStateType.Jumping then
            local v = r.AssemblyLinearVelocity
            local flat = Vector3.new(v.X, 0, v.Z)
            if flat.Magnitude >= MIN_SPEED and character:GetAttribute("MovementSpeedLimit") == nil then
                local speed = math.min(flat.Magnitude, h.WalkSpeed) * CARRY
                carry = flat.Unit * speed
            end
        elseif new ~= Enum.HumanoidStateType.Freefall then
            carry = nil
        end
    end)
end

RunService.Heartbeat:Connect(function()
    local c, h, r = carry, humanoid, root
    if not c or not h or not r or not r.Parent then return end
    local state = h:GetState()
    if state ~= Enum.HumanoidStateType.Jumping and state ~= Enum.HumanoidStateType.Freefall then carry = nil return end
    -- Steering still works: follow the stick/keys, keep the boosted speed.
    local dir = h.MoveDirection
    if dir.Magnitude < 0.1 then carry = nil return end
    local boosted = Vector3.new(dir.X, 0, dir.Z).Unit * c.Magnitude
    local v = r.AssemblyLinearVelocity
    r.AssemblyLinearVelocity = Vector3.new(boosted.X, v.Y, boosted.Z)
end)

local player = Players.LocalPlayer
player.CharacterAdded:Connect(bind)
if player.Character then task.spawn(bind, player.Character) end
