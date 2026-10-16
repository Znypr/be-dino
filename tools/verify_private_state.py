"""BD-360: owner-only player state (docs/112). Player attributes replicate to EVERY client, so private values moved to a
RemoteEvent channel (src/shared/PrivateStateCore.luau, src/server/PrivateState.luau, src/client/PrivateState.luau).

Static checks (no runtime needed):
  * every name set on a Player (receiver `player`/`claimant`) in src/server is classified PRIVATE or PUBLIC, and no PRIVATE
    name is ever set as, or read from, a Player attribute (reads must go through PrivateState.get / onChanged)
  * every SetAttribute receiver in src/server and src/shared is known (a new receiver must be classified here)
  * every PRIVATE name is set somewhere through PrivateState.set; PRIVATE and PUBLIC are disjoint
Runtime checks (pinned Luau, mocked Remote/Players/clock) run the REAL Core, server and client modules:
  snapshot on join, coalescing, order, dedupe, owner-only delivery, gap resync, reconnect, loading state, payload sizes.
Size report: public/private bytes before and after, taken from the 12-player simulation (tools/verify_multiplayer_sim.py).

    python tools/verify_private_state.py --runner /path/to/luau
"""
from __future__ import annotations

import argparse
import contextlib
import io
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

PLAYER_RECEIVERS = {"player", "claimant"}
OTHER_RECEIVERS = {
    "workspace", "character", "c", "part", "model", "folder", "container", "viewport", "target", "root", "copy", "pickup",
    "entry.model", "mesh", "visual", "p", "state.character", "shell", "l", "image", "e", "disc", "attacker.character",
    "winner.character", "t.part", "holder",
}
PUBLIC_BYTES_LIMIT = 2048


def core_tables() -> tuple[list[str], dict[str, str]]:
    text = (ROOT / "src/shared/PrivateStateCore.luau").read_text(encoding="utf-8")
    private_block = text.split("local PRIVATE = {", 1)[1].split("\n}", 1)[0]
    public_block = text.split("local PUBLIC: {[string]: string} = {", 1)[1].split("\n}", 1)[0]
    private = re.findall(r'"([A-Za-z0-9_]+)"', private_block)
    public = dict(re.findall(r'([A-Za-z0-9_]+) = "([a-z]+)"', public_block))
    return private, public


def static_checks() -> list[str]:
    problems: list[str] = []
    private, public = core_tables()
    if len(set(private)) != len(private):
        problems.append("duplicate names in the PRIVATE list")
    both = set(private) & set(public)
    if both:
        problems.append("names both PRIVATE and PUBLIC: " + ", ".join(sorted(both)))
    private_set = set(private)
    receivers_seen: set[str] = set()
    set_by_player: dict[str, list[str]] = {}
    private_set_through_state: set[str] = set()
    for folder in ("src/server", "src/shared"):
        for path in sorted((ROOT / folder).glob("*.luau")):
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r'([A-Za-z_][A-Za-z0-9_.]*):SetAttribute\(\s*("([A-Za-z0-9_]+)"|[^"\s])', text):
                receiver, literal = match.group(1), match.group(3)
                receivers_seen.add(receiver)
                if receiver in PLAYER_RECEIVERS:
                    if literal is None:
                        problems.append(f"{path.name}: dynamic name set on a Player ({match.group(0)}): classify it first")
                        continue
                    set_by_player.setdefault(literal, []).append(path.name)
                elif receiver not in OTHER_RECEIVERS:
                    problems.append(f"{path.name}: unknown SetAttribute receiver '{receiver}': add it to PLAYER_RECEIVERS or OTHER_RECEIVERS")
            for match in re.finditer(r'PrivateState\.(set|get)\(\s*([A-Za-z_]+),\s*("([A-Za-z0-9_]+)"|[^"\s,)]+)', text):
                if match.group(4) is None:
                    continue  # a table-driven name (Leaderboards) is checked at run time by the assert in set
                if match.group(4) not in private_set:
                    problems.append(f"{path.name}: PrivateState.{match.group(1)} with a non-private name {match.group(4)}")
                if match.group(1) == "set":
                    private_set_through_state.add(match.group(4))
    for name, files in sorted(set_by_player.items()):
        if name in private_set:
            problems.append(f"{', '.join(sorted(set(files)))}: private name '{name}' is set as a Player attribute (use PrivateState.set)")
        elif name not in public:
            problems.append(f"{', '.join(sorted(set(files)))}: Player attribute '{name}' is not classified (add it to PRIVATE or PUBLIC in PrivateStateCore)")
    for name in sorted(public):
        if name not in set_by_player:
            problems.append(f"PUBLIC name '{name}' is never set on a Player: remove it from the table")
    for name in private:
        if name not in private_set_through_state:
            problems.append(f"PRIVATE name '{name}' is never set through PrivateState.set")
    # reads of private names must not go to Player attributes, anywhere
    for folder in ("src/server", "src/shared", "src/client", "src/loading"):
        for path in sorted((ROOT / folder).glob("*.luau")):
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r'\b(player|claimant|localPlayer|LocalPlayer)[A-Za-z]*:(GetAttribute|GetAttributeChangedSignal)\(\s*"([A-Za-z0-9_]+)"', text):
                if match.group(3) in private_set:
                    problems.append(f"{path.name}: reads private '{match.group(3)}' from a Player attribute (use PrivateState)")
    boot = (ROOT / "src/client/Bootstrap.client.luau").read_text(encoding="utf-8")
    if "require(script.Parent.PrivateState)" not in boot:
        problems.append("Bootstrap.client does not require PrivateState")
    if "require(script.Parent.PrivateState).start()" not in (ROOT / "src/server/Bootstrap.server.luau").read_text(encoding="utf-8"):
        problems.append("Bootstrap.server does not start PrivateState")
    return problems


