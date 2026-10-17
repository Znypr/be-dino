"""BD-611 offline movement-speed model (docs/151 section 5, F1).

Part 1 lists EVERY way a character's server-observed horizontal speed can exceed WalkSpeed, with the maximum studs/s computed from the real Config /
CombatConfig / ProgressionConfig / ClassMovement numbers, and whether MovementGuard sees it (RunState Active only).
Part 2 runs the REAL src/shared/MovementWindow.luau and MovementEnvelope.luau against traces:
  * honest traces (walk, bunny hop, potion expiring, dash, leap, admin speed, class speeds) with adversarial replication delay at the guard (0.1 s),
    food (0.08 s) and crystal (0.25 s) cadences: the window must never reject one, and the margin (the largest delay it would still absorb) is printed;
  * speed cheats (1.5x .. 4.8x WalkSpeed, the old 106 / 69 / 52 studs/s): rejected, with the time to the first rejection and the net progress after rollbacks.
Not covered, because nothing offline can measure it: real replication jitter, collision push-out, and client physics on a phone (docs/151 section 8).

    python tools/verify_movement_speed.py --runner <luau>
"""
import argparse, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ['Config', 'ProgressionConfig', 'CombatConfig', 'ClassMovement', 'MovementEnvelope', 'MovementWindow']

