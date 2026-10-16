--!strict
local Config=require(script.Parent.ProgressionConfig)
local Genetics=require(script.Parent.EggGenetics)
local Rules={}
function Rules.item(catalog,id)
    for _,item in catalog do if item.id==id then return item end end
    return nil
end
function Rules.eventMutation(entry)
    local selected=nil
    for _,mutation in Config.EventMutations do
        if entry and entry.events and (entry.events[mutation.id] or 0)>0 then selected=mutation end
        for _,variant in (if entry then entry.variants or {} else {}) do
            if variant.count>0 and variant.mutationId==mutation.id then selected=mutation end
        end
    end
    return selected
end
function Rules.validEvents(events): boolean
    if events==nil then return true end
    if typeof(events)~="table" then return false end
    for id,count in events do
        if not Rules.item(Config.EventMutations,id) or typeof(count)~="number" or count~=count or count<0 or count%1~=0 or count>2000000000 then return false end
    end
    return true
end
function Rules.knownEventMutation(id): boolean return Rules.item(Config.EventMutations,id)~=nil end
-- chanceScale (BD-237, playtest admin only) multiplies the weather chance, capped at 100%. nil, non-numbers, NaN and
-- anything below 1 mean x1, so no caller can ever lower the shipped chance.
function Rules.scaledChance(chance: number, chanceScale: any): number
    local scale=if typeof(chanceScale)=="number" and chanceScale==chanceScale and chanceScale>=1 then chanceScale else 1
    return math.min(1,chance*scale)
end
function Rules.eventEgg(eventId,roll,chanceScale)
    local event=Rules.item(Config.Weather,eventId)
    return {eventId=if event then event.id else "clear",mutationId=if event and roll<Rules.scaledChance(event.chance,chanceScale) then event.mutation else ""}
end
function Rules.validEgg(metadata): boolean
    if typeof(metadata)~="table" then return false end
    if metadata.genes~=nil and not Genetics.valid(metadata.genes) then return false end
    local eventId=metadata.eventId or "clear"
    local mutationId=metadata.mutationId or ""
    local event=Rules.item(Config.Weather,eventId)
    return (eventId=="clear" or event~=nil) and typeof(mutationId)=="string" and (mutationId=="" or (event~=nil and event.mutation==mutationId))
end
-- BD-051 rotating Potion Shop. Pure and deterministic: offers depend only on the window number.
function Rules.shopWindow(now: number): number
    return math.floor(now/Config.PotionShop.PeriodSeconds)
end
function Rules.shopEndsAt(window: number): number
    return (window+1)*Config.PotionShop.PeriodSeconds
