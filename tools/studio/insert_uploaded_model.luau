--!nocheck
-- Insert an uploaded Roblox model into the Studio showcase place (docs/169, BD-659).
-- NOT game code: lives under tools/studio/, never under src/. Run it through the Studio MCP execute_luau (edit mode).
--
-- How to use: copy this file's text, replace the three __PLACEHOLDERS__ in CFG, run once with DryRun = true (it only
-- prints what it would do), read the output, then run again with DryRun = false.
--
-- Showcase layout (owner rule 2026-10-16, memory studio-showcase-layout): a Folder per design group under Workspace,
-- one row along X with 6-stud gaps, model sitting on the baseplate (lowest point y = 0), a cream sign at x = -14
-- (folder "Design signs") per group. Nothing loose. This script inspects the existing row first and refuses to
-- duplicate a model that is already there.

local CFG = {
	AssetId = __ASSET_ID__, -- number printed by tools/roblox_asset_upload.py (ASSET_ID line)
	Name = "__NAME__", -- species/design name for the model, e.g. "Cockatoosaurus"
	Group = "__GROUP__", -- existing group folder in Workspace, e.g. "Silly secret dinos v3"
	DryRun = true, -- true = print the plan only; false = really insert
	CreateGroup = false, -- true = allowed to create the group folder (then add a sign at x = -14 yourself)
	Replace = false, -- true = delete an existing model with the same Name first
	Gap = 6, -- studs between neighbours in the row
	FallbackRowZ = 150, -- used only for a brand-new group (secret-bird row is z = 150)
	AnchorAll = true, -- showcase models must not fall or drift; the animation module also works anchored
	-- Optional, only if the import came as separate MeshParts WITHOUT Motor6D joints: child part -> parent part.
	-- Example (cockatoo): { Head = "Body", Crest = "Head", Tail = "Body", ArmL = "Body", ArmR = "Body", LegL = "Body", LegR = "Body", FootL = "LegL", FootR = "LegR" }
	Joints = nil,
	-- Optional renames after import, e.g. { ["Mesh"] = "Body" }.
	RenameParts = nil,
}

local InsertService = game:GetService("InsertService")
local out = {}
local function say(...)
	local parts = table.pack(...)
	for i = 1, parts.n do parts[i] = tostring(parts[i]) end
	table.insert(out, table.concat(parts, " "))
end
local function finish()
	print(table.concat(out, "\n"))
end

-- 1) inspect what is already there --------------------------------------------------------------------------
local group = workspace:FindFirstChild(CFG.Group)
if not group then
	if not CFG.CreateGroup then
		say("STOP: no folder '" .. CFG.Group .. "' in Workspace. Top-level folders: ")
		for _, c in ipairs(workspace:GetChildren()) do
			if c:IsA("Folder") then say("  -", c.Name) end
		end
		say("Pick the right group or set CreateGroup = true.")
		return finish()
	end
