-- Remote fuzz harness (docs/151, BD-608 audit). Built and run by tools/verify_remote_fuzz.py, which fills the four tables below: the
-- sources of every src/server and src/shared module under 140 KB (embedded as strings), the playtest profile's real Config values,
-- the feature flags that ship off (turned on to exercise the dormant handlers) and the reviewed remote inventory. The REAL server
-- modules run unmodified on a virtual clock with a mocked DataStore (latency, the per-server request budget and transient failures,
-- like tools/verify_load.py). Nothing here proves Roblox networking: it proves what each handler does with the arguments a hostile
-- client can send, how often, and in what order.
--
-- Output protocol: REPORT|text, CHECK|PASS/FAIL|name|detail, DONE|total|failed.

local SOURCES = __SOURCES__
local PLAYTEST = __PLAYTEST__
local FLAGS_ON = __FLAGS_ON__
local EXPECTED = __EXPECTED__
local STORM_SECONDS = __STORM__ -- length of the request storms (60 in CI; 120 for the numbers in the audit document)
local ONLY = __ONLY__ -- run only the scenarios whose name contains this text (empty = all)

-------------------------------------------------------------------- checks
local CHECKS = {}
local function check(name, cond, detail)
    table.insert(CHECKS, {name = name, ok = cond == true, detail = tostring(detail or "")})
end
local REPORT = {}
local function report(text) table.insert(REPORT, text) end

-------------------------------------------------------------------- scheduler (virtual clock, cooperative coroutines)
local now = 0
local queue = {}
local seq = 0
local crashes = {}
local function schedule(at, co, ...)
    seq += 1
    table.insert(queue, {at = at, seq = seq, co = co, args = table.pack(...)})
end
local function sleep(seconds)
    schedule(now + math.max(0, seconds or 0), coroutine.running())
    return coroutine.yield()
end
local function runQueue(untilTime, stop)
    local steps = 0
    while #queue > 0 do
        if stop and stop() then break end
        steps += 1
        if steps > 2000000 then table.insert(crashes, "scheduler step limit (runaway loop?)") break end
        local best = 1
        for i = 2, #queue do
            local a, b = queue[i], queue[best]
            if a.at < b.at or (a.at == b.at and a.seq < b.seq) then best = i end
        end
        local item = table.remove(queue, best)
        if item.at > untilTime then table.insert(queue, item) break end
        now = math.max(now, item.at)
        if coroutine.status(item.co) == "suspended" then
            local ok, err = coroutine.resume(item.co, table.unpack(item.args, 1, item.args.n))
            if not ok then table.insert(crashes, tostring(err)) end
        end
    end
end
local task = {
    wait = function(s) sleep(s or 0) return s or 0 end,
    spawn = function(f, ...)
        local co = if type(f) == "thread" then f else coroutine.create(f)
        schedule(now, co, ...)
        return co
    end,
    delay = function(s, f, ...) local co = coroutine.create(f) schedule(now + s, co, ...) return co end,
    defer = function(f, ...) local co = coroutine.create(f) schedule(now, co, ...) return co end,
}
local vos = setmetatable({time = function() return math.floor(now) + 1700000000 end, clock = function() return now end}, {__index = os})

local function minstd(seed)
    local s = (seed % 2147483646) + 1
    return function()
        s = (s * 48271) % 2147483647
        return s / 2147483647
    end
end
local seedSource = minstd(20261017)
local Random = {new = function(seed)
    local nextValue = minstd(seed or math.floor(seedSource() * 2147483646))
    local r = {}
    function r:NextNumber(a, b) local x = nextValue() if a then return a + (b - a) * x end return x end
    function r:NextInteger(a, b) return a + math.floor(nextValue() * (b - a + 1)) end
    return r
end}

local function deepcopy(v)
    if type(v) ~= "table" then return v end
    local out = {}
    for k, x in v do out[deepcopy(k)] = deepcopy(x) end
    return out
end

