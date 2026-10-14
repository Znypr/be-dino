--!strict
-- BD-103: owner-accepted condition looks (docs/39) as TRANSPARENT overlay layers over the shell/pattern.
-- Art is the four 512 RGBA Blender layers (docs/76 upload list). assetId stays "" until the owner uploads and binds
-- it here; never invent IDs. Until bound, a non-art fallback (material/reflectance only) keeps conditions distinct.
local Overlays={}
Overlays.Layers={
    normal={layer="clean",assetId="",material=Enum.Material.SmoothPlastic,reflectance=0},
    cracked={layer="cracked_fractures",assetId="",material=Enum.Material.Plastic,reflectance=0},
    dirty={layer="dirty_smudges",assetId="",material=Enum.Material.Plastic,reflectance=0},
    rainbow={layer="rainbow_flank_stars",assetId="",material=Enum.Material.SmoothPlastic,reflectance=0.08},
    astra={layer="astra_opal_streaks",assetId="",material=Enum.Material.SmoothPlastic,reflectance=0.15},
}
function Overlays.describe(conditionId: string?)
    local layer=Overlays.Layers[conditionId or "normal"] or Overlays.Layers.normal
    return layer
end
function Overlays.signature(conditionId: string?): string
    local l=Overlays.describe(conditionId)
    return l.layer..":"..(if l.assetId~="" then l.assetId else "fallback")..":"..tostring(l.material)..":"..l.reflectance
end
function Overlays.apply(shell: BasePart,conditionId: string?)
    local l=Overlays.describe(conditionId)
    local old=shell:FindFirstChild("ConditionOverlay")
    if old then old:Destroy() end
    shell:SetAttribute("ConditionLayer",l.layer)
    if shell:GetAttribute("ConditionOriginalMaterial")==nil then shell:SetAttribute("ConditionOriginalMaterial",shell.Material.Name) end
    shell.Material,shell.Reflectance=l.material,l.reflectance
    if l.assetId~="" and shell:IsA("MeshPart") then
        local decal=Instance.new("Decal")
        decal.Name,decal.Texture,decal.Face="ConditionOverlay","rbxassetid://"..l.assetId,Enum.NormalId.Front
        decal.Transparency,decal.Parent=0,shell
    end
end
return Overlays
