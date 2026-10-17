--!nocheck
-- VFX lab runtime driver (docs/143). A ModuleScript placed in ReplicatedStorage.VFXLabDriver by tools/vfx_lab/lab_build.luau.
-- Runs on the CLIENT (a LocalScript calls Driver.start(workspace.VFXLab)); in Studio edit mode it can be started from the command
-- bar too. Every dino and effect part is ANCHORED and moved by CFrame here, so trails, beams and emitters follow exactly like they
-- would on a real moving dino. Cell folders carry attributes (Mode, Half, Speed, CX, CZ, Foot, Stamp) written by the builder.
local RunService = game:GetService("RunService")

local Driver = {}

local TEX = {
	fpL = "rbxassetid://95774401273236",
	fpR = "rbxassetid://136137589357951",
	cluster = "rbxassetid://126426640068376",
	tongue = "rbxassetid://137557420303766",
	spark = "rbxassetid://128440678279546",
	puff = "rbxassetid://134899601591965",
}

local function ns(points)
	local k = {}
	for _, p in points do
		table.insert(k, NumberSequenceKeypoint.new(p[1], p[2]))
	end
	return NumberSequence.new(k)
end

local function lerp(a, b, t)
	return a + (b - a) * t
end

local function smooth(t)
	t = math.clamp(t, 0, 1)
	return t * t * (3 - 2 * t)
end

-- ----------------------------------------------------------------------------------------------- footprint / stamp pools
local function newEmitter(parent, tex, o)
	local e = Instance.new("ParticleEmitter")
	e.Texture = tex
	e.Rate = 0
	e.Enabled = false
	e.LightInfluence = 0
	e.LightEmission = o.light or 0
	e.Lifetime = NumberRange.new(o.life[1], o.life[2] or o.life[1])
	e.Speed = NumberRange.new(o.speed[1], o.speed[2] or o.speed[1])
	e.SpreadAngle = Vector2.new(o.spread or 0, o.spread or 0)
	e.Size = o.size
	e.Transparency = o.tr
	e.Acceleration = o.acc or Vector3.zero
	e.Color = ColorSequence.new(o.color or Color3.new(1, 1, 1))
	e.Rotation = o.rot or NumberRange.new(0)
	if o.grid then
		e.FlipbookLayout = Enum.ParticleFlipbookLayout.Grid4x4
		e.FlipbookMode = o.mode or Enum.ParticleFlipbookMode.Loop
		e.FlipbookFramerate = NumberRange.new(o.fps or 16)
	end
	e.Parent = parent
	return e
end

