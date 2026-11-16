--!strict
-- BD-1233 (docs/242 gap 18): the code box and the group gift chest, server side. Behind Config.CodesEnabled (default false, ON only in the playtest
-- profile); with the flag off start() returns at once: no CodeAction remote, no connection, no profile access.
-- ReplicatedStorage.BeDinoRemotes.CodeAction (RemoteFunction) is the only way in. request = {action = "info"} | {action = "code", text = string} |
-- {action = "group"}. The client sends WORDS only; the server normalizes the text (Shared/CodeRules), looks it up in the server-only CodeTable,
-- checks group membership itself (Player:IsInGroup, Config.GameGroupId) and takes the amount from its own tables. Exactly-once per player through
-- ProfileRepository.redeemToken (additive field `redeemedCodes`). Answers {ok, status, text} with kid words; it never throws to the client.
-- Rate limited: one try per CodeRules.TryGap seconds and CodeRules.MaxWrongPerMinute wrong codes per minute.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config) :: any
local C = require(ReplicatedStorage.Shared.CodeRules)
local CodeTable = require(script.Parent.CodeTable) :: any

local Service = {}
local repository: any = nil
local lastTry: {[Player]: number} = setmetatable({}, {__mode = "k"}) :: any
local wrong: {[Player]: {number}} = setmetatable({}, {__mode = "k"}) :: any

local function answer(status: string, crystals: number?): any
    return {ok = status == "applied", status = status, text = C.message(status, crystals)}
end

local function groupId(): number
    local id = Config.GameGroupId
    return if type(id) == "number" and id >= 1 and id % 1 == 0 then id else 0
end

local function inGroup(player: Player): boolean
    local id = groupId()
    if id == 0 then return false end
    local ok, yes = pcall(function() return player:IsInGroup(id) end)
    return ok and yes == true
end

local function redeem(player: Player, token: string, crystals: number): any
    local ok, status = repository.redeemToken(player, token, crystals)
    if ok then return answer(status, crystals) end
    return answer("busy")
end

-- Entry point for OnServerInvoke (and offline tests). Never throws to the client.
function Service.handle(player: Player, request: any): any
    if Config.CodesEnabled ~= true or repository == nil then return answer("busy") end
    if typeof(request) ~= "table" then return answer("busy") end
    local action = request.action
    if action == "info" then
        local id = groupId()
        return {ok = true, status = "info", group = id ~= 0, groupDone = id ~= 0 and repository.codeUsed(player, C.GroupToken), groupCrystals = Config.GroupChestCrystals}
    end
    local now = os.clock()
    if now - (lastTry[player] or -100) < C.TryGap then return answer("slow") end
    lastTry[player] = now
    if action == "group" then
        if groupId() == 0 then return answer("group_off") end
        if repository.codeUsed(player, C.GroupToken) then return answer("group_done") end
        if not inGroup(player) then return answer("group_join") end
        local crystals = Config.GroupChestCrystals
        if type(crystals) ~= "number" or crystals < 1 or crystals % 1 ~= 0 then return answer("busy") end
        local result = redeem(player, C.GroupToken, crystals)
        if result.status == "already" then return answer("group_done") end
        return result
    elseif action == "code" then
        local kept, allowed = C.allowTry(wrong[player] or {}, now)
        wrong[player] = kept
        if not allowed then return answer("slow") end
        local code = C.normalize(request.text)
        local entry = if code then CodeTable[code] else nil
        local state = C.state(entry, os.time())
        if code == nil or state ~= "ok" then
            if state ~= "expired" then table.insert(kept, now) end
            return answer(if state == "expired" then "expired" else "wrong")
        end
        return redeem(player, C.token(code :: string), entry.crystals)
    end
    return answer("busy")
end

function Service.start(repo: any): any
    if Config.CodesEnabled ~= true then return nil end -- flag off: no remote, no connection, no profile access
    if repository ~= nil then return nil end
    repository = repo
    local folder = ReplicatedStorage:FindFirstChild("BeDinoRemotes")
    if folder == nil then
        folder = Instance.new("Folder")
        folder.Name = "BeDinoRemotes"
        folder.Parent = ReplicatedStorage
    end
    local remote = Instance.new("RemoteFunction")
    remote.Name = "CodeAction"
    remote.OnServerInvoke = function(player: any, request: any)
        local ok, response = pcall(Service.handle, player, request)
        return if ok then response else answer("busy")
    end
    remote.Parent = folder
    Players.PlayerRemoving:Connect(function(player: Player)
        lastTry[player], wrong[player] = nil, nil
    end)
    return remote
end

return Service
