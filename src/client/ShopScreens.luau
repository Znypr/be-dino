--!strict
-- BD-1088 / docs/160 s10: the shop screens (Crystal Shops, the odds pages, the purchase confirms and the Potion Shop) were inline in
-- Bootstrap's render function. They live here now, code unchanged. Bootstrap calls attach once with its screen helpers, then
-- render(name) for every name in Shop.names. The shop state (tab, page, pending purchase) is kept here.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Input = game:GetService("UserInputService")
local Http = game:GetService("HttpService")
local Marketplace = game:GetService("MarketplaceService")
local player = Players.LocalPlayer
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Theme = require(Shared.UITheme)
local ModelPreview = require(Shared.ModelPreview)
local ProgressionConfig = require(Shared.ProgressionConfig)
local ProgressionRules = require(Shared.ProgressionRules)
local EggGenetics = require(Shared.EggGenetics)
local EggAppearance = require(Shared.EggAppearance)
local ShopOdds = require(Shared.ShopOdds)
local UIFormat = require(Shared.UIFormat)
local EggOutcomeView = require(Shared.EggOutcomeView)
local NotifyQueue = require(Shared.NotifyQueue)
local Sfx = require(Shared.Sfx)
local C = Theme.Colors

local Shop = {}
Shop.names = {auras = true, oddsSimple = true, eggOdds = true, eggOutcomes = true, eggPurchase = true, conditionConfirm = true, auraConfirm = true,
    potions = true, potionConfirm = true, potionReplace = true}

-- Bootstrap's screen helpers, set by attach.
local body: any, heading: any, header: any, label: any, box: any, button: any, art: any
local open: any, notify: any, viewportScale: any, num: any, str: any, decoded: any, progression: any, render: any, isActive: any
local shopAction: any, shopResult: any

local chosenAura="meadow"
local cosmeticTab="auras"
local trailPage=1
local oddsLevelOverride=nil
local outcomeState={page=1,filters={}}
local potionChoice={id="speed_common",window=0} -- BD-539: the shop window the offers were drawn from
local pendingShop=nil
local function transact(action,id,replace)
    if pendingShop then notify("Purchase is still processing",C.gold) return end
    local token=Http:GenerateGUID(false)
    pendingShop={token=token,action=action,id=id,replace=replace==true,started=os.clock()}
    shopAction:FireServer(action,id,token,replace==true)
end

-- d: {body, heading, header, label, box, button, art, open, notify, viewportScale, num, str, decoded, progression, render, active}
function Shop.attach(d: any)
    body, heading, header, label, box, button, art = d.body, d.heading, d.header, d.label, d.box, d.button, d.art
    open, notify, viewportScale, num, str, decoded = d.open, d.notify, d.viewportScale, d.num, d.str, d.decoded
    progression, render, isActive = d.progression, d.render, d.active
    local remotes = ReplicatedStorage:WaitForChild("BeDinoRemotes", 60) :: Folder
    shopAction = remotes:WaitForChild("ProgressionAction")
    shopResult = remotes:WaitForChild("ProgressionResult")
    shopResult.OnClientEvent:Connect(function(token,ok,status)
        if pendingShop and pendingShop.token==token then pendingShop=nil end
        if ok then Sfx.play("shop_buy") end
        notify(if ok then "Done!" else NotifyQueue.statusText(status),if ok then C.accent else C.red,{key=if ok then "ok" else "error"})
        local current=isActive() if current=="auras" or current=="potions" then body:ClearAllChildren() render(current) end
    end)
end

-- Bootstrap's HUD tick: a purchase with no answer after 8 s is sent again with the same token (a delayed result cannot charge twice).
function Shop.retryPending()
    if pendingShop and os.clock()-pendingShop.started>8 then
        pendingShop.started=os.clock()
        shopAction:FireServer(pendingShop.action,pendingShop.id,pendingShop.token,pendingShop.replace)
    end
end