def wrapped(path: str) -> str:
    return "(function()\n" + (ROOT / path).read_text(encoding="utf-8") + "\nend)()"


LUAU = r'''
local failures, total = 0, 0
local function check(name, ok, detail)
    total += 1
    if not ok then failures += 1 print("[FAIL] " .. name .. " (" .. tostring(detail) .. ")") end
end

-- virtual clock and scheduler
local clock = 0
local timers = {}
local task = {
    delay = function(seconds, fn, ...) table.insert(timers, {at = clock + seconds, fn = fn, args = table.pack(...)}) end,
    spawn = function(fn, ...) local co = coroutine.create(fn) coroutine.resume(co, ...) end,
    wait = function(s) if coroutine.isyieldable() then coroutine.yield() end return s end,
}
local function advance(seconds)
    clock += seconds
    table.sort(timers, function(a, b) return a.at < b.at end)
    while timers[1] and timers[1].at <= clock do
        local t = table.remove(timers, 1)
        t.fn(table.unpack(t.args, 1, t.args.n))
    end
end
local os = {clock = function() return clock end, time = os.time}

local function signal()
    local s = {fns = {}}
    function s:Connect(f) table.insert(self.fns, f) return {Disconnect = function() end} end
    function s:fire(...) for _, f in self.fns do f(...) end end
    return s
end

local Core = @@CORE@@
local sentLog = {} -- every FireClient: {to=, message=}
local remote = setmetatable({OnServerEvent = signal(), OnClientEvent = signal(), serverCalls = {}}, {__newindex = function(t, k, v)
    rawset(t, k, v)
    if k == "Parent" and type(v) == "table" and v.children then v.children[t.Name] = t end
end})
function remote:FireClient(player, message) table.insert(sentLog, {to = player, message = message}) end
function remote:FireServer(...) table.insert(self.serverCalls, table.pack(...)) end
function remote:IsA(c) return c == "RemoteEvent" end
local folder = {children = {}}
function folder:FindFirstChild(n) return self.children[n] end
local playersService = {PlayerRemoving = signal()}
local services = {Players = playersService, ReplicatedStorage = {FindFirstChild = function(_, n) return if n == "BeDinoRemotes" then folder else nil end, Shared = {PrivateStateCore = "Core"}}}
local game = {GetService = function(_, n) return services[n] end}
local Instance = {new = function(class)
    local o = setmetatable({ClassName = class}, {__newindex = function(t, k, v)
        rawset(t, k, v)
        if k == "Parent" and type(v) == "table" and v.children then v.children[t.Name] = t end
    end})
    if class == "RemoteEvent" then return remote end
    return o
end}
local require = function(id) return Core end
local script = {Parent = {}}
local Server = @@SERVER@@
Server.start()
check("remote created in BeDinoRemotes", folder.children.PrivateState == remote)

local function player(id) return {UserId = id, Name = "P" .. id, Parent = true} end
local function sentTo(p) local out = {} for _, e in sentLog do if e.to == p then table.insert(out, e.message) end end return out end
local function hello(p) remote.OnServerEvent:fire(p, "hello") end

-- 1. classification
local seen = 0
for _, name in Core.PrivateNames do seen += 1 check("private name classified: " .. name, Core.classify(name) == "private") end
for name in Core.Public do check("public name classified: " .. name, Core.classify(name) == "public") check("public not private: " .. name, not Core.isPrivate(name)) end
check("unknown name is unclassified", Core.classify("NotAThing") == nil)
check("set refuses a non-private name", not pcall(Server.set, player(0), "EquippedBig", true))

-- 2. snapshot on join: values set BEFORE hello are held, nothing is sent, hello sends one full snapshot
local a, b = player(1), player(2)
Server.set(a, "CollectionJson", string.rep("x", 6900))
Server.set(a, "Crystals", 120)
Server.set(a, "NextChestId", "egg-1")
Server.set(b, "Crystals", 5)
advance(1)
check("nothing sent before hello", #sentLog == 0, #sentLog)
hello(a)
local sa = sentTo(a)
check("hello gives one snapshot to the owner only", #sentLog == 1 and #sa == 1 and sa[1].k == "s", #sentLog)
check("snapshot holds all three values", sa[1].d.CollectionJson ~= nil and sa[1].d.Crystals == 120 and sa[1].d.NextChestId == "egg-1")
check("snapshot never holds another player's value", sa[1].d.Crystals ~= 5)
check("get reads the server copy", Server.get(a, "Crystals") == 120 and Server.get(b, "Crystals") == 5 and Server.get(a, "Nope") == nil)
hello(a) -- inside the 0.5 s guard: ignored
check("a repeated hello inside 0.5 s is ignored", #sentLog == 1, #sentLog)
advance(1)
hello(a)
check("a later hello resends a snapshot (resync)", #sentTo(a) == 2)

-- client cache applies it
local cache = Core.newCache()
local changed, problem = Core.apply(cache, sentTo(a)[2])
check("client applies the snapshot", problem == nil and cache.received and cache.values.Crystals == 120 and #changed == 3, tostring(problem) .. #changed)

-- 3. coalescing: many sets inside one window leave as ONE delta, in set order, only final values
local before = #sentLog
for i = 1, 50 do Server.set(a, "Crystals", 120 + i) end
Server.set(a, "LastChestBig", true)
Server.set(a, "LastChestShiny", false)
Server.set(a, "LastClaimedChestId", "egg-1")
check("nothing leaves inside the window", #sentLog == before)
advance(0.1)
check("still nothing at 0.1 s", #sentLog == before)
advance(0.15)
check("exactly one delta after the window", #sentLog == before + 1, #sentLog - before)
local delta = sentLog[#sentLog].message
check("the delta is addressed to the owner", sentLog[#sentLog].to == a)
check("the delta carries only the final Crystals", delta.k == "d" and delta.d.Crystals == 170)
check("the delta lists changes in set order, claim id last", delta.o[1] == "Crystals" and delta.o[#delta.o] == "LastClaimedChestId", table.concat(delta.o, ","))
check("the delta is small", Core.bytes(delta) < 260, Core.bytes(delta))
local order = {}
local c2 = Core.apply(cache, delta)
check("client applies the delta and reports the names in order", cache.values.Crystals == 170 and cache.values.LastClaimedChestId == "egg-1" and c2[#c2] == "LastClaimedChestId")
check("the unchanged big value is not resent", delta.d.CollectionJson == nil)

-- 4. dedupe: same value, or a value set back to what the client has, sends nothing
local n0 = #sentLog
Server.set(a, "Crystals", 170) advance(1)
check("same value sends nothing", #sentLog == n0)
Server.set(a, "Crystals", 999) Server.set(a, "Crystals", 170) advance(1)
check("set and set back inside one window sends nothing", #sentLog == n0, #sentLog - n0)
Server.set(a, "NextChestId", nil) advance(1)
local removal = sentLog[#sentLog].message
check("a value set to nil is sent as a removal", removal.x ~= nil and removal.x[1] == "NextChestId")
Core.apply(cache, removal)
check("client removes it", cache.values.NextChestId == nil)

-- 5. owner only with two players
Server.sendSnapshot(b)
Server.set(b, "Crystals", 77) advance(1)
for _, e in sentLog do
    if e.to == a then check("player a never receives b's value", e.message.d.Crystals ~= 77) end
end
check("b received its own delta", #sentTo(b) == 2)

-- 6. gap: a lost delta asks for a resync, an old duplicate is ignored
local cache2 = Core.newCache()
Core.apply(cache2, {k = "s", v = 1, d = {Crystals = 1}})
local _, gap = Core.apply(cache2, {k = "d", v = 3, o = {"Crystals"}, d = {Crystals = 3}})
check("a skipped delta is a gap", gap == "gap")
local _, dup = Core.apply(cache2, {k = "d", v = 1, o = {"Crystals"}, d = {Crystals = 9}})
check("an old duplicate is ignored", dup == nil and cache2.values.Crystals == 1)
local _, early = Core.apply(Core.newCache(), {k = "d", v = 1, o = {"Crystals"}, d = {Crystals = 9}})
check("a delta before any snapshot asks for one", early == "gap")
check("a malformed message is refused", select(2, Core.apply(cache2, "x")) == "bad" and select(2, Core.apply(cache2, {k = "s"})) == "bad")
Core.apply(cache2, {k = "s", v = 2, d = {Crystals = 1, EquippedBig = true}})
check("a snapshot drops names that are not private", cache2.values.EquippedBig == nil)

-- 7. reconnect: forget (release) then a new Player object says hello and gets everything again
local a2 = player(1)
check("the new session starts empty", Server.get(a2, "Crystals") == nil)
Server.set(a2, "Crystals", 170) Server.set(a2, "CollectionJson", "{}")
hello(a2)
local fresh = sentTo(a2)
check("a rejoin receives a full snapshot", #fresh == 1 and fresh[1].k == "s" and fresh[1].d.Crystals == 170 and fresh[1].v == 1)
Server.forget(a)
check("forget drops the owner's values", Server.get(a, "Crystals") == nil)
local nf = #sentLog
Server.set(a, "Crystals", 1) advance(1)
check("nothing is sent to a forgotten player", #sentLog == nf)
playersService.PlayerRemoving:fire(a2)
Server.set(a2, "Crystals", 2) advance(1)
check("nothing is sent after the player is leaving", #sentTo(a2) == 1)
check("values stay readable on the server while leaving", Server.get(a2, "Crystals") == 2)

-- 8. sizes
local snapshotBytes = Core.bytes(sa[1])
print("SIZE|snapshot with a 6.9 KB collection|" .. snapshotBytes)
check("a snapshot is about the size of its values", snapshotBytes < 7100 + 100, snapshotBytes)
print("SIZE|delta after a hatch (10 values)|" .. Core.bytes(delta))

-- 9. the client module, run for real against a mocked remote
local clientRemote = {OnClientEvent = signal(), serverCalls = {}}
function clientRemote:FireServer(...) table.insert(self.serverCalls, table.pack(...)) end
function clientRemote:IsA(c) return c == "RemoteEvent" end
local attrs = {EquippedBig = true}
local localPlayer = {GetAttribute = function(_, n) return attrs[n] end, GetAttributeChangedSignal = function(_, n) return signal() end}
local clientFolder = {WaitForChild = function(_, n) return clientRemote end}
local rs = {WaitForChild = function(_, n)
    if n == "BeDinoRemotes" then return clientFolder end
    return {WaitForChild = function() return "Core" end}
end}
local clientServices = {Players = {LocalPlayer = localPlayer}, ReplicatedStorage = rs}
do
    local game = {GetService = function(_, n) return clientServices[n] end}
    local script = {Parent = {}}
    local warn = function() end
    local Client = @@CLIENT@@
    check("client sent hello on start", #clientRemote.serverCalls >= 1 and clientRemote.serverCalls[1][1] == "hello")
    check("before the snapshot nothing is ready", Client.isReady() == false and Client.get("Crystals") == nil and Client.num("Crystals") == 0 and Client.str("NextChestId") == "" and Client.str("NextChestId", "none") == "none")
    check("public names read the attribute", Client.get("EquippedBig") == true)
    local log = {}
    Client.onChanged("Crystals", function(v) table.insert(log, "Crystals=" .. tostring(v)) end)
    Client.onChanged("LastClaimedChestId", function(v) table.insert(log, "claim=" .. tostring(v) .. " big=" .. tostring(Client.get("LastChestBig"))) end)
    local anyNames = {}
    Client.onAnyChanged(function(n) table.insert(anyNames, n) end)
    Client.receive({k = "s", v = 1, d = {Crystals = 10, CollectionJson = "{}"}})
    check("after the snapshot it is ready and reads work", Client.isReady() and Client.num("Crystals") == 10 and Client.str("CollectionJson") == "{}")
    check("a snapshot fires the changed listeners", log[1] == "Crystals=10", log[1])
    Client.receive({k = "d", v = 2, o = {"LastChestBig", "LastClaimedChestId", "Crystals"}, d = {LastChestBig = true, LastClaimedChestId = "e1", Crystals = 11}})
    check("a delta applies every value before any listener runs (claim sees the big flag)", log[2] == "claim=e1 big=true", log[2])
    check("then fires the rest in order", log[3] == "Crystals=11" and anyNames[#anyNames] == "Crystals", tostring(log[3]))
    local calls = #clientRemote.serverCalls
    Client.receive({k = "d", v = 9, o = {"Crystals"}, d = {Crystals = 99}})
    check("a gap asks the server for a resync", #clientRemote.serverCalls == calls + 1 and clientRemote.serverCalls[calls + 1][1] == "resync")
    check("and does not apply the bad delta", Client.num("Crystals") == 11)
    local conn = Client.onChanged("Crystals", function() table.insert(log, "never") end)
    conn.Disconnect()
    Client.receive({k = "d", v = 3, o = {"Crystals"}, d = {Crystals = 12}})
    check("Disconnect stops a listener", not table.find(log, "never"))
end

print("RESULT|" .. total .. "|" .. failures)
'''


