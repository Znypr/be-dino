--!strict
-- Concurrency gate for EditableMesh-backed model loads (AuthoredCreatures). Pure: the clock and the sleep
-- function are injected so tools/verify_load_gate.py can run it offline. Requests above the cap WAIT for a slot
-- (bounded) instead of failing, so a preview never degrades to the box fallback just because many were requested.
local Gate = {}
function Gate.new(cap: number)
    return {cap = cap, active = 0, peak = 0, waited = 0, timedOut = 0, granted = 0}
end
function Gate.tryAcquire(gate): boolean
    if gate.active >= gate.cap then return false end
    gate.active += 1
    gate.granted += 1
    if gate.active > gate.peak then gate.peak = gate.active end
    return true
end
function Gate.release(gate)
    if gate.active > 0 then gate.active -= 1 end
end
-- Waits (sleep(seconds) yields) until a slot frees or `timeout` seconds pass. Returns true when acquired.
function Gate.acquire(gate, timeout: number, now: () -> number, sleep: (number) -> ()): boolean
    local started = now()
    local waited = false
    while not Gate.tryAcquire(gate) do
        if now() - started >= timeout then gate.timedOut += 1 return false end
        waited = true
        sleep(.05)
    end
    if waited then gate.waited += 1 end
    return true
end
return Gate
