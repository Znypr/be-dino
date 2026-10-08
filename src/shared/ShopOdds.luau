--!strict
local Config=require(script.Parent.Config)
local Progression=require(script.Parent.ProgressionConfig)
local Outcomes=require(script.Parent.EggOutcomeOdds)
local Odds={}
function Odds.lines(level)
    local lines={"RANDOM EGG ODDS", "Species (one purchased egg; no run-batch boost):"}
    local total=0 for _,row in Config.ChestSpeciesWeights do total+=row.weight end
    for _,row in Config.ChestSpeciesWeights do table.insert(lines,string.format("%s: %.4f%%",Config.SpeciesDisplayNames[row.speciesId],100*row.weight/total)) end
    total=0 for _,row in Config.ChestQuantityWeights do total+=row.weight end
    table.insert(lines,"Copies from a successful egg:")
    for _,row in Config.ChestQuantityWeights do table.insert(lines,string.format("%d copies: %.4f%%",row.count,100*row.weight/total)) end
    table.insert(lines,"Condition upgrade "..level..":")
    local weights=Progression.ConditionWeights[level+1]
    for i,row in Progression.Conditions do table.insert(lines,string.format("%s: %g%%; hatch %g%%; speed/growth %gx",row.name,weights[i],row.hatchChance*100,row.stats)) end
    table.insert(lines,string.format("Failed egg: %.4f%% overall; no dinosaur or crystal refund",weights[1]*(1-Progression.Conditions[1].hatchChance)))
    table.insert(lines,"Colors (each slot independently):")
    total=0 for _,row in Progression.EggColors do total+=row.weight end
    for _,row in Progression.EggColors do table.insert(lines,string.format("%s: %.4f%% per slot",row.name,100*row.weight/total)) end
    for _,row in Progression.EggColors do if row.id=="black" then table.insert(lines,"Black / Black genes: "..Outcomes.percent((row.weight/total)^2)) end end
    local patterns=Outcomes.patterns()
    table.insert(lines,"Patterns: "..#patterns.." equally likely; "..Outcomes.percent(1/#patterns).." each")
    local mode=Outcomes.blendMode()
    table.insert(lines,if mode=="legacy" then "Primary share 0-100%: "..Outcomes.percent(1/101).." each"
        elseif mode=="uniform" then "Mixed share 1-99%: "..Outcomes.percent(1/99).." each; matching genes 100%"
        else "Mixed shares 1% and 99%: "..Outcomes.percent(2/101).." each; shares 2-98%: "..Outcomes.percent(1/101).." each; matching genes 100%")
    table.insert(lines,"Normal size: 90%; BIG: 10% (size only, 1.2x)")
    table.insert(lines,"Purchased eggs: clear-weather, Shiny 0%; event mutation 0%")
    table.insert(lines,"Earned eggs: Shiny 5% during Volcano, Northern Lights, Earthquake or Blood Moon; otherwise 0%. BIG is independent.")
    table.insert(lines,"Each combined outcome multiplies its independent probabilities; only Cracked can fail.")
    table.insert(lines,"Displayed percentages are rounded; their total may differ from 100%. Filters retain original odds, not renormalized subset odds.")
    return lines
end
return Odds
