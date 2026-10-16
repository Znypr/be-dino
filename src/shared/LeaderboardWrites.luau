--!strict
-- BD-362: decides WHICH leaderboard values are worth an OrderedDataStore write. Pure and tested.
-- The stores keep max(old, new), so a value that is not above what this server already wrote for that player cannot change
-- anything and is skipped; play time grows every second so it is throttled to one write per PlayInterval (a leave still forces it).
local Rules = {}
Rules.PlayInterval = 600
export type State = {written: {[string]: {[number]: number}}, lastTry: {[string]: {[number]: number}}}
function Rules.new(): State return {written = {}, lastTry = {}} end
local function bucket(t: {[string]: {[number]: number}}, id: string): {[number]: number}
    local b = t[id]
    if not b then b = {} t[id] = b end
    return b
end
function Rules.shouldWrite(state: State, id: string, userId: number, value: number, now: number, force: boolean): boolean
    if value ~= value or value <= 0 or value == math.huge then return false end
    local last = bucket(state.written, id)[userId]
    if last and value <= last then return false end
    if id == "playSeconds" and not force then
        local tried = bucket(state.lastTry, id)[userId]
        if tried and now - tried < Rules.PlayInterval then return false end
    end
    return true
end
function Rules.begin(state: State, id: string, userId: number, now: number) bucket(state.lastTry, id)[userId] = now end
function Rules.succeeded(state: State, id: string, userId: number, value: number)
    local b = bucket(state.written, id)
    b[userId] = math.max(b[userId] or 0, value)
end
function Rules.forget(state: State, userId: number)
    for _, b in state.written do b[userId] = nil end
    for _, b in state.lastTry do b[userId] = nil end
end
return Rules
