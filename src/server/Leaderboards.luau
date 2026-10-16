--!strict
local Players=game:GetService("Players")
local DataStoreService=game:GetService("DataStoreService")
local RunService=game:GetService("RunService")
local Config=require(game:GetService("ReplicatedStorage").Shared.Config)
local Theme=require(game:GetService("ReplicatedStorage").Shared.UITheme)
local CaveHubLayout=require(game:GetService("ReplicatedStorage").Shared.CaveHubLayout)
local PrivateState=require(script.Parent.PrivateState)
local Writes=require(game:GetService("ReplicatedStorage").Shared.LeaderboardWrites) -- BD-362: write only what can change a board
local writeState=Writes.new()
local Leaderboards={}
local preview=RunService:IsStudio() and game.GameId==0
local rows={}
local boards={}
local names={}
local definitions={
    -- rarest "_v2": BD-044 five-tier scale; "_v1" holds old three-tier values and is no longer read.
    {id="rarest",attribute="RarestCaught",title="RAREST DINOS",color=Theme.Colors.gold,store="_v2"},
    {id="playSeconds",attribute="PlaySeconds",title="MOST PLAY TIME",color=Theme.Colors.accent},
    -- Robux Spent stays measured and stored; the cave hides its board (kid audience, Robux line: docs/115 LEAD decision 2026-10-16).
    {id="robux",attribute="RobuxSpent",title="ROBUX SPENT",color=Theme.Colors.blue,hiddenInCave=true},
}
-- Cave board look (docs/114 s6.1 band: warm, never pure black): wood frame, warm dark-brown panel, amber title, cream text.
local CAVE_WOOD,CAVE_PANEL,CAVE_AMBER,CAVE_CREAM=Color3.fromRGB(122,84,52),Color3.fromRGB(104,72,50),Color3.fromRGB(255,190,90),Color3.fromRGB(255,236,190)
local stores={}
function Leaderboards.publish(player: Player, metrics)
    if not metrics and player:GetAttribute("ProfileState")~="Loaded" then return end
    names[player.UserId]=player.Name
    local userId,now,force=player.UserId,os.clock(),metrics~=nil -- metrics are passed on leave: write play time then even inside its throttle
    local pending=0
    for _,definition in definitions do
        local value=if metrics then metrics[definition.id] else PrivateState.get(player,definition.attribute) or 0
        if preview then
            rows[definition.id]=rows[definition.id] or {}
            rows[definition.id][userId]=value
        elseif Writes.shouldWrite(writeState,definition.id,userId,value,now,force) then
            Writes.begin(writeState,definition.id,userId,now)
            pending+=1
            -- the three boards write in parallel (a leave used to wait for three sequential UpdateAsync calls)
            task.spawn(function()
                local ok,err=pcall(function()
                    stores[definition.id]:UpdateAsync(tostring(userId),function(old) return math.max(old or 0,value) end)
                end)
                if ok then Writes.succeeded(writeState,definition.id,userId,value)
                else warn("[Be Dino] leaderboard publish failed: "..tostring(err)) end
                pending-=1
            end)
        end
    end
    -- Wait for this call's writes so LeaveCoordinator still awaits them (bounded: UpdateAsync itself times out).
    local waited=0
    while pending>0 and waited<30 do task.wait(0.1) waited+=0.1 end
    if force and pending==0 then Writes.forget(writeState,userId) end
