--!strict
local Genetics=require(script.Parent.EggGenetics)
local Textures=require(script.Parent.GeneTextures)
local Appearance={}
local Patterns=require(script.Parent.PatternGenes)
local Overlays=require(script.Parent.ConditionOverlays)
-- BD-174: the egg condition (Cracked, Dirty, Rainbow, Astra) belongs to EGG visuals only. Dinosaur models get colours and pattern
-- but never the condition overlay or material. Callers that draw an egg pass showCondition = true.
function Appearance.apply(container: Instance,genes,showCondition: boolean?)
    if not genes or not Genetics.valid(genes) then return end
    local tint=Genetics.tint(genes)
    -- BD-216: the 2D egg picture fallback (ModelPreview.eggImage) takes the tint and the condition layer like EggPicture.
    if container:GetAttribute("EggImageFallback")==true then
        local shell2d=container:FindFirstChild("EggShell")
        if shell2d and shell2d:IsA("ImageLabel") then shell2d.ImageColor3=tint end
        local layer=container:FindFirstChild("EggCondition")
        if layer and layer:IsA("ImageLabel") then
            local look=Overlays.describe(genes.conditionId)
            local id=if showCondition==true and look.assetId~="" then "rbxassetid://"..look.assetId else ""
            layer.Image,layer.Visible=id,id~=""
        end
        return
    end
    local shell,shellSize=nil,-1
    for _,part in container:GetDescendants() do
        if part:IsA("BasePart") then
            local volume=part.Size.X*part.Size.Y*part.Size.Z
            if volume>shellSize then shell,shellSize=part,volume end
            if part:IsA("MeshPart") and Patterns.apply(part,genes) then continue end
            local original=part:GetAttribute("GeneOriginalColor")
            if typeof(original)~="Color3" then original=part.Color part:SetAttribute("GeneOriginalColor",original) end
            -- Preserve texture detail and geometry; SurfaceAppearance needs its own tint.
            local brightness=math.max(original.R,original.G,original.B)
            part.Color=if part:IsA("MeshPart") then tint else Color3.new(tint.R*brightness,tint.G*brightness,tint.B*brightness)
            if part:IsA("MeshPart") then Textures.apply(part) end
            for _,surface in part:GetChildren() do
                if surface:IsA("SurfaceAppearance") then surface.Color=tint end
            end
        end
    end
    if shell and showCondition==true then Overlays.apply(shell,genes.conditionId) end
end
return Appearance