-------------------------------------------------------------------- a real JSON round trip (strings, not tables)
local function jsonEncode(v, depth)
    depth = depth or 0
    if depth > 100 then error("JSONEncode: depth") end
    local t = type(v)
    if t == "nil" then return "null" end
    if t == "boolean" then return if v then "true" else "false" end
    if t == "number" then
        if v ~= v or v == math.huge or v == -math.huge then error("JSONEncode: cannot encode " .. tostring(v)) end
        if v % 1 == 0 and math.abs(v) < 1e15 then return string.format("%d", v) end
        return string.format("%.17g", v)
    end
    if t == "string" then
        return '"' .. string.gsub(v, '[%c"\\]', function(c)
            if c == '"' then return '\\"' elseif c == "\\" then return "\\\\" end
            return string.format("\\u%04x", string.byte(c))
        end) .. '"'
    end
    if t ~= "table" then error("JSONEncode: cannot encode " .. t) end
    local n, count = #v, 0
    for _ in v do count += 1 end
    if count == 0 then return "[]" end
    if n == count then
        local parts = table.create(n)
        for i = 1, n do parts[i] = jsonEncode(v[i], depth + 1) end
        return "[" .. table.concat(parts, ",") .. "]"
    end
    local keys = {}
    for k in v do
        if type(k) ~= "string" then error("JSONEncode: mixed or non-string keys") end
        table.insert(keys, k)
    end
    table.sort(keys)
    local parts = {}
    for _, k in keys do table.insert(parts, jsonEncode(k, depth + 1) .. ":" .. jsonEncode(v[k], depth + 1)) end
    return "{" .. table.concat(parts, ",") .. "}"
end
local function jsonDecode(s)
    if type(s) ~= "string" then error("JSONDecode: not a string") end
    local i = 1
    local function ws() while true do local c = string.sub(s, i, i) if c == " " or c == "\n" or c == "\t" or c == "\r" then i += 1 else break end end end
    local value
    local function str()
        i += 1
        local out = {}
        while true do
            local c = string.sub(s, i, i)
            if c == "" then error("JSONDecode: unterminated string") end
            if c == '"' then i += 1 break end
            if c == "\\" then
                local n = string.sub(s, i + 1, i + 1)
                if n == "u" then table.insert(out, utf8.char(tonumber(string.sub(s, i + 2, i + 5), 16) or 63)) i += 6
                else table.insert(out, ({n = "\n", t = "\t", r = "\r", b = "\b", f = "\f"})[n] or n) i += 2 end
            else table.insert(out, c) i += 1 end
        end
        return table.concat(out)
    end
    function value()
        ws()
        local c = string.sub(s, i, i)
        if c == "{" then
            i += 1 local obj = {} ws()
            if string.sub(s, i, i) == "}" then i += 1 return obj end
            while true do
                ws() if string.sub(s, i, i) ~= '"' then error("JSONDecode: key") end
                local k = str() ws()
                if string.sub(s, i, i) ~= ":" then error("JSONDecode: colon") end
                i += 1 obj[k] = value() ws()
                local d = string.sub(s, i, i) i += 1
                if d == "}" then return obj elseif d ~= "," then error("JSONDecode: object") end
            end
        elseif c == "[" then
            i += 1 local arr = {} ws()
            if string.sub(s, i, i) == "]" then i += 1 return arr end
            while true do
                table.insert(arr, value()) ws()
                local d = string.sub(s, i, i) i += 1
                if d == "]" then return arr elseif d ~= "," then error("JSONDecode: array") end
            end
        elseif c == '"' then return str()
        elseif string.sub(s, i, i + 3) == "true" then i += 4 return true
        elseif string.sub(s, i, i + 4) == "false" then i += 5 return false
        elseif string.sub(s, i, i + 3) == "null" then i += 4 return nil
        else
            local num = string.match(s, "^-?%d+%.?%d*[eE]?[+-]?%d*", i)
            if not num or num == "" then error("JSONDecode: unexpected '" .. c .. "'") end
            i += #num return tonumber(num)
        end
    end
    local result = value() ws()
    if i <= #s then error("JSONDecode: trailing data") end
    return result
end

-------------------------------------------------------------------- Roblox value mocks (only what the server modules touch)
local V3 = {}
V3.__index = V3
local function v3(x, y, z) return setmetatable({X = x, Y = y, Z = z}, V3) end
V3.__add = function(a, b) return v3(a.X + b.X, a.Y + b.Y, a.Z + b.Z) end
V3.__sub = function(a, b) return v3(a.X - b.X, a.Y - b.Y, a.Z - b.Z) end
V3.__mul = function(a, b)
    if type(a) == "number" then return v3(a * b.X, a * b.Y, a * b.Z) end
    if type(b) == "number" then return v3(a.X * b, a.Y * b, a.Z * b) end
    return v3(a.X * b.X, a.Y * b.Y, a.Z * b.Z)
