-- docs/147 (BD-498 experiment): scratch join-time probe. NOT part of the game: tools/qa/streaming_variants.py injects it into a COPY of a built place
-- (ReplicatedFirst) so the client records, in ReplicatedFirst attribute "Probe" (JSON): when the script started, when the character, the profile, the HUD
-- and WorldReady appeared (events, seconds of game time) and, every 2 s for 120 s, the parts and instances in Workspace and the Studio memory total.
-- Read it back with execute_luau on the Client. Never ships; build.py does not read tools/.
local Players=game:GetService("Players") local HttpService=game:GetService("HttpService") local Stats=game:GetService("Stats")
local RF=game:GetService("ReplicatedFirst")
local lp=Players.LocalPlayer
local rec={start=time(),events={},samples={}}
local function ev(n) if not rec.events[n] then rec.events[n]=time() RF:SetAttribute("Probe",HttpService:JSONEncode(rec)) end end
ev("scriptStart")
local function count()
 local d,p=0,0
 for _,i in workspace:GetDescendants() do d+=1 if i:IsA("BasePart") then p+=1 end end
 return d,p
end
task.spawn(function()
 local lastSample=0
 while time()-rec.start<120 do
  local ch=lp.Character local root=ch and ch:FindFirstChild("HumanoidRootPart")
  if root then ev("character") end
  if lp:GetAttribute("ProfileState")=="Loaded" then ev("profileLoaded") end
  if lp:GetAttribute("WorldReady") then ev("worldReady") end
  if lp.PlayerGui:FindFirstChild("BeDinoUI") then ev("hudGui") end
  if root and lp:GetAttribute("WorldReady") and lp:GetAttribute("ProfileState")=="Loaded" and lp.PlayerGui:FindFirstChild("BeDinoUI") then ev("playable") end
  if time()-lastSample>=2 then
   lastSample=time()
   local d,p=count()
   table.insert(rec.samples,{t=math.floor((time()-rec.start)*10)/10,desc=d,parts=p,mem=math.floor(Stats:GetTotalMemoryUsageMb()),loc=lp:GetAttribute("Location")})
   RF:SetAttribute("Probe",HttpService:JSONEncode(rec))
  end
  task.wait(.1)
 end
end)
