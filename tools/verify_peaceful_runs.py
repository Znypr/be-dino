"""BD-421 (Peaceful choice) and BD-422 (eggs are always kept) checks. Runs the REAL src/server/RunLifecycle.luau in pinned
Luau with mocked Roblox services (transaction logic only, not Studio replication).

BD-422: for every end reason (Eaten, Death, ManualExit, Disconnect) the settlement callback receives exactly the run's
CatchScore and egg events; the reason never changes them; a second end of the same run settles nothing.
BD-421: begin() snapshots the saved Peaceful setting into the PeacefulRun attribute ONCE (later setting changes do not
touch a running run), and static checks confirm PredationService / CombatService / the UI honour it.

    python tools/verify_peaceful_runs.py --runner /path/to/luau
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

HARNESS = r'''
local CFG = {RespawnDelaySeconds = 0, RunEggMaxPerRun = 400, WorldReadyTimeoutSeconds = 20, SpawnProtectionSeconds = 5}
local settingsJson = ""
local PS = {get = function(_, name) if name == "SettingsJson" then return settingsJson end return nil end}
local SM = {fromStore = function(t) return {peaceful = type(t) == "table" and t.peaceful == true} end}
local ReplicatedStorage = {Shared = {Config = CFG, IslandLayout = {}, SpawnGeometry = {}, SettingsModel = SM}}
local clock = 100
local EVENTS = "EVENTS_JSON"
local Http = {GenerateGUID = function() return "run-" .. tostring(clock) end,
    JSONDecode = function(_, s) if s == EVENTS then return {{rarity = "common"}, {rarity = "rare"}} end if s == "[]" then return {} end return {peaceful = s == "P"} end}
local services = {Players = {GetPlayers = function() return {} end}, ReplicatedStorage = ReplicatedStorage, HttpService = Http}
local game = {GetService = function(_, n) return services[n] end}
local workspace = {GetServerTimeNow = function() return clock end}
local task = {spawn = function(f, ...) f(...) end, wait = function() end, delay = function() end}
local script = {Parent = {PrivateState = PS}}
local require = function(x) return x end
local typeof = function(v) return type(v) end

local function module() @@MODULE@@ end
local RL = module()

local function mock(catchScore, events)
    local attrs = {RunState = "Active", RunId = "r1", CatchScore = catchScore, RunEggEvents = events, GrowthScore = 50}
    local humanoid = {Health = 100}
    local character = {Humanoid = humanoid}
    function character:GetAttribute(n) return attrs[n] end
    function character:SetAttribute(n, v) attrs[n] = v end
    function character:FindFirstChildOfClass() return humanoid end
    function character:FindFirstChild() return nil end
    function character:WaitForChild() return nil end
    local pattrs = {ProfileState = "Loaded"}
    local player = {Character = character, Parent = true}
    function player:GetAttribute(n) return pattrs[n] end
    function player:SetAttribute(n, v) pattrs[n] = v end
    function player:LoadCharacterAsync() end
    return player, character, attrs
end

local calls
RL.configureSettlement(function(_, runId, catchScore, reason, eggEvents, runSeconds) table.insert(calls, {runId = runId, catch = catchScore, reason = reason, events = #eggEvents}) return true end)

-- BD-422: every end reason keeps every earned egg
for _, reason in {"Eaten", "Death", "ManualExit", "Disconnect"} do
    calls = {}
    local player, character = mock(37, EVENTS)
    if reason == "Disconnect" then
        assert(RL.endForDisconnect(player) == "settled")
    else
        assert(RL.tryEnd(player, character, reason, 9) == true)
    end
    assert(#calls == 1, reason .. ": settled exactly once")
    assert(calls[1].catch == 37 and calls[1].events == 2 and calls[1].reason == reason, reason .. ": all eggs and egg events delivered")
    if reason == "Disconnect" then assert(RL.endForDisconnect(player) == "none" or RL.endForDisconnect(player) == "busy") else assert(RL.tryEnd(player, character, reason) == false) end
    assert(#calls == 1, reason .. ": a second end does not settle again")
end
-- an Eaten run with the most eggs the cap allows keeps them all (clamp is the run cap, not a penalty)
calls = {}
local p2, c2 = mock(400, "[]") assert(RL.tryEnd(p2, c2, "Eaten", 3)) assert(calls[1].catch == 400)
calls = {}
local p3, c3 = mock(0, "[]") assert(RL.tryEnd(p3, c3, "Eaten", 3)) assert(calls[1].catch == 0, "no eggs, none invented")

-- BD-421: Peaceful snapshot at run start
for _, case in {{"", false}, {"P", true}, {"N", false}} do
    settingsJson = case[1]
    local player, character, attrs = mock(0, "[]")
    attrs.RunState, attrs.RunId = "Sanctuary", nil
    character.Humanoid = nil
    RL.begin(player, character)
    assert(attrs.PeacefulRun == case[2], "PeacefulRun snapshot for setting '" .. case[1] .. "'")
    assert(attrs.RunState == "Active")
    settingsJson = if case[2] then "N" else "P" -- the player changes the setting mid-run
    assert(attrs.PeacefulRun == case[2], "mid-run change does not touch the running run")
end
print("BD-421/BD-422 runtime checks passed: 4 end reasons keep all eggs exactly once; Peaceful snapshot per run")
'''


def static():
    read = lambda p: (ROOT / p).read_text(encoding='utf-8')
    pred, comb, rl, menu, boot = (read(p) for p in ['src/server/PredationService.luau', 'src/server/CombatService.luau',
                                                    'src/server/RunLifecycle.luau', 'src/client/SettingsMenu.luau', 'src/client/Bootstrap.client.luau'])
    assert 'GetAttribute("PeacefulRun") ~= true' in pred, 'PredationService must skip Peaceful players (attacker and victim)'
    assert 'PeacefulRun' in comb, 'CombatService must use the run-start snapshot'
    assert 'PeacefulRun' in rl and 'peacefulSetting' in rl
    assert 'PeacefulRun' not in read('src/shared/SettingsModel.luau')
    assert re.search(r'toggle\(body, ctx, peacefulRow, "Peaceful"', menu) and 'CombatEnabled then 2' not in menu.split('BD-421')[1][:400], 'Peaceful toggle must not depend on CombatEnabled'
    assert 'PeacefulToggle' in boot, 'Sanctuary screen needs the Peaceful toggle'
    # settlement never branches on the end reason (BD-422)
    start = rl.index('local function settlementSnapshot')
    snap = rl[start:rl.index('local function respawnAfterSettlement')]
    assert 'reason' not in snap, 'settlementSnapshot must not depend on the end reason'
    boot_server = read('src/server/Bootstrap.server.luau')
    commit = re.search(r'commitRunSettlement\(([^)]*)\)', boot_server).group(1)
    assert 'reason' not in commit, 'the stored settlement must not depend on the end reason'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    static()
    body = (ROOT / 'src/server/RunLifecycle.luau').read_text(encoding='utf-8').replace('--!strict', '')
    code = HARNESS.replace('@@MODULE@@', body)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'peaceful.luau'
        path.write_text(code, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
