--!nocheck
-- Plain-Luau check of assets/blender/creatures/CockatooAnimations.luau with minimal Vector3 / CFrame stand-ins (no Roblox needed).
-- Run: python tools/blender/run_cockatoo_animation_test.py [path/to/luau.exe]
local Vector3 = {}
Vector3.__index = Vector3
function Vector3.new(x, y, z) return setmetatable({X = x or 0, Y = y or 0, Z = z or 0}, Vector3) end
Vector3.zero = Vector3.new(0, 0, 0)
Vector3.xAxis = Vector3.new(1, 0, 0)
Vector3.yAxis = Vector3.new(0, 1, 0)

local CFrame = {}
CFrame.__index = CFrame
local function make(p, r) return setmetatable({p = p, r = r}, CFrame) end -- r = row-major 3x3 {{..},{..},{..}}
local I = {{1, 0, 0}, {0, 1, 0}, {0, 0, 1}}
CFrame.identity = make(Vector3.zero, I)
function CFrame.new(v) return make(v, I) end
function CFrame.fromAxisAngle(axis, a)
	local x, y, z = axis.X, axis.Y, axis.Z
	local c, s = math.cos(a), math.sin(a)
	local t = 1 - c
	return make(Vector3.zero, {
		{t * x * x + c, t * x * y - s * z, t * x * z + s * y},
		{t * x * y + s * z, t * y * y + c, t * y * z - s * x},
		{t * x * z - s * y, t * y * z + s * x, t * z * z + c},
	})
end
function CFrame.__mul(a, b)
	local r = {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}}
	for i = 1, 3 do for j = 1, 3 do for k = 1, 3 do r[i][j] += a.r[i][k] * b.r[k][j] end end end
	local bp = b.p
	local p = Vector3.new(
		a.r[1][1] * bp.X + a.r[1][2] * bp.Y + a.r[1][3] * bp.Z + a.p.X,
		a.r[2][1] * bp.X + a.r[2][2] * bp.Y + a.r[2][3] * bp.Z + a.p.Y,
		a.r[3][1] * bp.X + a.r[3][2] * bp.Y + a.r[3][3] * bp.Z + a.p.Z)
	return make(p, r)
end
function CFrame:Inverse()
	local rt = {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}}
	for i = 1, 3 do for j = 1, 3 do rt[i][j] = self.r[j][i] end end
	local p = Vector3.new(
		-(rt[1][1] * self.p.X + rt[1][2] * self.p.Y + rt[1][3] * self.p.Z),
		-(rt[2][1] * self.p.X + rt[2][2] * self.p.Y + rt[2][3] * self.p.Z),
		-(rt[3][1] * self.p.X + rt[3][2] * self.p.Y + rt[3][3] * self.p.Z))
	return make(p, rt)
end
function CFrame:VectorToWorldSpace(v)
	return Vector3.new(
		self.r[1][1] * v.X + self.r[1][2] * v.Y + self.r[1][3] * v.Z,
		self.r[2][1] * v.X + self.r[2][2] * v.Y + self.r[2][3] * v.Z,
		self.r[3][1] * v.X + self.r[3][2] * v.Y + self.r[3][3] * v.Z)
end

--@MODULE@

local fails = 0
local function check(name, cond, extra)
	if not cond then
		fails += 1
		print("FAIL", name, extra or "")
	else
		print("ok  ", name)
	end
end
local function near(a, b, e) return math.abs(a - b) <= (e or 1e-3) end

-- rest: every Transform is identity at t = 0 for Idle (all first keys are 0 except the tail yaw 5 degrees)
local s0 = M.sample("Idle", 0)
check("idle body rest", near(s0.Body.p.Y, 0) and near(s0.Body.r[1][1], 1))
-- walk: right leg pitch 24 degrees at t = 0 (swings forward: foot moves toward -Z in Roblox)
local w0 = M.sample("Walk", 0)
local down = w0.LegR:VectorToWorldSpace(Vector3.new(0, -1, 0))
check("walk legR forward", down.Z < -0.3 and near(down.Y, -math.cos(math.rad(24)), 1e-3), tostring(down.Z) .. " " .. tostring(down.Y))
-- loops are continuous: t = 0 and t = length give the same pose
local a, b = M.sample("Walk", 0).LegL, M.sample("Walk", 1.0).LegL
check("walk loop closes", near(a.r[2][3], b.r[2][3]) and near(a.r[3][3], b.r[3][3]))
local a2, b2 = M.sample("Idle", 0.01).Head, M.sample("Idle", 3.01).Head
check("idle loop wraps", near(a2.p.Y, b2.p.Y, 1e-6))
-- jump is not a loop: clamps at the end, body ends at rest height
local j = M.sample("Jump", 5)
check("jump ends at rest", near(j.Body.p.Y, 0) and near(j.LegR.r[2][3], 0))
-- jump apex: body is up more than 1 stud around 0.6 s
local jm = M.sample("Jump", 0.6)
check("jump apex height", jm.Body.p.Y > 1.0 and jm.Body.p.Y < 1.3, tostring(jm.Body.p.Y))
-- arms flare out: right arm hanging vector gets +X
local arm = jm.ArmR:VectorToWorldSpace(Vector3.new(0, -1, 0))
check("jump arm flare out", arm.X > 0.8, tostring(arm.X))
-- forward kinematics: with an identity pose the posed CFrames equal the rest CFrames
local rest = {}
for i, name in M.Parts do rest[name] = CFrame.new(Vector3.new(i, 0, 0)) end
M.Data.Rest = {length = 1, loop = true, tracks = {}}
local p0 = M.poseParts(rest, CFrame.identity, "Rest", 0)
local okRest = true
for name, cf in p0 do if not near(cf.p.X, rest[name].p.X) then okRest = false end end
check("poseParts identity", okRest)
-- a Body pitch moves the children with it (head follows the body)
local pj = M.poseParts(rest, CFrame.identity, "Jump", 0.6)
check("children follow body", pj.Head.p.Y > 1.0)
print(fails == 0 and "ALL OK" or ("FAILED " .. fails))
if fails > 0 then error("cockatoo animation test failed") end
