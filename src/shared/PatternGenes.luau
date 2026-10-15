--!strict
-- Authored egg masks on creature UVs; eyes/mouth are fixed pixels, never tinted.
local Assets=game:GetService("AssetService")
local Http=game:GetService("HttpService")
local Genetics=require(script.Parent.EggGenetics)
local Pattern={}
-- BD-pattern-atlas: patterns share ONE EditableImage per (texture owner, genes) via PatternAtlasCache (reference
-- counted, warm LRU, hard cap 30 of Roblox's ~32). A legacy dino has 7 parts, so ~4 DIFFERENT patterned legacy
-- dinos (or ~30 authored ones) fit at once; identical genes are free. When the cap is hit, or a part is far away
-- (cheap LOD), the part shows a FLAT matte colour mixed from its genes instead, and a maintenance loop upgrades
-- the nearest flat parts as slots free up. A dino is never blank, textureless-cube or the wrong colours.
local Cache=require(script.Parent.PatternAtlasCache)
local atlas=Cache.new(30,function(image) image:Destroy() end)
local partEntry=setmetatable({},{__mode="k"})
local tracked=setmetatable({},{__mode="k"}) -- part -> genes, for every part we paint (textured or flat)
local FAR=160 -- studs: beyond this, world parts use the flat LOD
local function publish()
    local ok=pcall(function()
        local s=atlas:stats()
        workspace:SetAttribute("PatternImagesLive",s.live);workspace:SetAttribute("PatternImagesPinned",s.pinned)
        workspace:SetAttribute("PatternCacheHits",s.hits);workspace:SetAttribute("PatternCacheMisses",s.misses)
        workspace:SetAttribute("PatternCacheEvictions",s.evictions);workspace:SetAttribute("PatternCacheDenied",s.denied)
    end)
    return ok
end
local function release(part)
    local entry=partEntry[part]
    if not entry then return end
    partEntry[part]=nil
    atlas:release(entry)
end
function Pattern.stats() return atlas:stats() end
-- Flat colour: primary/secondary mixed by blend; the pattern's overall tone without needing a texture.
local function flatColor(genes): Color3
    local a,b=Genetics.color(genes.primaryColorId).rgb,Genetics.color(genes.secondaryColorId).rgb
    local t=if genes.primaryColorId==genes.secondaryColorId then 0 else math.clamp((genes.blend or 50)/100,0,1)
    return Color3.fromRGB(a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t,a[3]+(b[3]-a[3])*t)
end
local function flat(part: MeshPart,genes)
    release(part)
    for _,child in part:GetChildren() do if child:IsA("SurfaceAppearance") then child:Destroy() end end
    part.TextureContent=Content.none;part.TextureID=""
    part.Color=flatColor(genes)
    part:SetAttribute("PatternLOD","flat")
    publish()
end
local function wantFlat(part: MeshPart): boolean
    local camera=workspace.CurrentCamera
    if not camera or not part:IsDescendantOf(workspace) then return false end -- previews/viewports are always near
    return (camera.CFrame.Position-part.Position).Magnitude>FAR
end
local function show(part: MeshPart,entry)
    release(part)
    partEntry[part]=entry
    part.Destroying:Once(function() release(part) end)
    for _,child in part:GetChildren() do if child:IsA("SurfaceAppearance") then child:Destroy() end end
    part.Color=Color3.new(1,1,1);part.TextureContent=Content.fromObject(entry.image)
    part:SetAttribute("PatternLOD","texture")
end
local decoded={}
local function dataFor(part: MeshPart)
    local folder=script.Parent:FindFirstChild("CreatureGenes")
    local source=if folder then folder:FindFirstChild(part:GetAttribute("GeneSpecies") or "") else nil
    local data=nil
    if source then
        data=decoded[source]
        if not data then data=Http:JSONDecode(require(source));decoded[source]=data end
    else data=require(script.Parent.LegacyGenePatterns).data(part) end
    return data,source
end
-- All-or-nothing per model: a dino is fully textured or fully flat, never half and half.
local function groupOf(part: MeshPart): Instance
    return part:FindFirstAncestorOfClass("Model") or part
end
local function groupParts(group: Instance): {MeshPart}
    if group:IsA("MeshPart") then return {group :: MeshPart} end
    local list={}
    for _,d in group:GetDescendants() do
        if d:IsA("MeshPart") and (d:GetAttribute("GeneSpecies") or d:GetAttribute("GeneOriginalTexture") or d.TextureID~="" or tracked[d]) then table.insert(list,d) end
    end
    return list
end
local groupFlat=setmetatable({},{__mode="k"}) -- group -> true while the whole model is on the flat LOD
local function paint(part: MeshPart,genes): boolean
    local data,source=dataFor(part)
    if not data then return false end
    local owner=if source then part:GetAttribute("GeneSpecies") else part:GetAttribute("GeneOriginalTexture") -- legacy: one texture per part
    if not owner then return false end
    local sharedKey=tostring(owner).."|"..tostring(genes.patternId).."|"..tostring(genes.primaryColorId).."|"..tostring(genes.secondaryColorId).."|"..tostring(genes.blend)
    local current=partEntry[part]
    if current and current.key==sharedKey then return true end
    local entry=atlas:acquire(sharedKey)
    if entry then show(part,entry);publish();return true end
    local group=groupOf(part)
    if groupFlat[group]==nil then -- first uncached part of this model decides for all of its parts
        local need=#groupParts(group)
        if need>atlas:free() then groupFlat[group]=true;atlas.denied+=1 else groupFlat[group]=false end
    end
    if not part.Parent or groupFlat[group] then flat(part,genes);return false end
    local mask=data.patterns[genes.patternId or "01_blank"] or data.patterns["01_blank"]
    local size=data.size
    local histogram=table.create(254,0);local count=0
    for i=1,#mask,2 do
        local rank=tonumber(string.sub(mask,i,i+1),16)
        if rank<254 then histogram[rank+1]+=1;count+=1 end
    end
    local same=genes.primaryColorId==genes.secondaryColorId
    local target=math.floor(count*(if same then .5 else genes.blend/100))
    local threshold=253;local cumulative=0
    for rank=0,253 do
        if cumulative+histogram[rank+1]>=target then threshold=rank;break end
        cumulative+=histogram[rank+1]
    end
    local remainder=target-cumulative;local tied=0
    local a,b=Genetics.color(genes.primaryColorId).rgb,Genetics.color(genes.secondaryColorId).rgb
    -- Same-family genes still show lighter and darker pattern regions.
    local pixels=buffer.create(size*size*4)
    for p=0,size*size-1 do
        local rank=tonumber(string.sub(mask,p*2+1,p*2+2),16)
        local primary=rank<threshold or (rank==threshold and tied<remainder)
        if rank==threshold then tied+=1 end
        local rgb=if primary then a else b
        for channel=1,3 do
            local value=rgb[channel]
            if data.shading then value*=math.max(.28,data.shading[p+1]/255) end
            if same then value=math.clamp(value*(if primary then .8 else 1.08)+(if not primary then 12 else 0),0,255) end
            if rank==254 then value=tonumber(string.sub(data.fixedRGB,p*6+(channel-1)*2+1,p*6+(channel-1)*2+2),16) end
            buffer.writeu8(pixels,p*4+channel-1,math.floor(value+.5))
        end
        buffer.writeu8(pixels,p*4+3,255)
    end
    if not atlas:reserve() then flat(part,genes);return false end
    local ok,result=pcall(function() return Assets:CreateEditableImage({Size=Vector2.new(size,size)}) end)
    if not ok or not result then flat(part,genes);return false end
    result:WritePixelsBuffer(Vector2.zero,Vector2.new(size,size),pixels)
    show(part,atlas:insert(sharedKey,result))
    publish()
    return true
end
function Pattern.apply(part: MeshPart,genes): boolean
    tracked[part]=genes
    if wantFlat(part) then
        if not dataFor(part) then return false end -- not a pattern part: leave untouched
        flat(part,genes);return false
    end
    return paint(part,genes)
end
-- Maintenance (client only): drop far parts to flat, then give the nearest flat parts a texture as slots free up.
local function maintain()
    local camera=workspace.CurrentCamera
    if not camera then return end
    local flats={}
    for part,genes in tracked do
        if not part.Parent then tracked[part]=nil continue end
        local far=wantFlat(part)
        local lod=part:GetAttribute("PatternLOD")
        if far and lod=="texture" then flat(part,genes);groupFlat[groupOf(part)]=nil
        elseif not far and lod=="flat" then
            local d=if part:IsDescendantOf(workspace) then (camera.CFrame.Position-part.Position).Magnitude else 0
            table.insert(flats,{part=part,genes=genes,d=d})
        end
    end
    table.sort(flats,function(x,y) return x.d<y.d end)
    local done={}
    for _,f in flats do
        local group=groupOf(f.part)
        if done[group] then continue end
        done[group]=true
        local parts=groupParts(group)
        if #parts<=atlas:free() then
            groupFlat[group]=false
            for _,p in parts do
                local genes=tracked[p]
                if genes and p:GetAttribute("PatternLOD")=="flat" and not wantFlat(p) then paint(p,genes) end
            end
        end
    end
    publish()
end
if game:GetService("RunService"):IsClient() then
    task.spawn(function() while true do task.wait(1.5);pcall(maintain) end end)
end
return Pattern
