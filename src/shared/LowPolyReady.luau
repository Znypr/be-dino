--!strict
-- BD-381: pure rule for "the low-poly model of this species is still on its way". The server loads the 22 templates with
-- InsertService (LowPolyDinoLoader) AFTER the first client is already looking at menus, so a preview built in that window used to
-- take the legacy model and keep it for good. While pending, a preview must wait (flat picture) and rebuild when the template lands.
-- Pending ends when: the flag is off, the species is unmapped, the template exists, the loader finished (a missing template is then a
-- real load failure and the legacy fallback is allowed), or WaitSeconds passed (a loader that never reports must not hide dinos forever).
local Ready = {}
Ready.WaitSeconds = 90
function Ready.pending(enabled: boolean, mapped: boolean, hasTemplate: boolean, loaderDone: boolean, waitedSeconds: number): boolean
    if not enabled or not mapped or hasTemplate or loaderDone then return false end
    return waitedSeconds < Ready.WaitSeconds
end
return Ready
