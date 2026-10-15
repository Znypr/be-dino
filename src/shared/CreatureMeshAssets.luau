--!strict
-- Uploaded mesh bindings for the 16 authored creatures and the egg (BD-219). The skinned FBX exports live in
-- assets/blender/creatures/fbx (creature_<species>.fbx, same bone names, bind poses and UV layout as CreatureData).
-- When the owner uploads one, put its mesh asset id here ("rbxassetid://..."); AuthoredCreatures then prefers the
-- uploaded MeshPart over the runtime EditableMesh build, adds the same Bone instances (so Idle/Move poses and the
-- 15 Hz pose interpolation keep working) and paints patterns on the same UVs. Empty = not uploaded: never invent IDs.
-- Alternative drop-in without editing code: a MeshPart named <species> inside ReplicatedStorage.CreatureMeshes
-- (an imported skinned mesh, Bones optional: missing ones are rebuilt from CreatureData).
return {
    egg = {meshId = ""},
    archaeopteryx = {meshId = ""},
    baryonyx = {meshId = ""},
    brachiosaurus = {meshId = ""},
    dimorphodon = {meshId = ""},
    elasmosaurus = {meshId = ""},
    gallimimus = {meshId = ""},
    ichthyosaurus = {meshId = ""},
    microraptor = {meshId = ""},
    mosasaurus = {meshId = ""},
    pachycephalosaurus = {meshId = ""},
    parasaurolophus = {meshId = ""},
    plesiosaurus = {meshId = ""},
    pteranodon = {meshId = ""},
    quetzalcoatlus = {meshId = ""},
    spinosaurus = {meshId = ""},
    therizinosaurus = {meshId = ""},
}
