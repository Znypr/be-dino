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
local LeaveCoordinator = require(script.Parent.LeaveCoordinator)
local Telemetry = require(script.Parent.TelemetryService)
local SpawnGeometry = require(ReplicatedStorage.Shared.SpawnGeometry)

Players.CharacterAutoLoads = false

Lighting.ClockTime = 14
do -- BD-460 (docs/138): softer clear daylight, values in Config.IslandLight (was Brightness 2, Ambient 130,143,148, OutdoorAmbient = place default)
    local light = Config.IslandLight
    Lighting.Brightness = light.Brightness
    Lighting.Ambient = Color3.fromRGB(light.Ambient[1], light.Ambient[2], light.Ambient[3])
    Lighting.OutdoorAmbient = Color3.fromRGB(light.OutdoorAmbient[1], light.OutdoorAmbient[2], light.OutdoorAmbient[3])
end
-- Owner 2026-10-16 (docs/114): no haze in clear daylight. Only a whisper of depth (density .1, haze .3, no glare); trees and hills keep
-- their colour. The client weather script adopts this as its base and only raises it during weather events, then returns to it on clear.
if not Lighting:FindFirstChildOfClass("Atmosphere") then
    local atmosphere = Instance.new("Atmosphere")
    atmosphere.Name = "WorldHaze"
    atmosphere.Density, atmosphere.Offset, atmosphere.Glare, atmosphere.Haze = .1, .1, 0, .3
    atmosphere.Color, atmosphere.Decay = Color3.fromRGB(176, 205, 232), Color3.fromRGB(140, 176, 210)
    atmosphere.Parent = Lighting
end
require(script.Parent.ImportedResources).load()
-- BD-214 3D potion models are dormant (owner 2026-10-16: 2D icons in PotionArt.Images replace them); PotionModels.load() no longer runs
if Config.WorldArtMode=="BiomeKit" or Config.FoodArtMode=="Kit" then require(script.Parent.ImportedResources).loadWorldKit() end
task.spawn(function() require(script.Parent.LowPolyDinoLoader).load() end) -- BD-225 spike, no-op while Config.LowPolyDinos is false
if Config.WorldGeneratedMeshes and Config.WorldArtMode=="BiomeKit" then require(script.Parent.ImportedResources).loadGeneratedWorld() end
if require(ReplicatedStorage.Shared.HatchV2Assets).enabled(Config, game:GetService("RunService"):IsStudio() and game.GameId == 0) then task.spawn(function() require(script.Parent.ImportedResources).loadHatchV2() end) end -- BD-397 (docs/118), no-op while false
Arena.build()
require(script.Parent.StreamingSetup).start() -- BD-498 (docs/150): Persistent models when StreamingEnabled is on; returns at once while it is off
Leaderboards.start()

