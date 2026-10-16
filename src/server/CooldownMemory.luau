--!strict
-- BD-363 (docs/111 L3): request cooldowns keyed by UserId instead of the Player object, so leaving and rejoining the same server does
-- NOT reset them (the per-Player tables were cleared on PlayerRemoving). Memory only, never written to the profile. Entries expire
-- by age (longer than any cooldown) so the table stays small; nothing is cleared on leave. A hop to ANOTHER server still starts
-- fresh: that needs shared state (MemoryStore) and is not done here, ProfileRepository's own admission limits bound that case.
-- No Roblox globals, so tools/verify_multiplayer_sim.py can run this exact file.
local CooldownMemory = {}

function CooldownMemory.new(retainSeconds: number?)
    local retain = retainSeconds or 120
    local entries: {[number]: {[string]: number}} = {}
    local marks = 0
    local self = {}

    function self.last(userId: number, key: string): number
        local row = entries[userId]
        return if row then (row[key] or -math.huge) else -math.huge
    end

    function self.prune(now: number)
        for userId, row in entries do
            local empty = true
            for key, at in row do
                if now - at > retain then row[key] = nil else empty = false end
            end
            if empty then entries[userId] = nil end
        end
    end

    function self.mark(userId: number, key: string, now: number)
        local row = entries[userId]
        if not row then row = {} entries[userId] = row end
        row[key] = now
        marks += 1
        if marks % 64 == 0 then self.prune(now) end
    end

    -- true (and records the use) when `cooldown` seconds have passed since the last allowed use of this key.
    function self.allow(userId: number, key: string, now: number, cooldown: number): boolean
        if now - self.last(userId, key) < cooldown then return false end
        self.mark(userId, key, now)
        return true
    end

    function self.size(): number
        local n = 0
        for _, row in entries do for _ in row do n += 1 end end
        return n
    end

    return self
end

return CooldownMemory