end
V3.__div = function(a, b) return v3(a.X / b, a.Y / b, a.Z / b) end
V3.__unm = function(a) return v3(-a.X, -a.Y, -a.Z) end
V3.__eq = function(a, b) return a.X == b.X and a.Y == b.Y and a.Z == b.Z end
V3.__index = function(t, k)
    if k == "Magnitude" then return math.sqrt(t.X * t.X + t.Y * t.Y + t.Z * t.Z) end
    if k == "Unit" then local m = math.sqrt(t.X * t.X + t.Y * t.Y + t.Z * t.Z) return if m == 0 then v3(0, 0, 0) else v3(t.X / m, t.Y / m, t.Z / m) end
    if k == "Dot" then return function(a, b) return a.X * b.X + a.Y * b.Y + a.Z * b.Z end end
    return rawget(V3, k)
end
local Vector3 = {new = function(x, y, z) return v3(x or 0, y or 0, z or 0) end, zero = v3(0, 0, 0), one = v3(1, 1, 1), xAxis = v3(1, 0, 0), yAxis = v3(0, 1, 0), zAxis = v3(0, 0, 1)}
local Vector2 = {new = function(x, y)
    return setmetatable({X = x or 0, Y = y or 0}, {
        __sub = function(a, b) return setmetatable({X = a.X - b.X, Y = a.Y - b.Y}, getmetatable(a)) end,
        __index = function(t, k) if k == "Magnitude" then return math.sqrt(t.X * t.X + t.Y * t.Y) end end})
end}
local CF = {}
CF.__index = function(t, k)
    if k == "Position" then return t.p end
    if k == "LookVector" then return t.look end
    return rawget(CF, k)
end
local function cf(p, look) return setmetatable({p = p, look = look or v3(0, 0, -1)}, CF) end
CF.__mul = function(a, b) if getmetatable(b) == V3 then return a.p + b end return cf(a.p + (b.p or v3(0, 0, 0)), a.look) end
CF.__add = function(a, b) return cf(a.p + b, a.look) end
local CFrame = {new = function(x, y, z) if type(x) == "table" then return cf(x) end return cf(v3(x or 0, y or 0, z or 0)) end,
    Angles = function() return cf(v3(0, 0, 0)) end, lookAt = function(from, to) local d = to - from return cf(from, d.Unit) end}
local Color3 = {new = function(r, g, b) return {R = r, G = g, B = b} end, fromRGB = function(r, g, b) return {R = r / 255, G = g / 255, B = b / 255} end}
local enumCache = {}
local Enum = setmetatable({}, {__index = function(_, group)
    enumCache[group] = enumCache[group] or setmetatable({}, {__index = function(t, item)
        local e = {Name = item, EnumType = group}
        rawset(t, item, e)
        return e
    end})
    return enumCache[group]
end})
local RaycastParams = {new = function() return {} end}

-- A permissive stand-in for engine objects the fuzz does not care about (Lighting, PhysicsService, textures...).
local function Any(name)
    local t = {}
    local meta = {}
    meta.__index = function(self, k)
        if k == "Name" then return name end
        local child = Any(name .. "." .. tostring(k))
        rawset(self, k, child)
        return child
    end
    meta.__call = function() return Any(name .. "()") end
    meta.__add = function() return 0 end meta.__sub = function() return 0 end meta.__mul = function() return 0 end
    meta.__div = function() return 0 end meta.__unm = function() return 0 end
    meta.__lt = function() return false end meta.__le = function() return false end
    meta.__len = function() return 0 end
    meta.__tostring = function() return name end
    return setmetatable(t, meta)
end

