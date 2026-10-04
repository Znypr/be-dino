--!strict
local Players=game:GetService("Players")
local ReplicatedStorage=game:GetService("ReplicatedStorage")
local Lighting=game:GetService("Lighting")
local Http=game:GetService("HttpService")
local Config=require(ReplicatedStorage.Shared.ProgressionConfig)
local Rules=require(ReplicatedStorage.Shared.ProgressionRules)
local Resources=require(ReplicatedStorage.Shared.ResourceModels)
local MovementEnvelope=require(ReplicatedStorage.Shared.MovementEnvelope)
local GameConfig=require(ReplicatedStorage.Shared.Config)
local Service={}
local random=Random.new()
local WeatherClock=require(ReplicatedStorage.Shared.WeatherClock)
local clock=WeatherClock.new(workspace:GetServerTimeNow())
local current=nil
local weatherEnds=0
local nextWeather=0
local buckets={}
local auraStates={}
local function weatherPick()
    local total=0 for _,event in Config.Weather do total+=event.weight end
    local roll=random:NextNumber(0,total)
    for _,event in Config.Weather do roll-=event.weight if roll<=0 then return event end end
    return Config.Weather[1]
end
local function weatherAttributes()
    workspace:SetAttribute("WeatherId",if current then current.id else "clear")
    workspace:SetAttribute("WeatherName",if current then current.name else "Clear")
    workspace:SetAttribute("WeatherEndsAt",weatherEnds)
    workspace:SetAttribute("NextWeatherAt",nextWeather)
end
local function aura(player,c,p)
    local visual=c:FindFirstChild("DinoVisual")
    local root=c:FindFirstChild("HumanoidRootPart")
    local old=auraStates[player]
    local item=Rules.item(Config.Auras,p.equippedAura)
    if old and (old.character~=c or old.visual~=visual or old.id~=p.equippedAura) then
        for _,attachment in old.attachments do attachment:Destroy() end
        auraStates[player]=nil old=nil
    end
    if not item or not root or not visual then return end
    if not old then
        local attachments={}
        local color=Color3.fromRGB(item.color[1],item.color[2],item.color[3])
        for i=1,8 do
            local attachment=Instance.new("Attachment") attachment.Name="EquippedAuraEffect" attachment.Parent=root
            local emitter=Instance.new("ParticleEmitter")
            emitter.Name="AuraParticles" emitter.Texture="rbxasset://textures/particles/sparkles_main.dds"
            emitter.Color=ColorSequence.new(color)
            emitter.LightEmission=.8 emitter.Rate=1.5 emitter.Lifetime=NumberRange.new(.7,1.1)
            emitter.Speed=NumberRange.new(.3,.8) emitter.SpreadAngle=Vector2.new(30,30)
            emitter.Transparency=NumberSequence.new({NumberSequenceKeypoint.new(0,.15),NumberSequenceKeypoint.new(1,1)})
            emitter.Parent=attachment
            table.insert(attachments,attachment)
        end
        local light=Instance.new("PointLight") light.Color=color light.Brightness=.6 light.Parent=attachments[1]
        old={id=p.equippedAura,character=c,visual=visual,attachments=attachments,light=light}
        auraStates[player]=old
    end
    local size=c:GetAttribute("VisualScale") or 1
    for i,attachment in old.attachments do
        local angle=i*math.pi/4
        attachment.Position=Vector3.new(math.cos(angle)*1.8*size,-1,math.sin(angle)*1.8*size)
        local emitter=attachment:FindFirstChild("AuraParticles")
        if emitter then emitter.Size=NumberSequence.new(.18*size) end
    end
    old.light.Range=5*size
end

