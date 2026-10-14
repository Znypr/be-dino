"""Execute src/shared/LoadGate.luau (the AuthoredCreatures load-slot gate) with the pinned Luau runtime and a
simulated clock: 120 concurrent preview loads against a cap of 4 never exceed the cap, every request is served
(waits instead of failing, so no box fallback), slots are always released (also on failure), and a request that
cannot get a slot in time reports failure cleanly. Studio-only parts (real EditableMesh) are covered in docs/86.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
BODY = r'''
local clock = 0
local function now() return clock end
-- Tiny cooperative scheduler: a coroutine yields its wake-up time.
local function simulate(requests, cap, hold, timeout, failEvery)
    local gate = Gate.new(cap)
    local served, failed, timedOut = 0, 0, 0
    local queue = {}
    for i = 1, requests do
        local co = coroutine.create(function()
            local ok = Gate.acquire(gate, timeout, now, function(dt) coroutine.yield(clock + dt) end)
            if not ok then timedOut += 1 return end
            assert(gate.active <= cap, "cap exceeded")
            coroutine.yield(clock + hold) -- the load takes `hold` seconds
            if failEvery > 0 and i % failEvery == 0 then failed += 1 else served += 1 end
            Gate.release(gate) -- released on success and on failure
        end)
        table.insert(queue, {at = i * .01, co = co})
    end
    while #queue > 0 do
        table.sort(queue, function(a, b) return a.at < b.at end)
        local item = table.remove(queue, 1)
        clock = math.max(clock, item.at)
        local ok, wake = coroutine.resume(item.co)
        assert(ok, wake)
        if coroutine.status(item.co) ~= "dead" then item.at = wake table.insert(queue, item) end
    end
    return gate, served, failed, timedOut
end
local gate, served, failed, timedOut = simulate(120, 4, .25, 600, 0)
assert(gate.peak == 4 and gate.active == 0 and served == 120 and timedOut == 0, "all served, cap 4, nothing leaked")
assert(gate.waited > 100, "extra requests waited instead of failing")
gate, served, failed, timedOut = simulate(120, 4, .25, 600, 5)
assert(gate.active == 0 and served + failed == 120 and failed == 24 and gate.peak <= 4, "failed loads still release their slot")
gate, served, failed, timedOut = simulate(40, 2, 5, .5, 0)
assert(gate.active == 0 and timedOut > 0 and served + timedOut == 40 and gate.peak <= 2, "bounded wait reports failure cleanly")
local g = Gate.new(1)
assert(Gate.tryAcquire(g) and not Gate.tryAcquire(g)) Gate.release(g) Gate.release(g) assert(g.active == 0 and Gate.tryAcquire(g))
print("Load gate checks passed: cap 4 never exceeded across 120 concurrent loads, waits instead of failing, slots always released")
'''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    source = '(function()\n' + (ROOT / 'src/shared/LoadGate.luau').read_text(encoding='utf-8') + '\nend)()'
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'gate.luau'
        path.write_text('local Gate=' + source + '\n' + BODY, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
