--!strict
-- Authored egg masks on creature UVs; eyes/mouth are fixed pixels, never tinted.
local Assets=game:GetService("AssetService")
local Http=game:GetService("HttpService")
local Genetics=require(script.Parent.EggGenetics)
local Pattern={}
local images=setmetatable({},{__mode="k"})
local activeImages=0
function Pattern.apply(part: MeshPart,genes): boolean
    local folder=script.Parent:FindFirstChild("CreatureGenes")
    local source=if folder then folder:FindFirstChild(part:GetAttribute("GeneSpecies") or "") else nil
    local data=if source then Http:JSONDecode(require(source)) else require(script.Parent.LegacyGenePatterns).data(part)
    if not data then return false end
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
    local image=images[part]
    if not image then
        if activeImages>=32 or not part.Parent then return false end
        local ok,result=pcall(function() return Assets:CreateEditableImage({Size=Vector2.new(size,size)}) end)
        if not ok or not result then return false end
        image=result;images[part]=image;activeImages+=1
        part.Destroying:Once(function() image:Destroy();images[part]=nil;activeImages-=1 end)
    end
    image:WritePixelsBuffer(Vector2.zero,Vector2.new(size,size),pixels)
    for _,child in part:GetChildren() do if child:IsA("SurfaceAppearance") then child:Destroy() end end
    part.Color=Color3.new(1,1,1);part.TextureContent=Content.fromObject(image)
    return true
end
return Pattern