BODY = r'''
local Cfg, Prog, Combat, CM, Env, Win = M.Config, M.ProgressionConfig, M.CombatConfig, M.ClassMovement, M.MovementEnvelope, M.MovementWindow
local W, J, S, F, HOLD = Cfg.MovementGuardWindowSeconds, Cfg.MovementGuardWindowJitterSeconds, Cfg.MovementGuardWindowSlackStuds, Cfg.MovementGuardWindowSpeedFactor, Cfg.MovementGuardLimitHoldSeconds
local WALK = Cfg.WalkSpeed
local CARRY = Cfg.JumpForwardCarry
local function v3(x, z) return {X = x, Y = 0, Z = z} end
local failures = 0
local function check(ok, what) if not ok then failures += 1 print("FAIL: " .. what) end end

-- ---------------------------------------------------------------- Part 1: every source of speed above WalkSpeed
local speedCap = Prog.SpeedCap
local adminMax = 3 -- AdminRules.Settings.speedMultiplier.max (owner panel only, applied after SpeedCap)
local classMax = 0
for _, c in CM.ClassNames do classMax = math.max(classMax, CM.walkSpeed(c)) end
local leapAdmin = Prog.LeapHorizontalSpeed * 1.5
local waterDash = CM.speedLimit("Water", "jump")
local rows = {
    {"Walk, flag-off build (all classes)", WALK, "yes: limit = Humanoid.WalkSpeed", "bounded"},
    {"Class walk speed (Fly x1.2 / Ground 1.0 / Water 0.85 / Armored 0.8), playtest profile only", classMax, "yes: WalkSpeed follows ProgressionService", "bounded"},
    {"Speed buffs: potion x1.75 max, trail x1.18, weather x1.15, mutation; product capped at SpeedCap", WALK * speedCap, "yes: WalkSpeed", "bounded (cap " .. speedCap .. ")"},
    {"Same on the fastest class (Fly), SpeedCap reached", classMax * speedCap, "yes: WalkSpeed", "bounded"},
    {"Owner admin panel Run speed x3 (after the cap; AdminPanelEnabled, owner only)", classMax * speedCap * adminMax, "yes: WalkSpeed", "bounded, owner only"},
    {"Jump carry (client JumpCarry: x" .. CARRY .. " while airborne, bunny hopping holds it)", WALK * CARRY, "yes: inside the window factor " .. F, "bounded: client script constant"},
    {"Jump carry on the fastest buffed class", classMax * speedCap * CARRY, "yes: inside the window factor", "bounded"},
    {"E leap: horizontal " .. Prog.LeapHorizontalSpeed .. " for " .. Prog.LeapDuration .. " s, cooldown " .. Prog.LeapCooldown .. " s", Prog.LeapHorizontalSpeed, "yes: MovementSpeedLimit while the leap runs (+ LeapService's own envelope)", "bounded"},
    {"E leap with owner leapSpeed x1.5", leapAdmin, "yes: MovementSpeedLimit", "bounded, owner only"},
    {"Water dash (ClassDash): " .. waterDash .. " for 0.35 s, cooldown 3 s", waterDash, "yes: MovementSpeedLimit while it runs", "bounded"},
    {"Water 'leap' dash 90 (ClassMovement table only: no server or client path uses it)", 90, "n/a: not wired", "dead data"},
    {"Fly glide (ClassGlide, client): only LOWERS the fall speed, no horizontal term", 0, "n/a: vertical, MovementGuardMaxVerticalSpeed " .. Cfg.MovementGuardMaxVerticalSpeed, "bounded"},
    {"Fall / jump vertical speed", 0, "vertical envelope in MovementEnvelope.plausible (max " .. Cfg.MovementGuardMaxVerticalSpeed .. ")", "bounded"},
    {"Fall recovery teleport (FallRecovery.check)", math.huge, "no: MovementGuard.reset + guard skips fallen roots", "server teleport"},
    {"Run start teleport hub -> island (RunLifecycle, FallRecovery.teleport)", math.huge, "no: RunState is Sanctuary, the guard builds a new baseline at Active", "server teleport"},
    {"Hub travel / fast travel (HubTravelService, Sanctuary only)", math.huge, "no: RunState Sanctuary", "server teleport"},
    {"Home / respawn / cave hub spawn (PivotTo hub)", math.huge, "no: RunState not Active", "server teleport"},
    {"Combat soft knockback (CombatEnabled false in every profile): one nudge <= " .. 4 .. " studs", 4 / 0.1, "yes: inside MovementGuardWindowSlackStuds", "bounded"},
    {"DemoTrigger teleport (Studio only, flag off)", math.huge, "yes, and the guard rolls it back (not a shipped path)", "Studio only"},
    {"NPC predators / server-owned physics", 0, "n/a: not a player", "n/a"},
    {"Vehicles, seats, launch pads, springs, conveyors, BodyVelocity", 0, "none exist in src/ (grep)", "none"},
    {"Replication jitter (stale vs fresh position), collision push-out, slope steps", 0, "covered by JitterSeconds " .. J .. " and SlackStuds " .. S, "NOT measured: Studio acceptance"},
}
print("| Source of speed above WalkSpeed | Max studs/s | Does the guard see it | Bounded offline |")
print("| --- | ---: | --- | --- |")
for _, r in rows do
    print(string.format("| %s | %s | %s | %s |", r[1], if r[2] == math.huge then "teleport" else string.format("%.1f", r[2]), r[3], r[4]))
end

-- ---------------------------------------------------------------- Part 2: window numbers
print("")
print("| Speed limit | Old guard sustained | New window sustained | Old food | Old crystals | Window x WalkSpeed |")
print("| --- | ---: | ---: | ---: | ---: | ---: |")
local function oldSustained(limit, dt, tol, burst) return (limit * dt * tol + burst) / dt end
for _, limit in {WALK, WALK * speedCap, classMax * speedCap, Prog.LeapHorizontalSpeed} do
    print(string.format("| %.1f | %.0f | %.1f | %.0f | %.0f | %.2f |", limit,
        oldSustained(limit, Cfg.MovementGuardTickSeconds, Cfg.MovementGuardSpeedTolerance, Cfg.MovementGuardBurstStuds),
        Win.sustained(limit), oldSustained(limit, Cfg.FoodTickSeconds, 2, 2), oldSustained(limit, 0.25, 2, 2), Win.sustained(limit) / limit))
end
check(Win.sustained(WALK) < oldSustained(WALK, 0.25, 2, 2), "the window is tighter than the tightest old check at WalkSpeed")
check(Win.sustained(WALK) / WALK <= 2, "sustained bound at WalkSpeed is at most 2x")

-- Margins as named Config values must keep their meaning
check(F >= CARRY * 1.05, "MovementGuardWindowSpeedFactor (" .. F .. ") must stay at least 5% above JumpForwardCarry (" .. CARRY .. "): the bunny hop is the fastest honest sustained speed")
check(J >= 0.2 and S >= 4 and HOLD >= 0.4 and W >= 1.5 and Cfg.MovementGuardWindowEnabled == true, "window margins are named Config values and not shrunk below the audited minimum")
check(speedCap * 1.0 <= 2.2 + 1e-9, "SpeedCap is the 2.2 the model assumes")

-- A trace: position as a function of time. delay(t) is how stale the server's copy is; the server never goes back in time (clamped monotone).
local function run(posOf, limitAt, delayAt, cadence, duration)
    local w = Win.new()
    local t, lastSample, rejectedAt = 0, -math.huge, nil
    while t <= duration do
        local sample = math.max(lastSample, t - delayAt(t))
        lastSample = sample
        local ok = Win.push(w, t, v3(posOf(math.max(0, sample)), 0), limitAt(t))
        if not ok and not rejectedAt then rejectedAt = t end
        t += cadence
    end
    return rejectedAt
end
local function constant(v) return function(t) return v * t end end
local function squareDelay(maxDelay, period) return function(t) return if math.floor(t / period) % 2 == 0 then maxDelay else 0 end end
local function stepDelay(maxDelay, at) return function(t) return if t < at then maxDelay else 0 end end
local function randomDelay(maxDelay, seed) local state = seed * 7919 return function() state = (state * 1103515245 + 12345) % 2147483648 return maxDelay * state / 2147483648 end end
local cadences = {Cfg.MovementGuardTickSeconds, Cfg.FoodTickSeconds, 0.25}
local patterns = {}
for _, p in {0.25, 0.5, 1, 2, 3, 5} do table.insert(patterns, {"square " .. p, function(d) return squareDelay(d, p) end}) end
for _, a in {2.5, 6, 10, 20} do table.insert(patterns, {"step " .. a, function(d) return stepDelay(d, a) end}) end
for seed = 1, 4 do table.insert(patterns, {"random " .. seed, function(d) return randomDelay(d, seed) end}) end

-- Largest replication delay an honest trace survives (bisection over all patterns and cadences), for speed `v` against limit `limit`
local function maxDelaySurvived(v, limit)
    local lo, hi = 0, 6
    for _ = 1, 24 do
        local mid = (lo + hi) / 2
        local ok = true
        for _, cad in cadences do
            for _, pat in patterns do
                if run(constant(v), function() return limit end, pat[2](mid), cad, 30) then ok = false break end
            end
            if not ok then break end
        end
        if ok then lo = mid else hi = mid end
    end
    return lo
end

print("")
print("| Honest case | Speed | Limit seen | Rejected | Largest replication delay absorbed (s) |")
print("| --- | ---: | ---: | --- | ---: |")
local honest = {
    {"walk", WALK, WALK}, {"bunny hop (carry)", WALK * CARRY, WALK},
    {"buffed walk", WALK * speedCap, WALK * speedCap}, {"buffed bunny hop", WALK * speedCap * CARRY, WALK * speedCap},
    {"Fly class buffed bunny hop", classMax * speedCap * CARRY, classMax * speedCap},
    {"Armored walk (slowest)", CM.walkSpeed("Armored"), CM.walkSpeed("Armored")},
}
for _, h in honest do
    local rejected = false
    for _, cad in cadences do
        for _, pat in patterns do
            if run(constant(h[2]), function() return h[3] end, pat[2](J), cad, 30) then rejected = true end
        end
    end
    local margin = maxDelaySurvived(h[2], h[3])
    print(string.format("| %s | %.1f | %.1f | %s | %.2f |", h[1], h[2], h[3], tostring(rejected), margin))
    check(not rejected, "honest case rejected at the configured jitter: " .. h[1])
    check(margin >= J * 1.25, "honest case margin under 1.25x the configured jitter: " .. h[1] .. " " .. margin)
end

-- Transitions: the limit changes while the character keeps its old speed for a while (the client gets WalkSpeed late)
local function transition(name, speedAt, limitAt, duration)
    local pos = {}
    local rejected = false
    for _, cad in cadences do
        for _, pat in patterns do
            -- integrate speedAt numerically
            local dt = 0.005
            local x, table_ = 0, {}
            local steps = math.floor(duration / dt)
            for i = 0, steps do table_[i] = x x += speedAt(i * dt) * dt end
            local posOf = function(t) return table_[math.clamp(math.floor(t / dt + 0.5), 0, steps)] end
            if run(posOf, limitAt, pat[2](J), cad, duration) then rejected = true end
        end
    end
    print(string.format("| %s | %s |", name, tostring(rejected)))
    check(not rejected, "honest transition rejected: " .. name)
end
print("")
print("| Honest transition | Rejected |")
print("| --- | --- |")
local buffed = WALK * speedCap
transition("potion runs out while running (client keeps the old speed 0.4 s)", function(t) return if t < 5.4 then buffed else WALK end, function(t) return if t < 5 then buffed else WALK end, 12)
transition("potion runs out, bunny hopping", function(t) return (if t < 5.4 then buffed else WALK) * CARRY end, function(t) return if t < 5 then buffed else WALK end, 12)
transition("E leap after walking (client starts 0.3 s after the attribute)", function(t) return if t >= 5.3 and t < 5.3 + Prog.LeapDuration then Prog.LeapHorizontalSpeed else WALK end, function(t) return if t >= 5 and t < 5 + Prog.LeapDuration then Prog.LeapHorizontalSpeed else WALK end, 12)
transition("E leap, owner leapSpeed x1.5", function(t) return if t >= 5.3 and t < 5.3 + Prog.LeapDuration then leapAdmin else WALK end, function(t) return if t >= 5 and t < 5 + Prog.LeapDuration then leapAdmin else WALK end, 12)
transition("Water dash (client starts 0.3 s late, attribute cleared at 0.6 s)", function(t) return if t >= 5.3 and t < 5.65 then 48 else CM.walkSpeed("Water") end, function(t) return if t >= 5 and t < 5.6 then 48 else CM.walkSpeed("Water") end, 12)
transition("walk, stop, walk (idle must not matter)", function(t) return if t < 4 or t > 8 then WALK else 0 end, function() return WALK end, 14)
transition("sprint-start from rest at buffed speed", function(t) return buffed end, function() return buffed end, 12)

-- Cheats
print("")
print("| Speed cheat | Studs/s | Rejected after (s) | Net progress in 60 s with rollbacks (studs) | Honest walk in 60 s |")
print("| --- | ---: | ---: | ---: | ---: |")
local function cheat(v, limit, cadence)
    local w = Win.new()
    local t, pos, anchor, firstReject, rejects = 0, 0, 0, nil, 0
    local travelled = 0 -- how far the cheater really moved in total
    while t <= 60 do
        pos += v * cadence
        local ok, tag, ax = Win.push(w, t, v3(pos, 0), limit, pos)
        if not ok then
            rejects += 1
            firstReject = firstReject or t
            pos = tag :: number -- rollback to the window start
            Win.reset(w)
            Win.push(w, t, v3(pos, 0), limit, pos)
        end
        t += cadence
    end
    return firstReject, pos
end
local cheats = {
    {"1.8x (just above the window)", Win.sustained(WALK) * 1.02, WALK}, {"2x", WALK * 2, WALK}, {"3x", WALK * 3, WALK},
    {"old guard limit 4.8x (106)", oldSustained(WALK, 0.1, 3, 4), WALK}, {"old food limit 3.1x (69)", oldSustained(WALK, 0.08, 2, 2), WALK},
    {"old crystal limit 2.4x (52)", oldSustained(WALK, 0.25, 2, 2), WALK}, {"buffed 2x", buffed * 2, buffed}, {"old guard limit with a potion (185)", oldSustained(buffed, 0.1, 3, 4), buffed},
}
for _, c in cheats do
    local first, progress = cheat(c[2], c[3], Cfg.MovementGuardTickSeconds)
    print(string.format("| %s | %.0f | %s | %.0f | %.0f |", c[1], c[2], if first then string.format("%.1f", first) else "never", progress, c[3] * 60))
    check(first ~= nil, "cheat not rejected: " .. c[1])
    check(progress <= Win.sustained(c[3]) * 60 * 0.2, "cheat gains more than a fifth of the allowed sustained distance: " .. c[1] .. " " .. progress)
end
-- Riding the budget: the residual gain
local residual = Win.sustained(WALK)
print(string.format("\nResidual: a cheat that stays just under the window moves %.1f studs/s (x%.2f WalkSpeed) instead of 106 (x4.8); at x2.2 buff %.1f instead of 185", residual, residual / WALK, Win.sustained(buffed)))
check(run(constant(residual * 0.98), function() return WALK end, function() return 0 end, 0.1, 60) == nil, "a cheat just under the window passes (the window is exact, not stricter than documented)")
check(run(constant(residual * 1.05), function() return WALK end, function() return 0 end, 0.1, 60) ~= nil, "a cheat 5% above the window is rejected")
-- The per-tick check still stops teleports (unchanged)
check(not Env.plausible(Vector3.new(11, 0, 0), 0.1, Cfg.MovementGuardSpeedTolerance, Cfg.MovementGuardBurstStuds, 0, WALK), "a 11 stud tick step is still implausible at WalkSpeed")
print(if failures == 0 then "\nmovement speed model ok" else ("\nFAILURES: " .. failures))
if failures > 0 then error("movement speed model failed") end
'''


