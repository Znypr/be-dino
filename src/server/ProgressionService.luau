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
local ClassMovement=require(ReplicatedStorage.Shared.ClassMovement)
local ColourBonus=require(ReplicatedStorage.Shared.ColourBonus)
local Service={}
local PrivateState = require(script.Parent.PrivateState)
-- BD-172: colour growth bonus from the SERVER-held equipped genes (never client data); decoded once per distinct string.
local colourCache={json="",percent=0,multiplier=1}
local function colourGrowth(genesJson:any): (number,number)
    if typeof(genesJson)~="string" then return 0,1 end
    if colourCache.json~=genesJson then
        local ok,genes=pcall(function() return Http:JSONDecode(genesJson) end)
        colourCache.json=genesJson
        colourCache.percent=if ok then ColourBonus.percent(Config.EggColors,genes) else 0
        colourCache.multiplier=1+colourCache.percent/100
    end
    return colourCache.percent,colourCache.multiplier
end
local random=Random.new()
local WeatherClock=require(ReplicatedStorage.Shared.WeatherClock)
local clock=WeatherClock.new(workspace:GetServerTimeNow())
local current=nil
local weatherEnds=0
local nextWeather=0
local buckets={}
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
local function applyWeather()
    current,weatherEnds,nextWeather=clock.current,clock.endsAt,clock.nextAt
    local night=current and table.find({"thunder","bloodmoon","aurora"},current.id)~=nil
    Lighting.ClockTime=if night then 19 elseif current and current.id=="volcano" then 17 else 14
    Lighting.Brightness=if night then .9 elseif current then 1.6 else 2
    weatherAttributes()
end
-- BD-120 owner admin panel (AdminService validates the caller and arguments).
function Service.adminStartWeather(id: string,seconds: number): boolean
    for _,event in Config.Weather do
        if event.id==id then
            WeatherClock.force(clock,workspace:GetServerTimeNow(),event,seconds) applyWeather()
            return true
        end
    end
    return false
end
function Service.adminStopWeather()
    WeatherClock.clear(clock,workspace:GetServerTimeNow()) applyWeather()
