"""BD-503 (docs/147 s4 item 5): every server-side teleport of a dinosaur goes through the streaming-aware helper.

With workspace.StreamingEnabled the client only holds the world near its character, so a server teleport across the map must first call
player:RequestStreamAroundAsync(target, timeout). The one helper is src/server/StreamingTeleport.luau; FallRecovery.teleport (the single
server teleport: run start, hub travel, show-off, fall recovery, demo) calls it, RunLifecycle.requestStart calls it with a longer timeout,
Bootstrap (respawn at the hub, i.e. home after a settle) calls it. This check:

  * Luau: the helper is a no-op while StreamingEnabled is false, passes the position and timeout when on, never throws (pcall), skips a
    player who left, and `needed` skips a target inside 64 studs.
  * static: nothing but the helper calls RequestStreamAroundAsync; every src/server file that moves a character, part or model
    (PivotTo, .CFrame =, SetPrimaryPartCFrame, :MoveTo) is classified below (teleport = must use the helper, local correction / world
    build / NPC = allowed with the reason). A NEW file that moves something fails until it is classified here.

    python tools/verify_streaming_teleports.py --runner C:/path/luau.exe
Not Studio evidence: the Studio check is in the BD-503 row of docs/07-kanban.md.
"""
from pathlib import Path
import argparse, re, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'src/server'

LUAU = r'''
local calls = {}
local Players = {}
local flag = false
workspace = setmetatable({}, {__index = function(_, k) if k == "StreamingEnabled" then return flag end end})
game = {GetService = function(_, name) return Players end}
local function player(parent, fail)
 local p = {Parent = parent}
 function p:RequestStreamAroundAsync(pos, timeout)
  table.insert(calls, {pos = pos, timeout = timeout})
  if fail then error("stream failed") end
 end
 return p
end
local function pos(x) return setmetatable({x = x}, {__sub = function(a, b) return {Magnitude = math.abs(a.x - b.x)} end}) end
local function character(x)
 local root = {Position = x and pos(x) or nil}
 function root:IsA(name) return name == "BasePart" end
 local model = {}
 function model:FindFirstChild(name) if name == "HumanoidRootPart" and x then return root end return nil end
 return model
end

-- off: a no-op
local p = player(Players)
assert(S.request(p, pos(0)) == false and #calls == 0, "streaming off: no request")
assert(S.needed(character(0), pos(500)) == false, "streaming off: never needed")
-- on
flag = true
assert(S.request(p, pos(7)) == true, "on: request made")
assert(#calls == 1 and calls[1].timeout == S.DefaultTimeout and calls[1].pos.x == 7, "default timeout and position passed")
assert(S.DefaultTimeout <= 4, "short default timeout")
assert(S.request(p, pos(9), 8) == true and calls[2].timeout == 8, "explicit timeout passed")
-- never throws, a failure only reports false
local bad = player(Players, true)
local ok, result = pcall(S.request, bad, pos(1))
assert(ok and result == false, "a failing request is swallowed")
-- a player who left is not asked
local before = #calls
assert(S.request(player(nil), pos(1)) == false and #calls == before, "left player: no request")
-- needed: near targets skip the wait
assert(S.needed(character(10), pos(10 + S.NearStuds - 1)) == false, "inside the near distance: not needed")
assert(S.needed(character(10), pos(10 + S.NearStuds + 1)) == true, "outside the near distance: needed")
assert(S.needed(character(nil), pos(0)) == true, "no root yet: ask")
print("streaming teleport helper ok")
'''

# file -> (kind, reason). "teleport" = a character move that must use the helper; the others never need streaming.
CLASSIFIED = {
    'FallRecovery.luau': ('teleport', 'THE server teleport; calls StreamingTeleport.needed / request first'),
    'Bootstrap.server.luau': ('teleport', 'spawn / respawn at the hub pad (home after a settle); calls StreamingTeleport.request for the hub'),
    'LeapService.luau': ('local correction', 'rubber-bands to the last valid CFrame of the same stretch (already streamed)'),
    'MovementGuard.luau': ('local correction', 'snaps back to the last valid baseline (already streamed)'),
    'CombatService.luau': ('local correction', 'a push of a few studs on a hit'),
    'NpcPredatorService.luau': ('npc', 'server NPCs, not player dinos; streamed by distance like any model'),
    'Dinosaur.luau': ('local correction', 'welds the collider part to the root'),
    'Arena.luau': ('world build', 'places props at server start'),
    'CaveLighting.luau': ('world build', 'places cave lights at server start'),
    'CaveProps.luau': ('world build', 'places cave props at server start'),
    'ImportedResources.luau': ('world build', 'scales imported resource models at server start'),
    'Leaderboards.luau': ('world build', 'places the boards at server start'),
    'FoodService.luau': ('world build', 'moves food visuals, not a player'),
    'ProgressionService.luau': ('world build', 'places resource pickups'),
}
MOVE = re.compile(r':PivotTo\(|\.CFrame\s*=[^=]|SetPrimaryPartCFrame|:MoveTo\(|:Move\(')