def module(name):
    return '(function()\n' + (ROOT / 'src/shared' / f'{name}.luau').read_text(encoding='utf-8') + '\nend)()'


def script():
    parts = [
        'local M={}', 'local script={Parent=M}', 'local require=function(x) return x end',
        'local Vector3={new=function(x,y,z) return {X=x,Y=y,Z=z} end}',
        'local Vector2={new=function(x,y) return {X=x,Y=y,Magnitude=math.sqrt(x*x+y*y)} end}',
        'local workspace={Gravity=250}',
    ]
    for n in MODULES:
        parts.append(f'M.{n}={module(n)}')
    parts.append(BODY)
    return '\n'.join(parts)


def static_checks():
    cfg = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    for key in ('MovementGuardWindowEnabled', 'MovementGuardWindowSeconds', 'MovementGuardWindowSpeedFactor', 'MovementGuardWindowJitterSeconds',
                'MovementGuardWindowSlackStuds', 'MovementGuardLimitHoldSeconds'):
        assert key + ' =' in cfg, 'Config.' + key + ' missing'
    guard = (ROOT / 'src/server/MovementGuard.luau').read_text(encoding='utf-8')
    assert 'MovementWindow.push(state.window' in guard and 'MovementWindow.reset(state.window)' in guard, 'MovementGuard feeds and resets the window'
    assert 'root.CFrame = rollback' in guard, 'MovementGuard rolls back to the window start'
    food = (ROOT / 'src/server/FoodService.luau').read_text(encoding='utf-8')
    assert 'MovementWindow.push(window, now, position, limit)' in food and 'plausible = false' in food, 'FoodService uses the window'
    prog = (ROOT / 'src/server/ProgressionService.luau').read_text(encoding='utf-8')
    assert 'MovementWindow.push(window,now,root.Position,limit)' in prog and 'windowOk' in prog, 'crystal pickup uses the window'
    print('movement window wiring ok')


parser = argparse.ArgumentParser()
parser.add_argument('--runner', required=True)
args = parser.parse_args()
with tempfile.TemporaryDirectory() as d:
    path = Path(d) / 'movement_speed.luau'
    path.write_text(script(), encoding='utf-8')
    result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
    print(result.stdout, end='')
    print(result.stderr, end='')
if result.returncode == 0:
    static_checks()
raise SystemExit(result.returncode)
