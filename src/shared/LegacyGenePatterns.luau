--!strict
-- Shared authored egg patterns on the six earlier uploaded species' UV maps.
local Assets=game:GetService("AssetService")
local Http=game:GetService("HttpService")
local Bindings=require(script.Parent.GeneTextureAssets)
local Legacy={}
local cache={}
function Legacy.data(part: MeshPart)
    local id=part:GetAttribute("GeneOriginalTexture") or part.TextureID
    local asset=Bindings[string.match(id,"%d+") or ""]
    if not asset then return nil end
    part:SetAttribute("GeneOriginalTexture",id)
    if cache[asset]~=nil then return cache[asset] or nil end
    local ok,result=pcall(function()
        local source=Assets:CreateEditableImageAsync(Content.fromUri("rbxassetid://"..asset))
        assert(source,"Neutral texture unavailable")
        local size=source.Size
        local raw=source:ReadPixelsBuffer(Vector2.zero,size);source:Destroy()
        local masks=Http:JSONDecode(require(script.Parent.CreatureGenes.egg))
        local rgb={};local values={}
        for y=0,127 do for x=0,127 do
            local offset=(math.floor(y*size.Y/128)*size.X+math.floor(x*size.X/128))*4
            local p=y*128+x+1
            local value=buffer.readu8(raw,offset);values[p]=value
            table.insert(rgb,string.format("%02x%02x%02x",value,value,value))
        end end
        local patterns={}
        for name,mask in masks.patterns do
            local parts={}
            for p,value in values do table.insert(parts,if value<38 then "fe" else string.sub(mask,(p-1)*2+1,p*2)) end
            patterns[name]=table.concat(parts)
        end
        return {size=128,patterns=patterns,fixedRGB=table.concat(rgb),shading=values}
    end)
    cache[asset]=if ok then result else false
    return if ok then result else nil
end
return Legacy
