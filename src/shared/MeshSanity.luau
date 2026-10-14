--!strict
-- Pure sanity check for a freshly built authored MeshPart. A mesh that did not really load renders as a plain
-- cube/box (or has zero size); the built part's size must match the extents of the source vertices.
local Sanity = {}
-- expected / actual: Vector3-like with X, Y, Z. Returns ok, reason.
function Sanity.check(expected: any, actual: any, triangles: number?): (boolean, string?)
    for _, axis in {"X", "Y", "Z"} do
        local e, a = expected[axis], actual[axis]
        if a ~= a or e ~= e then return false, "nan" end
        if e <= 0 and a <= 0 then continue end
        if a <= 0.01 then return false, "empty" end
        if math.abs(a - e) > math.max(.15, .35 * e) then return false, "size mismatch" end
    end
    if triangles ~= nil and triangles < 4 then return false, "too few triangles" end
    -- A cube has three (almost) equal sides; authored creatures never do.
    local x, y, z = actual.X, actual.Y, actual.Z
    local lo, hi = math.min(x, y, z), math.max(x, y, z)
    if hi > 0 and lo / hi > .92 and not (expected.X > 0 and math.abs(expected.X / expected.Y - 1) < .08 and math.abs(expected.Z / expected.Y - 1) < .08) then
        return false, "cube"
    end
    return true, nil
end
return Sanity
