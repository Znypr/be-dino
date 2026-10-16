--!strict
-- BD-354 (docs/111): one place for "a player is leaving", used by PlayerRemoving AND BindToClose.
-- Guarantees: a leaving player's run settles at most once (RunLifecycle owns that), the profile lease is released exactly once
-- per leave even when the settlement was already running ("busy") or failed, and BindToClose can WAIT for all of it in
-- parallel instead of walking the players one after another (12 sequential DataStore round trips can pass the 30 s limit).
-- No Roblox globals except `task`, so tools/verify_multiplayer_sim.py runs this exact file.
local LeaveCoordinator = {}

export type Deps = {
    endForDisconnect: (any) -> string,
    release: (any) -> any,
    publish: ((any, any) -> ())?,
}

function LeaveCoordinator.new(deps: Deps)
    local self = {pending = 0, leaving = {} :: {[any]: boolean}, released = 0}

    -- Idempotent per leave: the first call does the work, repeats (PlayerRemoving then BindToClose) are no-ops.
    function self.releaseNow(player: any)
        if not self.leaving[player] then return end
        self.leaving[player] = nil
        self.pending -= 1
        local ok, metrics = pcall(deps.release, player)
        if not ok then warn("[Be Dino] release failed: " .. tostring(metrics)) return end
        self.released += 1
        if metrics and deps.publish then
            local published, err = pcall(deps.publish, player, metrics)
            if not published then warn("[Be Dino] leaderboard publish failed: " .. tostring(err)) end
        end
    end

    -- Called from the run-settlement callback (success OR failure). A no-op for players still in the game; for a player whose
    -- leave started while the settlement ran ("busy") it releases the lease. PlayerRemoving fires before Parent becomes nil,
    -- so the leaving flag, not Parent, is the truth.
    function self.settlementFinished(player: any)
        self.releaseNow(player)
    end

    local function run(player: any)
        local ok, status = pcall(deps.endForDisconnect, player)
        if not ok then warn("[Be Dino] endForDisconnect failed: " .. tostring(status)) status = "failed" end
        if status ~= "busy" then self.releaseNow(player) end
        -- "busy": settlement already runs (death/eaten raced the disconnect); its callback ends in settlementFinished.
    end

    -- The leave is registered (pending) BEFORE any yield, so waitIdle can never see a started-but-unregistered leave.
    local function register(player: any): boolean
        if self.leaving[player] then return false end
        self.leaving[player] = true
        self.pending += 1
        return true
    end

    function self.leave(player: any)
        if register(player) then run(player) end
    end

    function self.leaveAll(players: {any})
        for _, player in players do
            if register(player) then task.spawn(run, player) end
        end
    end

    -- BindToClose: returns when every leave finished, or after timeoutSeconds. Returns true when idle.
    function self.waitIdle(timeoutSeconds: number): boolean
        local waited = 0
        while self.pending > 0 and waited < timeoutSeconds do
            task.wait(0.1)
            waited += 0.1
        end
        return self.pending == 0
    end

    return self
end

return LeaveCoordinator