end
local adminMultipliers=function() return 1,1 end
function Service.setAdminMultipliers(source: () -> (number,number)) adminMultipliers=source end
local function crystalSpawns(repository)
    local folder=Instance.new("Folder") folder.Name="CrystalCurrency" folder.Parent=workspace
    local entries={}
    local terrain=RaycastParams.new() terrain.FilterType=Enum.RaycastFilterType.Include terrain.FilterDescendantsInstances={workspace.Terrain}
    local obstacles=RaycastParams.new() obstacles.FilterType=Enum.RaycastFilterType.Include obstacles.FilterDescendantsInstances={workspace.BeDinoArena,workspace.Terrain}
    local function place(entry)
        for _=1,60 do
            local reach=require(ReplicatedStorage.Shared.Config).ArenaHalfWidth-15
            local x,z=random:NextNumber(-reach,reach),random:NextNumber(-reach,reach)
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
        local model=Resources.clone("food_amber_a") -- one MeshPart (the legacy amber model is 21 parts x 64 crystals)
        if model then model:ScaleTo(2.2) else model=Resources.clone("amber") if model then model:ScaleTo(1.5) end end
        if model then model.Parent=part end
        local hint=Instance.new("BillboardGui") hint.Size=UDim2.fromOffset(100,28) hint.StudsOffset=Vector3.new(0,1.5,0) hint.MaxDistance=45 hint.Parent=part
        local text=Instance.new("TextLabel") text.Size=UDim2.fromScale(1,1) text.BackgroundTransparency=1
        text.Text="+3 Crystals" text.TextColor3=Color3.new(1,1,1) text.TextSize=18 text.Font=Enum.Font.FredokaOne text.Parent=hint require(game:GetService("ReplicatedStorage").Shared.TextStyle).apply(text) -- BD-390
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
    local function policy(player)
        PrivateState.set(player, "PaidRandomEligible",false)
        local ok,info=pcall(function() return game:GetService("PolicyService"):GetPolicyInfoForPlayerAsync(player) end)
        if player.Parent then PrivateState.set(player, "PaidRandomEligible",ok and typeof(info)=="table" and info.ArePaidRandomItemsRestricted==false) end
    end
    Players.PlayerAdded:Connect(function(player) task.spawn(policy,player) end)
    for _,player in Players:GetPlayers() do task.spawn(policy,player) end
    local remote=Instance.new("RemoteEvent") remote.Name="ProgressionAction" remote.Parent=ReplicatedStorage.BeDinoRemotes
    local response=Instance.new("RemoteEvent") response.Name="ProgressionResult" response.Parent=ReplicatedStorage.BeDinoRemotes
    remote.OnServerEvent:Connect(function(player,action,id,token,replace,...)
        if select("#",...)~=0 or typeof(action)~="string" or not table.find({"buyAura","equipAura","buyTrail","equipTrail","buyPotion","usePotion","buyEgg","upgradeCondition","buyPerk"},action)
            or typeof(id)~="string" or #id>40 or typeof(token)~="string" or #token<1 or #token>80
            or typeof(replace)~="boolean" then return end
        local now=os.clock() local bucket=buckets[player]
        if bucket and (bucket.busy or now-bucket.last<.4) then response:FireClient(player,token,false,"busy") return end
        buckets[player]={last=now,busy=true}
        -- BD-354: a throw inside the action must not leave busy=true forever (every later request would be refused).
        local ran,ok,status=pcall(repository.progressionAction,player,action,id,token,replace)
        if not ran then warn("[Be Dino] ProgressionAction failed: "..tostring(ok)) ok,status=false,"save_failed" end
        if buckets[player] then buckets[player].busy=false end
        if player.Parent then response:FireClient(player,token,ok,status) end
    end)
    nextWeather=clock.nextAt weatherAttributes()
    task.spawn(crystalSpawns,repository)
    task.spawn(function()
        while true do
            task.wait(1)
            local now=workspace:GetServerTimeNow()
            if WeatherClock.step(clock,now,weatherPick) then applyWeather() end
            for _,player in Players:GetPlayers() do
                local p=repository.progression(player)
                local c=player.Character
                if p and c then
                    local mutation=Rules.item(Config.EventMutations,player:GetAttribute("EquippedEventMutation") or "")
                    local growth,speed,loot=Rules.multipliers(p,player:GetAttribute("EquippedSpeciesId") or "compy",current,os.time(),mutation)
                    local adminGrowth,adminSpeed=adminMultipliers()
                    growth*=adminGrowth speed*=adminSpeed
                    local colourPercent,colourMultiplier=colourGrowth(player:GetAttribute("EquippedGenesJson"))
                    growth*=colourMultiplier -- BD-172: applied after the GrowthCap, so it is always an extra <= +10% on gained growth
                    c:SetAttribute("ColourGrowthPercent",colourPercent) PrivateState.set(player, "ColourGrowthPercent",colourPercent)
                    c:SetAttribute("EventMutationId",if mutation then mutation.id else "")
                    c:SetAttribute("GrowthMultiplier",growth) c:SetAttribute("WeatherLootMultiplier",loot)
                    PrivateState.set(player, "GrowthMultiplier",growth) PrivateState.set(player, "SpeedMultiplier",speed) PrivateState.set(player, "LootMultiplier",loot)
                    local h=c:FindFirstChildOfClass("Humanoid")
                    if h then
                        local classX=if GameConfig.CombatEnabled then ClassMovement.walkSpeed(ClassMovement.classForSpecies(player:GetAttribute("EquippedSpeciesId")))/GameConfig.WalkSpeed else 1 -- BD-246, flag off = 1
                        h.WalkSpeed=GameConfig.WalkSpeed*classX*(if c:GetAttribute("RunState")=="Active" then speed else 1)
                    end
                    c:SetAttribute("EquippedAuraId",p.equippedAura)
                    c:SetAttribute("EquippedTrailId",p.equippedTrail or "")
                    c:SetAttribute("ShinyDinosaur",player:GetAttribute("EquippedShiny")==true)
                    c:SetAttribute("GenesJson",player:GetAttribute("EquippedGenesJson") or "null")
                end
            end
        end
    end)
    Players.PlayerRemoving:Connect(function(p) buckets[p]=nil end)
end
return Service