-------------------------------------------------------------------- the module loader
local nodes = {}
local function exists(path)
    if SOURCES[path] then return true end
    for key in SOURCES do if string.sub(key, 1, #path + 1) == path .. "/" then return true end end
    return false
end
local function node(path)
    if nodes[path] then return nodes[path] end
    local n = {__path = path}
    setmetatable(n, {__index = function(_, k)
        if k == "Parent" then local parent = string.match(path, "^(.*)/[^/]+$") return parent and node(parent) end
        if k == "Name" then return string.match(path, "[^/]+$") end
        if k == "WaitForChild" then return function(_, c) return node(path .. "/" .. c) end end
        if k == "FindFirstChild" then return function(_, c) local p = path .. "/" .. c return if exists(p) then node(p) else nil end end
        return node(path .. "/" .. k)
    end})
    nodes[path] = n
    return n
end

-------------------------------------------------------------------- mock Instances and remotes
local function signal()
    local s = {fns = {}}
    function s:Connect(f) table.insert(self.fns, f) return {Disconnect = function() end} end
    function s:Wait() return coroutine.yield() end
    return s
end

local ENV -- the server under test
local function newInstance(className)
    local o = {ClassName = className, Name = className, children = {}, attrs = {}, OnServerEvent = signal(), Changed = signal(), Triggered = signal(),
        Heartbeat = signal(), Parent = nil, fired = {}}
    local methods = {}
    function methods.FindFirstChild(self, n) return self.children[n] end
    function methods.WaitForChild(self, n) return self.children[n] or error("WaitForChild: " .. tostring(n) .. " would hang") end
    function methods.FindFirstChildOfClass(self, c) for _, ch in self.children do if ch.ClassName == c then return ch end end return nil end
    function methods.FindFirstChildWhichIsA(self, c) for _, ch in self.children do if ch.ClassName == c then return ch end end return nil end
    function methods.GetChildren(self) local list = {} for _, ch in self.children do table.insert(list, ch) end return list end
    function methods.GetDescendants(self) return {} end
    function methods.Destroy(self) if self.Parent then self.Parent.children[self.Name] = nil end self.Parent = nil self.destroyed = true end
    function methods.Clone(self) return deepcopy(self) end
    function methods.IsA(self, c) return c == self.ClassName or c == "Instance" or (c == "BasePart" and (self.ClassName == "Part" or self.ClassName == "MeshPart")) end
    function methods.IsDescendantOf(self) return true end
    function methods.SetAttribute(self, k, v) self.attrs[k] = v end
    function methods.GetAttribute(self, k) return self.attrs[k] end
    function methods.GetAttributeChangedSignal() return signal() end
    function methods.FireClient(self, to, ...) table.insert(self.fired, {to = to, args = table.pack(...)}) if ENV then ENV.firedTotal += 1 end end
    function methods.FireAllClients(self, ...) table.insert(self.fired, {all = true, args = table.pack(...)}) end
    function methods.PivotTo() end
    function methods.ScaleTo() end
    return setmetatable(o, {
        __index = function(t, k) local m = methods[k] if m ~= nil then return m end return t.children[k] end,
        __newindex = function(t, k, v)
            rawset(t, k, v)
            if k == "Parent" and type(v) == "table" and rawget(v, "children") then v.children[rawget(t, "Name")] = t end
            if k == "Parent" and type(v) == "table" then
                -- the registry: every remote the services create
                if (t.ClassName == "RemoteEvent" or t.ClassName == "RemoteFunction") and ENV then ENV.remotes[t.Name] = t end
            end
        end,
    })
end

-------------------------------------------------------------------- the server under test
local DATA = {} -- profile store: key -> table
local GIFTDATA = {} -- gifts store
local LEASE_HOLDER = nil
local M -- metrics
local SCENARIO_FAIL_RATE = 0
local SCENARIO_AMBIGUOUS_RATE = 0
local AMBIGUOUS_NEXT = 0 -- the next N store calls apply their write and then lose the acknowledgement (deterministic version of the rate above)
local OPLABEL = setmetatable({}, {__mode = "k"})
local LATENCY_RNG = minstd(77)

local function newMetrics()
    return {requests = 0, throttled = 0, queueDrops = 0, writes = 0, transforms = 0, transientErrors = 0, ambiguous = 0, warnings = 0, byKeyWrites = {}, printed = {}, warned = {}}
end

-- Pure modules that cost seconds to build in the plain interpreter and do not depend on any flag the scenarios flip: built once, shared by every server.
local SHARED_MODULES = {["src/shared/CaveHubLayout"] = true}
local SHARED_CACHE = {}
local newCharFor
local function bootServer(name, overrides, opts)
    opts = opts or {}
    local server = {name = name, players = {}, cache = {}, remotes = {}, firedTotal = 0, bucket = nil, last = 0, waiting = 0, warnings = {}, prints = {}}
    ENV = server
    function server.rate() return 60 + 10 * math.max(1, #server.players) end
    local function refill()
        if server.bucket == nil then server.bucket = server.rate() server.last = now return end
        server.bucket = math.min(server.rate(), server.bucket + (now - server.last) * server.rate() / 60)
        server.last = now
    end
    local store = {}
    function store:UpdateAsync(key, transform)
        refill()
        server.bucket -= 1
        if server.bucket < 0 then
            if server.waiting >= 30 then
                server.bucket += 1
                M.queueDrops += 1
                error("DataStore throttle queue full")
            end
            server.waiting += 1
            M.throttled += 1
            sleep(-server.bucket / (server.rate() / 60))
            server.waiting -= 1
        end
        M.requests += 1
        sleep(0.06 + LATENCY_RNG() * 0.2)
        if LATENCY_RNG() < SCENARIO_FAIL_RATE then
            M.transientErrors += 1
            error("502: injected transient DataStore failure")
        end
        local result
        M.transforms += 1
        result = transform(deepcopy(DATA[key]))
        if result == nil then return nil end
        M.writes += 1
        M.byKeyWrites[key] = (M.byKeyWrites[key] or 0) + 1
        DATA[key] = deepcopy(result)
        if AMBIGUOUS_NEXT > 0 then
            AMBIGUOUS_NEXT -= 1
            M.ambiguous += 1
            error("504: acknowledgement lost after the write was applied")
        end
        if LATENCY_RNG() < SCENARIO_AMBIGUOUS_RATE then
            M.ambiguous += 1
            error("504: acknowledgement lost after the write was applied") -- the write DID happen; the caller retries
        end
        return deepcopy(result)
    end
    local giftStore = {}
    function giftStore:GetAsync(key) return deepcopy(GIFTDATA[key]) end
    function giftStore:UpdateAsync(key, transform)
        sleep(0.05)
        local result = transform(deepcopy(GIFTDATA[key]))
        if result == nil then return nil end
        GIFTDATA[key] = deepcopy(result)
        return deepcopy(result)
    end
    local guid = 0
    local policy = {restricted = false}
    local players = {PlayerAdded = signal(), PlayerRemoving = signal()}
    function players:GetPlayers() return table.clone(server.players) end
    function players:GetPlayerByUserId(id) for _, p in server.players do if p.UserId == id then return p end end return nil end
    function players:GetUserIdFromNameAsync(n) if n == "NoSuchUser" then error("not found") end return 90000 + #n end
    local services = {
        DataStoreService = {GetDataStore = function(_, n) if string.find(n, "_Gifts", 1, true) then return giftStore end return store end,
            GetOrderedDataStore = function() error("OrderedDataStore is not modelled") end},
        HttpService = {GenerateGUID = function() guid += 1 return name .. "-guid-" .. guid end, JSONEncode = function(_, v) return jsonEncode(v) end, JSONDecode = function(_, s) return jsonDecode(s) end},
        RunService = {IsStudio = function() return opts.studio == true end, IsServer = function() return true end, IsClient = function() return false end, Heartbeat = signal()},
        Players = players,
        Lighting = newInstance("Lighting"),
        PolicyService = {GetPolicyInfoForPlayerAsync = function() return {ArePaidRandomItemsRestricted = policy.restricted} end},
        TextService = {FilterStringAsync = function(_, text) return {GetNonChatStringForBroadcastAsync = function() return text end} end},
        UserService = {GetUserInfosByUserIdsAsync = function(_, ids) return {{DisplayName = "Disp" .. tostring(ids[1]), Username = "user" .. tostring(ids[1])}} end},
        PhysicsService = {IsCollisionGroupRegistered = function() return true end, RegisterCollisionGroup = function() end, CollisionGroupSetCollidable = function() end},
        MarketplaceService = newInstance("MarketplaceService"),
    }
    server.policy = policy
    server.runService = services.RunService
    server.PlayersService = players
    local RS = newInstance("ReplicatedStorage")
    RS.children.Shared = node("src/shared")
    services.ReplicatedStorage = RS
    server.RS = RS
    local workspace = newInstance("Workspace")
    workspace.Gravity = 250
    workspace.StreamingEnabled = false
    workspace.Terrain = newInstance("Terrain")
    workspace.BeDinoArena = newInstance("Folder")
    workspace.children.BeDinoArena = workspace.BeDinoArena
    workspace.attrs.IslandTerrainReady = true
    workspace.GetServerTimeNow = function() return 1.7e9 + now end
    workspace.Raycast = function() return nil end
    workspace.Blockcast = function() return nil end
    server.workspace = workspace
    server.Instance = {new = newInstance}
    local gameObj = {GameId = if opts.studio then 0 else 4242, PlaceId = 4243, JobId = "job-" .. name, CreatorType = Enum.CreatorType.User, CreatorId = 1,
        GetService = function(_, id) return services[id] or Any("service:" .. id) end}
    server.game = gameObj
    local env = {script = nil, game = gameObj, task = task, os = vos, workspace = workspace, Instance = server.Instance,
        warn = function(...) M.warnings += 1 table.insert(server.warnings, table.concat(table.pack(...), " ")) end,
        print = function(...) table.insert(server.prints, table.concat(table.pack(...), " ")) end,
        Random = Random, Vector3 = Vector3, Vector2 = Vector2, CFrame = CFrame, Color3 = Color3, Enum = Enum, RaycastParams = RaycastParams,
        typeof = function(v)
            if type(v) == "table" then
                local m = getmetatable(v)
                if m == V3 then return "Vector3" end
                if m == CF then return "CFrame" end
                if rawget(v, "ClassName") ~= nil and rawget(v, "children") ~= nil then return "Instance" end
                if rawget(v, "UserId") ~= nil and rawget(v, "attrs") ~= nil then return "Instance" end
                if rawget(v, "Name") ~= nil and rawget(v, "EnumType") ~= nil then return "EnumItem" end
            end
            return type(v)
        end}
    local function load(n)
        local path = n.__path
        if server.cache[path] ~= nil then return server.cache[path] end
        if SHARED_MODULES[path] and SHARED_CACHE[path] ~= nil then server.cache[path] = SHARED_CACHE[path] return SHARED_CACHE[path] end
        local source = SOURCES[path] or error("module not embedded in harness: " .. path)
        local chunk = assert(loadstring(source, "=" .. path))
        local fenv = table.clone(env)
        fenv.script = n
        fenv.require = load
        setfenv(chunk, setmetatable(fenv, {__index = function(_, k) local g = getfenv(0)[k] if g ~= nil then return g end return Any("global:" .. tostring(k)) end}))
        local result = chunk()
        server.cache[path] = result
        if SHARED_MODULES[path] then SHARED_CACHE[path] = result end
        return result
    end
    server.load = load
    -- release-profile values: the playtest profile, then the scenario's flags
    local config = table.clone(load(node("src/shared/Config")))
    for k, v in PLAYTEST do config[k] = v end
    if overrides then for k, v in overrides do config[k] = v end end
    server.cache["src/shared/Config"] = table.freeze(config)
    server.Config = server.cache["src/shared/Config"]
    server.newChar = newCharFor(server)
    return server
end

local function loadMod(server, path) return server.load(node(path)) end

-------------------------------------------------------------------- players
local function mockPlayer(server, userId)
    local p = {UserId = userId, Name = "P" .. userId, DisplayName = "Friend" .. userId, Parent = server.PlayersService, attrs = {}, sig = {}, respawns = 0, ClassName = "Player", children = {}}
    function p:SetAttribute(k, v)
        local old = self.attrs[k]
        self.attrs[k] = v
        if old ~= v and self.sig[k] then for _, f in self.sig[k].fns do task.spawn(f) end end
    end
    function p:GetAttribute(k) return self.attrs[k] end
    function p:GetAttributeChangedSignal(k) self.sig[k] = self.sig[k] or signal() return self.sig[k] end
    function p:Kick(message) self.kicked = message or true self.Parent = nil end
    function p:IsFriendsWith() return false end
    function p:GetRankInGroup() return 0 end
    function p:IsA(c) return c == "Player" or c == "Instance" end
    function p:RequestStreamAroundAsync() end
    p.CharacterAdded = signal()
    function p:LoadCharacterAsync()
        self.respawns += 1
        self.Character = server.newChar(self)
        for _, f in self.CharacterAdded.fns do task.spawn(f, self.Character) end
        if server.RL then server.RL.prepareSanctuary(self, self.Character) end
    end
    return p
end

newCharFor = function(server)
    return function(owner)
        local c = newInstance("Model")
        c.Name = owner.Name
        c.Parent = nil
        local humanoid = setmetatable({Died = signal(), ClassName = "Humanoid", children = {}, FloorMaterial = Enum.Material.Grass, WalkSpeed = 16, HipHeight = 2, _health = 100,
            RigType = Enum.HumanoidRigType.R15, attrs = {}}, {
            __index = function(t, k) if k == "Health" then return rawget(t, "_health") end if k == "IsA" then return function(_, c2) return c2 == "Humanoid" end end end,
            __newindex = function(t, k, v)
                if k == "Health" then
                    rawset(t, "_health", v)
                    if v <= 0 then for _, f in t.Died.fns do task.spawn(f) end end
                else rawset(t, k, v) end
            end})
        local root = newInstance("Part")
        root.Name = "HumanoidRootPart"
        root.Position = v3(0, 6, 580)
        root.CFrame = cf(v3(0, 6, 580))
        root.Size = v3(2, 2, 1)
        root.AssemblyLinearVelocity = v3(0, 0, 0)
        c.children.Humanoid = humanoid
        c.children.HumanoidRootPart = root
        c.humanoid, c.root = humanoid, root
        c:SetAttribute("DinoAttached", true)
        return c
    end
end

-------------------------------------------------------------------- profile-diff helpers
local function canon(v, depth)
    depth = depth or 0
    if depth > 60 then return "<deep>" end
    local t = type(v)
    if t == "table" then
        local keys = {}
        for k in v do table.insert(keys, k) end
        table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
        local parts = {}
        for _, k in keys do table.insert(parts, tostring(k) .. "=" .. canon(v[k], depth + 1)) end
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return tostring(v)
end
-- Everything that is wealth, inventory or progress: a malformed or unauthorised request must leave this byte for byte alone.
local WEALTH = {"collection", "eggs", "runEggBank", "eggNests", "pendingChestGrants", "progression", "metrics", "dinosaurIdentity", "purchaseReceipts", "equippedSpeciesId", "equippedVariantKey", "objectives", "ownedSkins", "claimedGifts"}
local function wealth(userId)
    local profile = DATA["u:" .. userId]
    if profile == nil then return "<none>" end
    local parts = {}
    for _, k in WEALTH do
        local value = profile[k]
        if k == "metrics" and type(value) == "table" then value = {robux = value.robux, rarest = value.rarest} end -- playSeconds moves with the lease renew
        parts[#parts + 1] = k .. "=" .. canon(value)
    end
    return table.concat(parts, ";")
end
local function crystalsOf(userId)
    local profile = DATA["u:" .. userId]
    return profile and profile.progression and profile.progression.crystals or 0
end

-------------------------------------------------------------------- scenario plumbing
TIMES = {}
local function runScenario(name, overrides, fn, opts)
    if ONLY ~= "" and not string.find(name, ONLY, 1, true) then return {name = name, skipped = true} end
    now = 0
    queue = {}
    DATA, GIFTDATA = {}, {}
    M = newMetrics()
    SCENARIO_FAIL_RATE = 0
    SCENARIO_AMBIGUOUS_RATE = 0
    AMBIGUOUS_NEXT = 0
    crashes = {}
    local cpu0 = os.clock()
    local server = bootServer(name, overrides, opts)
    local finished = false
    local failure = nil
    task.spawn(function()
        local ok, err = xpcall(function() fn(server) end, function(e) return tostring(e) .. "\n" .. debug.traceback() end)
        if not ok then failure = err else finished = true end
    end)
    runQueue(86400, function() return finished or failure ~= nil end)
    TIMES[name] = os.clock() - cpu0
    check(name .. ": scenario finished", finished, "now=" .. now .. (if failure then " error=" .. failure else ""))
    check(name .. ": no coroutine crashed", #crashes == 0, table.concat(crashes, " | "):sub(1, 1500))
    return server
end

-- Starts every server module the way Bootstrap does (order matters for the remote folder), under the mocks.
local function startServices(server, options)
    options = options or {}
    local load = function(path) return loadMod(server, path) end
    server.dinoCalls = {refresh = 0, setSpecies = 0}
    server.dino = {
        refreshForPlayer = function() server.dinoCalls.refresh += 1 end,
        setSpecies = function() server.dinoCalls.setSpecies += 1 end,
        addGrowth = function() end,
        render = function() end,
    }
    server.PS = load("src/server/PrivateState")
    server.PS.start()
    server.Repo = load("src/server/ProfileRepository")
    server.RL = load("src/server/RunLifecycle")
    server.LC = load("src/server/LeaveCoordinator")
    server.settleCalls = {}
    local leaving = server.LC.new({endForDisconnect = server.RL.endForDisconnect, release = server.Repo.release, publish = nil})
    server.leaving = leaving
    server.RL.configureSettlement(function(player, runId, catchScore, reason, eggEvents, runSeconds, nestWeather)
        server.settleCalls[runId] = (server.settleCalls[runId] or 0) + 1
        local ok, outcome, status = server.Repo.commitRunSettlement(player, runId, catchScore, eggEvents, runSeconds, nestWeather)
        leaving.settlementFinished(player)
        return ok
    end)
    server.Repo.setSettlementRecoveredHook(function(player) server.RL.recoverAfterSettlement(player) end)
    local function try(label, fn)
        local ok, err = xpcall(fn, function(e) return tostring(e) .. "\n" .. debug.traceback() end)
        if not ok then
            server.startErrors = server.startErrors or {}
            table.insert(server.startErrors, label .. ": " .. string.sub(tostring(err), 1, 300))
        end
        return ok
    end
    try("RunLifecycle", function() server.RL.start() end)
    try("ChestService", function() load("src/server/ChestService").start(server.Repo) end)
    try("CollectionService", function() load("src/server/CollectionService").start(server.Repo, server.dino) end)
    try("MutationService", function() load("src/server/MutationService").start(server.Repo, server.dino) end)
    try("VisualTestService", function() load("src/server/VisualTestService").start(server.dino) end)
    try("ProgressionService", function() load("src/server/ProgressionService").start(server.Repo) end)
    try("RareHatchService", function() load("src/server/RareHatchService").start() end)
    try("FusionService", function() load("src/server/FusionService").start(server.Repo) end)
    try("ObjectiveService", function() load("src/server/ObjectiveService").start(server.Repo) end)
    try("GiftService", function() load("src/server/GiftService").start(server.Repo) end)
    try("SkinService", function() load("src/server/SkinService").start(server.Repo) end)
    try("LeapService", function() load("src/server/LeapService").start() end)
    try("HubTravelService", function() load("src/server/HubTravelService").start() end)
    try("FeedbackService", function() load("src/server/FeedbackService").start() end)
    try("TelemetryService", function() load("src/server/TelemetryService").start() end)
    try("QaService", function() load("src/server/QaService").start() end)
    try("ClassMovementService", function() load("src/server/ClassMovementService").start() end)
    try("CombatService", function() server.combat = load("src/server/CombatService").start(server.RL, server.dino) end)
    try("AdminService", function() load("src/server/AdminService").start() end)
    try("DemoTriggerService", function() load("src/server/DemoTriggerService").start(server.Repo) end)
    server.Repo.start()
    if options.heartbeat then -- drive RunService.Heartbeat (Leap's envelope loop, Combat's tick) at 10 Hz of virtual time
        task.spawn(function()
            while true do
                task.wait(0.25)
                for _, f in server.runService.Heartbeat.fns do local ok, err = pcall(f, 0.25) if not ok then table.insert(crashes, 'Heartbeat: ' .. tostring(err)) end end
            end
        end)
    end
end

local function connect(server, userId, opts)
    opts = opts or {}
    local p = mockPlayer(server, userId)
    table.insert(server.players, p)
    for _, f in server.PlayersService.PlayerAdded.fns do task.spawn(f, p) end
    local loaded = server.Repo.load(p)
    local retries = 12
    while not loaded and p.Parent and retries > 0 and (p.attrs.ProfileState == "SessionBusy" or p.attrs.ProfileState == "LoadFailed") do
        retries -= 1
        sleep(5)
        loaded = server.Repo.load(p)
    end
    p.loaded = loaded
    if loaded then
        p.Character = server.newChar(p)
        server.RL.prepareSanctuary(p, p.Character)
        server.PS.sendSnapshot(p)
    end
    return p
end

local function disconnect(server, p)
    for _, f in server.PlayersService.PlayerRemoving.fns do
        local co = coroutine.create(f)
        local ok, err = coroutine.resume(co, p)
        if not ok then table.insert(crashes, "PlayerRemoving: " .. tostring(err)) end
    end
    server.leaving.leave(p)
    p.Parent = nil
    local i = table.find(server.players, p)
    if i then table.remove(server.players, i) end
end

-- Fires a remote the way the engine would: the handler runs in its own thread and an error is recorded, never rethrown.
local errors = {}
local function describe(v, depth)
    depth = depth or 0
    local t = type(v)
    if t == "string" then return #v > 24 and ("str[" .. #v .. "]") or string.format("%q", v) end
    if t == "table" then
        if depth > 1 then return "{...}" end
        local parts = {}
        local n = 0
        for k, x in v do n += 1 if n > 4 then parts[#parts + 1] = "..." break end parts[#parts + 1] = tostring(k) .. "=" .. describe(x, depth + 1) end
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return tostring(v)
end
local function argsText(...)
    local n = select("#", ...)
    local parts = {}
    for i = 1, n do parts[i] = describe((select(i, ...))) end
    return table.concat(parts, ", ")
end
local function handlersOf(remote)
    if remote.ClassName == "RemoteFunction" then
        return if remote.OnServerInvoke then {remote.OnServerInvoke} else {}
    end
    return remote.OnServerEvent.fns
end
local function fireNow(server, name, player, ...)
    local remote = server.remotes[name]
    if not remote then error("no such remote: " .. name) end
    local results
    for _, handler in handlersOf(remote) do
        local pack = table.pack(xpcall(handler, function(e) return tostring(e) .. " @ " .. string.match(debug.traceback(), "[^\n]*\n[^\n]*\n([^\n]*)") end, player, ...))
        if not pack[1] then
            table.insert(errors, {remote = name, args = argsText(...), message = tostring(pack[2])})
        elseif results == nil then
            results = pack
        end
    end
    if results then return table.unpack(results, 2, results.n) end
    return nil
end
local function firePar(server, name, player, ...)
    local args = table.pack(...)
    local box = {done = false}
    task.spawn(function()
        box.results = table.pack(fireNow(server, name, player, table.unpack(args, 1, args.n)))
        box.done = true
    end)
    return box
end
local function waitAll(boxes)
    for _ = 1, 10000 do
        local all = true
        for _, b in boxes do if not b.done then all = false break end end
        if all then return end
        sleep(0.05)
    end
end