local function makeStampPool(cell, runtime, mode, count)
	local pool = {}
	for i = 1, count do
		local p = Instance.new("Part")
		p.Name = "Print"
		p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.CastShadow = true, false, false, false, false
		p.Transparency = 1
		p.Size = Vector3.new(3.1, 0.1, 3.1)
		p.CFrame = CFrame.new(0, -50, 0)
		local d = Instance.new("Decal")
		d.Face = Enum.NormalId.Top
		d.Texture = TEX.fpL
		d.Transparency = 1
		d.Parent = p
		p.Parent = runtime
		local item = { part = p, decal = d, age = 99, life = 1.8 }
		local at = Instance.new("Attachment")
		at.Position = Vector3.new(0, 0.2, 0)
		at.Parent = p
		if mode == "embers" or mode == "hero" then
			item.embers = newEmitter(at, TEX.spark, {
				grid = true, mode = Enum.ParticleFlipbookMode.Random, light = 0.5, life = { 0.7, 1.3 }, speed = { 1.5, 3 }, spread = 40,
				size = ns({ { 0, 0.5 }, { 0.3, 0.7 }, { 1, 0 } }), tr = ns({ { 0, 0 }, { 0.7, 0.2 }, { 1, 1 } }), acc = Vector3.new(0, 3, 0),
			})
		end
		if mode == "cluster" or mode == "hero" then
			item.flame = newEmitter(at, TEX.cluster, {
				grid = true, fps = 16, light = 0.1, life = { 0.9, 1.0 }, speed = { 0, 0 }, size = ns({ { 0, 1.2 }, { 0.2, 3.2 }, { 1, 2.0 } }),
				tr = ns({ { 0, 1 }, { 0.1, 0.05 }, { 0.65, 0.25 }, { 1, 1 } }),
			})
			at.Position = Vector3.new(0, 1.2, 0)
		end
		if mode == "hero" then
			item.smoke = newEmitter(at, TEX.puff, {
				grid = true, mode = Enum.ParticleFlipbookMode.Random, light = 0, life = { 1.0, 1.4 }, speed = { 0.4, 0.8 }, spread = 25,
				size = ns({ { 0, 0.8 }, { 1, 2.4 } }), tr = ns({ { 0, 1 }, { 0.15, 0.55 }, { 1, 1 } }), color = Color3.fromRGB(255, 190, 130),
				acc = Vector3.new(0, 0.8, 0),
			})
		end
		if mode == "scorch" or mode == "hero" then
			local s = Instance.new("Part")
			s.Name = "Scorch"
			s.Shape = Enum.PartType.Cylinder
			s.Anchored, s.CanCollide, s.CanQuery, s.CanTouch, s.CastShadow = true, false, false, false, false
			s.Material = Enum.Material.SmoothPlastic
			s.Color = Color3.fromRGB(46, 30, 22)
			s.Size = Vector3.new(0.06, 2.5, 2.2)
			s.Transparency = 1
			s.Parent = runtime
			item.scorch = s
		end
		if mode == "light" or mode == "hero" then
			local l = Instance.new("PointLight")
			l.Color = Color3.fromRGB(255, 150, 60)
			l.Range = 9
			l.Brightness = 0
			l.Shadows = false
			l.Parent = at
			item.light = l
		end
		table.insert(pool, item)
	end
	return pool
end

local function stampAt(pool, pos, yaw, side, mode)
	-- reuse the oldest item
	local best, bestAge = pool[1], -1
	for _, it in pool do
		if it.age > bestAge then
			best, bestAge = it, it.age
		end
	end
	best.age = 0
	best.part.CFrame = CFrame.new(pos.X, 0.07, pos.Z) * CFrame.Angles(0, yaw, 0)
	best.decal.Texture = if side > 0 then TEX.fpR else TEX.fpL
	if best.scorch then
		best.scorch.CFrame = CFrame.new(pos.X, 0.05, pos.Z) * CFrame.Angles(0, yaw, math.pi / 2)
	end
	if best.embers then
		best.embers:Emit(5)
	end
	if best.flame then
		best.flame:Emit(1)
	end
	if best.smoke then
		best.smoke:Emit(1)
	end
end

local function updatePool(pool, dt)
	for _, it in pool do
		it.age += dt
		local f = it.age / it.life
		if f >= 1 then
			it.decal.Transparency = 1
			if it.scorch then
				it.scorch.Transparency = 1
			end
			if it.light then
				it.light.Brightness = 0
			end
		else
			-- cooling: bright yellow-white, then orange-red, then dark and gone
			local c
			if f < 0.35 then
				c = Color3.fromRGB(255, 255, 255):Lerp(Color3.fromRGB(255, 170, 90), f / 0.35)
			else
				c = Color3.fromRGB(255, 170, 90):Lerp(Color3.fromRGB(110, 45, 35), (f - 0.35) / 0.65)
			end
			it.decal.Color3 = c
			it.decal.Transparency = if f < 0.45 then 0 else smooth((f - 0.45) / 0.55) * 1.0
			if it.scorch then
				it.scorch.Transparency = lerp(0.35, 1, smooth(f))
			end
			if it.light then
				it.light.Brightness = 1.6 * (1 - f) * (1 - f)
			end
		end
	end
