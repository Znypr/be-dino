--!strict
-- BD-1047 (docs/187 section D): one generic 2D map of small numbers over the world, "a table of hex digits inside a class".
-- Pure Luau, no Instances, so the server, offline tools and tests share the same code (like BiomeMap). One layer per job
-- (food kind, tree kind, tree size, biome index ...); each layer decides what its digits mean. NOT used by any game system yet
-- (FoodService still places food with its own dice): this file only adds the data type.
--
-- Geometry: the world is centred on (0, 0). The layer has `width` x `height` cells and covers x in [-worldHalfWidth, +worldHalfWidth).
-- Cells are square: cellSize = 2 x worldHalfWidth / width, so z covers [-height x cellSize / 2, +height x cellSize / 2).
-- Cell (ix, iz) is 0-based; ix runs west to east (x), iz runs north to south (z, like the tools' pictures). A point exactly on the
-- far edge, or outside, belongs to no cell: `at` answers 0 and `set` returns false.
-- Memory: 1 byte per cell in a buffer (1 MB for 1,000 x 1,000). Values are whole numbers 0..15 (one hex digit).
--
-- Text format (what a ModuleScript can hold), version 1:
--   "WL1:<width>:<height>:<worldHalfWidth>:<body>"   whitespace anywhere is ignored
--   The cells are read row by row (ix fastest) and written as runs of equal values, no more and no less than width x height cells.
--   zero run     one or more of G..V        = the base-16 digits (G = 0 ... V = 15, big-endian) of (length - 1), so "G" is one 0,
--                                              "H" is two, "HG" is seventeen
--   value run    a hex digit 1..9, a..f, then g..v digits of (length - 1), none when the length is 1: "5" = one 5, "5h" = two 5s
--   Zeros are letters, so a map that is almost all zeros is tiny; a lone 0 digit is also accepted when reading ("0h" = two zeros).
--   tools/worldlayer.py is the Python mirror of encode/decode (so tools/layer_stats.py can read a layer).
local WorldLayer = {}
WorldLayer.__index = WorldLayer

WorldLayer.Version = 1
WorldLayer.MaxValue = 15
WorldLayer.MaxSide = 8192 -- decode refuses a bigger header (a memory bomb), new() refuses it too
WorldLayer.MaxCells = 16777216

export type Layer = typeof(setmetatable({} :: {
    width: number,
    height: number,
    worldHalfWidth: number,
    cellSize: number,
    cells: buffer,
}, WorldLayer))

export type Neighbour = {ix: number, iz: number, value: number}

local DIGIT_ZERO_RUN = 71 -- "G"
local DIGIT_VALUE_RUN = 103 -- "g"

function WorldLayer.new(width: number, height: number, worldHalfWidth: number): Layer
    assert(width % 1 == 0 and height % 1 == 0 and width >= 1 and height >= 1, "WorldLayer: width and height must be whole numbers of 1 or more")
    assert(width <= WorldLayer.MaxSide and height <= WorldLayer.MaxSide and width * height <= WorldLayer.MaxCells, "WorldLayer: layer is too large")
    assert(worldHalfWidth > 0 and worldHalfWidth < math.huge, "WorldLayer: worldHalfWidth must be a positive number")
    return setmetatable({
        width = width,
        height = height,
        worldHalfWidth = worldHalfWidth,
        cellSize = 2 * worldHalfWidth / width,
        cells = buffer.create(width * height),
    }, WorldLayer)
end

-- ---------------------------------------------------------------------------- conversions
-- 0-based cell of a world point (x, z). The answer can be outside 0..width-1 / 0..height-1: test it with `contains`.
function WorldLayer.cellOf(self: Layer, x: number, z: number): (number, number)
    local halfDepth = self.height * self.cellSize / 2
    return math.floor((x + self.worldHalfWidth) / self.cellSize), math.floor((z + halfDepth) / self.cellSize)
end

-- World position (x, z) of the centre of cell (ix, iz).
function WorldLayer.centreOf(self: Layer, ix: number, iz: number): (number, number)
    local halfDepth = self.height * self.cellSize / 2
    return -self.worldHalfWidth + (ix + 0.5) * self.cellSize, -halfDepth + (iz + 0.5) * self.cellSize
end

function WorldLayer.contains(self: Layer, ix: number, iz: number): boolean
    return ix >= 0 and ix < self.width and iz >= 0 and iz < self.height and ix % 1 == 0 and iz % 1 == 0
end

-- ---------------------------------------------------------------------------- reading and writing
-- Value at cell (ix, iz); 0 outside the layer.
function WorldLayer.atCell(self: Layer, ix: number, iz: number): number
    if not WorldLayer.contains(self, ix, iz) then return 0 end
    return buffer.readu8(self.cells, iz * self.width + ix)
end

-- Sets cell (ix, iz) to a whole number 0..15 (an invalid value is a programming error and raises). false when the cell is outside.
function WorldLayer.setCell(self: Layer, ix: number, iz: number, value: number): boolean
    assert(value % 1 == 0 and value >= 0 and value <= WorldLayer.MaxValue, "WorldLayer: a value must be a whole number 0..15")
    if not WorldLayer.contains(self, ix, iz) then return false end
    buffer.writeu8(self.cells, iz * self.width + ix, value)
    return true
end

-- Value at the world point (x, z); 0 outside the layer.
function WorldLayer.at(self: Layer, x: number, z: number): number
    local ix, iz = WorldLayer.cellOf(self, x, z)
    return WorldLayer.atCell(self, ix, iz)
end

-- Sets the cell that holds the world point (x, z); false when the point is outside.
function WorldLayer.set(self: Layer, x: number, z: number, value: number): boolean
    local ix, iz = WorldLayer.cellOf(self, x, z)
    return WorldLayer.setCell(self, ix, iz, value)
end

function WorldLayer.fill(self: Layer, value: number)
    assert(value % 1 == 0 and value >= 0 and value <= WorldLayer.MaxValue, "WorldLayer: a value must be a whole number 0..15")
    buffer.fill(self.cells, 0, value)
end

-- How many cells hold `value`; with no value: how many are not 0.
function WorldLayer.count(self: Layer, value: number?): number
    local total = 0
    for i = 0, self.width * self.height - 1 do
        local v = buffer.readu8(self.cells, i)
        if (if value == nil then v ~= 0 else v == value) then total += 1 end
    end
    return total
end

-- fn(ix, iz, value) for every cell that is not 0, row by row.
function WorldLayer.forEachNonZero(self: Layer, fn: (number, number, number) -> ())
    local width = self.width
    for i = 0, width * self.height - 1 do
        local v = buffer.readu8(self.cells, i)
        if v ~= 0 then fn(i % width, i // width, v) end
    end
end

-- The 4 side neighbours (or all 8 with diagonals) of cell (ix, iz) that lie inside the layer, in the order west, east, north, south,
-- then north-west, north-east, south-west, south-east.
function WorldLayer.neighbours(self: Layer, ix: number, iz: number, diagonals: boolean?): {Neighbour}
    local out: {Neighbour} = {}
    local steps = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}}
    if diagonals then
        for _, s in {{-1, -1}, {1, -1}, {-1, 1}, {1, 1}} do table.insert(steps, s) end
    end
    for _, s in steps do
        local nx, nz = ix + s[1], iz + s[2]
        if WorldLayer.contains(self, nx, nz) then
            table.insert(out, {ix = nx, iz = nz, value = buffer.readu8(self.cells, nz * self.width + nx)})
        end
    end
    return out
