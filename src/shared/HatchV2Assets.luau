--!strict
-- BD-397 (docs/114): the 3D meshes of the v2 hatch, published Roblox generate_mesh assets on the owner's account (docs/77).
-- Loaded ONCE by the server (ImportedResources.loadHatchV2, InsertService) into ReplicatedStorage.HatchV2Models only while
-- Config.HatchV2 is true; the client clones them into the hatch viewport. A failed load of the egg makes HatchEggV2 return nil
-- and the shipped v1 sequence runs; a failed bucket load hides the bucket (the paint arc and splash still play). Never invent ids.
local Assets = {}
Assets.FolderName = "HatchV2Models"
Assets.Models = {
    -- Reused: the generated egg already registered as world_gen_food_egg (WorldGeneratedMeshes.food_egg, never placed).
    egg = {assetId = "80664439797104", height = 2.4, note = "generated low-poly egg (docs/77 world_gen_food_egg)"},
    -- PLACEHOLDER stand-in until the paint bucket mesh is generated (docs/114 asset B): the cave hub barrel (CaveHubProps.hub_barrel).
    bucket = {assetId = "81905342774801", height = 1.35, note = "PLACEHOLDER: hub_barrel stands in for the paint bucket"},
}
Assets.Placeholder = {bucket = true}
return Assets
