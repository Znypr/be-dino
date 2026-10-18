-- BD-1068: turn Decal asset ids (what tools/roblox_asset_upload.py returns for a .png) into IMAGE ids.
-- A Decal id used as an ImageLabel image fails with "Asset type does not match requested type". The Decal's own Texture
-- property holds the real image id. Paste into Studio (execute_luau, Edit datamodel), edit DECAL_IDS, read the printed lines,
-- then bind them: python tools/bind_assets.py ids.txt  (name=rbxassetid://IMAGEID).
local DECAL_IDS = {
    -- name = decalId,
    class_ground = 134254487145276,
}
local InsertService = game:GetService("InsertService")
local out = {}
for name, id in DECAL_IDS do
    local ok, model = pcall(function() return InsertService:LoadAsset(id) end)
    if not ok then
        table.insert(out, name .. " FAILED: " .. tostring(model))
    else
        local decal = model:FindFirstChildWhichIsA("Decal", true)
        table.insert(out, name .. "=" .. (decal and decal.Texture or "NO DECAL FOUND"))
        model:Destroy()
    end
end
return table.concat(out, "\n")