end

-- Billboard flipbook stamps (T5): a pool of BillboardGuis, each plays the 16-frame cluster sheet once while rising and fading.
local function makeBillboards(runtime, count)
	local pool = {}
	for i = 1, count do
		local p = Instance.new("Part")
		p.Name = "BB"
		p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.CastShadow = true, false, false, false, false
		p.Transparency = 1
		p.Size = Vector3.one * 0.2
		p.CFrame = CFrame.new(0, -50, 0)
		local g = Instance.new("BillboardGui")
		g.Size = UDim2.new(3.6, 0, 3.6, 0)
		g.LightInfluence = 0
		g.AlwaysOnTop = false
		g.Adornee = p
		local img = Instance.new("ImageLabel")
		img.BackgroundTransparency = 1
		img.Size = UDim2.fromScale(1, 1)
		img.Image = TEX.cluster
		img.ImageRectSize = Vector2.new(256, 256)
		img.Parent = g
		g.Parent = p
		p.Parent = runtime
		table.insert(pool, { part = p, img = img, age = 99, life = 0.85, base = Vector3.zero })
	end
	return pool
end

local function updateBillboards(pool, dt)
	for _, it in pool do
		it.age += dt
		local f = it.age / it.life
		if f >= 1 then
			it.img.ImageTransparency = 1
		else
			local frame = math.min(15, math.floor(f * 16))
			it.img.ImageRectOffset = Vector2.new((frame % 4) * 256, (frame // 4) * 256)
			it.img.ImageTransparency = if f < 0.12 then lerp(1, 0.05, f / 0.12) else lerp(0.05, 1, smooth((f - 0.45) / 0.55))
			it.part.CFrame = CFrame.new(it.base + Vector3.new(0, f * 0.9, 0))
		end
	end
end

-- ----------------------------------------------------------------------------------------------- one cell
local function setupCell(cell, runtime)
	local dino = cell:FindFirstChild("Dino")
	local root = dino and dino:FindFirstChild("Root")
	if not root then
		return nil
	end
	local H = root:GetAttribute("H") or 1.7
	local S = root:GetAttribute("S") or 0.7
	local cx, cz = cell:GetAttribute("CX"), cell:GetAttribute("CZ")
	local run = cell:GetAttribute("Mode") == "run"
	local half = cell:GetAttribute("Half") or 12
	local speed = cell:GetAttribute("Speed") or 13
	local footMode = cell:GetAttribute("Foot")
	local trailMode = cell:GetAttribute("TrailStamp")
	local stampEvery = cell:GetAttribute("Stamp") or 3.4

	local rootRest = root.CFrame
	local rest = {}
	for _, part in dino:GetChildren() do
		if part:IsA("BasePart") and part ~= root then
			rest[part] = rootRest:ToObjectSpace(part.CFrame)
		end
	end
	local legs = {
		{ leg = dino:FindFirstChild("LegL"), foot = dino:FindFirstChild("FootL"), sign = 1 },
		{ leg = dino:FindFirstChild("LegR"), foot = dino:FindFirstChild("FootR"), sign = -1 },
	}
	local armL, armR = dino:FindFirstChild("ArmL"), dino:FindFirstChild("ArmR")
	local legHalf = root:GetAttribute("LegHalf") or 0.9
	local footRel = {}
	for _, l in legs do
		if l.leg and l.foot then
			footRel[l.foot] = rest[l.leg]:ToObjectSpace(rest[l.foot])
		end
	end
	local tail = dino:FindFirstChild("Tail")

	local fx = cell:FindFirstChild("Fx")
	local rigs = {}
	if fx then
		for _, d in fx:GetDescendants() do
			if d:IsA("BasePart") and d:GetAttribute("Rig") then
				table.insert(rigs, d)
				d:SetAttribute("_pos", d.Position)
			end
		end
	end

	local pool, bbs
	if footMode then
		pool = makeStampPool(cell, runtime, footMode, 10)
	end
	if trailMode == "billboard" then
		bbs = makeBillboards(runtime, 16)
	end

	local st = { x = -half, f = 0, turning = false, turnT = 0, moveBlend = 1, phase = 0, dist = 0, side = 1, bbAcc = 0, t0 = math.random() * 10 }
	local dirFlag = 1 -- +1 walking toward +x, -1 toward -x
	st.dir = 1

	local function yawFor(f)
		return -math.pi / 2 - math.pi * f
	end

	local function rootCFrame(t)
		if not run then
			local bob = math.sin(t * 1.6) * 0.04
			return CFrame.new(cx, H + bob, cz) * CFrame.Angles(0, math.pi - 0.62, 0), 0, 1
		end
		return nil
	end

	local function update(dt, t)
		local rcf
		local legA, move = 0, 0
		if run then
			if st.turning then
				st.turnT += dt
				local k = smooth(st.turnT / 0.85)
				-- f runs 0 -> 1 when turning from +x to -x, and 1 -> 0 coming back
				st.f = if st.dir == 1 then k else 1 - k
				if st.turnT >= 0.85 then
					st.turning = false
					st.f = if st.dir == 1 then 1 else 0
					st.dir = -st.dir
				end
				st.moveBlend = math.max(0, st.moveBlend - dt * 5)
			else
				st.moveBlend = math.min(1, st.moveBlend + dt * 3)
				st.x += (if st.dir == 1 then 1 else -1) * speed * st.moveBlend * dt
				if st.dir == 1 and st.x >= half then
					st.x, st.turning, st.turnT = half, true, 0
				elseif st.dir == -1 and st.x <= -half then
					st.x, st.turning, st.turnT = -half, true, 0
				end
			end
			-- while turning the dino faces the viewer: dir was flipped only AFTER the turn, so f maps correctly
			local yaw = yawFor(st.f)
			st.phase += speed * 0.72 * st.moveBlend * dt
			legA = math.sin(st.phase) * 0.85 * st.moveBlend
			local bob = math.abs(math.sin(st.phase)) * 0.14 * st.moveBlend
			rcf = CFrame.new(cx + st.x, H + bob, cz) * CFrame.Angles(0, yaw, 0)
			move = st.moveBlend
		else
			rcf = rootCFrame(t)
			legA = math.sin(t * 1.6) * 0.06
		end
		root.CFrame = rcf
		for part, off in rest do
			part.CFrame = rcf * off
		end
		for _, l in legs do
			if l.leg then
				local up = l.leg:GetAttribute("HipUp") or 0.9
				local hip = rest[l.leg].Position + Vector3.new(0, up, 0)
				local lcf = rcf * CFrame.new(hip) * CFrame.Angles(legA * l.sign, 0, 0) * CFrame.new(0, -up, 0)
				l.leg.CFrame = lcf
				if l.foot then
					l.foot.CFrame = lcf * footRel[l.foot]
				end
			end
		end
		if armL and armR then
			armL.CFrame = rcf * rest[armL] * CFrame.Angles(-legA * 0.5, 0, 0)
			armR.CFrame = rcf * rest[armR] * CFrame.Angles(legA * 0.5, 0, 0)
		end
		if tail then
			local sway = math.sin(t * (if run then 5 else 1.4)) * (if run then 0.12 else 0.18)
			local pv = rest[tail].Position - Vector3.new(0, 0, tail.Size.Z * 0.5)
			tail.CFrame = rcf * CFrame.new(pv) * CFrame.Angles(0, sway, 0) * CFrame.new(-pv) * rest[tail]
		end

		-- helper parts of the effects
		local ground = Vector3.new(rcf.Position.X, 0, rcf.Position.Z)
		for _, d in rigs do
			local rig = d:GetAttribute("Rig")
			if rig == "Orbit" then
				local R, W, Y, Ph = d:GetAttribute("R"), d:GetAttribute("W"), d:GetAttribute("Y"), d:GetAttribute("Ph") or 0
				local a = Ph + W * t
				local pos = ground + Vector3.new(math.cos(a) * R, Y, math.sin(a) * R)
				local sgn = if W >= 0 then 1 else -1
				local tangent = Vector3.new(-math.sin(a), 0, math.cos(a)) * sgn
				d.CFrame = CFrame.fromMatrix(pos, tangent, Vector3.yAxis)
			elseif rig == "Spin" then
				local W = d:GetAttribute("W") or 0
				local off = d:GetAttribute("Off") or CFrame.new()
				d.CFrame = CFrame.new(ground) * CFrame.Angles(0, W * t, 0) * off
			elseif rig == "Rigid" then
				d.CFrame = rcf * (d:GetAttribute("Off") or CFrame.new())
			elseif rig == "Follow" then
				local target = (rcf * (d:GetAttribute("Off") or CFrame.new())).Position
				local k = d:GetAttribute("K") or 4
				local cur = d:GetAttribute("_pos") or target
				cur = cur:Lerp(target, 1 - math.exp(-k * dt))
				d:SetAttribute("_pos", cur)
				d.CFrame = CFrame.new(cur) * (rcf - rcf.Position)
			end
		end

		-- footprints
		if pool and run then
			if move > 0.5 then
				st.dist += speed * move * dt
				if st.dist >= stampEvery then
					st.dist -= stampEvery
					st.side = -st.side
					local fwd = -rcf.LookVector
					fwd = rcf.LookVector
					local right = rcf.RightVector
					local pos = Vector3.new(rcf.Position.X, 0, rcf.Position.Z) + right * st.side * legHalf * 0.9 + fwd * 0.5 * st.side
					-- decal Top face: image "up" points toward the part's -Z, so face -Z along the dino's forward (LookVector) direction
					local yaw = math.atan2(-fwd.X, -fwd.Z)
					stampAt(pool, pos, yaw, st.side, footMode)
				end
			end
		end
		if pool then
			updatePool(pool, dt)
		end
		if bbs and run then
			if move > 0.5 then
				st.bbAcc += dt
				while st.bbAcc >= 0.06 do
					st.bbAcc -= 0.06
					local it
					local oldest = -1
					for _, c in bbs do
						if c.age > oldest then
							it, oldest = c, c.age
						end
					end
					it.age = 0
					local tailZ = root:GetAttribute("TailZ") or 3.4
					it.base = Vector3.new(rcf.Position.X, 0.3, rcf.Position.Z) - rcf.LookVector * (tailZ + 0.4) + Vector3.new(math.random() - 0.5, 0.5, math.random() - 0.5) * 0.6
					it.part.CFrame = CFrame.new(it.base)
				end
			end
			updateBillboards(bbs, dt)
		end
	end
	return update
end

-- ----------------------------------------------------------------------------------------------- entry points
function Driver.start(labFolder)
	Driver.stop()
	local runtime = Instance.new("Folder")
	runtime.Name = "LabRuntime"
	runtime.Parent = workspace
	local updates = {}
	for _, cell in labFolder:GetChildren() do
		if cell:IsA("Folder") and cell:GetAttribute("CX") then
			local u = setupCell(cell, runtime)
			if u then
				table.insert(updates, u)
			end
		end
	end
	local t = 0
	local conn
	conn = RunService.Heartbeat:Connect(function(dt)
		dt = math.min(dt, 0.1)
		t += dt
		for _, u in updates do
			u(dt, t)
		end
	end)
	Driver._conn, Driver._runtime = conn, runtime
	return function()
		Driver.stop()
	end
end

function Driver.stop()
	if Driver._conn then
		Driver._conn:Disconnect()
		Driver._conn = nil
	end
	if Driver._runtime then
		Driver._runtime:Destroy()
		Driver._runtime = nil
	end
end

return Driver
