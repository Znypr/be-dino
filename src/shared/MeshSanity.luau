--!strict
-- Pure sanity checks for authored MeshParts. A mesh that did not really load renders as a plain cube/box
-- (or has zero size); the built part's size must match the extents of the source vertices.
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
-- The cube root cause (BD-219, Studio evidence 2026-10-16): a MeshPart made by CreateMeshPartAsync(Content.fromObject(mesh))
-- does NOT own a copy of the geometry. Its MeshContent keeps pointing at the EditableMesh; once that is destroyed the
-- object reports 0 vertices / 0 faces and the part (and every clone of it, in the world or a ViewportFrame) renders as a
-- box of the right Size. Size alone can never catch it, so the loaded check looks at the content itself:
--   sourceType: "Object" (Content.fromObject), "Uri" (uploaded asset) or "None"; faces: face count of the object (nil when
--   it could not be read); meshId: the part's MeshId. Returns loaded, reason.
function Sanity.contentLoaded(sourceType: string, faces: number?, meshId: string?): (boolean, string?)
    if sourceType == "Object" then
        if faces == nil then return false, "mesh object unreadable" end
        if faces <= 0 then return false, "editable mesh destroyed (0 faces)" end
        return true, nil
    end
    if sourceType == "Uri" or (meshId ~= nil and meshId ~= "") then return true, nil end
    return false, "no mesh content"
end
return Sanity
