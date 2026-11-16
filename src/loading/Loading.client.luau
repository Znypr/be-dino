--!strict
-- Runs before character spawning, including when profile loading cannot finish.
local ReplicatedFirst = game:GetService("ReplicatedFirst")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local player = Players.LocalPlayer
local gui = Instance.new("ScreenGui")
gui.Name = "StartupUI"
gui.IgnoreGuiInset = true
gui.ResetOnSpawn = false
gui.DisplayOrder = 100
gui.Parent = player:WaitForChild("PlayerGui")
local background = Instance.new("CanvasGroup")
background.Size = UDim2.fromScale(1, 1)
background.BackgroundColor3 = Color3.fromRGB(18, 40, 49)
background.Parent = gui
local message = Instance.new("TextLabel")
message.AnchorPoint = Vector2.new(0.5, 0.5)
message.Position = UDim2.fromScale(0.5, 0.5)
message.Size = UDim2.new(0.8, 0, 0.55, 0)
message.BackgroundTransparency = 1
message.TextColor3 = Color3.fromRGB(239, 247, 228)
message.Font = Enum.Font.GothamBold
message.TextSize = 22
message.TextWrapped = true
message.Text = "BE DINO!\n\nPreparing your island..."
message.Parent = background
local track=Instance.new("Frame")
track.AnchorPoint,track.Position,track.Size=Vector2.new(.5,0),UDim2.fromScale(.5,.76),UDim2.new(.6,0,0,8)
track.BackgroundColor3,track.BorderSizePixel,track.ZIndex,track.Parent=Color3.fromRGB(36,68,77),0,4,background
local fill=Instance.new("Frame")
fill.Size,fill.BackgroundColor3,fill.BorderSizePixel,fill.ZIndex,fill.Parent=UDim2.fromScale(.15,1),Color3.fromRGB(93,237,31),0,5,track
local progressTween: Tween?=nil
local lastStage=0
-- BD-1214 (docs/240 step 3, style tile v3 board 8): with Config.ScreensCohesionEnabled the screen starts warm, not dark: a green field, the
-- title, the dino picture and a cream bar with an ink outline (R1, R5). The flag lives in Shared/Config, so the Roblox loading screen stays up
-- until Shared has arrived (at most 3 s) and the right look is built before anything shows. false = today's look, unchanged.
local warm=false
do
    local folder=game:GetService("ReplicatedStorage"):WaitForChild("Shared",3)
    local module=if folder then folder:WaitForChild("Config",1) else nil
    local ok,config=false,nil
    if module then ok,config=pcall(require,module) end
    warm=ok and typeof(config)=="table" and (config :: any).ScreensCohesionEnabled==true
end
local barWord: TextLabel?=nil
if warm then
    local shared=game:GetService("ReplicatedStorage"):WaitForChild("Shared")
    local Kit=require(shared:WaitForChild("ToyboxKit")) :: any
    local icons=require(shared:WaitForChild("UIIconAssets")) :: any
    local ink=Color3.fromRGB(Kit.Outline[1],Kit.Outline[2],Kit.Outline[3])
    local cream=Color3.fromRGB(Kit.Tone.panel[1],Kit.Tone.panel[2],Kit.Tone.panel[3])
    local function outline(target: GuiObject,thickness: number,border: boolean)
        local line=Instance.new("UIStroke")
        line.Color,line.Thickness,line.Parent=ink,thickness,target
        if border then line.ApplyStrokeMode=Enum.ApplyStrokeMode.Border end
    end
    background.BackgroundColor3=Color3.fromRGB(104,178,64)
    local field=Instance.new("UIGradient")
    field.Rotation,field.Color,field.Parent=90,ColorSequence.new(Color3.fromRGB(146,206,92),Color3.fromRGB(70,138,48)),background
    local title=Instance.new("TextLabel")
    title.Name,title.AnchorPoint,title.Position,title.Size="Title",Vector2.new(.5,.5),UDim2.fromScale(.5,.2),UDim2.new(.8,0,0,96)
    title.BackgroundTransparency,title.Font,title.TextScaled,title.Text,title.ZIndex=1,Enum.Font.FredokaOne,true,"Be Dino!",3
    title.TextColor3,title.Parent=Color3.fromRGB(255,214,64),background
    outline(title,4,false)
    local id=icons.dinos
    if typeof(id)=="string" and string.match(id,"^rbxassetid://%d+$") then
        local dino=Instance.new("ImageLabel")
        dino.Name,dino.AnchorPoint,dino.Position,dino.Size="Dino",Vector2.new(.5,.5),UDim2.fromScale(.5,.47),UDim2.fromScale(.3,.3)
        dino.BackgroundTransparency,dino.Image,dino.ScaleType,dino.ZIndex,dino.Parent=1,id,Enum.ScaleType.Fit,3,background
        Instance.new("UIAspectRatioConstraint").Parent=dino
    end
    track.Name,track.Position,track.Size,track.BackgroundColor3=  "Bar",UDim2.fromScale(.5,.7),UDim2.new(.5,0,0,44),cream
    local round=Instance.new("UICorner")
    round.CornerRadius,round.Parent=UDim.new(0,14),track
    outline(track,3,true)
    local pad=Instance.new("UIPadding")
    pad.PaddingTop,pad.PaddingBottom,pad.PaddingLeft,pad.PaddingRight=UDim.new(0,6),UDim.new(0,6),UDim.new(0,6),UDim.new(0,6)
    pad.Parent=track
    local fillRound=Instance.new("UICorner")
    fillRound.CornerRadius,fillRound.Parent=UDim.new(0,10),fill
    local word=Instance.new("TextLabel")
    word.Name,word.BackgroundTransparency,word.Size,word.ZIndex,word.Font="Word",1,UDim2.fromScale(1,1),6,Enum.Font.FredokaOne
    word.TextSize,word.TextColor3,word.Text,word.Parent=16,ink,"Waking up your dinos...",track
    barWord=word
    message.Font,message.TextSize,message.TextColor3=Enum.Font.FredokaOne,20,Color3.new(1,1,1)
    message.AnchorPoint,message.Position,message.Size,message.ZIndex=Vector2.new(.5,0),UDim2.fromScale(.5,.8),UDim2.new(.8,0,.18,0),3
    message.Text=""
    outline(message,3,false)