require(script.Parent.PrivateState).start() -- BD-360 owner-only channel, before any profile can load
ProfileRepository.start()
-- BD-354: PlayerRemoving and BindToClose share one idempotent, awaitable leave path (settle once, release once).
local leaving = LeaveCoordinator.new({
    endForDisconnect = RunLifecycle.endForDisconnect,
    release = ProfileRepository.release,
    publish = Leaderboards.publish,
})
RunLifecycle.configureSettlement(function(player: Player, runId: string, catchScore: number, reason: string, eggEvents, runSeconds, nestWeather)
    -- BD-156 / BD-479: each nest carries the weather active when it was FOUND in the run (the snapshot's per-nest ledger), not the settlement weather
    local ok, settledOutcome = ProfileRepository.commitRunSettlement(player, runId, catchScore, eggEvents, runSeconds, nestWeather)
    if ok then Telemetry.runSettled(player, reason, runSeconds, settledOutcome, runId) end -- BD-426: read-only, flag-gated
    if not ok then
        warn(string.format("[Be Dino] settlement failed for %s (%s)", player.Name, reason))
        leaving.settlementFinished(player) -- a failed settlement of a departed player must still release the lease
        return false
    end

    if Config.DuplicateSettlementProbe then
        local retryOk, _, retryStatus = ProfileRepository.commitRunSettlement(player, runId, catchScore, eggEvents, runSeconds, nestWeather) -- BD-479: same arguments as a true retry, so a probe that is not a duplicate could never stamp a different weather
        if not retryOk or retryStatus ~= "duplicate" then
            player:SetAttribute("ProfileState", "SaveFailed")
            warn("[Be Dino] duplicate settlement probe failed for " .. player.Name)
            leaving.settlementFinished(player)
            return false
        end
        player:SetAttribute("LastSettlementProbe", "duplicate-ok")
    end

    leaving.settlementFinished(player)
    return true
end)
-- BD-359: a settlement that outlasted its retry window is committed later by the lease renew tick; then respawn the player.
ProfileRepository.setSettlementRecoveredHook(function(player: Player) RunLifecycle.recoverAfterSettlement(player) end)
require(script.Parent.FeedbackService).start() -- docs/126: no-op while Config.PlaytestFeedbackEnabled is false
Telemetry.start() -- BD-426: no-op while Config.RunTelemetryEnabled is false
RunLifecycle.start()
CollectionService.start(ProfileRepository, Dinosaur)
ChestService.start(ProfileRepository)
MutationService.start(ProfileRepository, Dinosaur)
MovementGuard.start()
require(script.Parent.FallRecovery).start(MovementGuard.reset) -- BD-210 fall-out-of-world safety net
VisualTestService.start(Dinosaur)
require(script.Parent.ProgressionService).start(ProfileRepository)
require(script.Parent.RareHatchService).start() -- BD-428
require(script.Parent.FusionService).start(ProfileRepository)
require(script.Parent.ObjectiveService).start(ProfileRepository) -- BD-073: returns at once (no remote, no profile access) while Config.ObjectivesEnabled is false
workspace.Gravity=require(game:GetService("ReplicatedStorage").Shared.Config).Gravity
require(script.Parent.LeapService).start()
require(script.Parent.HubTravelService).start() -- BD-287: creates the HubTravel remote only while Config.CaveHub is true
require(script.Parent.HubGateService).start() -- BD-290/291: Island Gate dwell + HubDinos collision group, only while Config.CaveHub is true
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
    -- BD-210: no character before the world (terrain + hub) is built.
    while workspace:GetAttribute("IslandTerrainReady") ~= true or not workspace:FindFirstChild("BeDinoArena") do
        if not player.Parent then return end
        task.wait(.2)
    end
    local loaded = ProfileRepository.load(player)
    -- BD-354: another server (or our own previous session) can still hold the lease for up to ProfileLeaseSeconds after a
    -- quick rejoin or teleport, and a DataStore outage fails the load; wait it out instead of leaving the player without a character.
    local retries = math.ceil((Config.ProfileLeaseSeconds + 10) / 5)
    while not loaded and player.Parent and retries > 0 and (player:GetAttribute("ProfileState") == "SessionBusy" or player:GetAttribute("ProfileState") == "LoadFailed") do
        retries -= 1
        task.wait(5)
        loaded = ProfileRepository.load(player)
    end
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
        -- BD-210: the character goes to the hub floor at once (before the dinosaur attach yields), not after it.
        local hub = CFrame.new(SpawnGeometry.hubPoint(Config))
        character:PivotTo(hub)
        task.spawn(function()
            Dinosaur.attach(character, Config.WalkSpeed, player)
            if player.Character == character then character:PivotTo(hub) end
        end)
        -- BD-503: home after a settle / death / first join is a respawn at the hub pad; with StreamingEnabled ask the client to stream the hub in as well
        -- (concurrent, so the BD-210 "at once" placement above and the attach are not delayed; no-op while streaming is off).
        task.spawn(function() require(script.Parent.StreamingTeleport).request(player, hub.Position) end)
    end)
    task.spawn(spawnLoadedPlayer, player)
end

Players.PlayerAdded:Connect(setup)
for _, player in Players:GetPlayers() do setup(player) end

Players.PlayerRemoving:Connect(leaving.leave)

game:BindToClose(function()
    leaving.leaveAll(Players:GetPlayers()) -- in parallel; BindToClose gets 30 s in total
    if not leaving.waitIdle(27) then warn("[Be Dino] shutdown: some players were not released in time") end
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
-- BD-243/244 HP combat returns nil at once while Config.CombatEnabled is false; BD-245 wild predators then also do nothing.
require(script.Parent.NpcPredatorService).start(require(script.Parent.CombatService).start(RunLifecycle, Dinosaur))
require(script.Parent.ClassMovementService).start() -- BD-246: returns at once while ClassMovementEnabled is false
require(script.Parent.AdminService).start() -- BD-120 owner-only admin panel (docs/79)
require(script.Parent.QaService).start() -- BD-085 owner phone QA overlay marks (docs/127); inert while Config.QaOverlayEnabled is false
require(script.Parent.DemoTriggerService).start(ProfileRepository) -- docs/133 demo triggers: returns at once unless unpublished Studio and the demo flag

print("[Be Dino] " .. Config.Build .. " ready. Resource redesign.")
