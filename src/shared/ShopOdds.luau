--!strict
local Config=require(script.Parent.Config)
local Progression=require(script.Parent.ProgressionConfig)
local Outcomes=require(script.Parent.EggOutcomeOdds)
local Odds={}
-- Normalized condition percentages for an upgrade tier (weights are integers out of
-- ConditionWeightScale, so 0.5% stays exact). Shared by disclosure text and shop UI.
function Odds.conditionPercents(level)
    local weights=Progression.ConditionWeights[math.clamp(level or 0,0,#Progression.ConditionWeights-1)+1]
    local sum=0 for _,weight in weights do sum+=weight end
    local result={}
    for i,weight in weights do result[i]=100*weight/sum end
    return result
end
function Odds.lines(level)
    local lines={"Random egg chances", "Species (bought egg, no run boost):"}
    local total=0 for _,row in Config.ChestSpeciesWeights do total+=row.weight end
    for _,row in Config.ChestSpeciesWeights do table.insert(lines,string.format("%s: %.4f%%",Config.SpeciesDisplayNames[row.speciesId],100*row.weight/total)) end
    total=0 for _,row in Config.ChestQuantityWeights do total+=row.weight end
    table.insert(lines,"Dinosaurs from a successful egg:")
    for _,row in Config.ChestQuantityWeights do table.insert(lines,string.format("%d %s: %.4f%%",row.count,if row.count==1 then "dinosaur" else "dinosaurs",100*row.weight/total)) end
    table.insert(lines,"Condition upgrade "..level.." ("..Progression.ConditionOddsVersion.."):")
    local percents=Odds.conditionPercents(level)
    for i,row in Progression.Conditions do table.insert(lines,string.format("%s: %g%%; hatch %g%%",row.name,percents[i],row.hatchChance*100)) end
    table.insert(lines,"Failed egg: "..Outcomes.percent(Outcomes.failure(level)).." overall; no dinosaur or crystal refund")
    table.insert(lines,"Colors (each slot independently):")
    total=0 for _,row in Progression.EggColors do total+=row.weight end
    for _,row in Progression.EggColors do table.insert(lines,string.format("%s (%s): %.4f%% per slot",row.name,row.rarity or "Common",100*row.weight/total)) end
    for _,row in Progression.EggColors do if row.id=="black" then table.insert(lines,"Black / Black genes: "..Outcomes.percent((row.weight/total)^2)) end end
    table.insert(lines,"Patterns (each egg, by rarity):")
    local patternRows=Progression.EggPatterns
    if patternRows then
        local patternTotal=0 for _,row in patternRows do patternTotal+=row.weight end
        for _,row in patternRows do table.insert(lines,string.format("%s (%s): %.4f%%",row.name,row.rarity,100*row.weight/patternTotal)) end
    else
        local patterns=Outcomes.patterns()
        table.insert(lines,"Patterns: "..#patterns.." equally likely; "..Outcomes.percent(1/#patterns).." each")
    end
    local mode=Outcomes.blendMode()
    table.insert(lines,if mode=="legacy" then "Primary share 0-100%: "..Outcomes.percent(1/101).." each"
        elseif mode=="uniform" then "Mixed share 1-99%: "..Outcomes.percent(1/99).." each; matching genes 100%"
        else "Mixed shares 1% and 99%: "..Outcomes.percent(2/101).." each; shares 2-98%: "..Outcomes.percent(1/101).." each; matching genes 100%")
    table.insert(lines,string.format("Normal size: %g%%, BIG (Rare): %g%%. Size only, %g%% bigger.",100*(1-Config.BigChance),100*Config.BigChance,math.floor(100*((Config.BigScaleMultiplier or 1.2)-1)+.5)))
    table.insert(lines,"Bought eggs hatch in clear weather: Shiny 0%, event mutation 0%")
    table.insert(lines,string.format("Earned eggs: Shiny (Epic) %g%% in Volcano, Northern Lights, Earthquake or Blood Moon.",100*Config.ShinyChance))
    table.insert(lines,"Other weather: Shiny 0%. BIG is rolled separately.")
    table.insert(lines,"Each full result multiplies its separate chances. Only Cracked can fail.")
    table.insert(lines,"Percentages are rounded, so totals may not be 100%.")
    table.insert(lines,"Filters keep the original chances of each result.")
    return lines
end
return Odds
