--!strict
-- ProfileRepository part (docs/150): crystal shop / potion / cosmetic purchases and the Robux receipt credit.
-- Moved unchanged out of ProfileRepository.luau, which installs it with the helpers it shares (store, retry, admit, adopt, ...);
-- tools/verify_profile_golden.py proves the stored profile is byte-identical to before the split.
return function(ProfileRepository: any, shared: any)
local Config = shared.Config
local CosmeticOwnership = shared.CosmeticOwnership
local HttpService = shared.HttpService
local PaidRandomGate = shared.PaidRandomGate
local PrivateState = shared.PrivateState
local ProgressionConfig = shared.ProgressionConfig
local ProgressionRules = shared.ProgressionRules
local ReplicatedStorage = shared.ReplicatedStorage
local RewardMath = shared.RewardMath
local admit = shared.admitAs("ProfileShop") -- BD-650: the label names the service in the rate_limited count
local adopt = shared.adopt
local availableChestCapacity = shared.availableChestCapacity
local enqueueChestIds = shared.enqueueChestIds
local equippedOf = shared.equippedOf
local findOperation = shared.findOperation
local identityAvailable = shared.identityAvailable
local isValidProfile = shared.isValidProfile
local keyFor = shared.keyFor
local localPreview = shared.localPreview
local objectives = shared.objectives
local ownSession = shared.ownSession
local profiles = shared.profiles
local retry = shared.retry
local store = shared.store
local syncAttributes = shared.syncAttributes
local trimOperations = shared.trimOperations

-- BD-618 (h): recentOperations keeps the last 50 operations of the profile, so a purchase token replayed after 50 newer operations ran again
-- (it cost again; no gain). The tokens this server has committed for a user are also remembered in memory (never written to the profile, so no
-- schema or rollback change); a replay of one that has left the profile's ring is answered as a duplicate instead of running a second time.
local TOKEN_MEMORY_LIMIT = 400
local committedTokens: {[number]: {order: {string}, byId: {[string]: {action: string, item: string}}}} = {}

local function rememberToken(userId: number, operationId: string, action: string, item: string)
    local memory = committedTokens[userId]
    if not memory then
        memory = {order = {}, byId = {}}
        committedTokens[userId] = memory
    end
    if memory.byId[operationId] then return end
    memory.byId[operationId] = {action = action, item = item}
    table.insert(memory.order, operationId)
    while #memory.order > TOKEN_MEMORY_LIMIT do
        memory.byId[table.remove(memory.order, 1) :: string] = nil
    end
end

