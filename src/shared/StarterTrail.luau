--!strict
-- BD-1175 (docs/225 sections 3 and 7): where the starter run's food trail goes. Pure (no Instances, no raycasts): the server passes in
-- "is this spot valid ground?" (FoodService.groundOk, the same ground rule as every other food), so the rule itself is tested offline with
-- mocked ground (tools/verify_starter_trail.py). Every number is PROVISIONAL and is tuned in Studio with the bot (BD-1175 step 7).
local Trail = {}
Trail.Kind = "amber" -- existing food: 50 points = one egg each at FoodCatchRate 12/500 (FoodService.TYPES)
Trail.FirstStuds = 14 -- PROVISIONAL: the first food, just outside the clear spawn circle
Trail.StepStuds = 8 -- PROVISIONAL: from one food to the next (a Compy walks it in about half a second)
Trail.MaxFoods = 6 -- never a long trail, whatever the numbers say
Trail.MinGapStuds = 5 -- two trail foods are never on top of each other
-- The spawn disc FoodService.groundAt keeps empty (same numbers there; the verifier compares them). One stud of margin.
Trail.ClearX, Trail.ClearZ, Trail.ClearRadius, Trail.ClearMargin = 0, 30, 11, 1
Trail.Angles = {0, 20, -20, 40, -40, 60, -60, 90, -90, 135, -135, 180} -- degrees off the walking direction, straight ahead first
Trail.Shifts = {0, 0.5, -0.5} -- in steps: the planned distance first, then half a step further, then half a step nearer

local function finite(v: any): boolean
    return type(v) == "number" and v == v and v ~= math.huge and v ~= -math.huge
end

-- How many trail foods make `cardEggs` eggs: the smallest count whose food points reach that many whole eggs (the same floor as
-- FoodCatchRules.award), at least 1, at most MaxFoods. Amber (50) at 12/500 with a 3-egg card: 3.
function Trail.count(cardEggs: any, pointsPerFood: any, catchRate: any): number
    if not finite(cardEggs) or not finite(pointsPerFood) or not finite(catchRate) or cardEggs < 1 or pointsPerFood <= 0 or catchRate <= 0 then return 0 end
    for n = 1, Trail.MaxFoods do
        if math.floor(n * pointsPerFood * catchRate + 1e-9) >= math.floor(cardEggs) then return n end
    end
    return Trail.MaxFoods
end

function Trail.outsideClear(x: number, z: number): boolean
    local dx, dz = x - Trail.ClearX, z - Trail.ClearZ
    local r = Trail.ClearRadius + Trail.ClearMargin
    return dx * dx + dz * dz >= r * r
end

-- The spots tried for trail food number `index` (1 = nearest), best first. `o`: originX, originZ, dirX, dirZ.
function Trail.candidates(o: any, index: number): {{x: number, z: number}}
    local list = {}
    if type(o) ~= "table" or not finite(o.originX) or not finite(o.originZ) or not finite(index) then return list end
    local dx, dz = o.dirX, o.dirZ
    local length = if finite(dx) and finite(dz) then math.sqrt(dx * dx + dz * dz) else 0
    if length < 1e-3 then dx, dz, length = 0, -1, 1 end -- no direction: the way a fresh run start looks (-Z)
    dx, dz = dx / length, dz / length
    for _, shift in Trail.Shifts do
        local distance = Trail.FirstStuds + (index - 1 + shift) * Trail.StepStuds
        if distance >= Trail.FirstStuds then
            for _, degrees in Trail.Angles do
                local a = math.rad(degrees)
                local c, s = math.cos(a), math.sin(a)
                table.insert(list, {x = o.originX + (dx * c - dz * s) * distance, z = o.originZ + (dx * s + dz * c) * distance})
            end
        end
    end
    return list
end

-- The trail: for each food the first candidate that is outside the clear spawn circle, not on top of an earlier trail food and on valid
-- ground. A food with no valid spot is left out (a shorter trail, never a food in a bad place). `o` also carries `count`.
function Trail.place(o: any, groundOk: (x: number, z: number) -> boolean): {{x: number, z: number, index: number}}
    local spots = {}
    if type(o) ~= "table" or not finite(o.count) or type(groundOk) ~= "function" then return spots end
    for index = 1, math.min(math.floor(o.count), Trail.MaxFoods) do
        for _, spot in Trail.candidates(o, index) do
            local free = Trail.outsideClear(spot.x, spot.z)
            if free then
                for _, taken in spots do
                    local dx, dz = spot.x - taken.x, spot.z - taken.z
                    if dx * dx + dz * dz < Trail.MinGapStuds * Trail.MinGapStuds then free = false break end
                end
            end
            if free and groundOk(spot.x, spot.z) == true then
                table.insert(spots, {x = spot.x, z = spot.z, index = index})
                break
            end
        end
    end
    return spots
end

return Trail
