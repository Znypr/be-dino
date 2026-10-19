--!strict
-- BD-1110 / docs/160 s10: the Dino Index screen ("collection") and the dino details screen ("detail", the DinoIndexPanels version and the
-- older fallback) were inline in Bootstrap's render function. They live here now, code unchanged. Bootstrap calls attach once with its
-- screen helpers, then render(name) for every name in DinoIndexScreens.names. The Patterns and Colours tabs and the details panels
-- (DinoIndexPanels) stay separate modules; this module only draws the cards, the progress bar and the fallback details. The selected species
-- (which dino the details show) is kept here, nobody else in Bootstrap reads it.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Http = game:GetService("HttpService")
local player = Players.LocalPlayer
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Theme = require(Shared.UITheme)
local Preview = require(Shared.DinosaurPreview)
local ProgressionConfig = require(Shared.ProgressionConfig)
local UIFormat = require(Shared.UIFormat)
local FusionSelection = require(Shared.FusionSelection)
local DinoIndexPanels = require(script.Parent.DinoIndexPanels)
local C = Theme.Colors

local Screens = {}
Screens.names = {collection = true, detail = true}

-- Bootstrap's screen helpers, set by attach.
local body: any, heading: any, header: any, label: any, box: any, button: any
local open: any, notify: any, viewportScale: any, num: any, str: any, decoded: any, openFusion: any, equip: any
local copies: any, bestMutation: any, eventMutation: any, ownedTraits: any, hero: any, speciesIndex: any, motionNow: any
local motion = true -- read from Bootstrap at the start of every render (Calm motion can change between two openings)

local selected = "compy"
local rarityColors=Theme.RarityColors
local rarityNames=Config.SpeciesRarityNames
local oddsWeight,oddsTotal={},0 -- base chance of one purchased egg, shown on Dino Index cards (docs/85)
for _,row in Config.ChestSpeciesWeights do oddsWeight[row.speciesId]=row.weight oddsTotal+=row.weight end
local function meter(parent: GuiObject,x: number,y: number,w: number,value: number,maxValue: number,color: Color3,text: string,h: number?,size: number?)
    local b=box(parent,x,y,w,h or 34,C.outline,parent.ZIndex+1)
    local fill=Instance.new("Frame")
    local fraction=if maxValue>0 then math.clamp(value/maxValue,0,1) else 0
    fill.Size,fill.BorderSizePixel,fill.BackgroundColor3,fill.ZIndex,fill.Parent=UDim2.new(if motion then 0 else fraction,0,1,0),0,color,b.ZIndex+1,b
    Theme.animate(fill,.22,{Size=UDim2.new(fraction,0,1,0)})
    label(b,text,0,0,w,h or 34,size or 20)
    return b
end

-- d: {body, heading, header, label, box, button, open, notify, viewportScale, num, str, decoded, openFusion, equip, copies, bestMutation,
--     eventMutation, ownedTraits, hero, speciesIndex, motion}
function Screens.attach(d: any)
    body, heading, header, label, box, button = d.body, d.heading, d.header, d.label, d.box, d.button
    open, notify, viewportScale, num, str, decoded = d.open, d.notify, d.viewportScale, d.num, d.str, d.decoded
    openFusion, equip = d.openFusion, d.equip
    copies, bestMutation, eventMutation, ownedTraits, hero, speciesIndex, motionNow = d.copies, d.bestMutation, d.eventMutation, d.ownedTraits, d.hero, d.speciesIndex, d.motion
end

