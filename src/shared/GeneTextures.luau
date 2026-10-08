--!strict
-- Authored neutral texture per original asset, not live images per dinosaur/color.
local Bindings=require(script.Parent.GeneTextureAssets)
local Textures={}
function Textures.neutralPixels(pixels,width,height)
    local w,h=math.min(512,width),math.min(512,height)
    local output=buffer.create(w*h*4)
    for y=0,h-1 do
        for x=0,w-1 do
            local source=(math.floor(y*height/h)*width+math.floor(x*width/w))*4
            local target=(y*w+x)*4
            local value=math.max(buffer.readu8(pixels,source),buffer.readu8(pixels,source+1),buffer.readu8(pixels,source+2))
            buffer.writeu8(output,target,value) buffer.writeu8(output,target+1,value) buffer.writeu8(output,target+2,value)
            buffer.writeu8(output,target+3,buffer.readu8(pixels,source+3))
        end
    end
    return output,w,h
end
function Textures.apply(part: MeshPart)
    local id=part:GetAttribute("GeneOriginalTexture")
    if id==nil then id=part.TextureID part:SetAttribute("GeneOriginalTexture",id) end
    if id=="" or part:FindFirstChildOfClass("SurfaceAppearance") then return end
    if part:GetAttribute("GeneTextureState")~=nil then return end
    local asset=Bindings[string.match(id,"%d+") or ""]
    local resources=game:GetService("ReplicatedStorage"):FindFirstChild("Resources")
    local templates=if resources then resources:FindFirstChild("GeneSurfaces") else nil
    local template=if templates then templates:FindFirstChild(string.match(id,"%d+") or "") else nil
    if asset and asset~="" and template and template:IsA("SurfaceAppearance") then
        -- Legacy TextureID ignores MeshPart.Color; PBR Color tints the neutral map.
        local surface=template:Clone()
        surface.Name="GeneSurface"
        surface.Color=part.Color
        surface.Parent=part
        part.TextureID=""
        part:SetAttribute("GeneTextureState","Applied")
        task.spawn(function()
            local image=Instance.new("ImageLabel")
            image.Image="rbxassetid://"..asset
            local failed=false
            local ok=pcall(function()
                game:GetService("ContentProvider"):PreloadAsync({image},function(_,status)
                    if status~=Enum.AssetFetchStatus.Success then failed=true end
                end)
            end)
            image:Destroy()
            if part.Parent and (not ok or failed) then surface:Destroy() part.TextureID=id part:SetAttribute("GeneTextureState","Unavailable") end
        end)
    else part:SetAttribute("GeneTextureState","Unavailable") end
end
return Textures
