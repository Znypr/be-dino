--!strict
local Config=require(script.Parent.Config)
local Progression=require(script.Parent.ProgressionConfig)
local Genetics=require(script.Parent.EggGenetics)
local Odds={}

local function total(rows)
    local n=0 for _,row in rows do n+=row.weight end return n
end
local function selectRows(rows,value,key)
    local result={}
    for _,row in rows do if value==nil or row[key]==value then table.insert(result,row) end end
    return result
end
function Odds.percent(probability: number): string
    if probability==0 then return "0%" end
    local value=probability*100
    local digits=math.max(4,4-math.floor(math.log10(math.abs(value))))
    return string.format("%."..math.min(20,digits).."f%%",value)
end
function Odds.blendMode(): string
    -- Legacy rolls have 101 shares. The current pattern integration clamps endpoints.
    -- A future uniform 1-99 roll must explicitly declare Genetics.BlendMode="uniform".
    return Genetics.BlendMode or (if Genetics.Patterns then "clamped" else "legacy")
end
function Odds.shareProbability(a: string,b: string,share: number): number
    local mode=Odds.blendMode()
    if mode=="legacy" then return if share>=0 and share<=100 then 1/101 else 0 end
    if a==b then return if share==100 then 1 else 0 end
    if share<1 or share>99 then return 0 end
    return if mode=="uniform" then 1/99 elseif share==1 or share==99 then 2/101 else 1/101
end
function Odds.failure(level: number): number
    local weights=Progression.ConditionWeights[math.clamp(level,0,#Progression.ConditionWeights-1)+1]
    local sum=0 for _,weight in weights do sum+=weight end
    local probability=0
    for i,condition in Progression.Conditions do probability+=weights[i]/sum*(1-condition.hatchChance) end
    return probability
end
function Odds.patterns()
    return Genetics.Patterns or {"legacy"}
end
function Odds.catalog(level: number,filters)
    filters=filters or {}
    local tier=math.clamp(level,0,#Progression.ConditionWeights-1)
    local weights=Progression.ConditionWeights[tier+1]
    local weightTotal=0 for _,w in weights do weightTotal+=w end
    local conditions={}
    for i,c in Progression.Conditions do
        if weights[i]>0 and c.hatchChance>0 and (not filters.condition or filters.condition==c.id) then
            table.insert(conditions,{row=c,probability=weights[i]/weightTotal*c.hatchChance})
        end
    end
    local species=selectRows(Config.ChestSpeciesWeights,filters.species,"speciesId")
    local copies=selectRows(Config.ChestQuantityWeights,filters.copies,"count")
    local patterns={}
    for _,id in Odds.patterns() do if not filters.pattern or filters.pattern==id then table.insert(patterns,id) end end
    local sizes={}
    for _,big in {false,true} do if filters.big==nil or big==filters.big then table.insert(sizes,big) end end
    local pairs={}
    local shareCount=0
    for _,a in Progression.EggColors do for _,b in Progression.EggColors do
        if (not filters.primary or filters.primary==a.id) and (not filters.secondary or filters.secondary==b.id) then
            local first,count=0,101
            if Odds.blendMode()~="legacy" then
                first,count=if a.id==b.id then 100 else 1,if a.id==b.id then 1 else 99
            end
            table.insert(pairs,{a=a,b=b,first=first,count=count,offset=shareCount})
            shareCount+=count
        end
    end end
    local includeFailure=next(filters)==nil
    local combinations=#conditions*#species*#copies*#patterns*#sizes*shareCount
    local catalog={count=combinations+(if includeFailure then 1 else 0),level=tier,
        filtered=not includeFailure,failure=Odds.failure(tier)}
    local speciesTotal,copiesTotal,colorTotal=total(Config.ChestSpeciesWeights),total(Config.ChestQuantityWeights),total(Progression.EggColors)
    function catalog.at(index: number)
        if index%1~=0 or index<1 or index>catalog.count then return nil end
        if includeFailure and index==1 then return {failed=true,probability=catalog.failure} end
        local n=index-1-(if includeFailure then 1 else 0)
        local function take(length)
            local i=n%length+1 n=math.floor(n/length) return i
        end
        local shareIndex=take(shareCount)-1
        local pair
        for _,p in pairs do if shareIndex>=p.offset and shareIndex<p.offset+p.count then pair=p break end end
        local share=pair.first+shareIndex-pair.offset
        local big=sizes[take(#sizes)]
        local pattern=patterns[take(#patterns)]
        local quantity=copies[take(#copies)]
        local sp=species[take(#species)]
        local condition=conditions[take(#conditions)]
        local probability=condition.probability*sp.weight/speciesTotal*quantity.weight/copiesTotal
            *pair.a.weight/colorTotal*pair.b.weight/colorTotal
            *Odds.shareProbability(pair.a.id,pair.b.id,share)/#Odds.patterns()
            *(if big then Config.BigChance else 1-Config.BigChance)
        return {failed=false,probability=probability,speciesId=sp.speciesId,count=quantity.count,
            conditionId=condition.row.id,conditionName=condition.row.name,stats=condition.row.stats,
            primaryId=pair.a.id,primaryName=pair.a.name,secondaryId=pair.b.id,secondaryName=pair.b.name,
            share=share,patternId=pattern,big=big}
    end
    return catalog
end
return Odds
