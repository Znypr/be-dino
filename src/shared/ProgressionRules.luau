--!strict
local Config=require(script.Parent.ProgressionConfig)
local Rules={}
function Rules.item(catalog,id)
    for _,item in catalog do if item.id==id then return item end end
    return nil
end
function Rules.eventMutation(entry)
    local selected=nil
    for _,mutation in Config.EventMutations do
        if entry and entry.events and (entry.events[mutation.id] or 0)>0 then selected=mutation end
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
function Rules.eventEgg(eventId,roll)
    local event=Rules.item(Config.Weather,eventId)
    return {eventId=if event then event.id else "clear",mutationId=if event and roll<event.chance then event.mutation else ""}
end
function Rules.validEgg(metadata): boolean
    if typeof(metadata)~="table" then return false end
    local eventId=metadata.eventId or "clear"
    local mutationId=metadata.mutationId or ""
    local event=Rules.item(Config.Weather,eventId)
    return (eventId=="clear" or event~=nil) and typeof(mutationId)=="string" and (mutationId=="" or (event~=nil and event.mutation==mutationId))
end
local function finite(n): boolean return typeof(n)=="number" and n==n and math.abs(n)<math.huge end
function Rules.upgrade(profile)
    -- Additive schema migration: never replace an existing wallet or inventory.
    if profile.progression==nil then
        profile.progression={crystals=0,auras={},equippedAura="",potions={},buffs={}}
    end
    local p=profile.progression
    if p.trails==nil then p.trails={} end
    if p.equippedTrail==nil then p.equippedTrail="" end
    return profile.progression
end
function Rules.valid(p): boolean
    if p==nil then return true end -- historical profiles are migrated on load
    if typeof(p)~="table" or not finite(p.crystals) or p.crystals<0 or p.crystals>Config.MaxCrystals or p.crystals%1~=0 then return false end
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
        if p.crystals<item.price then return false,"insufficient_crystals" end
        p.crystals-=item.price p.trails[id]=true
        return true,"purchased"
    elseif action=="equipTrail" then
        if id~="" and not p.trails[id] then return false,"not_owned" end
        p.equippedTrail=id
        return true,"equipped"
    elseif action=="buyPotion" then
        local item=Rules.item(Config.Potions,id)
        if not item then return false,"unknown_item" end
        if (p.potions[id] or 0)>=999 then return false,"inventory_full" end
        if p.crystals<item.price then return false,"insufficient_crystals" end
        p.crystals-=item.price p.potions[id]=(p.potions[id] or 0)+1
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
function Rules.multipliers(p,species,weather,now)
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
            if item then if kind=="growth" then growth*=item.multiplier elseif kind=="speed" then speed*=item.multiplier end end
        end
    end
    return math.min(Config.GrowthCap,growth*(if aura then aura.growth else 1)),math.min(Config.SpeedCap,speed),loot
end
return Rules