end

-- ---------------------------------------------------------------------------- text
-- Base-16 digits (big-endian) of m (m >= 0) as characters starting at `first`.
local function lengthDigits(m: number, first: number): string
    local chars = {}
    repeat
        table.insert(chars, 1, string.char(first + m % 16))
        m //= 16
    until m == 0
    return table.concat(chars)
end

function WorldLayer.encode(self: Layer): string
    local parts: {string} = {string.format("WL1:%d:%d:%.9g:", self.width, self.height, self.worldHalfWidth)}
    local cells = self.cells
    local total = self.width * self.height
    local i = 0
    while i < total do
        local value = buffer.readu8(cells, i)
        local j = i + 1
        while j < total and buffer.readu8(cells, j) == value do j += 1 end
        local m = j - i - 1
        if value == 0 then
            table.insert(parts, lengthDigits(m, DIGIT_ZERO_RUN))
        else
            table.insert(parts, string.format("%x", value))
            if m > 0 then table.insert(parts, lengthDigits(m, DIGIT_VALUE_RUN)) end
        end
        i = j
    end
    return table.concat(parts)
end

-- Reads text made by `encode`. Returns the layer, or nil and a short reason when the text is not a valid layer.
function WorldLayer.decode(text: string): (Layer?, string?)
    local clean = string.gsub(text, "%s", "")
    local w, h, half, bodyStart = string.match(clean, "^WL1:(%d+):(%d+):([%d%.eE%+%-]+):()")
    if not w then return nil, "bad header (expected WL1:<width>:<height>:<worldHalfWidth>:)" end
    local width, height, halfWidth = tonumber(w), tonumber(h), tonumber(half)
    if width == nil or height == nil or halfWidth == nil then return nil, "bad header numbers" end
    if width < 1 or height < 1 or width > WorldLayer.MaxSide or height > WorldLayer.MaxSide or width * height > WorldLayer.MaxCells then
        return nil, "layer size out of range"
    end
    if not (halfWidth > 0 and halfWidth < math.huge) then return nil, "worldHalfWidth must be positive" end
    local layer = WorldLayer.new(width, height, halfWidth)
    local cells = layer.cells
    local total = width * height
    local pos = 0
    local i, n = bodyStart :: number, #clean
    while i <= n do
        local c = string.byte(clean, i)
        local value: number
        local first: number
        if c >= 71 and c <= 86 then -- G..V: a run of zeros
            value, first = 0, DIGIT_ZERO_RUN
        elseif (c >= 48 and c <= 57) or (c >= 97 and c <= 102) then -- a hex digit starts a run of that value
            value = if c <= 57 then c - 48 else c - 87
            first = DIGIT_VALUE_RUN
            i += 1
        else
            return nil, string.format("unexpected character %q at %d", string.char(c), i)
        end
        local m = 0
        while i <= n do
            local d = string.byte(clean, i)
            if d < first or d > first + 15 then break end
            m = m * 16 + (d - first)
            i += 1
            if m >= total then break end -- (a longer run could not fit; the check below reports it)
        end
        local length = m + 1
        if pos + length > total then return nil, "more cells than width x height" end
        if value ~= 0 then buffer.fill(cells, pos, value, length) end
        pos += length
    end
    if pos ~= total then return nil, string.format("%d cells found, %d expected", pos, total) end
    return layer, nil
end

return WorldLayer
