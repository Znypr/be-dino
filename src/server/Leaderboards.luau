--!strict
local Players=game:GetService("Players")
local DataStoreService=game:GetService("DataStoreService")
local RunService=game:GetService("RunService")
local Config=require(game:GetService("ReplicatedStorage").Shared.Config)
local Theme=require(game:GetService("ReplicatedStorage").Shared.UITheme)
local Leaderboards={}
local preview=RunService:IsStudio() and game.GameId==0
local rows={}
local boards={}
local names={}
local definitions={
    {id="rarest",attribute="RarestCaught",title="RAREST DINOS",color=Theme.Colors.gold},
    {id="playSeconds",attribute="PlaySeconds",title="MOST PLAY TIME",color=Theme.Colors.accent},
    {id="robux",attribute="RobuxSpent",title="ROBUX SPENT",color=Theme.Colors.blue},
}
local stores={}
function Leaderboards.publish(player: Player, metrics)
    if not metrics and player:GetAttribute("ProfileState")~="Loaded" then return end
    names[player.UserId]=player.Name
    for _,definition in definitions do
        local value=if metrics then metrics[definition.id] else player:GetAttribute(definition.attribute) or 0
        if preview then
            rows[definition.id]=rows[definition.id] or {}
            rows[definition.id][player.UserId]=value
        else
            local ok,err=pcall(function()
                stores[definition.id]:UpdateAsync(tostring(player.UserId),function(old) return math.max(old or 0,value) end)
            end)
            if not ok then warn("[Be Dino] leaderboard publish failed: "..tostring(err)) end
        end
    end
end
local function displayValue(id: string,value: number): string
    if id=="rarest" then return ({"Common","Rare","Legendary"})[value] or "Not ranked" end
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
    workspace.BeDinoArena.Sanctuary.SanctuarySign.Position=Vector3.new(0,35,402)
    local folder=Instance.new("Folder") folder.Name="Leaderboards" folder.Parent=workspace.BeDinoArena.Sanctuary
    for i,definition in definitions do
        if not preview then stores[definition.id]=DataStoreService:GetOrderedDataStore(Config.ProfileDataStoreName.."_"..definition.id.."_v1") end
        local part=Instance.new("Part")
        part.Name,part.Size,part.Position=definition.title,Vector3.new(27,23,1),Vector3.new((i-2)*30,19,399)
        part.Anchored,part.CanCollide,part.Color,part.Material,part.Parent=true,false,Theme.Colors.panel,Enum.Material.SmoothPlastic,folder
        local surface=Instance.new("SurfaceGui")
        surface.Face,surface.CanvasSize,surface.Parent=Enum.NormalId.Front,Vector2.new(540,460),part
        local function text(y,h,size,color)
            local label=Instance.new("TextLabel")
            label.Position,label.Size,label.BackgroundTransparency=UDim2.fromOffset(12,y),UDim2.fromOffset(516,h),1
            label.Font,label.TextSize,label.TextColor3,label.TextWrapped,label.Parent=Enum.Font.FredokaOne,size,color,true,surface
            return label
        end
        text(8,52,44,definition.color).Text=definition.title
        local status=text(60,22,18,Theme.Colors.text)
        local list={}
        for rank=1,8 do
            local row=text(86+(rank-1)*44,42,24,Theme.Colors.text)
            row.TextScaled=true
            local constraint=Instance.new("UITextSizeConstraint")
            constraint.MinTextSize,constraint.MaxTextSize,constraint.Parent=16,24,row
            list[rank]=row
            local rule=Instance.new("Frame")
            rule.Position,rule.Size=UDim2.fromOffset(12,128+(rank-1)*44),UDim2.fromOffset(516,1)
            rule.BackgroundColor3,rule.BackgroundTransparency,rule.BorderSizePixel,rule.Parent=Theme.Colors.text,.9,0,surface
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