def build_luau() -> str:
    return (LUAU.replace("@@CORE@@", wrapped("src/shared/PrivateStateCore.luau"))
            .replace("@@SERVER@@", wrapped("src/server/PrivateState.luau"))
            .replace("@@CLIENT@@", wrapped("src/client/PrivateState.luau")))


def sim_sizes(runner: str) -> dict[str, int]:
    import verify_multiplayer_sim
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = verify_multiplayer_sim.main(["--runner", runner])
    text = buffer.getvalue()
    if code != 0:
        print(text[-2000:])
        raise SystemExit("the 12-player simulation failed: no size report")
    found: dict[str, int] = {}
    for key, label in (("public_fresh", "PUBLIC player attribute bytes, fresh profile"),
                       ("public_after", "PUBLIC player attribute bytes, after 10 runs of 40 eggs"),
                       ("private_fresh", "PRIVATE owner-only bytes, fresh profile"),
                       ("private_after", "PRIVATE owner-only bytes, after 10 runs of 40 eggs")):
        match = re.search(re.escape(label) + r"[^=]*= (\d+)", text)
        if not match:
            raise SystemExit("size metric missing from the simulation: " + label)
        found[key] = int(match.group(1))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    args = parser.parse_args(argv)
    problems = static_checks()
    with tempfile.TemporaryDirectory() as folder:
        script = Path(folder) / "private_state.luau"
        script.write_text(build_luau(), encoding="utf-8")
        done = subprocess.run([args.runner, str(script)], capture_output=True, text=True)
    lines = done.stdout.splitlines()
    result = [line for line in lines if line.startswith("RESULT|")]
    for line in lines:
        if line.startswith("[FAIL]"):
            print(line)
        elif line.startswith("SIZE|"):
            _, label, value = line.split("|")
            print(f"  SIZE  {label}: {value} bytes")
    if done.returncode != 0 or not result:
        print(done.stdout[-3000:])
        print(done.stderr[-3000:])
        print("Private state runtime test did not complete.")
        return 1
    total, failed = (int(x) for x in result[0].split("|")[1:3])
    sizes = sim_sizes(args.runner)
    everything = sizes["public_after"] + sizes["private_after"]
    print("  SIZE  per-player Player-attribute bytes (replicated to ALL clients), mid-game after 10 runs of 40 eggs:")
    print(f"        before BD-360: {everything} (all {everything} were attributes)   after: {sizes['public_after']}   owner-only: {sizes['private_after']}")
    print(f"        fresh profile: before {sizes['public_fresh'] + sizes['private_fresh']}   after {sizes['public_fresh']}")
    print(f"        12 players, full resync to 11 receivers each: before {everything * 11 * 12}   after {sizes['public_after'] * 11 * 12}")
    if sizes["public_after"] >= PUBLIC_BYTES_LIMIT:
        problems.append(f"public attribute bytes {sizes['public_after']} >= {PUBLIC_BYTES_LIMIT}")
    for problem in problems:
        print("[FAIL] " + problem)
    ok = failed == 0 and not problems
    print(f"Private state {'passed' if ok else 'FAILED'}: {total - failed}/{total} runtime checks, {len(problems)} static problem(s).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
