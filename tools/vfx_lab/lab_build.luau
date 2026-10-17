--!nocheck
-- VFX lab builder (docs/143). Run in Roblox Studio EDIT mode (command bar / MCP execute_luau); rebuilds the whole lab in the open place:
--   Workspace.VFXLab (ground, walkway, signs, 3 rows x 6 cells, each with a low-poly dino and its fire effect), ReplicatedStorage.VFXLabDriver
--   (ModuleScript, from tools/vfx_lab/lab_driver.luau) and StarterPlayerScripts.VFXLabClient (LocalScript that starts the driver in Play).
-- The driver source is fetched from a local http server (python -m http.server 8766 in tools/vfx_lab). Texture ids are the owner-approved
-- test uploads of resources/effects/vfx-lab/*.png (docs/143 lists them). Nothing here ships in the game.
local HttpService = game:GetService("HttpService")
local InsertService = game:GetService("InsertService")
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local StarterPlayer = game:GetService("StarterPlayer")

local TEX = {
	big = "rbxassetid://108400424399819", -- 2x2 of 512: four bold hero tongues
	swirl = "rbxassetid://140062106480149", -- 2x2 of 512: tongues that lean and curl sideways
	tongue16 = "rbxassetid://137557420303766", -- 4x4 of 256: looping single tongue
	cluster = "rbxassetid://126426640068376", -- 4x4 of 256: looping 3-tongue cluster
	spark = "rbxassetid://128440678279546", -- 4x4 of 128
	puff = "rbxassetid://134899601591965", -- 4x4 of 256, neutral grey-white (tinted warm at runtime)
	streak = "rbxassetid://108862354322703", -- 1024x256 tile strip
	flameStrip = "rbxassetid://102746206435444", -- 1024x256 tile strip
	trail = "rbxassetid://90532892863660", -- 1024x512 thick ribbon
	ring = "rbxassetid://123124022829862", -- 1024 top-down ground ring
	fpL = "rbxassetid://95774401273236",
	fpR = "rbxassetid://136137589357951",
}
local DRIVER_URL = "http://127.0.0.1:8766/lab_driver.luau"
local COMPY, RAPTOR = 94548957808227, 83260397513385
local DINO_H = 5.4 -- studs, standing height of every stand-in

-- ------------------------------------------------------------------------------------------------ cleanup
HttpService.HttpEnabled = true
for _, n in { "VFXLab", "LabRuntime" } do
	local o = workspace:FindFirstChild(n)
	if o then
		o:Destroy()
	end
end
for _, c in workspace:GetChildren() do
	if c ~= workspace.Terrain and c ~= workspace.CurrentCamera and not c:IsA("Camera") and c.Name ~= "VFXLab" then
		c:Destroy()
	end
end
local lab = Instance.new("Folder")
lab.Name = "VFXLab"
lab.Parent = workspace

-- ------------------------------------------------------------------------------------------------ lighting: bright clear daylight
for _, c in Lighting:GetChildren() do
	c:Destroy()
end
Lighting.ClockTime = 12.5
Lighting.Brightness = 2.6
Lighting.Ambient = Color3.fromRGB(120, 125, 135)
Lighting.OutdoorAmbient = Color3.fromRGB(165, 170, 180)
Lighting.ColorShift_Top = Color3.new(0, 0, 0)
Lighting.EnvironmentDiffuseScale = 0.5
Lighting.EnvironmentSpecularScale = 0.3
Lighting.ShadowSoftness = 0.25
Lighting.FogEnd = 100000
Lighting.FogStart = 100000
Lighting.GlobalShadows = true
Instance.new("Sky").Parent = Lighting
pcall(function()
	workspace.Terrain.Decoration = false
end)

-- ------------------------------------------------------------------------------------------------ helpers
local function new(class, props, parent)
	local o = Instance.new(class)
	for k, v in props do
		o[k] = v
	end
	o.Parent = parent
	return o
end

local function ns(points)
	local k = {}
	for _, p in points do
		table.insert(k, NumberSequenceKeypoint.new(p[1], p[2]))
	end
	return NumberSequence.new(k)
end

local function part(parent, name, size, cf, props)
	local p = Instance.new("Part")
	p.Name = name
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.CastShadow = false
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	p.Material = Enum.Material.SmoothPlastic
	p.Size = size
	p.CFrame = cf
	for k, v in props or {} do
		p[k] = v
	end
	p.Parent = parent
	return p
end

-- ------------------------------------------------------------------------------------------------ world
local RZ = { 0, -80, -160 } -- row z
local COLX = {} -- column x
for i = 1, 6 do
	COLX[i] = (i - 1) * 40
end
local ground = part(lab, "Ground", Vector3.new(420, 4, 360), CFrame.new(100, -2, -75), {
	Color = Color3.fromRGB(104, 168, 70),
	Material = Enum.Material.Grass,
	CanCollide = true,
	CanQuery = true,
	CastShadow = true,
})
local pathColor = Color3.fromRGB(226, 214, 180)
for i, rz in RZ do
	part(lab, "Walkway" .. i, Vector3.new(292, 0.3, 7), CFrame.new(100, 0.15, rz + 15), { Color = pathColor, CanCollide = true, CanQuery = true })
end
part(lab, "Spine", Vector3.new(7, 0.3, 190), CFrame.new(-26, 0.15, -75), { Color = pathColor, CanCollide = true, CanQuery = true })
new("SpawnLocation", { Name = "Spawn", Anchored = true, Size = Vector3.new(8, 0.4, 8), CFrame = CFrame.new(-26, 0.5, 28), Neutral = true, Transparency = 0.6, CanCollide = true, Duration = 0 }, lab)

local function sign(parent, name, cf, size, build)
	local board = part(parent, name, size, cf, { Color = Color3.fromRGB(252, 246, 232), CastShadow = false })
	local sg = new("SurfaceGui", {
		Face = Enum.NormalId.Front,
		SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud,
		PixelsPerStud = 40,
		LightInfluence = 0,
		Brightness = 1,
	}, board)
	build(sg, size.X * 40, size.Y * 40)
	return board
end

local function label(parent, text, size, color, pos, sz, font, align)
	return new("TextLabel", {
		BackgroundTransparency = 1,
		Text = text,
		TextColor3 = color,
		TextSize = size,
		Font = font or Enum.Font.GothamBold,
		Position = pos,
		Size = sz,
		TextXAlignment = align or Enum.TextXAlignment.Left,
		TextYAlignment = Enum.TextYAlignment.Center,
		TextWrapped = true,
	}, parent)
end

-- ------------------------------------------------------------------------------------------------ dino stand-in (published low-poly generated models)
local dinoCache = {}
local function loadModel(id)
	if not dinoCache[id] then
		local ok, res = pcall(InsertService.LoadAsset, InsertService, id)
		assert(ok, "LoadAsset failed " .. tostring(res))
		dinoCache[id] = res
	end
	return dinoCache[id]:Clone()
end

local PART_NAMES = { { "left leg", "LegL" }, { "right leg", "LegR" }, { "left arm", "ArmL" }, { "right arm", "ArmR" }, { "tail", "Tail" }, { "head", "Head" }, { "body", "Body" } }
local function makeDino(parent, id, cx, cz)
	local src = loadModel(id)
	local dino = Instance.new("Model")
	dino.Name = "Dino"
	local root = new("Part", { Name = "Root", Anchored = true, CanCollide = false, CanQuery = false, CanTouch = false, Transparency = 1, Size = Vector3.new(0.4, 0.4, 0.4), CFrame = CFrame.new(0, 0, 0) }, dino)
	for _, d in src:GetDescendants() do
		if d:IsA("MeshPart") then
			local lname = d.Name:lower()
			for _, pn in PART_NAMES do
				if lname:find(pn[1], 1, true) then
					d.Name = pn[2]
					break
				end
			end
			d.Anchored, d.CanCollide, d.CanQuery, d.CanTouch, d.CastShadow = true, false, false, false, true
			d.Parent = dino
		end
	end
	src:Destroy()
	dino.PrimaryPart = root
	local _, ext = dino:GetBoundingBox()
	dino:ScaleTo(DINO_H / ext.Y)
	local cf, size = dino:GetBoundingBox()
	local bottom = cf.Position.Y - size.Y / 2 -- root at origin, so this is -H
	local H = -bottom
	root:SetAttribute("H", H)
	root:SetAttribute("TailZ", dino:FindFirstChild("Tail").Position.Z + dino:FindFirstChild("Tail").Size.Z * 0.5)
	local legL, legR = dino:FindFirstChild("LegL"), dino:FindFirstChild("LegR")
	root:SetAttribute("LegHalf", math.abs(legL.Position.X))
	legL:SetAttribute("HipUp", legL.Size.Y * 0.42)
	legR:SetAttribute("HipUp", legR.Size.Y * 0.42)
	dino:PivotTo(CFrame.new(cx, H, cz))
	dino.Parent = parent
	local tail = dino:FindFirstChild("Tail")
	local ctx = {
		H = H,
		tailZ = tail.Position.Z - root.Position.Z + tail.Size.Z * 0.5, -- rear end of the tail, root space (dino faces -Z)
		headTop = 0,
	}
	return dino, root, ctx
end

-- ------------------------------------------------------------------------------------------------ emitters / beams / trails
local function emitter(parent, name, o)
	local e = Instance.new("ParticleEmitter")
	e.Name = name
	e.Texture = o.tex
	e.LightInfluence = 0
	e.LightEmission = o.light or 0
	e.Color = ColorSequence.new(o.color or Color3.new(1, 1, 1))
	e.Rate = o.rate
	e.Lifetime = NumberRange.new(o.life[1], o.life[2] or o.life[1])
	e.Speed = NumberRange.new(o.speed[1], o.speed[2] or o.speed[1])
	e.SpreadAngle = Vector2.new(o.spread or 0, o.spread or 0)
	e.Size = o.size
	e.Transparency = o.tr
	e.Acceleration = o.acc or Vector3.zero
	e.Drag = o.drag or 0
	e.Rotation = o.rot or NumberRange.new(0)
	e.RotSpeed = o.rotspeed or NumberRange.new(0)
	e.EmissionDirection = o.dir or Enum.NormalId.Top
	e.ZOffset = o.z or 0
	e.Orientation = Enum.ParticleOrientation.FacingCamera
	e.LockedToPart = o.locked or false
	if o.grid then
		e.FlipbookLayout = o.grid
		e.FlipbookMode = o.mode or Enum.ParticleFlipbookMode.Random
		e.FlipbookFramerate = NumberRange.new(o.fps or 12)
		e.FlipbookStartRandom = o.startRandom or false
	end
	e.Parent = parent
	return e
end

local G2, G4 = Enum.ParticleFlipbookLayout.Grid2x2, Enum.ParticleFlipbookLayout.Grid4x4
local FADE = ns({ { 0, 1 }, { 0.12, 0.08 }, { 0.7, 0.28 }, { 1, 1 } })

-- big bold tongues (2x2 sheet, random design per particle)
local function tongues(parent, name, tex, rate, s, extra)
	local o = {
		tex = tex, grid = G2, mode = Enum.ParticleFlipbookMode.Random, rate = rate, light = 0.12,
		life = { 0.85, 1.15 }, speed = { 0.3, 0.7 }, spread = 8,
		size = ns({ { 0, 0.3 * s }, { 0.22, s }, { 0.75, 0.9 * s }, { 1, 0.35 * s } }), tr = FADE,
		acc = Vector3.new(0, 1.2, 0), rot = NumberRange.new(-8, 8),
	}
	for k, v in extra or {} do
		o[k] = v
	end
	return emitter(parent, name, o)
end

local function sparks(parent, name, rate, s, extra)
	local o = {
		tex = TEX.spark, grid = G4, mode = Enum.ParticleFlipbookMode.Random, rate = rate, light = 0.6,
		life = { 0.7, 1.3 }, speed = { 1.5, 3.2 }, spread = 60,
		size = ns({ { 0, 0.5 * s }, { 0.3, s }, { 1, 0 } }), tr = ns({ { 0, 0.1 }, { 0.7, 0.2 }, { 1, 1 } }),
		acc = Vector3.new(0, 2.5, 0), rot = NumberRange.new(0, 360), rotspeed = NumberRange.new(-60, 60),
	}
	for k, v in extra or {} do
		o[k] = v
	end
	return emitter(parent, name, o)
end

local WARM = Color3.fromRGB(255, 176, 104)
local DUST = Color3.fromRGB(214, 184, 140)
local function puffs(parent, name, rate, s, color, extra)
	local o = {
		tex = TEX.puff, grid = G4, mode = Enum.ParticleFlipbookMode.Random, rate = rate, light = 0,
		life = { 1.0, 1.5 }, speed = { 0.4, 0.9 }, spread = 25,
		size = ns({ { 0, 0.5 * s }, { 0.4, s }, { 1, 1.35 * s } }), tr = ns({ { 0, 1 }, { 0.15, 0.5 }, { 0.6, 0.65 }, { 1, 1 } }),
		color = color or WARM, acc = Vector3.new(0, 0.6, 0), rot = NumberRange.new(0, 360), rotspeed = NumberRange.new(-20, 20),
	}
	for k, v in extra or {} do
		o[k] = v
	end
	return emitter(parent, name, o)
end

local function beam(parent, a0, a1, o)
	local b = Instance.new("Beam")
	b.Attachment0, b.Attachment1 = a0, a1
	b.Texture = o.tex
	b.TextureMode = Enum.TextureMode.Wrap
	b.TextureLength = o.len or 4
	b.TextureSpeed = o.speed or -0.8
	b.Width0, b.Width1 = o.w0 or 1.2, o.w1 or o.w0 or 1.2
	b.FaceCamera = true
	b.LightEmission = o.light or 0.15
	b.LightInfluence = 0
	b.Segments = o.segs or 12
	b.CurveSize0, b.CurveSize1 = o.c0 or 0, o.c1 or 0
	b.Transparency = o.tr or ns({ { 0, 0.05 }, { 0.5, 0.08 }, { 1, 0.05 } })
	b.Color = ColorSequence.new(o.color or Color3.new(1, 1, 1))
	b.Parent = parent
	return b
end

local function trail(parent, a0, a1, o)
	local t = Instance.new("Trail")
	t.Attachment0, t.Attachment1 = a0, a1
	t.Texture = o.tex
	t.TextureMode = Enum.TextureMode.Stretch
	t.Lifetime = o.life or 0.6
	t.MinLength = 0.1
	t.FaceCamera = o.face or false
	t.LightEmission = o.light or 0.15
	t.LightInfluence = 0
	t.Transparency = o.tr or ns({ { 0, 0 }, { 0.55, 0.12 }, { 1, 1 } })
	t.WidthScale = o.width or ns({ { 0, 1 }, { 1, 1 } })
	t.Color = ColorSequence.new(o.color or Color3.new(1, 1, 1))
	t.Parent = parent
	return t
end

-- helper parts the driver moves
local function helper(fx, name, rig, attrs)
	local p = part(fx, name, Vector3.new(0.4, 0.4, 0.4), CFrame.new(0, 3, 0), { Transparency = 1 })
	p:SetAttribute("Rig", rig)
	for k, v in attrs or {} do
		p:SetAttribute(k, v)
	end
	return p
end

local function orbit(fx, name, R, W, Y, Ph)
	local p = helper(fx, name, "Orbit", { R = R, W = W, Y = Y, Ph = Ph })
	new("Attachment", { Name = "A" }, p)
	return p
end

local function groundDecal(fx, name, diameter, tex, W, y, color)
	local p = helper(fx, name, "Spin", { W = W, Off = CFrame.new(0, y, 0) })
	p.Size = Vector3.new(diameter, 0.1, diameter)
	new("Decal", { Face = Enum.NormalId.Top, Texture = tex, Color3 = color or Color3.new(1, 1, 1), Transparency = 0 }, p)
	return p
end

local function cagePanels(fx, count, R, h, tex, W)
	for i = 1, count do
		local a = (i - 1) / count * math.pi * 2
		local p = helper(fx, "Panel" .. i, "Spin", { W = W, Off = CFrame.new(math.sin(a) * R, h / 2 + 0.1, math.cos(a) * R) * CFrame.Angles(0, a, 0) })
		p.Size = Vector3.new(h * 0.8, h, 0.1)
		for _, face in { Enum.NormalId.Front, Enum.NormalId.Back } do
			local sg = new("SurfaceGui", { Face = face, LightInfluence = 0, SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud, PixelsPerStud = 60 }, p)
			new("ImageLabel", {
				BackgroundTransparency = 1, Size = UDim2.fromScale(1, 1), Image = tex, ImageRectSize = Vector2.new(256, 256),
				ImageRectOffset = Vector2.new(((i - 1) % 4) * 256, 0), ImageTransparency = 0.05,
			}, sg)
		end
	end
end

-- ------------------------------------------------------------------------------------------------ cost scan for the signs
local function cost(containers, extra)
	local c = { emit = 0, live = 0, beams = 0, trails = 0, parts = 0, lights = 0, guis = 0, decals = 0 }
	for _, cont in containers do
		for _, d in cont:GetDescendants() do
			if d:IsA("ParticleEmitter") and d.Enabled then
				c.emit += 1
				c.live += d.Rate * (d.Lifetime.Min + d.Lifetime.Max) / 2
			elseif d:IsA("Beam") then
				c.beams += 1
			elseif d:IsA("Trail") then
				c.trails += 1
			elseif d:IsA("Light") then
				c.lights += 1
			elseif d:IsA("SurfaceGui") or d:IsA("BillboardGui") then
				c.guis += 1
			elseif d:IsA("Decal") or d:IsA("Texture") then
				c.decals += 1
			elseif d:IsA("BasePart") and d.Name ~= "Root" and d.Parent and d.Parent.Name ~= "Dino" then
				c.parts += 1
			end
		end
	end
	for k, v in extra or {} do
		c[k] = (c[k] or 0) + v
	end
	return c
end

local function costText(c)
	local bits = {}
	local function add(n, word)
		if n > 0 then
			table.insert(bits, n .. " " .. word)
		end
	end
	add(c.emit, "emitters (about " .. math.floor(c.live + 0.5) .. " live sprites)")
	add(c.beams, "beams")
	add(c.trails, "trails")
	add(c.parts, "parts")
	add(c.decals, "decals")
	add(c.guis, "gui planes")
	add(c.lights, "lights")
	if #bits == 0 then
		return "nothing extra"
	end
	return table.concat(bits, ", ")
end

local ROWCOL = { Color3.fromRGB(240, 110, 40), Color3.fromRGB(226, 160, 20), Color3.fromRGB(220, 60, 50) }
local PHONECOL = { SAFE = Color3.fromRGB(60, 160, 90), OK = Color3.fromRGB(214, 160, 30), HEAVY = Color3.fromRGB(205, 70, 55) }

local function cellSign(cellFolder, row, cx, cz, id, title, uses, c, phone, note)
	local accent = ROWCOL[row]
	sign(cellFolder, "Sign", CFrame.new(cx, 12.5, cz - 13) * CFrame.Angles(0, math.pi, 0), Vector3.new(26, 11, 0.5), function(sg, w, h)
		local bar = new("Frame", { BackgroundColor3 = accent, Size = UDim2.new(1, 0, 0, 104), BorderSizePixel = 0 }, sg)
		label(bar, id, 64, Color3.new(1, 1, 1), UDim2.new(0, 28, 0, 0), UDim2.new(0, 150, 1, 0), Enum.Font.GothamBlack)
		label(bar, title, 54, Color3.new(1, 1, 1), UDim2.new(0, 170, 0, 0), UDim2.new(1, -190, 1, 0), Enum.Font.GothamBlack)
		label(sg, "Uses: " .. uses, 34, Color3.fromRGB(40, 40, 52), UDim2.new(0, 28, 0, 116), UDim2.new(1, -56, 0, 100), Enum.Font.GothamMedium)
		label(sg, "Cost: " .. costText(c), 34, Color3.fromRGB(40, 40, 52), UDim2.new(0, 28, 0, 214), UDim2.new(1, -56, 0, 100), Enum.Font.GothamBold)
		local pill = new("Frame", { BackgroundColor3 = PHONECOL[phone], Position = UDim2.new(0, 28, 0, 330), Size = UDim2.new(0, 250, 0, 70) }, sg)
		new("UICorner", { CornerRadius = UDim.new(0, 18) }, pill)
		label(pill, "PHONE: " .. phone, 32, Color3.new(1, 1, 1), UDim2.new(0, 0, 0, 0), UDim2.new(1, 0, 1, 0), Enum.Font.GothamBlack, Enum.TextXAlignment.Center)
		label(sg, note, 30, Color3.fromRGB(60, 60, 72), UDim2.new(0, 300, 0, 322), UDim2.new(1, -330, 0, 90), Enum.Font.GothamMedium)
	end)
	-- two posts
	for _, dx in { -11, 11 } do
		part(cellFolder, "Post", Vector3.new(0.8, 12, 0.8), CFrame.new(cx + dx, 6, cz - 13.4), { Color = Color3.fromRGB(120, 90, 60) })
	end
end

-- ------------------------------------------------------------------------------------------------ cells
local cells = {}
local function defCell(row, col, id, title, dinoId, mode, uses, phone, note, build, attrs, extra)
	local cx, cz = COLX[col], RZ[row]
	local folder = Instance.new("Folder")
	folder.Name = id .. "_" .. title:gsub("[^%w]+", "")
	folder:SetAttribute("CX", cx)
	folder:SetAttribute("CZ", cz)
	folder:SetAttribute("Mode", mode)
	if mode == "run" then
		folder:SetAttribute("Half", 12)
		folder:SetAttribute("Speed", 13)
	end
	for k, v in attrs or {} do
		folder:SetAttribute(k, v)
	end
	folder.Parent = lab
	local dino, root, dctx = makeDino(folder, dinoId, cx, cz)
	local fx = Instance.new("Folder")
	fx.Name = "Fx"
	fx.Parent = folder
	local ctx = { folder = folder, fx = fx, root = root, dino = dino, H = dctx.H, tailZ = dctx.tailZ, cx = cx, cz = cz }
	function ctx.att(name, pos)
		return new("Attachment", { Name = name, Position = pos }, root)
	end
	build(ctx)
	local ex = extra and extra() or nil
	local c = cost({ fx, root }, ex)
	cellSign(folder, row, cx, cz, id, title, uses, c, phone, note)
	table.insert(cells, { id = id, title = title, cost = c, phone = phone, uses = uses })
end

local H0 = 2.7 -- approx hip height used for attachment placement only (the real H is read per dino)

-- ===================== ROW 1: AURAS (dino stands still) ====================================================================
-- A1 HERO: ground ring + big sideways-swirling tongues + swirl beams + warm puffs + sparks + glow
defCell(1, 1, "A1", "HERO: layered", COMPY, "idle",
	"Ring decal x2 + 4 orbiting tongue emitters (hero + swirl sheets, 512 px frames) + 6 beam swirls + warm puffs + sparks + light",
	"HEAVY", "No-limits match of the reference. Phone: use only the ring + 2 tongue emitters (see A6).",
	function(c)
		groundDecal(c.fx, "RingBig", 11.5, TEX.ring, 0.5, 0.08)
		groundDecal(c.fx, "RingInner", 8, TEX.ring, -0.9, 0.09, Color3.fromRGB(255, 240, 200))
		for i = 1, 4 do
			local sheet = if i % 2 == 1 then TEX.big else TEX.swirl
			local p = orbit(c.fx, "TongueOrbit" .. i, 3.7, (if i % 2 == 1 then 1 else -1) * 1.5, 1.9, (i - 1) * math.pi / 2)
			tongues(p.A, "Tongues", sheet, 3, 4.0, { rot = NumberRange.new(-14, 14) })
		end
		for ring = 1, 2 do
			local pts = {}
			for i = 1, 3 do
				pts[i] = orbit(c.fx, "BeamPt" .. ring .. "_" .. i, if ring == 1 then 3.5 else 3.0, if ring == 1 then 1.1 else -0.9, if ring == 1 then 1.3 else 3.3, (i - 1) * math.pi * 2 / 3)
			end
			for i = 1, 3 do
				local R = if ring == 1 then 3.5 else 3.0
				beam(c.fx, pts[i].A, pts[i % 3 + 1].A, { tex = TEX.streak, w0 = 1.5, len = 6, speed = if ring == 1 then -0.5 else 0.5, c0 = 0.77 * R, c1 = 0.77 * R, segs = 14 })
			end
		end
		for i = 1, 2 do
			local p = orbit(c.fx, "PuffOrbit" .. i, 3.9, 0.9 * (if i == 1 then 1 else -1), 0.9, i * math.pi)
			puffs(p.A, "Puffs", 2.4, 3.4, WARM)
		end
		sparks(c.att("SparkRoot", Vector3.new(0, -0.5, 0)), "Sparks", 9, 0.8, { spread = 180, speed = { 1.5, 3.5 } })
		local la = c.att("Glow", Vector3.new(0, 0, 0))
		new("PointLight", { Color = Color3.fromRGB(255, 150, 70), Brightness = 2, Range = 16, Shadows = false }, la)
	end)

-- A2 particles only (a): tongues from 3 orbiters + puffs + sparks; no beams, no parts besides invisible emitters carriers
defCell(1, 2, "A2", "Tongue particles", COMPY, "idle",
	"ParticleEmitters only: 3 orbiting tongue emitters (hero sheet, swirl sheet), warm puffs, sparks. No beams, no decals",
	"OK", "Best readable-per-cost for the tongues; ring needs a decal (A6).",
	function(c)
		for i = 1, 3 do
			local p = orbit(c.fx, "TongueOrbit" .. i, 3.7, (if i == 2 then -1.4 else 1.4), 1.9, (i - 1) * math.pi * 2 / 3)
			tongues(p.A, "Tongues", if i == 2 then TEX.swirl else TEX.big, 3.6, 4.0, { rot = NumberRange.new(-14, 14) })
		end
		local p = orbit(c.fx, "PuffOrbit", 3.8, 0.9, 0.9, 0)
		puffs(p.A, "Puffs", 3, 3.4, WARM)
		sparks(c.att("SparkRoot", Vector3.new(0, -0.5, 0)), "Sparks", 8, 0.8, { spread = 180 })
	end)

-- A3 beams (b)
defCell(1, 3, "A3", "Beam swirls", COMPY, "idle",
	"Beams with the scrolling streak strip: 2 rings x 3 beams curving around the body, fire-coloured texture, no particles except sparks",
	"OK", "Reads as swirling streaks, not as flames. Good as a second layer on top of tongues.",
	function(c)
		for ring = 1, 2 do
			local R = if ring == 1 then 3.4 else 2.9
			local pts = {}
			for i = 1, 3 do
				pts[i] = orbit(c.fx, "BeamPt" .. ring .. "_" .. i, R, if ring == 1 then 1.2 else -1.0, if ring == 1 then 1.2 else 3.2, (i - 1) * math.pi * 2 / 3)
			end
			for i = 1, 3 do
				beam(c.fx, pts[i].A, pts[i % 3 + 1].A, { tex = TEX.streak, w0 = 1.7, len = 6.8, speed = if ring == 1 then -0.6 else 0.6, c0 = 0.77 * R, c1 = 0.77 * R, segs = 14 })
			end
		end
		sparks(c.att("SparkRoot", Vector3.new(0, -0.5, 0)), "Sparks", 6, 0.8, { spread = 180 })
	end)

-- A4 orbiting trails (c)
defCell(1, 4, "A4", "Orbit trails", COMPY, "idle",
	"3 Trail objects on orbiting anchors (flame strip texture) leave a rising ribbon swirl; sparks",
	"OK", "Cheap swirl feel; the ribbon is thin and plain. Trails are the cheapest 3D swirl.",
	function(c)
		for i = 1, 3 do
			local p = orbit(c.fx, "TrailOrbit" .. i, 3.2, 2.0 * (if i == 2 then -1 else 1), 0.9 + (i - 1) * 1.4, (i - 1) * 2.1)
			local a0 = new("Attachment", { Name = "T0", Position = Vector3.new(0, 0.75, 0) }, p)
			local a1 = new("Attachment", { Name = "T1", Position = Vector3.new(0, -0.75, 0) }, p)
			trail(c.fx, a0, a1, { tex = TEX.flameStrip, life = 1.1, tr = ns({ { 0, 0.05 }, { 0.6, 0.2 }, { 1, 1 } }) })
		end
		sparks(c.att("SparkRoot", Vector3.new(0, -0.5, 0)), "Sparks", 6, 0.8, { spread = 180 })
	end)

-- A5 mesh-ish parts (d): ring decals + 8 flame cage panels rotating
defCell(1, 5, "A5", "Ring + flame cage", COMPY, "idle",
	"Spinning ground-ring decal + 8 spinning panels (SurfaceGui flame crops, both faces) = a flame cage, no particles",
	"OK", "Strong silhouette for few parts, but panels look flat from above; SurfaceGuis cost more than decals.",
	function(c)
		groundDecal(c.fx, "RingBig", 11.5, TEX.ring, 0.5, 0.08)
		cagePanels(c.fx, 8, 3.3, 4.4, TEX.flameStrip, 0.7)
	end)

-- A6 cheap phone-safe
defCell(1, 6, "A6", "Cheap phone-safe", COMPY, "idle",
	"One ring decal + 2 orbiting tongue emitters (low rate) + a few sparks",
	"SAFE", "The version to ship on phones: about 25 live sprites, 0 beams, 1 decal.",
	function(c)
		groundDecal(c.fx, "RingBig", 10, TEX.ring, 0.5, 0.08)
		for i = 1, 2 do
			local p = orbit(c.fx, "TongueOrbit" .. i, 3.7, 1.5, 1.9, (i - 1) * math.pi)
			tongues(p.A, "Tongues", if i == 1 then TEX.big else TEX.swirl, 2.6, 4.0, { rot = NumberRange.new(-14, 14) })
		end
		sparks(c.att("SparkRoot", Vector3.new(0, -0.5, 0)), "Sparks", 4, 0.8, { spread = 180 })
	end)

-- ===================== ROW 2: TRAILS (dino runs back and forth) ===============================================================
-- helper: thick ribbon trail on the tail (y spans lower..upper of the root)
local function thickTrail(c, up, down, life, tex, tint, widthSeq)
	local z = c.tailZ - 0.2
	local a0 = c.att("TrailTop" .. tostring(math.random(1e6)), Vector3.new(0, up, z))
	local a1 = c.att("TrailBot" .. tostring(math.random(1e6)), Vector3.new(0, down, z))
	return trail(c.fx, a0, a1, { tex = tex, life = life, color = tint, width = widthSeq })
end

local function dustFeet(c, rate, s)
	local a = c.att("Dust" .. tostring(math.random(1e6)), Vector3.new(0, -c.H + 0.3, 0.6))
	return puffs(a, "Dust", rate, s, DUST, { life = { 0.7, 1.1 }, speed = { 1, 2 }, spread = 40, tr = ns({ { 0, 1 }, { 0.15, 0.4 }, { 1, 1 } }), acc = Vector3.new(0, 0.5, 0) })
end

defCell(2, 1, "T1", "HERO: thick ribbon", COMPY, "run",
	"Thick 2.8-stud Trail with the ribbon texture + 2 follower beams + tongue particles shed from the tail + tan dust + sparks",
	"HEAVY", "No-limits match of the reference. Phone: ribbon + dust only (T2).",
	function(c)
		thickTrail(c, 1.3, -1.5, 0.6, TEX.trail)
		for i = 1, 2 do
			local fol = helper(c.fx, "Follow" .. i, "Follow", { K = 5 - i, Off = CFrame.new(0, 0.7 - (i - 1) * 1.5, c.tailZ + 2.6) })
			local a1 = new("Attachment", { Name = "F" }, fol)
			local a0 = c.att("BeamTail" .. i, Vector3.new(0, 0.7 - (i - 1) * 1.5, c.tailZ - 0.2))
			beam(c.fx, a0, a1, { tex = TEX.streak, w0 = 1.0, w1 = 0.3, len = 5, speed = -2.2 })
		end
		local a = c.att("TongueShed", Vector3.new(0, 0.2, c.tailZ + 0.2))
		tongues(a, "Tongues", TEX.swirl, 11, 3.8, { speed = { 0, 0.3 }, life = { 0.5, 0.75 }, spread = 4 })
		dustFeet(c, 9, 2.2)
		sparks(c.att("SparkTail", Vector3.new(0, 0.2, c.tailZ)), "Sparks", 14, 0.7, { speed = { 1, 2.4 } })
	end)

defCell(2, 2, "T2", "Thick ribbon (cheap)", COMPY, "run",
	"One thick 2.8-stud Trail (ribbon texture) + tan dust puffs. Nothing else",
	"SAFE", "Best value: one Trail object reads as a fire streak. About 12 live sprites.",
	function(c)
		thickTrail(c, 1.3, -1.5, 0.55, TEX.trail)
		dustFeet(c, 7, 2.0)
	end)

defCell(2, 3, "T3", "Tongue particles", COMPY, "run",
	"ParticleEmitter flame tongues (hero + swirl sheets) left behind in world space + dust; no Trail objects",
	"OK", "Reads as flames, bumpy edge; flames stay where emitted so a turn leaves a nice burning patch.",
	function(c)
		local a = c.att("TongueShed", Vector3.new(0, 0.2, c.tailZ + 0.2))
		tongues(a, "Tongues", TEX.swirl, 14, 4.2, { speed = { 0, 0.2 }, life = { 0.6, 0.85 }, spread = 2 })
		local b = c.att("TongueShed2", Vector3.new(0, 0.5, c.tailZ + 0.4))
		tongues(b, "Tongues2", TEX.big, 8, 3.6, { speed = { 0, 0.2 }, life = { 0.5, 0.7 } })
		dustFeet(c, 7, 2.0)
	end)

defCell(2, 4, "T4", "Follower beams", COMPY, "run",
	"3 Beams from the tail to lagging follower parts, scrolling streak texture; sparks",
	"OK", "Gives a flowing, bending streak; texture is thin lines, not flames.",
	function(c)
		for i = 1, 3 do
			local y = 1.0 - (i - 1) * 1.0
			local fol = helper(c.fx, "Follow" .. i, "Follow", { K = 6 - i, Off = CFrame.new(0, y, c.tailZ + 3.2) })
			local a1 = new("Attachment", { Name = "F" }, fol)
			local a0 = c.att("BeamTail" .. i, Vector3.new(0, y, c.tailZ - 0.2))
			beam(c.fx, a0, a1, { tex = TEX.streak, w0 = 1.3, w1 = 0.5, len = 5.2, speed = -2.0 })
		end
		sparks(c.att("SparkTail", Vector3.new(0, 0.2, c.tailZ)), "Sparks", 8, 0.7, { speed = { 1, 2.2 } })
	end)

defCell(2, 5, "T5", "Stacked trails", COMPY, "run",
	"3 Trail objects stacked: thick ribbon, wide streak strip, small flame strip; no particles",
	"OK", "Layers add depth; 3 trails per dino is the practical phone cap.",
	function(c)
		thickTrail(c, 1.2, -1.4, 0.55, TEX.trail)
		thickTrail(c, 2.2, 0.2, 0.7, TEX.streak, Color3.fromRGB(255, 214, 140), ns({ { 0, 1 }, { 1, 0.4 } }))
		thickTrail(c, 0.2, -1.9, 0.45, TEX.flameStrip)
	end)

defCell(2, 6, "T6", "Billboard flames", COMPY, "run",
	"Pool of 16 BillboardGui flame sprites, flipbook animated by script from the 4x4 cluster sheet; spawned along the path",
	"HEAVY", "Looks good (full-frame flipbook) but GUI planes cost more than particles; use only a few.",
	function(c)
		c.folder:SetAttribute("TrailStamp", "billboard")
		dustFeet(c, 7, 2.0)
	end, nil, function()
		return { guis = 16, parts = 16 }
	end)

-- ===================== ROW 3: FOOTPRINTS (dino runs back and forth) ============================================================
local function footExtra(mode)
	return function()
		local ex = { parts = 10, decals = 10 }
		if mode == "embers" or mode == "hero" then
			ex.emit = (ex.emit or 0) + 10
			ex.live = (ex.live or 0) + 14
		end
		if mode == "cluster" or mode == "hero" then
			ex.emit = (ex.emit or 0) + 10
			ex.live = (ex.live or 0) + 6
		end
		if mode == "hero" then
			ex.emit = ex.emit + 10
			ex.live = ex.live + 4
		end
		if mode == "scorch" or mode == "hero" then
			ex.parts += 10
		end
		if mode == "light" or mode == "hero" then
			ex.lights = 10
		end
		return ex
	end
end

local FOOTATTR = { Stamp = 3.4 }
local function footAttrs(mode)
	return { Foot = mode, Stamp = 3.4 }
end

defCell(3, 1, "F1", "HERO: fire prints", COMPY, "run",
	"Pooled print decals (10) cooling yellow to red + scorch pads + flame cluster flipbook + embers + smoke + a short light per print",
	"HEAVY", "Matches the reference. Pools: 10 prints; the light and the smoke are the costly layers.",
	function(c)
		dustFeet(c, 4, 1.6)
	end, footAttrs("hero"), footExtra("hero"))

defCell(3, 2, "F2", "Decal only (cheap)", COMPY, "run",
	"10 pooled Part+Decal prints that fade; nothing else",
	"SAFE", "Cheapest readable footprint: 10 decals, 0 particles. Reads as a glowing stamp.",
	function(c) end, footAttrs("decal"), footExtra("decal"))

defCell(3, 3, "F3", "Decal + embers", COMPY, "run",
	"Decal prints + a 5-spark ember burst per step from a pooled emitter",
	"OK", "Embers add life for little cost (a burst of 5 sprites per step).",
	function(c) end, footAttrs("embers"), footExtra("embers"))

defCell(3, 4, "F4", "Print + scorch pad", COMPY, "run",
	"Decal prints (cooling colour) over a dark scorch pad part that fades slower",
	"SAFE", "Dark pad makes the glow pop on bright grass; extra part per print.",
	function(c) end, footAttrs("scorch"), footExtra("scorch"))

defCell(3, 5, "F5", "Flame cluster", COMPY, "run",
	"Decal prints + a small looping flame-cluster flipbook (4x4 sheet) planted on each print",
	"OK", "Burning prints: one flipbook sprite per print, 6 live at a time.",
	function(c) end, footAttrs("cluster"), footExtra("cluster"))

defCell(3, 6, "F6", "Print + glow light", COMPY, "run",
	"Decal prints + a PointLight per print that fades with it (10 lights pooled)",
	"HEAVY", "Looks warm on the ground but dynamic lights are the likeliest phone frame cliff.",
	function(c) end, footAttrs("light"), footExtra("light"))

-- ------------------------------------------------------------------------------------------------ headers and welcome
local ROWNAMES = { "AURAS: fire ring around the dino", "TRAILS: flames behind a running dino", "FOOTPRINTS: glowing fire steps" }
for i, rz in RZ do
	sign(lab, "Header" .. i, CFrame.new(-40, 11, rz + 4) * CFrame.Angles(0, math.pi * 0.85, 0), Vector3.new(30, 10, 0.5), function(sg, w, h)
		new("Frame", { BackgroundColor3 = ROWCOL[i], Size = UDim2.fromScale(1, 1), BorderSizePixel = 0 }, sg)
		label(sg, "ROW " .. i, 70, Color3.new(1, 1, 1), UDim2.new(0, 40, 0, 40), UDim2.new(1, -80, 0, 100), Enum.Font.GothamBlack)
		label(sg, ROWNAMES[i], 92, Color3.new(1, 1, 1), UDim2.new(0, 40, 0, 150), UDim2.new(1, -80, 0, 260), Enum.Font.GothamBlack)
	end)
	part(lab, "HeaderPost" .. i, Vector3.new(1, 11, 1), CFrame.new(-40, 5.5, rz + 4.3), { Color = Color3.fromRGB(120, 90, 60) })
end
sign(lab, "Welcome", CFrame.new(-26, 8, 34) * CFrame.Angles(0, math.pi, 0), Vector3.new(24, 9, 0.5), function(sg, w, h)
	new("Frame", { BackgroundColor3 = Color3.fromRGB(46, 58, 80), Size = UDim2.fromScale(1, 1), BorderSizePixel = 0 }, sg)
	label(sg, "FIRE VFX LAB", 90, Color3.fromRGB(255, 190, 80), UDim2.new(0, 40, 0, 20), UDim2.new(1, -80, 0, 120), Enum.Font.GothamBlack)
	label(sg, "Walk the front path of each row. Row 1 auras, row 2 trails, row 3 footprints. Column 1 is the no-limits HERO, the others are alternatives. Signs say what each uses and what it costs on a phone.", 36, Color3.new(1, 1, 1), UDim2.new(0, 40, 0, 150), UDim2.new(1, -80, 0, 200), Enum.Font.GothamMedium)
end)
part(lab, "WelcomePost", Vector3.new(1, 8, 1), CFrame.new(-26, 4, 34.3), { Color = Color3.fromRGB(120, 90, 60) })

-- ------------------------------------------------------------------------------------------------ driver + client script
for _, n in { "VFXLabDriver" } do
	local o = ReplicatedStorage:FindFirstChild(n)
	if o then
		o:Destroy()
	end
end
local driver = Instance.new("ModuleScript")
driver.Name = "VFXLabDriver"
driver.Source = HttpService:GetAsync(DRIVER_URL, true)
driver.Parent = ReplicatedStorage
local sps = StarterPlayer:WaitForChild("StarterPlayerScripts")
local old = sps:FindFirstChild("VFXLabClient")
if old then
	old:Destroy()
end
local cs = Instance.new("LocalScript")
cs.Name = "VFXLabClient"
cs.Source = [[
local Driver = require(game:GetService("ReplicatedStorage"):WaitForChild("VFXLabDriver"))
Driver.start(workspace:WaitForChild("VFXLab"))
]]
cs.Parent = sps

local out = {}
for _, c in cells do
	table.insert(out, string.format("%s %s | %s | emit %d live %d beams %d trails %d parts %d decals %d guis %d lights %d", c.id, c.title, c.phone, c.cost.emit, c.cost.live, c.cost.beams, c.cost.trails, c.cost.parts, c.cost.decals, c.cost.guis, c.cost.lights))
end
return out