end
local rowZ, nextMinX = CFG.FallbackRowZ, 0
local existing = {}
if group then
	for _, c in ipairs(group:GetChildren()) do
		if c.Name ~= "Design signs" and (c:IsA("Model") or c:IsA("BasePart")) then
			local cf, size
			if c:IsA("Model") then cf, size = c:GetBoundingBox() else cf, size = c.CFrame, c.Size end
			table.insert(existing, { name = c.Name, x = cf.Position.X, z = cf.Position.Z, maxX = cf.Position.X + size.X / 2 })
		end
	end
	table.sort(existing, function(a, b) return a.x < b.x end)
	if #existing > 0 then
		rowZ = existing[#existing].z
		nextMinX = existing[#existing].maxX + CFG.Gap
	end
end
say("Group:", CFG.Group, "| existing models:", #existing, "| row z =", rowZ, "| next free x (left edge) =", nextMinX)
for _, e in ipairs(existing) do say("  existing:", e.name, "x =", string.format("%.1f", e.x)) end
if group and group:FindFirstChild(CFG.Name) then
	if CFG.Replace then
		say("Replace = true: will delete the existing", CFG.Name)
	else
		say("STOP: '" .. CFG.Name .. "' is already in the group. Set Replace = true to swap it.")
		return finish()
	end
end

-- 2) load the uploaded asset ---------------------------------------------------------------------------------
local ok, loaded = pcall(function() return InsertService:LoadAsset(CFG.AssetId) end)
if not ok then
	say("STOP: LoadAsset failed:", tostring(loaded))
	say("Likely causes: the asset is still in review, belongs to another account than the one logged into Studio, or the id is wrong.")
	return finish()
end
local model
for _, c in ipairs(loaded:GetChildren()) do
	if c:IsA("Model") or c:IsA("BasePart") then model = c break end
end
if not model then
	loaded:Destroy()
	say("STOP: the loaded asset has no Model or part inside.")
	return finish()
end
for _, d in ipairs(loaded:GetDescendants()) do
	if d:IsA("LuaSourceContainer") then
		loaded:Destroy()
		say("STOP: the asset contains a script (" .. d.Name .. "). Models from this pipeline must not. Not inserted.")
		return finish()
	end
end
if model:IsA("BasePart") then -- a single MeshPart: wrap it so the rest of the script has one shape
	local wrapper = Instance.new("Model")
	model.Parent = wrapper
	model = wrapper
end

-- 3) report parts ---------------------------------------------------------------------------------------------
local parts, motors = {}, 0
for _, d in ipairs(model:GetDescendants()) do
	if d:IsA("BasePart") then table.insert(parts, d) end
	if d:IsA("Motor6D") then motors += 1 end
end
if CFG.RenameParts then
	for _, p in ipairs(parts) do
		local new = CFG.RenameParts[p.Name]
		if new then p.Name = new end
	end
end
say("Loaded", #parts, "parts, ", motors, "Motor6D joints.")
for _, p in ipairs(parts) do
	say(string.format("  %s (%s) size %.2f x %.2f x %.2f", p.Name, p.ClassName, p.Size.X, p.Size.Y, p.Size.Z))
end

-- 4) assemble Motor6D joints from part pivots if asked and none exist ----------------------------------------
local byName = {}
for _, p in ipairs(parts) do byName[p.Name] = p end
if CFG.Joints and motors == 0 then
	for childName, parentName in pairs(CFG.Joints) do
		local c, p = byName[childName], byName[parentName]
		if not c or not p then
			say("  joint skipped (missing part):", childName, "->", parentName)
		else
			if not CFG.DryRun then
				local joint = Instance.new("Motor6D")
				local world = c:GetPivot() -- the part's imported pivot is the joint position (Blender origin = joint)
				joint.Name = childName
				joint.Part0 = p
				joint.Part1 = c
				joint.C0 = p.CFrame:Inverse() * world
				joint.C1 = c.CFrame:Inverse() * world
				joint.Parent = c
			end
			say("  joint:", parentName, "->", childName)
		end
	end
elseif CFG.Joints then
	say("  Joints given but the model already has", motors, "Motor6D: left alone.")
end

-- 5) place it in the row --------------------------------------------------------------------------------------
model.Name = CFG.Name
model:SetAttribute("UploadedAssetId", CFG.AssetId)
model:PivotTo(CFrame.new(0, 0, 0)) -- zero rotation so the bounding box is axis aligned (tools/blender_export_roblox.py --faces +Y makes a +Y-facing Blender model face -Z; older exports with forward -Z came in turned 180 degrees)
local bbCF, bbSize = model:GetBoundingBox()
local dx = nextMinX + bbSize.X / 2 - bbCF.Position.X
local dy = bbSize.Y / 2 - bbCF.Position.Y -- lowest point on y = 0
local dz = rowZ - bbCF.Position.Z
local target = Vector3.new(dx, dy, dz)
say(string.format("Model size %.2f x %.2f x %.2f studs -> centre x = %.2f, z = %.2f, lowest y = 0", bbSize.X, bbSize.Y, bbSize.Z, bbCF.Position.X + dx, rowZ))

if CFG.DryRun then
	loaded:Destroy()
	say("DRY RUN: nothing was changed in the place. Set DryRun = false to insert.")
	return finish()
end

if group and CFG.Replace and group:FindFirstChild(CFG.Name) then group[CFG.Name]:Destroy() end
if not group then
	group = Instance.new("Folder")
	group.Name = CFG.Group
	group.Parent = workspace
	say("Created folder", CFG.Group, "- remember the cream sign at x = -14 (folder 'Design signs').")
end
model:PivotTo(CFrame.new(target))
for _, p in ipairs(parts) do
	if CFG.AnchorAll then p.Anchored = true end
end
model.Parent = group
loaded:Destroy()
say("INSERTED", CFG.Name, "into", CFG.Group, "(unsaved until the owner presses Ctrl+S in that Studio window).")
finish()
