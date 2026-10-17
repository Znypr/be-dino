-- Objectives e2e: short real run (walks to the gate, eats food for E2E_SECONDS), adapted from the s1-pass walker: scripted walker (Humanoid:MoveTo visible food), normal speed, no admin boosts
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")
local player = Players.LocalPlayer
shared.W1 = {log = {}, rows = {}, done = false, stop = false}
local S = shared.W1
local function say(s) table.insert(S.log, string.format("[%.1f] %s", time(), s)) end
local function root() local c = player.Character return c and c:FindFirstChild("HumanoidRootPart") end
local function hum() local c = player.Character return c and c:FindFirstChildOfClass("Humanoid") end
local function cattr(n) local c = player.Character return c and c:GetAttribute(n) end
local function rs() return cattr("RunState") end
local Config = require(RS.Shared.Config)
local Gate = require(RS.Shared.CaveGateRules)
local function foodVisible(f)
  if f.Transparency < 1 then return true end
  local p = f:FindFirstChildWhichIsA("BasePart", true)
  return p ~= nil and p.Transparency < 1
end
local function snapshot(label, t)
  local catch = cattr("CatchScore") or 0
  local carry = cattr("FoodCatchCarry") or 0
  local growth = cattr("GrowthScore") or 0
  local rawFood = growth / Config.GrowthPerFood
  local h = hum()
  local row = {label = label, t = t, eggs = catch, carry = carry, growth = growth, rawFood = rawFood,
    scale = cattr("VisualScale"), crystalPickups = player:GetAttribute("CrystalPickupCount"),
    weather = workspace:GetAttribute("WeatherId"), speed = h and h.WalkSpeed, species = player:GetAttribute("EquippedSpeciesId"),
    mult = cattr("WeatherLootMultiplier"), gm = cattr("GrowthMultiplier") or player:GetAttribute("GrowthMultiplier")}
  table.insert(S.rows, row)
  say(string.format("%s t=%.0fs eggs=%s carry=%.2f growth=%.2f rawFood(growth/0.1)=%.0f scale=%s crystalPickups=%s weather=%s walkspeed=%s species=%s lootMult=%s growthMult=%s",
    label, t, tostring(catch), carry, growth, rawFood, tostring(row.scale), tostring(row.crystalPickups), tostring(row.weather), tostring(row.speed), tostring(row.species), tostring(row.mult), tostring(row.gm)))
end
task.spawn(function()
  local ok, err = pcall(function()
    -- 1. leave through the gate
    local z = Gate.zone()
    local target = Vector3.new(z.sx + z.ux * 4, z.floorY + 3, z.sz + z.uz * 4)
    local t0, last = time(), -9
    while rs() ~= "Active" and time() - t0 < 60 do
      local r = root()
      if r and not Gate.inZone(r.Position.X, r.Position.Z, r.Position.Y) and time() - last > 2.5 then
        local h = hum(); if h then h:MoveTo(target) end; last = time()
      end
      task.wait(0.2)
    end
    if rs() ~= "Active" then say("RUN DID NOT START, RunState=" .. tostring(rs())) S.done = true return end
    -- wait for island load (RunState turns Active slightly before the dino is on the island)
    task.wait(1)
    local runStart = time()
    S.runStart = runStart
    say("RUN START (RunState Active) at gate walk " .. string.format("%.1f", runStart - t0) .. "s")
    snapshot("start", 0)
    local food = workspace:WaitForChild("Food", 10)
    local blocked = {}
    local nextMark = 60
    local sTick = 0
    while time() - runStart < (shared.E2E_SECONDS or 40) and rs() == "Active" and not S.stop do
      -- pick best visible food
      local r = root()
      local best, score = nil, -1
      if r then
        for _, f in food:GetChildren() do
          if f:IsA("BasePart") and not blocked[f] and f:GetAttribute("Points") and foodVisible(f) then
            local d = (f.Position - r.Position).Magnitude + 10
            local s = f:GetAttribute("Points") / (d * d)
            if s > score then best, score = f, s end
          end
        end
      end
      if not best then say("no visible food") task.wait(0.5)
      else
        local h = hum(); if h then h:MoveTo(best.Position) end
        local t1, got = time(), false
        while time() - t1 < 6 and time() - runStart < (shared.E2E_SECONDS or 40) do
          task.wait(0.1)
          if time() - runStart >= nextMark then snapshot("min" .. (nextMark // 60), time() - runStart) nextMark += 60 end
          local rr = root(); if not rr then break end
          local flat = Vector3.new(rr.Position.X - best.Position.X, 0, rr.Position.Z - best.Position.Z).Magnitude
          if flat < 3 or not foodVisible(best) then got = true break end
        end
        if not got then blocked[best] = true; local hh = hum(); if hh then hh.Jump = true end end
      end
      if time() - runStart >= nextMark then snapshot("min" .. (nextMark // 60), time() - runStart) nextMark += 60 end
    end
    local h = hum(); local rr = root(); if h and rr then h:MoveTo(rr.Position) end
    local t = time() - runStart
    while nextMark <= 300 and t >= nextMark - 0.5 do snapshot("min" .. (nextMark // 60), t) nextMark += 60 end
    snapshot("end", t)
    say("RUN WALK FINISHED, RunState=" .. tostring(rs()))
  end)
  if not ok then say("ERROR " .. tostring(err)) end
  S.done = true
end)
return "walker started"