def run(runner):
    helper = (SERVER / 'StreamingTeleport.luau').read_text()
    prelude, tests = LUAU.split('-- off: a no-op')
    script = prelude + 'local S=(function()\n' + helper + '\nend)()\n-- off: a no-op' + tests
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_streaming_teleports.luau'; path.write_text(script)
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        if out.returncode: raise SystemExit(out.stdout[-3000:] + out.stderr)
        return out.stdout.strip()


def code_lines(text):
    for number, line in enumerate(text.splitlines(), 1):
        yield number, (line.split('--')[0] if '--' in line else line)


def static_checks():
    helper = (SERVER / 'StreamingTeleport.luau').read_text()
    assert 'if not workspace.StreamingEnabled then return false end' in helper, 'the helper is a no-op while streaming is off'
    assert 'pcall(function() player:RequestStreamAroundAsync(position,' in helper, 'the request is pcall-wrapped'
    for path in sorted(SERVER.glob('*.luau')):
        if path.name == 'StreamingTeleport.luau': continue
        for number, line in code_lines(path.read_text()):
            assert 'RequestStreamAroundAsync' not in line, f'{path.name}:{number}: only StreamingTeleport.luau may call RequestStreamAroundAsync'

    # every file that moves something is classified
    seen = {}
    for path in sorted(SERVER.glob('*.luau')):
        hits = [n for n, line in code_lines(path.read_text()) if MOVE.search(line)]
        if hits: seen[path.name] = hits
    for name, hits in seen.items():
        assert name in CLASSIFIED, f'{name}:{hits[0]} moves a character/part/model but is not classified in tools/verify_streaming_teleports.py: ' \
                                   'a dino teleport must go through FallRecovery.teleport (StreamingTeleport), anything else needs a reason here'
    for name in CLASSIFIED:
        assert name in seen, f'{name} no longer moves anything: drop it from CLASSIFIED'

    # the funnel
    fall = (SERVER / 'FallRecovery.luau').read_text()
    body = fall[fall.index('function FallRecovery.teleport('):fall.index('function FallRecovery.check(')]
    assert 'StreamingTeleport.needed(character, target.Position)' in body and 'StreamingTeleport.request(player, target.Position)' in body, 'teleport asks for streaming'
    assert body.index('StreamingTeleport.request(') < body.index('character:PivotTo(target)'), 'the stream request comes BEFORE the move'
    assert 'player.Character ~= character' in body, 'the player and character are re-checked after the wait'
    assert 'streamed ~= true' in body, 'a caller that streamed already can skip the second request'

    # every caller of the teleport goes through FallRecovery.teleport (no private PivotTo of a character elsewhere)
    callers = []
    for path in sorted(SERVER.glob('*.luau')):
        for number, line in code_lines(path.read_text()):
            if re.search(r'FallRecovery\)?\.teleport\(', line) and path.name != 'FallRecovery.luau': callers.append(path.name)
    assert sorted(set(callers)) == ['CaveShowOff.luau', 'DemoTriggerService.luau', 'HubTravelService.luau', 'RunLifecycle.luau'], callers
    for name in ('Dinosaur', 'LeapService', 'MovementGuard', 'ClassMovementService', 'FoodService'):
        text = (SERVER / f'{name}.luau').read_text()
        assert 'character:PivotTo' not in text, f'{name} must not teleport a character itself'

    # run start: own request (longer timeout, double-entry guard) then the teleport with streamed = true
    run_life = (SERVER / 'RunLifecycle.luau').read_text()
    assert 'StreamingTeleport.request(player, SpawnGeometry.islandPoint(Layout), 8)' in run_life, 'run start streams the island with the 8 s timeout'
    assert re.search(r'FallRecovery\)\.teleport\(player, character, CFrame\.new\(SpawnGeometry\.islandPoint\(Layout\)\), true\)', run_life), 'run start passes streamed = true'

    # respawn at the hub (home after a settle): the helper is called concurrently with the placement
    boot = (SERVER / 'Bootstrap.server.luau').read_text()
    assert boot.count('character:PivotTo(hub)') == 2 and 'StreamingTeleport).request(player, hub.Position)' in boot, 'Bootstrap asks to stream the hub'
    assert boot.index('StreamingTeleport).request(player, hub.Position)') > boot.index('character:PivotTo(hub)'), 'BD-210: the first placement stays immediate'
    assert 'local StreamingTeleport' not in boot, 'no new top-level local in server Bootstrap'


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runner', required=True); args = p.parse_args()
    static_checks()
    print(run(args.runner))
    print('streaming teleport call sites ok: ' + ', '.join(f'{k} ({v[0]})' for k, v in CLASSIFIED.items() if v[0] == 'teleport'))