local function crystalSpawns(repository)
    local folder=Instance.new("Folder") folder.Name="CrystalCurrency" folder.Parent=workspace
    local entries={}
    local terrain=RaycastParams.new() terrain.FilterType=Enum.RaycastFilterType.Include terrain.FilterDescendantsInstances={workspace.Terrain}
    local obstacles=RaycastParams.new() obstacles.FilterType=Enum.RaycastFilterType.Include obstacles.FilterDescendantsInstances={workspace.BeDinoArena,workspace.Terrain}
    local function place(entry)
        for _=1,60 do
            local x,z=random:NextNumber(-245,245),random:NextNumber(-245,245)
            local hit=workspace:Raycast(Vector3.new(x,140,z),Vector3.new(0,-180,0),terrain)
            if hit and hit.Material~=Enum.Material.Water and hit.Normal.Y>.65 and Vector2.new(x,z-30).Magnitude>12 then
                local position=hit.Position+Vector3.new(0,1.4,0)
                if not workspace:Raycast(position,Vector3.new(0,2,0),obstacles) then
                    entry.part.Position=position
                    if entry.model then entry.model:PivotTo(CFrame.new(hit.Position+Vector3.new(0,.15,0))) end
                    return true
                end
            end
        end
        return false
    end
    local function visible(entry,on)
        entry.part.Transparency=if on and not entry.model then 0 else 1
        entry.hint.Enabled=on
        if entry.model then for _,part in entry.model:GetDescendants() do if part:IsA("BasePart") then part.Transparency=if on then 0 else 1 end end end
    end
    for i=1,Config.CrystalCount do
        local part=Instance.new("Part") part.Name="CrystalPickup" part.Shape=Enum.PartType.Ball part.Size=Vector3.one*1.3
        part.Anchored,part.CanCollide,part.CanTouch,part.CanQuery=true,false,false,false
        part.Material,part.Color=Enum.Material.Neon,Color3.fromRGB(255,200,66)
        local model=Resources.clone("amber") if model then model:ScaleTo(1.5) model.Parent=part end
        local hint=Instance.new("BillboardGui") hint.Size=UDim2.fromOffset(100,28) hint.StudsOffset=Vector3.new(0,1.5,0) hint.MaxDistance=45 hint.Parent=part
        local text=Instance.new("TextLabel") text.Size=UDim2.fromScale(1,1) text.BackgroundTransparency=1
        text.Text="+3 Crystals" text.TextColor3=part.Color text.TextSize=18 text.Font=Enum.Font.FredokaOne text.TextStrokeTransparency=0 text.Parent=hint
        local entry={part=part,model=model,hint=hint,readyAt=0,busy=false,available=true,token=Http:GenerateGUID(false)}
        if place(entry) then part.Parent=folder visible(entry,true) table.insert(entries,entry) else part:Destroy() end
    end
    workspace:SetAttribute("CrystalPickupCount",#entries)
    local previous={}
    Players.PlayerRemoving:Connect(function(p) previous[p]=nil end)
    task.spawn(function()
        while true do
            task.wait(.25)
            local now=os.clock()
            local eligible={}
            for _,player in Players:GetPlayers() do
                local c=player.Character
                local root=if c then c:FindFirstChild("HumanoidRootPart") else nil
                local h=if c then c:FindFirstChildOfClass("Humanoid") else nil
                if c and root and root:IsA("BasePart") and h and h.Health>0 and c:GetAttribute("RunState")=="Active" then
                    local last=previous[player]
                    if last and last.character==c and MovementEnvelope.plausible(root.Position-last.position,now-last.time,2,2,root.AssemblyLinearVelocity.Y,c:GetAttribute("MovementSpeedLimit") or h.WalkSpeed)
                        and player:GetAttribute("MovementSecurityStatus")=="OK" and repository.isLoaded(player) then eligible[player]=true end
                    previous[player]={character=c,position=root.Position,time=now}
                else previous[player]=nil end
            end
            for _,entry in entries do
                if entry.busy then continue end
                if not entry.available and now>=entry.readyAt then
                    if place(entry) then entry.available=true entry.token=Http:GenerateGUID(false) visible(entry,true) end
                end
                if not entry.available then continue end
                local winner=nil local nearest=math.huge
                for _,player in Players:GetPlayers() do
                    local c=player.Character
                    local root=if c then c:FindFirstChild("HumanoidRootPart") else nil
                    local h=if c then c:FindFirstChildOfClass("Humanoid") else nil
                    if c and root and root:IsA("BasePart") and h and h.Health>0 and c:GetAttribute("RunState")=="Active"
                        and eligible[player] then
                        local delta=entry.part.Position-root.Position
                        local distance=Vector3.new(delta.X,0,delta.Z).Magnitude
                        if distance<math.min(5,2.5+(c:GetAttribute("VisualScale") or 1)*.5) and math.abs(delta.Y)<6
                            and distance<nearest and not workspace:Raycast(root.Position,delta,obstacles) then winner=player nearest=distance end
                    end
                end
                if winner then
                    entry.busy=true visible(entry,false)
                    local claimant=winner
                    task.spawn(function()
                        local ok,status=repository.progressionAction(claimant,"grant","crystal",entry.token,false,Config.CrystalValue)
                        if ok then entry.available=false entry.readyAt=os.clock()+Config.CrystalRespawnSeconds end
                        entry.busy=false
                        visible(entry,not ok)
                        if claimant.Parent then claimant:SetAttribute("LastCrystalStatus",status) end
                    end)
                end
            end
        end
    end)
end
function Service.start(repository)
    local remote=Instance.new("RemoteEvent") remote.Name="ProgressionAction" remote.Parent=ReplicatedStorage.BeDinoRemotes
    local response=Instance.new("RemoteEvent") response.Name="ProgressionResult" response.Parent=ReplicatedStorage.BeDinoRemotes
    remote.OnServerEvent:Connect(function(player,action,id,token,replace,...)
        if select("#",...)~=0 or typeof(action)~="string" or not table.find({"buyAura","equipAura","buyPotion","usePotion"},action)
            or typeof(id)~="string" or #id>40 or typeof(token)~="string" or #token<1 or #token>80
            or typeof(replace)~="boolean" then return end
        local now=os.clock() local bucket=buckets[player]
        if bucket and (bucket.busy or now-bucket.last<.4) then response:FireClient(player,token,false,"busy") return end
        buckets[player]={last=now,busy=true}
        local ok,status=repository.progressionAction(player,action,id,token,replace)
        if buckets[player] then buckets[player].busy=false end
        if player.Parent then response:FireClient(player,token,ok,status) end
    end)
    nextWeather=clock.nextAt weatherAttributes()
    task.spawn(crystalSpawns,repository)
    task.spawn(function()
        while true do
            task.wait(1)
            local now=workspace:GetServerTimeNow()
            if WeatherClock.step(clock,now,weatherPick) then
                current,weatherEnds,nextWeather=clock.current,clock.endsAt,clock.nextAt
                Lighting.ClockTime=if current and current.id=="thunder" then 19 else 14
                Lighting.Brightness=if current and current.id=="thunder" then .9 elseif current then 1.6 else 2
                weatherAttributes()
            end
            for _,player in Players:GetPlayers() do
                local p=repository.progression(player)
                local c=player.Character
                if p and c then
                    local growth,speed,loot=Rules.multipliers(p,player:GetAttribute("EquippedSpeciesId") or "compy",current,os.time())
                    c:SetAttribute("GrowthMultiplier",growth) c:SetAttribute("WeatherLootMultiplier",loot)
                    player:SetAttribute("GrowthMultiplier",growth) player:SetAttribute("SpeedMultiplier",speed) player:SetAttribute("LootMultiplier",loot)
                    local h=c:FindFirstChildOfClass("Humanoid")
                    if h then h.WalkSpeed=GameConfig.WalkSpeed*(if c:GetAttribute("RunState")=="Active" then speed else 1) end
                    aura(player,c,p)
                end
            end
        end
    end)
    Players.PlayerRemoving:Connect(function(p) buckets[p]=nil auraStates[p]=nil end)
end
return Service
