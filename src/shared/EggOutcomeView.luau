--!strict
local Theme=require(script.Parent.UITheme)
local Config=require(script.Parent.Config)
local Progression=require(script.Parent.ProgressionConfig)
local Odds=require(script.Parent.EggOutcomeOdds)
local C=Theme.Colors
local View={}
local patternNames={legacy="Legacy",["01_blank"]="Blank",["02_emerald_islands"]="Islands",
    ["03_round_spots"]="Round spots",["04_bold_patches"]="Bold patches",["05_horizontal_bands"]="Bands",
    ["06_wavy_stripes"]="Wavy stripes",["07_diamond_scales"]="Diamond scales",["08_freckles"]="Freckles"}
local function text(parent,value,x,y,w,h,size,color)
    local t=Instance.new("TextLabel")
    t.BackgroundTransparency,t.Position,t.Size=1,UDim2.fromOffset(x,y),UDim2.fromOffset(w,h)
    t.Text,t.TextColor3,t.TextSize,t.Font=value,color or C.text,size,Enum.Font.FredokaOne
    t.TextWrapped,t.TextXAlignment,t.ZIndex,t.Parent=true,Enum.TextXAlignment.Left,parent.ZIndex+1,parent
    return t
end
local function button(parent,value,x,y,w,h,callback)
    local b=Instance.new("TextButton")
    b.Position,b.Size,b.BackgroundColor3=UDim2.fromOffset(x,y),UDim2.fromOffset(w,h),C.card
    b.Text,b.TextColor3,b.TextSize,b.ZIndex,b.Parent=value,C.text,17,parent.ZIndex+2,parent
    Theme.decorate(b,4)
    b.Activated:Connect(callback)
    return b
end
function View.add(body,state,level,height,onChange,onBack)
    local h=math.ceil(math.max(48,height))
    local dropdown
    local dropdownKey
    local function menu(title,key,options,x,y,w)
        local value=state.filters[key]
        local selected="All"
        for _,option in options do if option.id==value then selected=option.name end end
        button(body,title..": "..selected.."  v",x,y,w,h,function()
            if dropdown then
                dropdown:Destroy() dropdown=nil
                if dropdownKey==key then dropdownKey=nil return end
            end
            dropdownKey=key
            dropdown=Instance.new("ScrollingFrame")
            dropdown.Name,dropdown.BackgroundColor3,dropdown.BorderSizePixel="OutcomeFilterMenu",C.panel,0
            dropdown.Position=UDim2.fromOffset(x,y+h)
            dropdown.Size=UDim2.fromOffset(w,math.min(220,402-y-h))
            dropdown.CanvasSize,dropdown.ScrollBarThickness=UDim2.fromOffset(0,(#options+1)*h),6
            dropdown.ZIndex,dropdown.Parent=90,body
            local choices={{name="All"}}
            for _,option in options do table.insert(choices,option) end
            for i,option in choices do
                button(dropdown,option.name,0,(i-1)*h,w-8,h,function()
                    state.filters[key]=option.id state.page=1 onChange()
                end)
            end
        end)
    end
    local species={} for _,s in Config.ChestSpeciesWeights do table.insert(species,{id=s.speciesId,name=Config.SpeciesDisplayNames[s.speciesId]}) end
    local conditions={} for _,c in Progression.Conditions do table.insert(conditions,{id=c.id,name=c.name}) end
    local colors={} for _,c in Progression.EggColors do table.insert(colors,{id=c.id,name=c.name}) end
    local patterns={} for _,p in Odds.patterns() do table.insert(patterns,{id=p,name=patternNames[p] or p}) end
    menu("Species","species",species,0,0,200)
    menu("Condition","condition",conditions,208,0,200)
    menu("Primary","primary",colors,416,0,200)
    menu("Secondary","secondary",colors,624,0,200)
    menu("Pattern","pattern",patterns,0,h+6,260)
    menu("Size","big",{{id=false,name="Normal"},{id=true,name="BIG"}},268,h+6,260)
    menu("Copies","copies",{{id=1,name="1"},{id=2,name="2"},{id=3,name="3"}},536,h+6,280-h)
    local reset=button(body,"X",824-h,h+6,h,h,function() state.filters={} state.page=1 onChange() end)
    reset.Name="ClearOutcomeFilters"
    local hint=text(body,"Clear filters",600,h*2+14,224,22,16,C.gold) hint.Visible=false
    reset.MouseEnter:Connect(function() hint.Visible=true end)
    reset.MouseLeave:Connect(function() hint.Visible=false end)
    local catalog=Odds.catalog(level,state.filters)
    local pages=math.max(1,math.ceil(catalog.count/2))
    state.page=math.clamp(state.page,1,pages)
    local y=2*h+14
    text(body,"Tier "..catalog.level.." | "..catalog.count.." outcomes | Shiny 0% | Event: None",0,y,824,22,16,C.gold)
    y+=28
    local footer=402-h
    local rowHeight=(footer-y-8)/2
    for slot=1,2 do
        local outcome=catalog.at((state.page-1)*2+slot)
        if not outcome then continue end
        local top=y+(slot-1)*rowHeight
        local description
        if outcome.failed then description="No dinosaur\nEgg consumed; no crystal refund"
        else
            description=Config.SpeciesDisplayNames[outcome.speciesId].." x"..outcome.count.." | "..outcome.conditionName.." | "..(if outcome.big then "BIG" else "Normal size")
                .."\n"..outcome.primaryName.." "..outcome.share.."% / "..outcome.secondaryName.." "..(100-outcome.share).."%"
                .." | "..(patternNames[outcome.patternId] or outcome.patternId)
        end
        text(body,description,4,top,560,rowHeight-4,18)
        text(body,Odds.percent(outcome.probability),574,top,246,rowHeight-4,19,C.gold)
    end
    if catalog.count==0 then text(body,"No matching outcomes",0,y,824,80,22) end
    local prev=button(body,"<",0,footer,h,h,function() state.page=math.max(1,state.page-1) onChange() end)
    prev.Name="PreviousOutcomePage"
    local input=Instance.new("TextBox")
    input.Name,input.Position,input.Size="OutcomePage",UDim2.fromOffset(h+10,footer),UDim2.fromOffset(170,h)
    input.BackgroundColor3,input.TextColor3,input.TextSize,input.Font=C.card,C.text,18,Enum.Font.FredokaOne
    input.Text,input.ClearTextOnFocus,input.ZIndex,input.Parent=tostring(state.page),false,body.ZIndex+2,body
    Theme.decorate(input,4)
    input.FocusLost:Connect(function()
        local value=tonumber(input.Text)
        if value and value==value and value%1==0 then state.page=math.clamp(value,1,pages) end
        onChange()
    end)
    local nextButton=button(body,">",h+190,footer,h,h,function() state.page=math.min(pages,state.page+1) onChange() end)
    nextButton.Name="NextOutcomePage"
    text(body,"/ "..pages.." pages\nRounded; totals may differ from 100%",2*h+200,footer,400-2*h,h,15)
    button(body,"BACK",610,footer,214,h,onBack)
end
return View
