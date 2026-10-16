--!strict
-- BD-100 (docs/72, docs/73): the one place that turns seconds and multipliers into child-friendly text.
local UIFormat={}
-- 40 s, 5 min, 2 h, 2 h 10 min. Whole seconds are rounded up; minutes and hours drop zero parts.
function UIFormat.duration(seconds: number): string
    local total=math.max(0,math.ceil(seconds))
    if total<60 then return total.." s" end
    if total<3600 then return (total//60).." min" end
    local hours,minutes=total//3600,(total%3600)//60
    return if minutes==0 then hours.." h" else hours.." h "..minutes.." min"
end
function UIFormat.readyIn(seconds: number): string return "Ready in "..UIFormat.duration(seconds) end
-- 1.2 -> "+20%", 0.8 -> "-20%", 1 -> "" (neutral).
function UIFormat.percent(multiplier: number): string
    local value=math.floor((multiplier-1)*100+.5)
    if value==0 then return "" end
    return (if value>0 then "+" else "-")..math.abs(value).."%"
end
function UIFormat.boost(name: string,multiplier: number): string?
    local text=UIFormat.percent(multiplier)
    if text=="" then return nil end
    return name.." "..text
end
-- Only active boosts, in a fixed order; empty table when nothing is active.
function UIFormat.boostLines(growth: number,speed: number,loot: number): {string}
    local lines={}
    for _,pair in {{"Speed",speed},{"Growth",growth},{"Eggs",loot}} do
        local line=UIFormat.boost(pair[1] :: string,pair[2] :: number)
        if line then table.insert(lines,line) end
    end
    return lines
end
-- "Speed +20% - 5 min"
function UIFormat.potion(kind: string,multiplier: number,seconds: number): string
    local name=string.upper(string.sub(kind,1,1))..string.sub(kind,2)
    return (UIFormat.boost(name,multiplier) or name).." - "..UIFormat.duration(seconds)
end
return UIFormat
