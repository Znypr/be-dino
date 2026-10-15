--!strict
local Players = game:GetService("Players")
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local Arena = require(script.Parent.Arena)
local ChestService = require(script.Parent.ChestService)
local CollectionService = require(script.Parent.CollectionService)
local Dinosaur = require(script.Parent.Dinosaur)
local MutationService = require(script.Parent.MutationService)
local MovementGuard = require(script.Parent.MovementGuard)
local ProfileRepository = require(script.Parent.ProfileRepository)
local RunLifecycle = require(script.Parent.RunLifecycle)
local VisualTestService = require(script.Parent.VisualTestService)
local Leaderboards = require(script.Parent.Leaderboards)

Players.CharacterAutoLoads = false

Lighting.ClockTime = 14
Lighting.Brightness = 2
Lighting.Ambient = Color3.fromRGB(130, 143, 148)
-- World v2 distance haze: a gentle default Atmosphere so the 832-stud island fades into depth. The client weather script
-- adopts an existing Atmosphere as its base (it only ever raises density/haze above these values), so they cooperate.
if not Lighting:FindFirstChildOfClass("Atmosphere") then
    local atmosphere = Instance.new("Atmosphere")
    atmosphere.Name = "WorldHaze"
    atmosphere.Density, atmosphere.Offset, atmosphere.Glare, atmosphere.Haze = .22, .12, 0, 1.15
    atmosphere.Color, atmosphere.Decay = Color3.fromRGB(190, 208, 214), Color3.fromRGB(148, 176, 190)
    atmosphere.Parent = Lighting
end
require(script.Parent.ImportedResources).load()
require(script.Parent.PotionModels).load() -- BD-214 textured potion models for menu ViewportFrames
if Config.WorldArtMode=="BiomeKit" or Config.FoodArtMode=="Kit" then require(script.Parent.ImportedResources).loadWorldKit() end
Arena.build()
Leaderboards.start()

ProfileRepository.start()
RunLifecycle.configureSettlement(function(player: Player, runId: string, catchScore: number, reason: string, eggEvents, runSeconds)
    local ok = ProfileRepository.commitRunSettlement(player, runId, catchScore, eggEvents, runSeconds, workspace:GetAttribute("WeatherId")) -- BD-156: nests dropped in weather carry it
    if not ok then
        warn(string.format("[Be Dino] settlement failed for %s (%s)", player.Name, reason))
        return false
    end

    if Config.DuplicateSettlementProbe then
        local retryOk, _, retryStatus = ProfileRepository.commitRunSettlement(player, runId, catchScore)
        if not retryOk or retryStatus ~= "duplicate" then
            player:SetAttribute("ProfileState", "SaveFailed")
            warn("[Be Dino] duplicate settlement probe failed for " .. player.Name)
            return false
        end
        player:SetAttribute("LastSettlementProbe", "duplicate-ok")
    end

    if not player.Parent then
        local metrics=ProfileRepository.release(player)
        if metrics then Leaderboards.publish(player,metrics) end
    end
    return true
end)
RunLifecycle.start()
CollectionService.start(ProfileRepository, Dinosaur)
ChestService.start(ProfileRepository)
MutationService.start(ProfileRepository, Dinosaur)
MovementGuard.start()
VisualTestService.start(Dinosaur)
require(script.Parent.ProgressionService).start(ProfileRepository)
require(script.Parent.FusionService).start(ProfileRepository)
workspace.Gravity=require(game:GetService("ReplicatedStorage").Shared.Config).Gravity
require(script.Parent.LeapService).start()
game:GetService("MarketplaceService").ProcessReceipt=function(receipt)
    local player=Players:GetPlayerByUserId(receipt.PlayerId)
    if player and ProfileRepository.purchase(player,receipt) then
        task.spawn(Leaderboards.publish,player,nil)
        return Enum.ProductPurchaseDecision.PurchaseGranted
    end
    return Enum.ProductPurchaseDecision.NotProcessedYet
end

local function spawnLoadedPlayer(player: Player)
    player.CanLoadCharacterAppearance = false
    local loaded = ProfileRepository.load(player)
    if not loaded or not player.Parent then
        warn("[Be Dino] profile load blocked character spawn for " .. player.Name)
        return
    end

    local ok, err = pcall(function()
        player:LoadCharacterAsync()
    end)
    if not ok then
        player:SetAttribute("CharacterState", "SpawnFailed")
        warn("[Be Dino] initial character load failed: " .. tostring(err))
    end
end

local function setup(player: Player)
    player.CanLoadCharacterAppearance = false
    for _,attribute in {"EquippedBig","EquippedGenesJson"} do
        player:GetAttributeChangedSignal(attribute):Connect(function()
            local character=player.Character
            if character and character:GetAttribute("DinoAttached") then Dinosaur.refreshForPlayer(character,player) end
        end)
    end
    player.CharacterAdded:Connect(function(character)
        if player:GetAttribute("ProfileState") ~= "Loaded" then
            character:Destroy()
            return
        end
        RunLifecycle.prepareSanctuary(player, character)
        task.spawn(function()
            Dinosaur.attach(character, Config.WalkSpeed, player)
            if player.Character == character then character:PivotTo(CFrame.new(0, 11, Config.SanctuaryCenterZ)) end
        end)
    end)
    task.spawn(spawnLoadedPlayer, player)
end

Players.PlayerAdded:Connect(setup)
for _, player in Players:GetPlayers() do setup(player) end

Players.PlayerRemoving:Connect(function(player)
    local status = RunLifecycle.endForDisconnect(player)
    if status ~= "busy" then
        local metrics=ProfileRepository.release(player)
        if metrics then Leaderboards.publish(player,metrics) end
    end
end)

game:BindToClose(function()
    for _, player in Players:GetPlayers() do
        local status = RunLifecycle.endForDisconnect(player)
        if status ~= "busy" then
            local metrics=ProfileRepository.release(player)
            if metrics then Leaderboards.publish(player,metrics) end
        end
    end
end)

local FoodService = require(script.Parent.FoodService)
local foodReady, foodError = xpcall(function() FoodService.start(Dinosaur,ProfileRepository) end, debug.traceback)
if not foodReady then
    workspace:SetAttribute("FoodSpawnStatus", "Failed")
    workspace:SetAttribute("FoodStartupError", tostring(foodError))
    warn("[Be Dino] FOOD STARTUP FAILED: " .. tostring(foodError))
end
local PredationService = require(script.Parent.PredationService)
PredationService.start(RunLifecycle, Dinosaur)
require(script.Parent.AdminService).start() -- BD-120 owner-only admin panel (docs/79)

print("[Be Dino] " .. Config.Build .. " ready. Resource redesign.")