end
function Rules.shopOffers(window: number)
    local shop=Config.PotionShop
    -- Park-Miller generator; products stay below 2^53 so results are identical on every platform.
    local state=(window*16807+1013904223)%2147483646+1
    local function nextUnit(): number
        state=(state*48271)%2147483647
        return state/2147483647
    end
    for _=1,6 do nextUnit() end
    -- Pools per rarity; each slot picks a rarity (weighted, among rarities with potions left), then a distinct potion.
    local pools={}
    for _,item in Config.Potions do
        pools[item.rarity]=pools[item.rarity] or {}
        table.insert(pools[item.rarity],item)
    end
    local offers={}
    for _=1,math.min(shop.OfferCount,#Config.Potions) do
        local total=0
        for _,rarity in shop.Rarities do if pools[rarity] and #pools[rarity]>0 then total+=shop.RarityWeights[rarity] or 0 end end
        local roll=nextUnit()*total
        local chosen=nil
        for _,rarity in shop.Rarities do
            if pools[rarity] and #pools[rarity]>0 then
                chosen=rarity
                roll-=shop.RarityWeights[rarity] or 0
                if roll<0 then break end
            end
        end
        local pool=pools[chosen :: string]
        local item=table.remove(pool,math.min(#pool,1+math.floor(nextUnit()*#pool)))
        local weights=shop.StockWeights[item.rarity]
        local stockTotal=0 for _,w in weights do stockTotal+=w end
        local stockRoll=nextUnit()*stockTotal
        local stock=#weights
        for i,w in weights do stockRoll-=w if stockRoll<0 then stock=i break end end
        table.insert(offers,{id=item.id,stock=stock})
    end
    return offers
end
function Rules.shopRemaining(p,window: number,id: string): number
    for _,offer in Rules.shopOffers(window) do
        if offer.id==id then
            local bought=if p.shop and p.shop.window==window then (p.shop.bought[id] or 0) else 0
            return math.max(0,offer.stock-bought)
        end
    end
    return 0
end
local function finite(n): boolean return typeof(n)=="number" and n==n and math.abs(n)<math.huge end
function Rules.upgrade(profile)
    -- Additive schema migration: never replace an existing wallet or inventory.
    if profile.progression==nil then
        profile.progression={crystals=0,auras={},equippedAura="",potions={},buffs={}}
    end
    local p=profile.progression
    if p.trails==nil then p.trails={white=true} end
    p.trails.white=true
    if p.equippedTrail==nil then p.equippedTrail="white" end
    if p.accountXP==nil then p.accountXP=0 end
    if p.conditionLevel==nil then p.conditionLevel=0 end
    return profile.progression
end
-- BD-436: permanent discovery log (progression.discovered = {colours={id=true}, patterns={..}, mutations={..}}). ADDITIVE and
-- optional: older builds ignore the field (docs/111), a missing field reads as empty and is filled lazily. Ids are only ever ADDED, so
-- fusing a dino away never un-discovers its colour. Sets are capped so the profile cannot grow without bound.
Rules.DiscoveredMaxPerKind=64
local DISCOVERY_KEYS={"colours","patterns","mutations"}
local function discoveryLog(progress)
    local log=progress.discovered
    if typeof(log)~="table" then log={} progress.discovered=log end -- junk in our own optional field is replaced
    for _,key in DISCOVERY_KEYS do
        if typeof(log[key])~="table" then log[key]={} end
    end
    return log
end
local function markDiscovered(set,id): boolean
    if typeof(id)~="string" or id=="" or id=="none" or #id>40 or set[id]~=nil then return false end
    local n=0
    for _ in set do n+=1 end
    if n>=Rules.DiscoveredMaxPerKind then return false end
    set[id]=true
    return true
end
-- Records one dino's colour / pattern / mutation. Returns {colour=true, pattern=true, mutation=true} for FIRST-time finds only.
function Rules.discover(profile,genes,mutationId)
    local log=discoveryLog(Rules.upgrade(profile))
    local g=if typeof(genes)=="table" then genes else {}
    local fresh={}
    if markDiscovered(log.colours,g.primaryColorId) then fresh.colour=true end
    if markDiscovered(log.patterns,g.patternId) then fresh.pattern=true end
    if markDiscovered(log.mutations,mutationId) then fresh.mutation=true end
    return fresh
end
-- Lazy backfill on load: adds what the player owns right now (collection variants/events, identity instances). Idempotent, add-only.
function Rules.backfillDiscovered(profile)
    local log=discoveryLog(Rules.upgrade(profile))
    local function add(genes,mutationId)
        local g=if typeof(genes)=="table" then genes else {}
        markDiscovered(log.colours,g.primaryColorId)
        markDiscovered(log.patterns,g.patternId)
        markDiscovered(log.mutations,mutationId)
    end
    if typeof(profile.collection)=="table" then
        for _,entry in profile.collection do
            if typeof(entry)=="table" then
                if typeof(entry.events)=="table" then for id,n in entry.events do if typeof(n)=="number" and n>0 then markDiscovered(log.mutations,id) end end end
                if typeof(entry.variants)=="table" then
                    for _,v in entry.variants do
                        if typeof(v)=="table" and typeof(v.count)=="number" and v.count>0 then add(v.genes,v.mutationId) end
                    end
                end
            end
        end
    end
    local identity=profile.dinosaurIdentity
    if typeof(identity)=="table" and typeof(identity.instances)=="table" then
        for _,inst in identity.instances do
            if typeof(inst)=="table" then add(inst.genes,inst.mutationId) end
        end
    end
    return log
end
-- Counts for the owner-only PrivateState (never the id lists).
function Rules.discoveryCounts(profile)
    local p=profile.progression
    local log=if typeof(p)=="table" and typeof(p.discovered)=="table" then p.discovered else {}
    local out={}
    for _,key in DISCOVERY_KEYS do
        local n=0
        if typeof(log[key])=="table" then for _ in log[key] do n+=1 end end
        out[key]=n
    end
    return out
end
function Rules.valid(p): boolean
    if p==nil then return true end -- historical profiles are migrated on load
    if typeof(p)~="table" or not finite(p.crystals) or p.crystals<0 or p.crystals>Config.MaxCrystals or p.crystals%1~=0 then return false end
    if p.accountXP~=nil and (not finite(p.accountXP) or p.accountXP<0 or p.accountXP%1~=0 or p.accountXP>2000000000) then return false end
    if p.conditionLevel~=nil and (not finite(p.conditionLevel) or p.conditionLevel<0 or p.conditionLevel%1~=0 or p.conditionLevel>#Config.ConditionUpgrades) then return false end
    if typeof(p.auras)~="table" or typeof(p.potions)~="table" or typeof(p.buffs)~="table" or typeof(p.equippedAura)~="string" then return false end
    for id,value in p.auras do if not Rules.item(Config.Auras,id) or value~=true then return false end end
    if p.equippedAura~="" and not p.auras[p.equippedAura] then return false end
    if p.trails~=nil then
        if typeof(p.trails)~="table" then return false end
        for id,value in p.trails do if not Rules.item(Config.Trails,id) or value~=true then return false end end
    end
    if p.equippedTrail~=nil then
        if typeof(p.equippedTrail)~="string" then return false end
        if p.equippedTrail~="" and (not p.trails or not p.trails[p.equippedTrail]) then return false end
    end
    if p.perks~=nil then
        if typeof(p.perks)~="table" then return false end
        for id,value in p.perks do if typeof(id)~="string" or not Rules.item(Config.Perks,id) or value~=true then return false end end
    end
    if p.shop~=nil then
        local shop=p.shop
        if typeof(shop)~="table" or not finite(shop.window) or shop.window<0 or shop.window%1~=0 or typeof(shop.bought)~="table" then return false end
        for id,count in shop.bought do
            if typeof(id)~="string" or not Rules.item(Config.Potions,id) or not finite(count) or count<0 or count%1~=0 or count>Config.PotionShop.MaxStock then return false end
        end
    end
    for id,count in p.potions do
        if not Rules.item(Config.Potions,id) or not finite(count) or count<0 or count%1~=0 or count>999 then return false end
    end
    for kind,buff in p.buffs do
        local item=if typeof(buff)=="table" then Rules.item(Config.Potions,buff.id) else nil
        if not item or item.kind~=kind or not finite(buff.expiresAt) or buff.expiresAt<0 then return false end
    end
    return true
end
function Rules.apply(profile,action,id,now,replace,amount): (boolean,string)
    local p=Rules.upgrade(profile)
    if action=="grant" then
        if not finite(amount) or amount<1 or amount%1~=0 or amount>100 then return false,"invalid_amount" end
        p.crystals=math.min(Config.MaxCrystals,p.crystals+amount)
        return true,"crystals_collected"
    elseif action=="buyAura" then
        local item=Rules.item(Config.Auras,id)
        if not item then return false,"unknown_item" end
        if p.auras[id] then return false,"already_owned" end
        if p.crystals<item.price then return false,"insufficient_crystals" end
        p.crystals-=item.price p.auras[id]=true
        return true,"purchased"
    elseif action=="equipAura" then
        if id~="" and not p.auras[id] then return false,"not_owned" end
        p.equippedAura=id
        return true,"equipped"
    elseif action=="buyTrail" then
        local item=Rules.item(Config.Trails,id)
        if not item then return false,"unknown_item" end
        if p.trails[id] then return false,"already_owned" end
        if Rules.level(p)<item.level then return false,"level_locked" end
        if p.crystals<item.price then return false,"insufficient_crystals" end
        p.crystals-=item.price p.trails[id]=true
        return true,"purchased"
    elseif action=="equipTrail" then
        if id~="" and not p.trails[id] then return false,"not_owned" end
        p.equippedTrail=id
        return true,"equipped"
    elseif action=="upgradeCondition" then
        local nextLevel=p.conditionLevel+1
        local upgrade=Config.ConditionUpgrades[nextLevel]
        if not upgrade then return false,"max_level" end
        if id~=tostring(nextLevel) then return false,"upgrade_changed" end
        if Rules.level(p)<upgrade.requiredLevel then return false,"level_locked" end
        if p.crystals<upgrade.price then return false,"insufficient_crystals" end
        p.crystals-=upgrade.price p.conditionLevel=nextLevel
        return true,"upgraded"
    elseif action=="buyPotion" then
        -- id is "<potionId>@<window>": only the current window's disclosed offers can be bought, within stock.
        local potionId,windowText=string.match(id,"^([%w_]+)@(%d+)$")
        if not potionId then return false,"window_required" end
        local item=Rules.item(Config.Potions,potionId)
        if not item then return false,"unknown_item" end
        local window=tonumber(windowText) :: number
        if window~=Rules.shopWindow(now) then return false,"stale_window" end
        local offered=false
        for _,offer in Rules.shopOffers(window) do if offer.id==potionId then offered=true end end
        if not offered then return false,"not_offered" end
        if Rules.shopRemaining(p,window,potionId)<1 then return false,"sold_out" end
        if (p.potions[potionId] or 0)>=999 then return false,"inventory_full" end
        if p.crystals<item.price then return false,"insufficient_crystals" end
        if not p.shop or p.shop.window~=window then p.shop={window=window,bought={}} end
        p.shop.bought[potionId]=(p.shop.bought[potionId] or 0)+1
        p.crystals-=item.price p.potions[potionId]=(p.potions[potionId] or 0)+1
        return true,"purchased"
    elseif action=="buyPerk" then
        local item=Rules.item(Config.Perks,id)
        if not item then return false,"unknown_item" end
        if Rules.hasPerk(p,id) then return false,"already_owned" end
        if p.crystals<item.price then return false,"insufficient_crystals" end
        p.crystals-=item.price
        p.perks=p.perks or {}
        p.perks[id]=true
        return true,"purchased"
    elseif action=="usePotion" then
        local item=Rules.item(Config.Potions,id)
        if not item then return false,"unknown_item" end
        if (p.potions[id] or 0)<1 then return false,"not_owned" end
        local buff=p.buffs[item.kind]
        if buff and buff.expiresAt>now and not replace then return false,"replace_confirmation_required" end
        p.potions[id]-=1 p.buffs[item.kind]={id=id,expiresAt=now+item.duration}
        return true,"activated"
    end
    return false,"invalid_action"
end
-- BD-391/405: perks are an additive optional table `perks = {fastTravel = true}`; absent = nothing owned (old profiles unchanged).
function Rules.hasPerk(p,id: string): boolean
    return typeof(p)=="table" and typeof(p.perks)=="table" and p.perks[id]==true
end
function Rules.level(p)
    return math.min(Config.AccountMaxLevel,1+math.floor(math.sqrt((p.accountXP or 0)/Config.AccountXPPerLevel)))
end
-- BD-185: egg condition (Cracked/Dirty/Normal/Rainbow/Astra) is an EGG-only property; it never scales a living dino's stats.
function Rules.multipliers(p,species,weather,now,mutation)
    local aura=Rules.item(Config.Auras,p.equippedAura)
    local factor=Config.RarityFactors[species] or 1
    local growth,speed,loot=1,1,1
    if weather then
        growth=1+(weather.growth-1)*factor
        speed=1+(weather.speed-1)*factor
        loot=1+(weather.loot-1)*factor
    end
    for kind,buff in p.buffs do
        if buff.expiresAt>now then
            local item=Rules.item(Config.Potions,buff.id)
            if item then if kind=="growth" then growth*=item.multiplier elseif kind=="speed" then speed*=item.multiplier elseif kind=="loot" then loot*=item.multiplier end end
        end
    end
    local trail=Rules.item(Config.Trails,p.equippedTrail or "")
    return math.min(Config.GrowthCap,growth*(if aura then aura.growth else 1)*(if mutation then mutation.growth else 1)),
        math.min(Config.SpeedCap,speed*(if trail then trail.speed else 1)*(if mutation then mutation.speed else 1)),loot
end
return Rules