end
local function displayValue(id: string,value: number): string
    if id=="rarest" then return Config.SpeciesRarityNames[value] or "Not ranked" end
    if id=="playSeconds" then return string.format("%dh %02dm",value//3600,(value%3600)//60) end
    return tostring(value).." R$"
end
local function refresh()
    for _,definition in definitions do
        local page={}
        local ok=true
        if preview then
            for id,value in rows[definition.id] or {} do if value>0 then table.insert(page,{key=tostring(id),value=value}) end end
            table.sort(page,function(a,b) return if a.value==b.value then tonumber(a.key)<tonumber(b.key) else a.value>b.value end)
        else
            ok=pcall(function() page=stores[definition.id]:GetSortedAsync(false,8,1):GetCurrentPage() end)
        end
        local board=boards[definition.id]
        if not board then continue end -- hidden in the cave: data still publishes above
        board.Status.Text=if not ok then "Temporarily unavailable" elseif preview then "UNSAVED STUDIO PREVIEW" else "ALL-TIME"
        for rank=1,8 do
            local entry=page[rank]
            local text=""
            if entry then
                local id=tonumber(entry.key)
                if not names[id] then
                    local found,name=pcall(function() return Players:GetNameFromUserIdAsync(id) end)
                    names[id]=if found then name else "User "..entry.key
                end
                text=string.format("%d. %s  |  %s",rank,names[id],displayValue(definition.id,entry.value))
            elseif rank==1 then text=if ok then "No ranked players yet" else "Please check again later" end
            board.Rows[rank].Text=text
        end
    end
end
function Leaderboards.start()
    workspace.BeDinoArena.Sanctuary.SanctuarySign.Position=Vector3.new(0,35,CaveHubLayout.hub(Config).centerZ+37)
    local folder=Instance.new("Folder") folder.Name="Leaderboards" folder.Parent=workspace.BeDinoArena.Sanctuary
    -- BD-281 QA: with the cave on the boards stand behind the Fame station (the old hard-coded z=399 would be outside the cave).
    local hub=CaveHubLayout.hub(Config)
    local boardX,boardZ,boardGap=0,399,30
    local spots=if hub.enabled then CaveHubLayout.boardSpots() else nil -- BD-285 QA: an arc east of the Fame pad, away from the lava line
    local spotOrder={1,3} -- two cave boards stand at the outer arc spots (the middle one stays open)
    local shown=0
    for i,definition in definitions do
        if not preview then stores[definition.id]=DataStoreService:GetOrderedDataStore(Config.ProfileDataStoreName.."_"..definition.id..(definition.store or "_v1")) end
        if hub.enabled and definition.hiddenInCave then continue end
        shown+=1
        local part=Instance.new("Part")
        part.Name,part.Size=definition.title,Vector3.new(27,23,1)
        if spots then
            local s=spots[spotOrder[shown]]
            part.Size=Vector3.new(CaveHubLayout.Boards.width,CaveHubLayout.Boards.height,1) -- same 540 x 460 canvas, a little smaller so three fit east of the Fame pad
            part.CFrame=CFrame.new(s.x,CaveHubLayout.Boards.y,hub.centerZ+s.z)*CFrame.Angles(0,s.yaw,0)
        else
            part.Position=Vector3.new(boardX+(i-2)*boardGap,19,boardZ)
        end
        part.Anchored,part.CanCollide,part.Color,part.Material,part.Parent=true,false,Theme.Colors.panel,Enum.Material.SmoothPlastic,folder
        local cave=spots~=nil
        local titleColor,textColor=definition.color,Theme.Colors.text
        if cave then
            titleColor,textColor=CAVE_AMBER,CAVE_CREAM
            part.Color,part.Material=CAVE_PANEL,Enum.Material.Wood
            local frame=Instance.new("Part") -- wood frame just behind the panel, a little larger
            frame.Name,frame.Size,frame.CFrame=definition.title.." Frame",part.Size+Vector3.new(2,2,0.5),part.CFrame*CFrame.new(0,0,0.6)
            frame.Anchored,frame.CanCollide,frame.CanTouch,frame.CanQuery,frame.Color,frame.Material,frame.Parent=true,false,false,false,CAVE_WOOD,Enum.Material.Wood,folder
        end
        local surface=Instance.new("SurfaceGui")
        surface.Face,surface.CanvasSize,surface.Parent=Enum.NormalId.Front,Vector2.new(540,460),part
        if cave then
            surface.LightInfluence,surface.Brightness=0.4,1.2 -- lit by the lamps, never a black hole
            local back=Instance.new("Frame")
            back.Size,back.BackgroundColor3,back.BorderSizePixel,back.Parent=UDim2.fromScale(1,1),CAVE_PANEL,0,surface
        end
        local function text(y,h,size,color)
            local label=Instance.new("TextLabel")
            if cave then label.TextStrokeColor3,label.TextStrokeTransparency=Color3.fromRGB(46,30,20),0.3 end
            label.Position,label.Size,label.BackgroundTransparency=UDim2.fromOffset(12,y),UDim2.fromOffset(516,h),1
            label.Font,label.TextSize,label.TextColor3,label.TextWrapped,label.Parent=Enum.Font.FredokaOne,size,color,true,surface
            return label
        end
        text(8,52,44,titleColor).Text=definition.title
        local status=text(60,22,18,textColor)
        local list={}
        for rank=1,8 do
            local row=text(86+(rank-1)*44,42,24,textColor)
            row.TextScaled=true
            local constraint=Instance.new("UITextSizeConstraint")
            constraint.MinTextSize,constraint.MaxTextSize,constraint.Parent=16,24,row
            list[rank]=row
            local rule=Instance.new("Frame")
            rule.Position,rule.Size=UDim2.fromOffset(12,128+(rank-1)*44),UDim2.fromOffset(516,1)
            rule.BackgroundColor3,rule.BackgroundTransparency,rule.BorderSizePixel,rule.Parent=textColor,.9,0,surface
        end
        boards[definition.id]={Status=status,Rows=list}
    end
    task.spawn(function()
        while folder.Parent do
            for _,player in Players:GetPlayers() do Leaderboards.publish(player,nil) end
            refresh()
            task.wait(60)
        end
    end)
end
return Leaderboards
