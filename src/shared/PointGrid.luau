--!strict
-- BD-361: uniform grid over the X/Z plane so "which items are near this point" costs the items in a few cells, not every item.
-- Pure (no Roblox types). FoodService keeps ~2,400 pickups in it; per tick each player queries a radius instead of scanning all foods.
local PointGrid = {}
PointGrid.__index = PointGrid
export type Grid = typeof(setmetatable({} :: {cell: number, cells: {[number]: {[any]: boolean}}, where: {[any]: number}}, PointGrid))
local function key(cx: number, cz: number): number return cx * 100003 + cz end -- cx, cz stay far below 50,000 for any map here
function PointGrid.new(cellSize: number): Grid
    return setmetatable({cell = math.max(1, cellSize), cells = {}, where = {}}, PointGrid)
end
function PointGrid.insert(self: Grid, item: any, x: number, z: number)
    if self.where[item] then PointGrid.remove(self, item) end
    local k = key(math.floor(x / self.cell), math.floor(z / self.cell))
    local bucket = self.cells[k]
    if not bucket then bucket = {} self.cells[k] = bucket end
    bucket[item] = true
    self.where[item] = k
end
function PointGrid.remove(self: Grid, item: any)
    local k = self.where[item]
    if not k then return end
    local bucket = self.cells[k]
    if bucket then bucket[item] = nil if next(bucket) == nil then self.cells[k] = nil end end
    self.where[item] = nil
end
function PointGrid.move(self: Grid, item: any, x: number, z: number) PointGrid.insert(self, item, x, z) end
-- Calls fn(item) for every item whose CELL overlaps the square of half-size radius around (x, z); callers still do the exact distance test.
function PointGrid.query(self: Grid, x: number, z: number, radius: number, fn: (any) -> ())
    local c = self.cell
    for cx = math.floor((x - radius) / c), math.floor((x + radius) / c) do
        for cz = math.floor((z - radius) / c), math.floor((z + radius) / c) do
            local bucket = self.cells[key(cx, cz)]
            if bucket then for item in bucket do fn(item) end end
        end
    end
end
return PointGrid