end
ReplicatedFirst:RemoveDefaultLoadingScreen()
task.spawn(function()
    if warm then return end -- BD-1214: the warm look has no dark background picture
    local shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared", 10)
    local module = if shared then shared:FindFirstChild("UITheme") else nil
    if not module then return end
    local ok, theme = pcall(require, module)
    if not ok or theme.BackgroundImageId == "" then return end
    local image = Instance.new("ImageLabel")
    image.Size = UDim2.fromScale(1,1)
    image.ScaleType = Enum.ScaleType.Crop
    image.Image = theme.BackgroundImageId
    image.BackgroundTransparency = 1
    image.ZIndex = 1
    image.Parent = background
    local shade = Instance.new("Frame")
    shade.Size = UDim2.fromScale(1,1)
    shade.BackgroundColor3 = Color3.fromRGB(10,26,36)
    shade.BackgroundTransparency = .35
    shade.ZIndex = 2
    shade.Parent = background
    message.ZIndex = 3
end)
local started = os.clock()
local failures = {
    LoadFailed = "Your saved data could not load. Rejoin to retry. In a published Studio test, enable Studio API access under Game Settings > Security.",
    SessionBusy = "Your previous session is still closing. Wait a moment, then rejoin.",
    SchemaError = "Your save needs a version update. Please report this to Znypr.",
    LeaseLost = "Your save session changed. Rejoin before continuing.",
    SaveFailed = "Saving is unavailable. Rejoin before continuing.",
}
local connection: RBXScriptConnection?
connection = RunService.Heartbeat:Connect(function()
    local state = player:GetAttribute("ProfileState")
    local character = player.Character
    local mainUI=player.PlayerGui:FindFirstChild("BeDinoUI")
    local ready=state == "Loaded" and character and character:GetAttribute("DinoAttached") and mainUI and mainUI:GetAttribute("Ready")
    local stage=if ready then 3 elseif state=="Loaded" then 2 else 1
    if stage~=lastStage then
        lastStage=stage
        if progressTween then progressTween:Cancel() end
        progressTween=TweenService:Create(fill,TweenInfo.new(.2),{Size=UDim2.fromScale(({.2,.65,1})[stage],1)})
        progressTween:Play()
    end
    if ready then
        if connection then connection:Disconnect() end
        local fade=TweenService:Create(background,TweenInfo.new(.2),{GroupTransparency=1})
        fade.Completed:Once(function() gui:Destroy() end)
        fade:Play()
        return
    end
    local reason = failures[state :: any]
    if reason then
        message.Text = "CAN'T START YET\n\n" .. reason
    elseif player:GetAttribute("CharacterState") == "SpawnFailed" then
        message.Text = "CHARACTER COULD NOT SPAWN\n\nRejoin to retry. Check Studio Output for the character loading error."
    elseif os.clock() - started > 20 then
        message.Text = "TAKING LONGER THAN EXPECTED\n\nStatus: " .. tostring(state or "Server starting")
            .. "\nIf this does not finish, rejoin and check Studio Output. Your existing save has not been replaced."
    elseif barWord then
        message.Text = "" -- BD-1214: the warm look says it in the bar, in kid words
        barWord.Text = if state == "Loaded" then "Your dino is coming..." else "Waking up your dinos..."
    else
        message.Text = "BE DINO!\n\n" .. (if state == "Loaded" then "Preparing your dinosaur..." else "Loading your collection...")
    end
end)
