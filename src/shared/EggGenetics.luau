--!strict
local Config=require(script.Parent.ProgressionConfig)
local Genetics={}
local function item(rows,id)
    for _,row in rows do if row.id==id then return row end end
    return nil
end
function Genetics.condition(id) return item(Config.Conditions,id) end
function Genetics.color(id) return item(Config.EggColors,id) end
local function pick(weights,roll)
    local total=0 for _,weight in weights do total+=weight end
    local value=math.clamp(roll,0,1)*total
    for i,weight in weights do value-=weight if value<0 then return i end end
    return #weights
end
function Genetics.roll(level,rng)
    local weights=Config.ConditionWeights[math.clamp(level or 0,0,#Config.ConditionWeights-1)+1]
    local condition=Config.Conditions[pick(weights,rng:NextNumber())]
    local colors={} for _,color in Config.EggColors do table.insert(colors,color.weight) end
    local hatchRoll=rng:NextNumber()
    return {conditionId=condition.id,hatchSuccess=condition.hatchChance==1 or hatchRoll<condition.hatchChance,
        primaryColorId=Config.EggColors[pick(colors,rng:NextNumber())].id,
        secondaryColorId=Config.EggColors[pick(colors,rng:NextNumber())].id,
        blend=math.min(100,math.floor(rng:NextNumber()*101))}
end
function Genetics.valid(g)
    if typeof(g)~="table" or not Genetics.condition(g.conditionId) or not Genetics.color(g.primaryColorId)
        or not Genetics.color(g.secondaryColorId) or typeof(g.hatchSuccess)~="boolean"
        or typeof(g.blend)~="number" or g.blend~=g.blend or g.blend<0 or g.blend>100 or g.blend%1~=0 then return false end
    return g.hatchSuccess or g.conditionId=="cracked"
end
function Genetics.key(g)
    return g.conditionId..":"..g.primaryColorId..":"..g.secondaryColorId..":"..g.blend
end
function Genetics.tint(g)
    local a,b=Genetics.color(g.primaryColorId).rgb,Genetics.color(g.secondaryColorId).rgb
    return Color3.fromRGB(a[1],a[2],a[3]):Lerp(Color3.fromRGB(b[1],b[2],b[3]),1-g.blend/100)
end
return Genetics