function Shop.render(name: string)
    if name=="auras" then
        heading.Text,header.BackgroundColor3="Crystal Shops",C.purple
        local p=progression()
        p.trails=p.trails or {}
        local isTrail=cosmeticTab=="trails"
        local touch=Input.TouchEnabled
        local targetHeight=if touch then math.max(45,45/viewportScale()) else 44
        local tabsHeight=if touch then targetHeight else 40
        local cardsY=tabsHeight+12
        local cardsHeight=if touch then 402-cardsY-targetHeight-12 else 270
        local buyY=cardsHeight-targetHeight-10
        if cosmeticTab=="conditions" and num("AccountLevel")<require(Shared.FtueP1).ConditionsTabLevel then cosmeticTab="auras" isTrail=false end -- BD-445: tab hidden until level 3
        local noCrystalsHint=require(Shared.FtueP1).noCrystalsHintShown(num("Crystals"),cosmeticTab)
        local hintInFooter=noCrystalsHint and (cosmeticTab=="auras" or cosmeticTab=="trails") -- BD-445/BD-529: the hint takes the footer line of the aura and trail pages
        if noCrystalsHint and not hintInFooter then label(body,require(Shared.FtueP1).NoCrystalsHint,0,362,824,34,22,C.gold) end -- BD-445
        -- BD-532 (docs/115 EG1): the server refuses random crystal items under this exact rule (Shared/PaidRandomGate); the egg and the condition
        -- upgrade are greyed out "Coming soon" BEFORE the tap instead of answering "Not available yet" after it. The policy gate is not loosened.
        local PaidRandomGate=require(Shared.PaidRandomGate)
        local randomBlocked=PaidRandomGate.blocked(Config.DeveloperProducts,Config.PaidRandomItemsEnabled,require(script.Parent.PrivateState).get("PaidRandomEligible"))
        local ShopTiles=require(script.Parent.ShopTiles) -- BD-047: tab icons; each shows only when its image id exists
        local shopTabs=require(Shared.FtueP1).shopTabs(num("AccountLevel"))
        if ShopTiles.landing then
            ShopTiles.build({label=label,box=box},body,{tabs=shopTabs,info=ShopTiles.info(p,ProgressionConfig.RandomEggPrice,num("Crystals"),randomBlocked),
                onPick=function(tab) Sfx.play("ui_click") ShopTiles.landing=false cosmeticTab=tab open("auras") end})
            return
        end
        for i,tab in shopTabs do
            local tabButton=button(body,string.upper(tab),(i-1)*165,0,155,tabsHeight,if cosmeticTab==tab then C.blue else C.card,function() cosmeticTab=tab open("auras") end)
            tabButton.TextSize=20
            ShopTiles.decorateTab(tabButton,tab,tabsHeight)
        end
        if cosmeticTab=="eggs" then
            if not ShopTiles.eggProduct(body,20,cardsY+12,220) then art(body,"egg",20,cardsY+12,220) end
            label(body,"Random Egg",270,cardsY,535,40,30,C.gold)
            label(body,ProgressionConfig.RandomEggPrice.." Crystals\nBalance: "..num("Crystals").."  •  Level "..num("AccountLevel"),270,cardsY+45,535,60,22)
            button(body,"Chances",270,cardsY+119,535,targetHeight,C.blue,function() oddsLevelOverride=nil outcomeState={page=1,filters={}} open("oddsSimple") end)
            if randomBlocked then -- BD-532: greyed out, no confirm, nothing to tap
                local soon=button(body,string.upper(PaidRandomGate.ComingSoon),270,cardsY+targetHeight+130,535,targetHeight,C.card,function() end)
                soon.Name,soon.AutoButtonColor,soon.TextTransparency="BuyEggComingSoon",false,.15
            else
                local eggShort=num("Crystals")<ProgressionConfig.RandomEggPrice -- BD-530: no confirm screen with a negative balance
                button(body,if eggShort then "NEED "..ProgressionConfig.RandomEggPrice.." CRYSTALS" else "BUY EGG",270,cardsY+targetHeight+130,535,targetHeight,if eggShort then C.card else C.accent,function()
                    if eggShort then notify("Need "..ProgressionConfig.RandomEggPrice.." Crystals",C.gold) return end
                    open("eggPurchase")
                end).Name="BuyEggButton"
            end
            -- BD-391/405 (docs/115 D22): Fast travel perk, bought with crystals. PROVISIONAL price. Walking stays the default.
            if Config.FastTravelPerk and Config.CaveHub and require(Shared.FtueP1).fastTravelEntryShown(num("AccountLevel"),type(p.perks)=="table" and p.perks.fastTravel==true) then -- BD-447
                local owned=type(p.perks)=="table" and p.perks.fastTravel==true
                local perkPrice=ProgressionConfig.FastTravelPrice
                label(body,"Fast travel: zip to the shops",0,math.max(cardsY+targetHeight*2+150,336),520,34,22,C.gold)
                button(body,if owned then "YOURS" else perkPrice.." Crystals",540,math.max(cardsY+targetHeight*2+146,332),284,targetHeight,if owned then C.card else C.accent,function()
                    if not owned then transact("buyPerk","fastTravel") open("auras") end
                end).Active=not owned
            end
            return
        elseif cosmeticTab=="conditions" then
            local weights=ShopOdds.conditionPercents(p.conditionLevel or 0) -- BD-045: normalized percents
            local upgrade=ProgressionConfig.ConditionUpgrades[(p.conditionLevel or 0)+1]
            -- docs/73: plain egg per condition on a floor swatch; chance only (no stats text, no odds screen).
            local safeLine=require(Shared.OddsCopy).safeEggsLine(require(Shared.FtueRules).safeEggsLeftView(require(Shared.FtueRules).collectionCopies(decoded("CollectionJson","{}")),num("ActiveChestCount"),num("QueuedEggsWaiting")))
            if safeLine then label(body,safeLine,0,cardsY,824,30,20,C.gold) end -- BD-372/365: the safe-first-eggs note, only while true
            -- BD-394: the Blender stage when uploaded (ConditionStageAssetIds); else the live egg tiles.
            local staged=require(script.Parent.ConditionStage).background(body,0,cardsY+62,824,144)
            for i,row in ProgressionConfig.Conditions do
                local x=(i-1)*165
                label(body,row.name,x,cardsY+32,155,28,22)
                local tile=box(body,x,cardsY+62,155,144,Color3.fromRGB(122,148,112):Lerp(C.panel,.25),24)
                if staged then tile.BackgroundTransparency=1 end
                if not (staged and require(script.Parent.ConditionStage).egg(tile,row.id)) then
                    -- BD-141: the flat official egg render + this condition's registered overlay (docs/77) fills the tile. The 3D viewport egg
                    -- could fall back to a plain cream shape, so the tile uses the deterministic image path (never a bare box).
                    local pic=require(script.Parent.EggPicture).add(tile,EggGenetics.neutral(row.id),150)
                    pic.Name,pic.AnchorPoint,pic.Position="ConditionEggPicture",Vector2.new(.5,.5),UDim2.fromScale(.5,.5)
                end
                label(body,string.format("%g%%",weights[i]),x,cardsY+210,155,34,24,C.blue)
            end
            local upgradeText,upgradeOk=require(Shared.FtueP1).upgradeButton(upgrade,num("AccountLevel"),num("Crystals")) -- BD-372: grey with the reason, never green over a lock
            if randomBlocked then upgradeText,upgradeOk=PaidRandomGate.ComingSoon,false end -- BD-532: the server refuses upgradeCondition under the same rule
            local upgradeButton=button(body,upgradeText,142,cardsY+254,540,targetHeight,if upgradeOk then C.accent else C.card,function() if upgradeOk and upgrade then open("conditionConfirm") end end)
            upgradeButton.TextSize=20
            upgradeButton.Name=if upgradeOk then "UpgradeButton" else "UpgradeLocked"
            if not upgradeOk then upgradeButton.AutoButtonColor=false upgradeButton.TextTransparency=.15 end
            label(body,require(Shared.FtueP1).upgradeHint(upgrade,num("AccountLevel")),0,cardsY+254+targetHeight+4,824,30,19,C.gold)
            return
        elseif cosmeticTab=="crystals" then
            -- BD-179: one card per pack in a 3-wide grid (same card look as the potion shop). Prices load from the marketplace.
            label(body,"You have "..num("Crystals").." Crystals",0,cardsY-4,824,34,26,C.gold)
            local cardRules=require(Shared.ShopCardState)
            if cardRules.packsView(Config.CrystalPacksEnabled)==cardRules.SoonView then
                -- BD-546: packs are off: one friendly card, no price button and no price lookup. Same flag as the server (Config.CrystalPacksEnabled).
                local soon=box(body,142,cardsY+50,540,200,C.card:Lerp(C.purple,.25),24)
                soon.Name="CrystalsComingSoon"
                art(soon,"amber",224,14,92)
                label(soon,cardRules.SoonTitle,0,110,540,46,36,C.gold)
                label(soon,cardRules.SoonLine,0,156,540,32,22)
                return
            end
            local products={} for id,amount in Config.DeveloperProducts do table.insert(products,{id=id,amount=amount}) end
            table.sort(products,function(a,b) return a.amount<b.amount end)
            if #products==0 then label(body,"Crystal packs are not ready yet",0,cardsY+80,824,60,27)
            else
                local gridTop=cardsY+58
                local grid=Instance.new("ScrollingFrame") grid.Name="CrystalGrid"
                grid.BackgroundTransparency,grid.BorderSizePixel,grid.ScrollBarThickness,grid.ZIndex=1,0,8,body.ZIndex+1
                grid.Position,grid.Size=UDim2.fromOffset(0,gridTop),UDim2.fromOffset(824,402-gridTop)
                grid.CanvasSize=UDim2.fromOffset(0,math.ceil(#products/3)*152) grid.Parent=body
                local cards={}
                for i,product in products do
                    local x=((i-1)%3)*276 local y=math.floor((i-1)/3)*152
                    local card=box(grid,x,y,264,144,C.card:Lerp(C.purple,.25),24)
                    local iconSize=52+math.min(i,6)*4 -- art grows with pack size
                    art(card,"amber",10+(76-iconSize)/2,8+(76-iconSize)/2,iconSize)
                    label(card,tostring(product.amount),92,6,166,44,32,C.gold)
                    label(card,"Crystals",92,48,166,26,19)
                    local tag=label(card,"",92,74,166,20,15,C.accent) tag.Visible=false
                    local b=button(card,require(Shared.ShopCardState).packButton(nil),8,96,248,44,C.gold:Lerp(C.panel,.35),function() end)
                    b.TextScaled=true b.TextWrapped=false b.Active=false -- BD-430: the price always fits the button, never "..."
                    local fit=Instance.new("UITextSizeConstraint") fit.MaxTextSize,fit.MinTextSize,fit.Parent=22,14,b -- docs/114 s4.4: never under 14 px
                    cards[i]={button=b,tag=tag}
                end
                -- Each card shows its price as soon as it is known; a price that never arrives stays "Price soon".
                local ShopCardState=require(Shared.ShopCardState)
                local prices={}
                local function paint(i,product)
                    local c=cards[i]
                    if not c or not c.button.Parent then return end
                    local price=prices[i]
                    c.button.Text=ShopCardState.packButton(price)
                    if price and Config.CrystalPacksEnabled==true then
                        c.button.Active=true c.button.BackgroundColor3=C.gold:Lerp(C.panel,.1)
                        if not c.wired then c.wired=true c.button.Activated:Connect(function() Marketplace:PromptProductPurchase(player,product.id) end) end
                    end
                end
                local function tags()
                    local baseRate=if prices[1] then products[1].amount/prices[1] else nil
                    for i,product in products do
                        local price=prices[i]
                        if price and baseRate and i>1 and cards[i] then
                            local bonus=math.floor((product.amount/price/baseRate-1)*100+.5)
                            if bonus>=1 then cards[i].tag.Text="+"..bonus.."% extra" cards[i].tag.Visible=true end
                        end
                    end
                end
                for i,product in products do
                    task.spawn(function()
                        local ok,info=pcall(function() return Marketplace:GetProductInfo(product.id,Enum.InfoType.Product) end)
                        if ok and info.IsForSale~=false and typeof(info.PriceInRobux)=="number" then prices[i]=info.PriceInRobux end
                        if grid.Parent then paint(i,product) tags() end
                    end)
                end
            end
            return
        end
        -- BD-393: say whose style this is (the one equipped dino) and where to change it; the cards move down a little.
        require(script.Parent.ShopCards).forHeader({label=label,box=box},body,cardsY-2,str("EquippedSpeciesId","compy"))
        cardsY+=require(Shared.ShopForDino).HeaderHeight
        cardsHeight=if touch then 402-cardsY-targetHeight-12 else require(Shared.ShopForDino).CardsHeightDesktop
        buyY=cardsHeight-targetHeight-10
        local owned=if isTrail then p.trails else p.auras
        local equippedId=if isTrail then p.equippedTrail or "" else p.equippedAura
        for i,item in (if isTrail then ProgressionConfig.Trails else ProgressionConfig.Auras) do
            if isTrail and (i<(trailPage-1)*3+1 or i>trailPage*3) then continue end
            local slot=if isTrail then (i-1)%3 else i-1
            -- BD-142/BD-143: big live previews, rarity chip, words for speed, shared card states (src/client/ShopCards).
            local equipped,locked=equippedId==item.id,isTrail and num("AccountLevel")<item.level and not owned[item.id]
            require(script.Parent.ShopCards).build({label=label,box=box,button=button,art=art},body,{
                kind=if isTrail then "trail" else "aura",item=item,speciesId=str("EquippedSpeciesId","compy"),owned=owned[item.id]==true,equipped=equipped,level=num("AccountLevel"),
                x=slot*276,y=cardsY,height=cardsHeight,buyY=buyY,targetHeight=targetHeight,
                onPress=function()
                    if locked then notify("Requires account level "..item.level,C.gold) return end
                    if owned[item.id] then transact(if isTrail then "equipTrail" else "equipAura",if equipped then "" else item.id)
                    else chosenAura=item.id open("auraConfirm") end
                end})
        end
        local footerY=402-targetHeight
        if isTrail then
            -- BD-334: the arrow that cannot go further is dimmed and inert (page 1 "<", page 4 ">").
            button(body,"<",0,footerY,110,targetHeight,if trailPage<=1 then C.card else C.blue,function() if trailPage<=1 then return end trailPage=math.max(1,trailPage-1) open("auras") end).TextTransparency=if trailPage<=1 then .6 else 0
            button(body,">",714,footerY,110,targetHeight,if trailPage>=4 then C.card else C.blue,function() if trailPage>=4 then return end trailPage=math.min(4,trailPage+1) open("auras") end).TextTransparency=if trailPage>=4 then .6 else 0
        end
        label(body,(if hintInFooter then require(Shared.FtueP1).NoCrystalsHint else "Level "..num("AccountLevel").." • "..num("Crystals").." Crystals")..(if isTrail then " • "..trailPage.." / 4" else ""),115,footerY,590,targetHeight,21,C.gold)
    elseif name=="oddsSimple" then
        -- BD-270: short, kid-readable odds (src/shared/OddsCopy). Every group adds up to 100%.
        local OddsCopy=require(Shared.OddsCopy)
        local upgradeOdds=oddsLevelOverride~=nil
        heading.Text,header.BackgroundColor3=if upgradeOdds then "Upgrade Chances" else "Egg Chances",C.blue
        local groups=if upgradeOdds then OddsCopy.upgradeGroups(oddsLevelOverride :: number) else OddsCopy.eggGroups(progression().conditionLevel or 0,require(Shared.FtueRules).safeEggsLeftView(require(Shared.FtueRules).collectionCopies(decoded("CollectionJson","{}")),num("ActiveChestCount"),num("QueuedEggsWaiting"))) -- BD-365: the safe-eggs line only while true
        local list=Instance.new("ScrollingFrame") list.Name,list.BackgroundTransparency,list.BorderSizePixel,list.Size,list.ScrollBarThickness,list.ZIndex,list.Parent="OddsSimple",1,0,UDim2.fromOffset(824,308),8,24,body
        local lineY=0
        for _,group in groups do
            label(list,group.title,10,lineY,790,34,26,C.gold) lineY+=36
            for _,row in group.rows do
                label(list,row.name,30,lineY,520,30,22).TextXAlignment=Enum.TextXAlignment.Left
                label(list,row.text,560,lineY,220,30,22,C.blue).TextXAlignment=Enum.TextXAlignment.Right
                lineY+=32
            end
            if group.note then label(list,group.note,10,lineY,790,28,OddsCopy.NoteTextSize) lineY+=30 end
            label(list,"Total: 100%",10,lineY,790,26,17,C.gold) lineY+=36
        end
        for _,note in OddsCopy.notes(not upgradeOdds) do label(list,note,10,lineY,790,28,19) lineY+=32 end
        -- BD-606: a line about the secret dino in FREE eggs, only while one can drop
        if not upgradeOdds then for _,note in OddsCopy.freeEggNotes(Config.SecretSpeciesEnabled==true and #require(Shared.SecretSpeciesConfig).readyIds()>0) do label(list,note,10,lineY,790,28,19) lineY+=32 end end
        list.CanvasSize=UDim2.fromOffset(0,lineY)
        button(body,"MORE DETAILS",0,322,402,math.max(64,45/viewportScale()),C.blue,function() open("eggOdds") end).TextSize=20
        button(body,"BACK",422,322,402,math.max(64,45/viewportScale()),C.blue,function() open(if upgradeOdds then "conditionConfirm" else "eggPurchase") end)
    elseif name=="eggOdds" then
        heading.Text,header.BackgroundColor3="Egg Chances",C.blue
        local level=oddsLevelOverride or progression().conditionLevel or 0
        local lines=ShopOdds.lines(level)
        local list=Instance.new("ScrollingFrame") list.Name,list.BackgroundTransparency,list.BorderSizePixel,list.Size,list.CanvasSize,list.ScrollBarThickness,list.ZIndex,list.Parent="EggOdds",1,0,UDim2.fromOffset(824,308),UDim2.fromOffset(0,#lines*46),8,24,body
        local lineY=0
        for _,line in lines do
            local lineHeight=if #line>95 then 88 elseif #line>60 then 66 else 44
            label(list,line,10,lineY,790,lineHeight,21)
            lineY+=lineHeight+2
        end
        list.CanvasSize=UDim2.fromOffset(0,lineY)
        button(body,"All outcomes",0,322,402,math.max(64,45/viewportScale()),C.blue,function() open("eggOutcomes") end).TextSize=20
        button(body,"Back",422,322,402,math.max(64,45/viewportScale()),C.blue,function() open("auras") end)
    elseif name=="eggOutcomes" then
        heading.Text,header.BackgroundColor3="Final Egg Outcomes",C.blue
        EggOutcomeView.add(body,outcomeState,oddsLevelOverride or progression().conditionLevel or 0,
            math.max(64,45/viewportScale()),function() open("eggOutcomes") end,function() open("eggOdds") end)
    elseif name=="eggPurchase" or name=="conditionConfirm" then
        local p=progression()
        local upgrade=ProgressionConfig.ConditionUpgrades[(p.conditionLevel or 0)+1]
        local isEgg=name=="eggPurchase"
        heading.Text,header.BackgroundColor3=if isEgg then "Buy Random Egg?" else "Upgrade Conditions?",C.gold
        local price=if isEgg then ProgressionConfig.RandomEggPrice elseif upgrade then upgrade.price else 0
        local OddsCopy=require(Shared.OddsCopy)
        if isEgg or not upgrade then art(body,"egg",20,15,200)
        else -- BD-303: show the egg whose chance grows most, not a plain egg
            local tile=box(body,20,15,200,175,Color3.fromRGB(122,148,112):Lerp(C.panel,.25),24)
            local view=ModelPreview.add(tile,"egg")
            view:SetAttribute("InspectZoom",1.6)
            EggAppearance.apply(view,EggGenetics.neutral(OddsCopy.biggestGain(upgrade.level-1,upgrade.level)),true)
        end
        label(body,price.." Crystals\nBalance after: "..(num("Crystals")-price),260,10,550,80,27,C.gold)
        label(body,if isEgg then OddsCopy.hatchSentence(p.conditionLevel or 0) else OddsCopy.upgradeUnlock(if upgrade then upgrade.requiredLevel else nil,num("AccountLevel"))..(if upgrade then " Only new eggs get better chances." else ""),260,105,550,95,23)
        if not isEgg and upgrade then
            local parts={} local newOdds=ShopOdds.conditionPercents(upgrade.level) for i,row in ProgressionConfig.Conditions do table.insert(parts,row.name.." "..string.format("%g",newOdds[i]).."%") end
            label(body,table.concat(parts," • "),0,213,824,60,21,C.blue)
        end
        -- BD-270: the odds button sits before every random, crystal-costing action (egg purchase and condition upgrade).
        button(body,"Chances",0,300,250,math.max(64,45/viewportScale()),C.blue,function()
            oddsLevelOverride=if isEgg then nil else (if upgrade then upgrade.level else nil)
            outcomeState={page=1,filters={}} open("oddsSimple")
        end).TextSize=20
        button(body,"CONFIRM",270,300,270,math.max(64,45/viewportScale()),C.accent,function()
            transact(if isEgg then "buyEgg" else "upgradeCondition",if isEgg then "random" elseif upgrade then tostring(upgrade.level) else "") open("auras")
        end)
        button(body,"CANCEL",560,300,264,math.max(64,45/viewportScale()),C.red,function() open("auras") end)
    elseif name=="auraConfirm" then
        local isTrail=cosmeticTab=="trails"
        local item=ProgressionRules.item(if isTrail then ProgressionConfig.Trails else ProgressionConfig.Auras,chosenAura)
        heading.Text,header.BackgroundColor3=if isTrail then "Buy Trail?" else "Buy Aura?",C.purple
        art(body,(if isTrail then "trail_" else "aura_")..item.id,30,25,220)
        label(body,item.name.." • "..(if isTrail then "Cosmetic trail" else (UIFormat.boost("Growth",item.growth) or "Growth")),290,24,510,70,29)
        label(body,item.price.." Crystals\nBalance after purchase: "..(num("Crystals")-item.price),290,125,510,90,25,C.gold)
        button(body,if isTrail then "BUY TRAIL" else "BUY AURA",290,261,510,57,C.accent,function() transact(if isTrail then "buyTrail" else "buyAura",item.id) open("auras") end)
        button(body,"CANCEL",290,337,510,45,C.red,function() open("auras") end)
    elseif name=="potions" then
        heading.Text,header.BackgroundColor3="Potion Shop",C.accent
        local p=progression()
        -- BD-051: server-clock rotation. Offers/stock come from the shared deterministic rules; the server re-checks every purchase.
        local window=ProgressionRules.shopWindow(workspace:GetServerTimeNow())
        potionChoice.window=window
        local restock=label(body,"",0,0,824,32,21,C.gold)
        local function header_text()
            local left=math.max(0,math.ceil(ProgressionRules.shopEndsAt(window)-workspace:GetServerTimeNow()))
            restock.Text=string.format("Crystals: %s  •  New offers in %s",num("Crystals"),UIFormat.duration(left))
        end
        header_text()
        task.spawn(function()
            while restock.Parent and isActive()=="potions" do
                task.wait(1)
                if not restock.Parent or isActive()~="potions" then return end
                if ProgressionRules.shopWindow(workspace:GetServerTimeNow())~=window then
                    notify("Potion shop restocked",C.blue,{key="potion_restock",icon="potion_speed_Common"}) Sfx.play("shop_refresh")
                    body:ClearAllChildren() render("potions") return
                end
                header_text()
            end
        end)
        -- docs/68: 6 offers in a 3x2 grid plus the owned list scroll together, so the panel fits a phone landscape (UIScale) and desktop.
        local scroller=Instance.new("ScrollingFrame")
        scroller.Name="PotionScroll"
        scroller.Position,scroller.Size,scroller.BackgroundTransparency=UDim2.fromOffset(0,34),UDim2.fromOffset(824,368),1
        scroller.BorderSizePixel,scroller.ScrollBarThickness,scroller.ZIndex,scroller.Parent=0,8,body.ZIndex+1,body
        scroller.ScrollingDirection=Enum.ScrollingDirection.Y
        local rarityColor=Theme.RarityColors
        local function bottle(item) return "potion_"..item.kind.."_"..item.rarity end -- native vector bottle (PotionArt): shape = effect, trim/glow/pips = rarity
        for i,offer in ProgressionRules.shopOffers(window) do
            local item=ProgressionRules.item(ProgressionConfig.Potions,offer.id)
            local left=ProgressionRules.shopRemaining(p,window,offer.id)
            local x=((i-1)%3)*276 local y=math.floor((i-1)/3)*140
            local color=rarityColor[item.rarity] or C.accent
            -- BD-267: shared card states (Normal / Sold out): src/shared/ShopCardState + src/client/ShopCard.
            local ShopCardState,ShopCard=require(Shared.ShopCardState),require(script.Parent.ShopCard)
            local look=ShopCardState.look({left=left,buyButton=item.price.." Crystals"},item.price.." Crystals")
            local card=box(scroller,x,y,264,132,ShopCard.cardColor(C.card:Lerp(color,.28),look),24)
            art(card,bottle(item),6,8,64)
            label(card,item.name,74,2,186,24,19,color)
            label(card,UIFormat.potion(item.kind,item.multiplier,item.duration),74,26,186,36,15)
            label(card,if left>0 then left.." left" else look.caption,74,62,186,20,15,ShopCard.captionColor(look))
            local buy=button(card,look.buttonText,8,84,248,44,color:Lerp(C.panel,.45),function() -- docs/114 s4.4: 44 px target
                if left>0 then potionChoice.id=item.id open("potionConfirm") end
            end)
            ShopCard.styleButton(buy,look,color:Lerp(C.panel,.45))
            buy.TextSize=16
        end
        label(scroller,"Rarer potions show up less often.",0,278,824,20,15,C.gold)
        label(scroller,"Your potions (tap to use)",0,298,824,22,18,C.gold)
        local slot=0
        for _,item in ProgressionConfig.Potions do
            local owned=p.potions[item.id] or 0
            if owned>0 then
                local x=(slot%3)*276 local y=322+math.floor(slot/3)*50
                slot+=1
                local useButton=button(scroller,item.name.." x"..owned.."  USE",x,y,264,44,C.purple,function()
                    potionChoice.id=item.id
                    local buff=p.buffs[item.kind]
                    if buff and buff.expiresAt>workspace:GetServerTimeNow() then open("potionReplace") else transact("usePotion",item.id,false) end
                end)
                useButton.TextSize=16
                -- BD-101: the owner's potion icon beside the name (a sibling above the button, so the text keeps its own padding);
                -- no valid image id -> no icon and the button looks exactly as before.
                if require(Shared.PotionArt).icon(scroller,item.id,UDim2.fromOffset(34,34),UDim2.fromOffset(x+5,y+22),useButton.ZIndex+1) then
                    local pad=Instance.new("UIPadding") pad.PaddingLeft=UDim.new(0,40) pad.Parent=useButton
                end
            end
        end
        if slot==0 then label(scroller,"Buy a potion above to use it",0,322,824,32,18) end
        scroller.CanvasSize=UDim2.fromOffset(0,322+math.max(1,math.ceil(slot/3))*50+8)
    elseif name=="potionConfirm" or name=="potionReplace" then
        local item=ProgressionRules.item(ProgressionConfig.Potions,potionChoice.id)
        local replacing=name=="potionReplace"
        heading.Text,header.BackgroundColor3=if replacing then "Replace Active Potion?" else "Buy Potion?",C.accent
        art(body,"potion_"..item.kind.."_"..item.rarity,30,22,220)
        label(body,item.name.." • "..UIFormat.potion(item.kind,item.multiplier,item.duration),290,15,510,62,28)
        label(body,if replacing then "Using this ends your old "..item.kind.." potion" else UIFormat.duration(item.duration).." • "..item.price.." Crystals\nBalance after purchase: "..(num("Crystals")-item.price),290,101,510,135,24,C.gold)
        button(body,if replacing then "Replace" else "BUY POTION",290,263,510,58,C.accent,function()
            if replacing then transact("usePotion",item.id,true) else transact("buyPotion",item.id.."@"..potionChoice.window,false) end
            open("potions")
        end)
        button(body,"CANCEL",290,339,510,44,C.red,function() open("potions") end)
    end
end

return Shop