function Screens.render(name: string)
    motion = motionNow()
    if name=="collection" then
        heading.Text,header.BackgroundColor3="Dino Index",C.blue
        if require(script.Parent.IndexTabs).mount(open) then return end
        local unlocked=0
        -- BD-269: at most 24 cards are built per page, so a long Index stays light on phones (pager shows only if >1 page).
        local IndexProgress=require(Shared.IndexProgress)
        -- BD-604 (docs/149 SS4): with Config.SecretSpeciesEnabled the secret cards follow the normal 22 (same table when the flag is off);
        -- secrets are counted apart ("2 / 7 secrets found") and never enter the normal "Collected X of 22" number.
        local Secret=require(Shared.SecretSpeciesConfig)
        local order=Secret.indexOrder(Config.SpeciesOrder,Config.SecretSpeciesEnabled)
        local pg=IndexProgress.page(#order,24,IndexProgress.state.page)
        IndexProgress.state.page=pg.page
        local list=Instance.new("ScrollingFrame")
        list.Name,list.Size,list.Position="DinoCards",UDim2.fromOffset(824,326),UDim2.fromOffset(0,0)
        list.BackgroundTransparency,list.BorderSizePixel,list.ScrollBarThickness=1,0,6
        local lay=IndexProgress.cardLayout(viewportScale(),326) -- BD-332: two rows always visible (compact cards when short)
        local cardButtonHeight,cardHeight,rowHeight=lay.buttonHeight,lay.cardHeight,lay.rowHeight
        list.CanvasSize=UDim2.fromOffset(0,math.ceil((pg.last-pg.first+1)/3)*rowHeight)
        list.ZIndex,list.Parent=24,body
        for i,id in order do
            local base,gold,diamond=copies(id)
            local event=eventMutation(id)
            local rarity=speciesIndex(id)
            local found=base+gold+diamond>0 or event~=nil or ownedTraits(id)~=nil
            local secret=i>#Config.SpeciesOrder
            if found and not secret then unlocked+=1 end
            if i<pg.first or i>pg.last then continue end
            local look=if secret then Secret.indexCard(id,found) else FusionSelection.indexCard(found)
            local card=box(list,((i-pg.first)%3)*276,math.floor((i-pg.first)/3)*rowHeight,264,cardHeight,if found then rarityColors[rarity] else Color3.fromRGB(62,64,74),24)
            Theme.texture(card,264,cardHeight)
            label(card,look.nameText or Config.SpeciesDisplayNames[id],4,if lay.compact then 3 else 8,256,if lay.compact then 26 else 35,if lay.compact then 21 else 25)
            label(card,look.rarityText or (rarityNames[rarity].." • "..FusionSelection.pct(100*(oddsWeight[id] or 0)/oddsTotal).." of eggs"),4,if lay.compact then 28 else 44,256,if lay.compact then 20 else 25,if lay.compact then 15 else 18)
            if found then
                hero(card,id,7,lay.heroY,250,lay.heroHeight,bestMutation(id))
                require(script.Parent.ClassRow).card(label,card,id,if event then "" elseif ownedTraits(id) then (require(Shared.ColourBonus).text(ProgressionConfig.EggColors,(ownedTraits(id) :: any).genes) or "Special variant") else require(script.Parent.ClassRow).label(id).." • "..require(Shared.FtueP1).indexCount(base,gold,diamond),lay.detailY,lay.compact,lay.heroY)
                if event then require(script.Parent.MutationBadge).chip(card,event.id,UDim2.new(0.5,0,0,lay.detailY),Vector2.new(0.5,0)) end -- BD-352: real badge, not 9 px text
                if lay.compact then
                    local tap=Instance.new("TextButton") -- the whole card opens the dino (no VIEW DINO bar when short)
                    tap.Name,tap.Text,tap.BackgroundTransparency,tap.Size,tap.ZIndex,tap.Parent="ViewDino","",1,UDim2.fromScale(1,1),card.ZIndex+8,card
                    tap.Activated:Connect(function() selected=id open("detail") end)
                else
                    button(card,"VIEW DINO",12,233,240,cardButtonHeight,C.card,function() selected=id open("detail") end)
                end
            else
                -- No button: silhouette block re-centered in the freed space. Soft edge = a faint, slightly larger
                -- copy underneath (2 viewports max, no per-frame work); skipped when motion/effects are reduced.
                local blockY=if lay.compact then lay.heroY else 70+math.floor((cardButtonHeight+12)/2)
                if secret and not look.silhouette then
                    label(card,"?",7,blockY,250,if lay.compact then lay.heroHeight else 128,if lay.compact then 44 else 72) -- a secret with no model yet: a plain mark, never a broken dino
                elseif motion then
                    local halo=Preview.add(card,id,"silhouette")
                    halo.Name,halo.ImageTransparency=("SilhouetteSoftEdge"),.82
                    halo.Position,halo.Size=UDim2.fromOffset(-2,blockY-9),UDim2.fromOffset(268,if lay.compact then lay.heroHeight+18 else 146)
                end
                if not secret or look.silhouette then
                    local view=Preview.add(card,id,"silhouette")
                    view.Position,view.Size=UDim2.fromOffset(7,blockY),UDim2.fromOffset(250,if lay.compact then lay.heroHeight else 128)
                end
                label(card,look.status,5,if lay.compact then lay.detailY else blockY+134,254,if lay.compact then 22 else 25,if lay.compact then 14 else 16)
            end
        end
        -- BD-269: "Collected X of Y (P%)" bar with milestone ticks (src/shared/IndexProgress).
        local progress=IndexProgress.summary(unlocked,#Config.SpeciesOrder)
        local meterWidth=if pg.pages>1 then 420 else 600
        -- BD-1124 (docs/202 R12): with TimerChipsEnabled the bar is big (44 px, like the buttons beside it) and says "Found 1/22" in 24 px; else the BD-269 line.
        local bigBar=Config.TimerChipsEnabled==true
        meter(body,0,if bigBar then 350 else 356,meterWidth,unlocked,#Config.SpeciesOrder,C.accent,if bigBar then progress.short else progress.text,if bigBar then 44 else nil,if bigBar then 24 else nil).Name="IndexBar"
        if Config.SecretSpeciesEnabled==true then label(body,Secret.summary(Secret.countFound(decoded("CollectionJson","{}"))).text,0,328,420,24,18,C.gold) end -- BD-604 SS4: secrets counted apart from the 22
        if pg.pages>1 then
            button(body,"<",430,350,50,44,C.blue,function() IndexProgress.state.page=pg.page-1 open("collection") end)
            label(body,pg.page.." / "..pg.pages,482,350,60,44,20)
            button(body,">",546,350,50,44,C.blue,function() IndexProgress.state.page=pg.page+1 open("collection") end)
        end
        for _,tick in progress.ticks do
            if tick.fraction<1 then
                local mark=Instance.new("Frame") mark.Name,mark.BorderSizePixel,mark.ZIndex,mark.Parent="IndexMilestone",0,body.ZIndex+8,body
                mark.Size,mark.Position=UDim2.fromOffset(4,8),UDim2.fromOffset(math.floor(meterWidth*tick.fraction)-2,if bigBar then 396 else 388) -- BD-300: below the bar, never over its text
                mark.BackgroundColor3=if tick.reached then C.gold else C.text
                mark.BackgroundTransparency=if tick.reached then 0 else .35
            end
        end
        button(body,"FUSION",624,350,200,44,C.gold,function() openFusion() end)
    elseif name=="detail" and DinoIndexPanels.supported() then
        -- BD-149/150/151: drag-to-turn hero, My dinos grid, per-copy EQUIP, Sort and filter (src/client/DinoIndexPanels).
        local index=speciesIndex(selected)
        local base,gold,diamond=copies(selected)
        local event=eventMutation(selected)
        heading.Text,header.BackgroundColor3=Config.SpeciesDisplayNames[selected] or require(Shared.SecretSpeciesConfig).name(selected),rarityColors[index]
        DinoIndexPanels.species({
            body=body,speciesId=selected,color=rarityColors[index],
            owned=base+gold+diamond>0 or event~=nil or ownedTraits(selected)~=nil,
            fallbackStage=bestMutation(selected),
            fallbackLine=string.format("Base %d, Gold %d, Diamond %d",base,gold,diamond),
            scale=viewportScale,
            revision=function() return num("ProfileRevision") end,
            equipped=function()
                local ok,genes=pcall(function() return Http:JSONDecode(str("EquippedGenesJson","null")) end)
                return {speciesId=str("EquippedSpeciesId","compy"),genes=if ok and typeof(genes)=="table" then genes else nil,
                    shiny=player:GetAttribute("EquippedShiny")==true,big=player:GetAttribute("EquippedBig")==true,mutationId=str("EquippedEventMutation")}
            end,
            equip=function(speciesId,variantKey) notify("Equipping...",C.blue) equip:FireServer(speciesId,Http:GenerateGUID(false),variantKey) end,
            notify=notify,
            onBack=function() open("collection") end,
        })
    elseif name=="detail" then
        local index=speciesIndex(selected)
        local base,gold,diamond=copies(selected)
        local event=eventMutation(selected)
        local owned=base+gold+diamond>0 or event~=nil or ownedTraits(selected)~=nil
        heading.Text,header.BackgroundColor3=Config.SpeciesDisplayNames[selected] or require(Shared.SecretSpeciesConfig).name(selected),rarityColors[index]
        local stage=box(body,0,0,380,360,rarityColors[index],24)
        hero(stage,selected,0,20,380,280,bestMutation(selected))
        label(stage,rarityNames[index].." • "..FusionSelection.pct(100*(oddsWeight[selected] or 0)/oddsTotal).." of eggs",0,302,380,42,28)
        label(body,"Your collection",414,0,400,42,28)
        label(body,string.format("Base: %d • Gold: %d\nDiamond: %d",base,gold,diamond),414,62,400,92,25)
        label(body,if event then event.name.." • "..table.concat(UIFormat.boostLines(event.growth,event.speed,1)," • ") else "6 Base make Gold, 3 Gold make Emerald, 2 Emerald make Diamond. Your best is used.",414,173,400,66,22,C.gold)
        do local line=label(body,require(Shared.ClassInfo).line(selected),414,241,400,28,22,require(Shared.ClassInfo).Colors[require(Shared.ClassInfo).forSpecies(selected).class]) -- BD-423: class + one-line feel hint
            line.TextScaled,line.TextWrapped=true,false -- BD-443: shrink to fit one line on a phone, never clip
            local fit=Instance.new("UITextSizeConstraint") fit.MinTextSize,fit.MaxTextSize,fit.Parent=14,22,line end
        local equipped=str("EquippedSpeciesId","compy")==selected
        button(body,if equipped then "EQUIPPED" elseif not owned then "LOCKED" else "EQUIP",426,273,372,52,if owned then C.accent else C.card,function()
            if not owned then notify("Hatch eggs to find this dino") return end
            if not equipped then notify("Equipping...",C.blue) equip:FireServer(selected,Http:GenerateGUID(false)) end
        end)
        button(body,"Back",426,341,372,45,C.blue,function() open("collection") end)
    end
end

return Screens
