"""BD-1047 (docs/187 section D): tests for src/shared/WorldLayer.luau (run in the pinned Luau runner) and its Python mirror tools/worldlayer.py.

Checks: world <-> cell conversion (square cells, half-open edges, a wide map), at / set / bounds / bad values, neighbours, the exact text
of small layers, round trips (hand-made, random fuzz, a 1,000 x 1,000 map with 3,600 random cells that must stay a few KB), bad text
(refused, never a crash), and that Luau and Python read each other's text and write identical text.
Offline logic only; nothing here is read by a game system yet.

    python tools/verify_world_layer.py --runner /path/to/luau
"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import worldlayer as wl  # noqa: E402

# the same deterministic pattern in Luau and Python (a LCG; values 1..15 plus a stripe and a block)
PATTERN_LUAU = r'''
local function pattern(layer)
    local seed = 12345
    local w, h = layer.width, layer.height
    for _ = 1, 300 do
        seed = (seed * 48271) % 2147483647
        local ix = seed % w
        seed = (seed * 48271) % 2147483647
        local iz = seed % h
        seed = (seed * 48271) % 2147483647
        WorldLayer.setCell(layer, ix, iz, seed % 15 + 1)
    end
    for ix = 3, w - 4 do WorldLayer.setCell(layer, ix, 5, 7) end
    for iz = 10, 19 do for ix = 20, 33 do WorldLayer.setCell(layer, ix, iz, 12) end end
end
'''

BODY = r'''
local function expect(ok: boolean, message: string) if not ok then error(message, 2) end end
local function same(a, b): boolean
    return a.width == b.width and a.height == b.height and math.abs(a.worldHalfWidth - b.worldHalfWidth) < 1e-6
        and buffer.tostring(a.cells) == buffer.tostring(b.cells)
end
local seed = 99
local function rnd(): number seed = (seed * 48271) % 2147483647 return seed / 2147483647 end

-- geometry: 256 x 256 cells over an 832 stud arena = 3.25 studs per cell
local L = WorldLayer.new(256, 256, 416)
expect(math.abs(L.cellSize - 3.25) < 1e-12, "cell size")
local ix, iz = WorldLayer.cellOf(L, 0, 0) expect(ix == 128 and iz == 128, "origin cell")
ix, iz = WorldLayer.cellOf(L, -416, -416) expect(ix == 0 and iz == 0, "west north corner")
ix, iz = WorldLayer.cellOf(L, 415.99, 415.99) expect(ix == 255 and iz == 255, "last cell")
ix, iz = WorldLayer.cellOf(L, 416, 0) expect(ix == 256, "the far edge belongs to no cell")
expect(not WorldLayer.set(L, 416, 0, 3) and WorldLayer.at(L, 416, 0) == 0, "outside: set refused, at is 0")
expect(not WorldLayer.set(L, -500, 0, 3) and WorldLayer.at(L, 0, 9999) == 0, "far outside")
expect(not WorldLayer.set(L, 0/0, 0, 3) and WorldLayer.at(L, 0/0, 0) == 0 and WorldLayer.at(L, math.huge, 0) == 0, "NaN and infinity are outside")
local cx, cz = WorldLayer.centreOf(L, 0, 0) expect(math.abs(cx + 414.375) < 1e-9 and math.abs(cz + 414.375) < 1e-9, "centre of cell 0,0")
for _ = 1, 500 do
    local a, b = math.floor(rnd() * 256), math.floor(rnd() * 256)
    local x, z = WorldLayer.centreOf(L, a, b)
    local c, d = WorldLayer.cellOf(L, x, z)
    expect(c == a and d == b, "cellOf(centreOf) is the same cell")
end
-- a wide map: 200 x 100 cells over x in [-100, 100): 1 stud cells, z in [-50, 50)
local W = WorldLayer.new(200, 100, 100)
expect(W.cellSize == 1, "wide map cell size")
ix, iz = WorldLayer.cellOf(W, 99.5, 49.5) expect(ix == 199 and iz == 99, "wide map last cell")
ix, iz = WorldLayer.cellOf(W, 0, 50) expect(iz == 100, "wide map far edge in z")
expect(WorldLayer.set(W, -100, -50, 9) and WorldLayer.atCell(W, 0, 0) == 9 and WorldLayer.at(W, -99.5, -49.5) == 9, "set by world point")

-- values and bounds
expect(WorldLayer.setCell(L, 5, 6, 15) and WorldLayer.atCell(L, 5, 6) == 15, "value 15")
expect(not WorldLayer.setCell(L, 256, 0, 1) and not WorldLayer.setCell(L, -1, 0, 1) and WorldLayer.atCell(L, -1, 0) == 0, "cell bounds")
for _, bad in {16, -1, 2.5, 0/0, math.huge} do
    expect(not pcall(WorldLayer.setCell, L, 1, 1, bad), "a bad value must raise: " .. tostring(bad))
end
expect(WorldLayer.count(L) == 1 and WorldLayer.count(L, 15) == 1 and WorldLayer.count(L, 0) == 65535, "count")
local seen = 0 WorldLayer.forEachNonZero(L, function(a, b, v) seen += 1 expect(a == 5 and b == 6 and v == 15, "forEachNonZero") end) expect(seen == 1, "forEachNonZero count")
WorldLayer.fill(L, 3) expect(WorldLayer.count(L, 3) == 65536, "fill") WorldLayer.fill(L, 0)

-- neighbours
local N = WorldLayer.new(5, 5, 2.5)
expect(#WorldLayer.neighbours(N, 0, 0) == 2 and #WorldLayer.neighbours(N, 0, 0, true) == 3, "corner neighbours")
expect(#WorldLayer.neighbours(N, 2, 2) == 4 and #WorldLayer.neighbours(N, 2, 2, true) == 8, "centre neighbours")
expect(#WorldLayer.neighbours(N, 2, 0) == 3 and #WorldLayer.neighbours(N, 2, 0, true) == 5, "edge neighbours")
WorldLayer.setCell(N, 3, 2, 6)
local east = WorldLayer.neighbours(N, 2, 2)[2] expect(east.ix == 3 and east.iz == 2 and east.value == 6, "neighbour order west, east, north, south and values")

-- exact text
local T = WorldLayer.new(4, 1, 2)
WorldLayer.setCell(T, 2, 0, 5) WorldLayer.setCell(T, 3, 0, 5)
expect(WorldLayer.encode(T) == "WL1:4:1:2:H5h", "text of 0 0 5 5: " .. WorldLayer.encode(T))
expect(WorldLayer.encode(WorldLayer.new(1, 1, 1)) == "WL1:1:1:1:G", "one zero")
expect(WorldLayer.encode(WorldLayer.new(17, 1, 8)) == "WL1:17:1:8:HG", "seventeen zeros")
local F = WorldLayer.new(3, 1, 1.5) WorldLayer.fill(F, 15) expect(WorldLayer.encode(F) == "WL1:3:1:1.5:fi", "all fifteen")
local alt = WorldLayer.new(4, 1, 2) WorldLayer.setCell(alt, 1, 0, 1) WorldLayer.setCell(alt, 3, 0, 2)
expect(WorldLayer.encode(alt) == "WL1:4:1:2:G1G2", "alternating: " .. WorldLayer.encode(alt))
local back = WorldLayer.decode("WL1:4:1:2:\n H5h ") expect(back ~= nil and same(back :: any, T), "decode ignores whitespace")
local lenient = WorldLayer.decode("WL1:4:1:2:0h5h") expect(lenient ~= nil and same(lenient :: any, T), "a 0 digit run is accepted when reading")

-- round trips: all zero, all values, big runs, fuzz
local function roundtrip(layer, label)
    local text = WorldLayer.encode(layer)
    local decoded, why = WorldLayer.decode(text)
    expect(decoded ~= nil, label .. ": decode failed " .. tostring(why))
    expect(same(decoded :: any, layer), label .. ": round trip differs")
    expect(WorldLayer.encode(decoded :: any) == text, label .. ": encode is stable")
end
roundtrip(WorldLayer.new(1, 1, 1), "one cell")
roundtrip(WorldLayer.new(1000, 1000, 416), "all zero")
local full = WorldLayer.new(300, 200, 150) WorldLayer.fill(full, 9) roundtrip(full, "all nine")
for v = 1, 15 do local one = WorldLayer.new(7, 3, 3.5) WorldLayer.fill(one, v) WorldLayer.setCell(one, 3, 1, 0) roundtrip(one, "value " .. v) end
for n = 1, 150 do
    local w, h = 1 + math.floor(rnd() * 60), 1 + math.floor(rnd() * 40)
    local layer = WorldLayer.new(w, h, 0.25 + rnd() * 500)
    local mode = n % 3
    for _ = 1, math.floor(rnd() * w * h * (if mode == 0 then 1.5 else 0.1)) do
        WorldLayer.setCell(layer, math.floor(rnd() * w), math.floor(rnd() * h), if mode == 2 then 1 + math.floor(rnd() * 3) else math.floor(rnd() * 16))
    end
    roundtrip(layer, "fuzz " .. n)
end
-- the big one: 1,000 x 1,000 cells, 3,600 random cells of food kinds 1..4
local big = WorldLayer.new(1000, 1000, 416)
local placed = 0
while placed < 3600 do
    local a, b = math.floor(rnd() * 1000), math.floor(rnd() * 1000)
    if WorldLayer.atCell(big, a, b) == 0 then WorldLayer.setCell(big, a, b, 1 + math.floor(rnd() * 4)) placed += 1 end
end
local t0 = os.clock()
local bigText = WorldLayer.encode(big)
local bigBack, bigWhy = WorldLayer.decode(bigText)
local secs = os.clock() - t0
expect(bigBack ~= nil, "big decode " .. tostring(bigWhy))
expect(same(bigBack :: any, big), "big round trip")
expect(WorldLayer.count(big) == 3600, "big count")
expect(#bigText < 20000, "3,600 cells in 1,000 x 1,000 must stay a few KB of text, got " .. #bigText)
print(string.format("BIG\t%d\t%.2f", #bigText, secs))

-- bad text is refused, never a crash
for _, bad in {"", "hello", "WL1:", "WL1:0:5:10:G", "WL1:5:0:10:G", "WL1:4:1:0:HH", "WL1:4:1:2:H", "WL1:4:1:2:HHH", "WL1:4:1:2:H5hh", "WL1:4:1:2:H!",
    "WL1:4:1:2:HA", "WL1:99999:99999:2:G", "WL1:4:1:2:5hhhhhhhhhhhhhhhhhhhhhhhh", "WL2:4:1:2:HH", "WL1:4:1:-2:HH", "WL1:4:1:2:HHGG"} do
    local layer, why = WorldLayer.decode(bad)
    expect(layer == nil and type(why) == "string", "must refuse " .. string.format("%q", bad))
end
for _ = 1, 300 do -- random junk after a good header
    local junk = {} for i = 1, 1 + math.floor(rnd() * 12) do junk[i] = string.char(33 + math.floor(rnd() * 90)) end
    local layer = WorldLayer.decode("WL1:4:2:2:" .. table.concat(junk))
    if layer then expect(WorldLayer.encode(layer :: any) ~= nil, "valid by chance") end
end
expect(not pcall(WorldLayer.new, 0, 5, 1) and not pcall(WorldLayer.new, 5, 5, 0) and not pcall(WorldLayer.new, 9000, 1, 1) and not pcall(WorldLayer.new, 2.5, 5, 1), "new refuses bad sizes")

-- cross check with Python: this exact pattern, written as text
local X = WorldLayer.new(64, 32, 32)
pattern(X)
print("X\t" .. WorldLayer.encode(X))
local fromPy = {}
for line in string.gmatch(PYTEXT, "[^\n]+") do table.insert(fromPy, line) end
local decodedPy = WorldLayer.decode(fromPy[1])
expect(decodedPy ~= nil and same(decodedPy :: any, X), "Luau reads the text Python wrote")
print("OK")
'''


def mod(name):
    return '(function()\n' + (ROOT / 'src/shared' / f'{name}.luau').read_text(encoding='utf-8') + '\nend)()'


failures = []


def check(ok, message):
    if not ok:
        failures.append(message)
        print('FAIL', message)


def pattern(layer):
    seed = 12345
    w, h = layer.width, layer.height
    for _ in range(300):
        seed = (seed * 48271) % 2147483647
        ix = seed % w
        seed = (seed * 48271) % 2147483647
        iz = seed % h
        seed = (seed * 48271) % 2147483647
        layer.set_cell(ix, iz, seed % 15 + 1)
    for ix in range(3, w - 3):
        layer.set_cell(ix, 5, 7)
    for iz in range(10, 20):
        for ix in range(20, 34):
            layer.set_cell(ix, iz, 12)


def python_checks():
    import random
    layer = wl.WorldLayer(4, 1, 2)
    layer.set_cell(2, 0, 5)
    layer.set_cell(3, 0, 5)
    check(layer.encode() == 'WL1:4:1:2:H5h', 'python text of 0 0 5 5')
    check(wl.WorldLayer(17, 1, 8).encode() == 'WL1:17:1:8:HG', 'python seventeen zeros')
    check(wl.decode('WL1:4:1:2:\n H5h ') == layer, 'python decode ignores whitespace')
    L = wl.WorldLayer(256, 256, 416)
    check(abs(L.cell_size - 3.25) < 1e-12 and L.cell_of(0, 0) == (128, 128) and L.cell_of(416, 0)[0] == 256, 'python geometry')
    check(not L.set(416, 0, 3) and L.at(416, 0) == 0 and L.set(-416, -416, 4) and L.at_cell(0, 0) == 4, 'python bounds')
    x, z = L.centre_of(10, 20)
    check(L.cell_of(x, z) == (10, 20), 'python centre round trip')
    check(len(L.neighbours(0, 0)) == 2 and len(L.neighbours(2, 2, True)) == 8, 'python neighbours')
    rng = random.Random(7)
    for n in range(100):
        w, h = rng.randint(1, 60), rng.randint(1, 40)
        m = wl.WorldLayer(w, h, 0.25 + rng.random() * 500)
        for _ in range(int(rng.random() * w * h * (1.5 if n % 3 == 0 else 0.1))):
            m.set_cell(rng.randrange(w), rng.randrange(h), rng.randrange(16) if n % 3 != 2 else rng.randint(1, 3))
        check(wl.decode(m.encode()) == m, f'python fuzz {n}')
    big = wl.WorldLayer(1000, 1000, 416)
    placed = 0
    while placed < 3600:
        a, b = rng.randrange(1000), rng.randrange(1000)
        if big.at_cell(a, b) == 0:
            big.set_cell(a, b, rng.randint(1, 4))
            placed += 1
    text = big.encode()
    check(wl.decode(text) == big and len(text) < 20000, f'python big round trip, {len(text)} chars')
    for bad in ('', 'hello', 'WL1:4:1:2:H', 'WL1:4:1:2:HHH', 'WL1:4:1:2:H!', 'WL1:99999:99999:2:G', 'WL1:4:1:-2:HH', 'WL1:4:1:2:HHGG'):
        try:
            wl.decode(bad)
            check(False, f'python must refuse {bad!r}')
        except ValueError:
            pass
    check(wl.WorldLayer(3, 2, 1).rows() == [[0, 0, 0], [0, 0, 0]], 'python rows')
    return len(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    py_size = python_checks()
    python_layer = wl.WorldLayer(64, 32, 32)
    pattern(python_layer)
    python_text = python_layer.encode()
    code = ('local WorldLayer = ' + mod('WorldLayer') + '\n' + PATTERN_LUAU + '\nlocal PYTEXT = ' + repr(python_text).replace("'", '"') + '\n' + BODY)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'world_layer.luau'
        path.write_text(code, encoding='utf-8')
        r = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    if r.returncode or 'OK' not in r.stdout:
        print(r.stdout[-3000:], r.stderr[-3000:])
        return 1
    luau_text = None
    for line in r.stdout.splitlines():
        p = line.split('\t')
        if p[0] == 'X':
            luau_text = p[1]
        elif p[0] == 'BIG':
            print(f'1,000 x 1,000 with 3,600 cells: {p[1]} characters as text (Luau), {py_size} (Python); encode + decode took {p[2]} s in Luau')
    check(luau_text == python_text, 'Luau and Python write identical text for the same layer')
    check(luau_text is not None and wl.decode(luau_text) == python_layer, 'Python reads the text Luau wrote')
    if failures:
        print(f'{len(failures)} check(s) failed')
        return 1
    print('world layer OK (Luau and Python)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