function ProfileRepository.progressionAction(player: Player, action: string, id: string, token: string, replace: boolean?, amount: number?)
    if not ProfileRepository.isLoaded(player) then return false,"profile_not_loaded" end
    if typeof(token)~="string" or #token<1 or #token>80 then return false,"invalid_token" end
    -- BD-532: one shared rule (the client greys the tile out with the same function before the tap); the policy gate is NOT loosened
    if PaidRandomGate.guards(action) and PaidRandomGate.blocked(Config.DeveloperProducts, Config.PaidRandomItemsEnabled, PrivateState.get(player, "PaidRandomEligible")) then return false,"random_items_unavailable" end
    if action=="buyPerk" and (Config.FastTravelPerk~=true or Config.CaveHub~=true) then return false,"perk_unavailable" end -- BD-391/405: flag off = no purchase
    local eggId=nil
    local egg=nil
    local purchaseConditionLevel=ProfileRepository.progression(player).conditionLevel
    if action=="buyEgg" then
        if id~="random" then return false,"unknown_item" end
        eggId=HttpService:GenerateGUID(false)
        egg=ProfileRepository.prepareEgg(player,{eventId="clear",mutationId=""})
        egg.source={kind="crystal_shop", currency="crystals", funding="unknown", conditionLevel=purchaseConditionLevel}
        egg.reward=RewardMath.computeChestReward(Random.new(),1)
    end
    local operationId="progression:"..token
    local cachedProfile=profiles[player]
    local remembered=if cachedProfile and not findOperation(cachedProfile,operationId) and committedTokens[player.UserId] then committedTokens[player.UserId].byId[operationId] else nil
    if remembered then -- BD-618 (h): committed earlier this server, but trimmed out of the profile's operation ring
        if remembered.action~=action or remembered.item~=id then return false,"token_conflict" end
        return true,"duplicate"
    end
    local now=os.time()
    local denied="save_failed"
    local duplicate=false
    local outcome=nil
    local leaseLost=false
    if not admit(player) then return false,"rate_limited" end
    local ok,updated=retry("progression",function()
        return store:UpdateAsync(keyFor(player),function(profile)
            if not isValidProfile(profile) then denied="invalid_profile" return nil end
            if not ownSession(profile) then leaseLost=true return nil end
            local existing=findOperation(profile,operationId)
            if existing then
                if existing.outcome.action~=action or existing.outcome.item~=id then denied="token_conflict" return nil end
                outcome=existing.outcome duplicate=true return profile
            end
            local progress = ProgressionRules.upgrade(profile)
            if localPreview and Config.StudioTestWalletEnabled then progress.crystals = Config.StudioTestCrystals end
            local applied,status
            local boundInstance=nil
            if action=="buyEgg" then
                if availableChestCapacity(profile)<1 then denied="queue_full" return nil end
                if progress.crystals<ProgressionConfig.RandomEggPrice then denied="insufficient_crystals" return nil end
                -- Do not buy against stale odds if a concurrent condition upgrade committed.
                if progress.conditionLevel~=purchaseConditionLevel then denied="upgrade_changed" return nil end
                progress.crystals-=ProgressionConfig.RandomEggPrice
                enqueueChestIds(profile,{eggId},now,{egg})
                applied,status=true,"egg_purchased"
            elseif Config.PerDinoCosmeticsEnabled==true and (action=="buyAura" or action=="equipAura" or action=="buyTrail" or action=="equipTrail") then
                -- BD-059 phase 2: bound to the equipped dino instance, same atomic token write as every other purchase.
                applied,status,boundInstance=CosmeticOwnership.apply(profile,action,id,{rules=ProgressionRules,config=ProgressionConfig,identityOk=identityAvailable(profile.dinosaurIdentity),equipped=(function() local id,key=equippedOf(profile) return {speciesId=id,variantKey=key} end)()})
            else applied,status=ProgressionRules.apply(profile,action,id,now,replace,amount) end
            if localPreview and Config.StudioTestWalletEnabled then progress.crystals = Config.StudioTestCrystals end
            if not applied then denied=status return nil end
            outcome={action=action,item=id,status=status,instanceId=boundInstance}
            profile.revision+=1
            profile.session.expiresAt=now+Config.ProfileLeaseSeconds
            table.insert(profile.recentOperations,{id=operationId,kind="progression",outcome=outcome})
            trimOperations(profile)
            return profile
        end)
    end)
    if not ok then player:SetAttribute("ProfileState","SaveFailed") return false,"save_failed" end
    if leaseLost then player:SetAttribute("ProfileState","LeaseLost") return false,"lease_lost" end
    if not updated then return false,denied end
    if not duplicate then rememberToken(player.UserId,operationId,action,id) end
    if not player.Parent then return true,if duplicate then "duplicate" else outcome.status end
    adopt(player, updated)
    if player.Parent and profiles[player] then syncAttributes(player,profiles[player]) end
    if Config.ObjectivesEnabled == true and action=="buyPotion" and not duplicate then objectives().record(player,"potion_bought",1) end -- BD-074: after the committed purchase
    return true,if duplicate then "duplicate" else outcome.status
end

-- Only called by the server's MarketplaceService callback. Receipts are never trimmed.
function ProfileRepository.purchase(player: Player, receipt)
    if not ProfileRepository.isLoaded(player) then return false end
    local crystals = Config.DeveloperProducts[receipt.ProductId]
    if typeof(crystals) ~= "number" or crystals < 1 or crystals % 1 ~= 0 then return false end
    if receipt.PlayerId ~= player.UserId or typeof(receipt.PurchaseId) ~= "string" or #receipt.PurchaseId < 1 or #receipt.PurchaseId > 120
        or typeof(receipt.CurrencySpent) ~= "number" or receipt.CurrencySpent ~= receipt.CurrencySpent
        or receipt.CurrencySpent < 0 or receipt.CurrencySpent % 1 ~= 0 or receipt.CurrencySpent > 2000000000 then return false end
    local ok, updated = retry("purchase", function()
        return store:UpdateAsync(keyFor(player),function(profile)
            if not isValidProfile(profile) or not ownSession(profile) then return nil end
            if profile.purchaseReceipts[receipt.PurchaseId] then return profile end
            local count=0 for _ in profile.purchaseReceipts do count+=1 end
            if count>=10000 then return nil end -- Fail closed before the profile size limit.
            local progress=ProgressionRules.upgrade(profile)
            local maxCrystals=require(ReplicatedStorage.Shared.ProgressionConfig).MaxCrystals
            if progress.crystals+crystals>maxCrystals or profile.metrics.robux+receipt.CurrencySpent>2000000000 then return nil end
            progress.crystals+=crystals
            profile.metrics.robux+=receipt.CurrencySpent
            profile.purchaseReceipts[receipt.PurchaseId]=true
            profile.revision+=1
            profile.session.expiresAt=os.time()+Config.ProfileLeaseSeconds
            return profile
        end)
    end)
    if not ok or not updated then return false end
    if not profiles[player] then return true end
    adopt(player, updated)
    syncAttributes(player,profiles[player])
    return true
end
end
