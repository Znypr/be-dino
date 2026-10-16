--!strict
-- BD-103: owner-accepted condition looks (docs/39) as TRANSPARENT overlay layers over the shell/pattern.
-- Art is the four 512 RGBA Blender layers (docs/76 upload list). assetId stays "" until the owner uploads and binds
-- it here; never invent IDs. Until bound, a non-art fallback (material/reflectance only) keeps conditions distinct.
local Overlays={}
Overlays.Layers={
    normal={layer="clean",assetId="",material=Enum.Material.SmoothPlastic,reflectance=0},
    cracked={layer="cracked_fractures",assetId="126956807167774",material=Enum.Material.Plastic,reflectance=0,stack=2},
    dirty={layer="dirty_smudges",assetId="105931497056313",material=Enum.Material.Plastic,reflectance=0,stack=2},
    -- BD-226: the Rainbow/Astra art is faint at card size, so its decal is stacked (`stack` copies, same bound asset) and an
    -- Astra egg preview gets a soft cosmic tint (`previewTint`, applied to the ViewportFrame by EggAppearance). No new art.
    rainbow={layer="rainbow_flank_stars",assetId="117352915695915",material=Enum.Material.SmoothPlastic,reflectance=0.08,stack=4},
    astra={layer="astra_opal_streaks",assetId="102255733208943",material=Enum.Material.SmoothPlastic,reflectance=0.15,stack=4,previewTint=Color3.fromRGB(185,170,255)},
}
-- BD-394: zoom of the Conditions shop egg tiles (was 1.6): the marks fill the larger tile, so cracks, smudges, streaks and stars read at card size.
Overlays.ShopZoom=1.85
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
    for _,old in shell:GetChildren() do
        if old:IsA("Decal") and (old.Name=="ConditionOverlay" or old.Name=="ConditionOverlayBoost") then old:Destroy() end
    end
    shell:SetAttribute("ConditionLayer",l.layer)
    if shell:GetAttribute("ConditionOriginalMaterial")==nil then shell:SetAttribute("ConditionOriginalMaterial",shell.Material.Name) end
    shell.Material,shell.Reflectance=l.material,l.reflectance
    if l.assetId~="" and shell:IsA("MeshPart") then
        local decal=Instance.new("Decal")
        decal.Name,decal.Texture,decal.Face="ConditionOverlay","rbxassetid://"..l.assetId,Enum.NormalId.Front
        decal.Transparency,decal.Parent=0,shell
        for _=2,(l :: any).stack or 1 do
            local copy=decal:Clone()
            copy.Name,copy.Parent="ConditionOverlayBoost",shell
        end
    end
end
return Overlays
