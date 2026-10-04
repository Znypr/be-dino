--!strict
-- Client-local precipitation pool: bounded instance count and no gameplay collision.
local Lighting=game:GetService("Lighting")
local Players=game:GetService("Players")
local RunService=game:GetService("RunService")
local Shared=game:GetService("ReplicatedStorage").Shared
local Theme=require(Shared.UITheme)
local player=Players.LocalPlayer
local random=Random.new()
local folder=Instance.new("Folder") folder.Name="LocalWeatherFX" folder.Parent=workspace
local drops={}
for _=1,36 do
    local part=Instance.new("Part") part.Name="Precipitation"
    part.Anchored,part.CanCollide,part.CanTouch,part.CanQuery,part.CastShadow=true,false,false,false,false
    part.Material=Enum.Material.Neon part.Transparency=1 part.Parent=folder
    table.insert(drops,{part=part,x=random:NextNumber(-20,20),z=random:NextNumber(-20,20),y=random:NextNumber(-10,20)})
end
local flash=Instance.new("ColorCorrectionEffect") flash.Name="ThunderFlash" flash.Parent=Lighting
local nextFlash=0 local flashUntil=0
local elapsed=0
RunService.Heartbeat:Connect(function(dt)
    elapsed+=dt
    if elapsed<1/30 then return end
    dt=elapsed elapsed=0
    local id=workspace:GetAttribute("WeatherId") or "clear"
    local c=player.Character
    local root=if c then c:FindFirstChild("HumanoidRootPart") else nil
    local on=id~="clear" and Theme.MotionEnabled and root~=nil
    for _,drop in drops do
        local part=drop.part
        part.Transparency=if on then .35 else 1
        if on then
            drop.y-=dt*(if id=="blizzard" then 6 else 48)
            if drop.y< -10 then drop.y=20 drop.x=random:NextNumber(-20,20) drop.z=random:NextNumber(-20,20) end
            part.Size=if id=="blizzard" then Vector3.one*.15 else Vector3.new(.04,1.7,.04)
            part.Color=if id=="blizzard" then Color3.new(1,1,1) else Color3.fromRGB(125,197,239)
            part.Position=root.Position+Vector3.new(drop.x,drop.y,drop.z)
        end
    end
    local now=os.clock()
    if id=="thunder" and on and now>=nextFlash then nextFlash=now+random:NextNumber(12,25) flashUntil=now+.12 end
    flash.Brightness=if id=="thunder" and on and now<flashUntil then .25 else 0
    if c then
        local rootPart=c:FindFirstChild("HumanoidRootPart")
        if rootPart then for _,part in rootPart:GetDescendants() do if part:IsA("ParticleEmitter") and part.Name=="AuraParticles" then part.Enabled=Theme.MotionEnabled end end end
    end
end)
