# 96 No more cubes: root cause and fix for cube eggs and cube dinos (BD-216, BD-219)

16 October 2026. Studio evidence from an unpublished playtest build (PlaceId 0, owner Studio, Play Solo client).

## Root cause (proven)

`AssetService:CreateMeshPartAsync(Content.fromObject(editableMesh))` does **not** copy the geometry into the MeshPart.
The returned part's `MeshContent` keeps pointing at the `EditableMesh` object (`SourceType = Object`, `MeshId = ""`).
`src/shared/AuthoredCreatures.luau` destroyed that mesh right after creating the part ("the MeshPart owns a copy: free
the budget now"). After `mesh:Destroy()`:

| Probe (Play Solo client, egg from `CreatureData`) | `Size` | `MeshContent.Object:GetFaces()` | Drawn as |
| --- | --- | --- | --- |
| live EditableMesh | 1.81 x 2.40 x 1.81 | 722 vertices / 1,400 faces | egg |
| mesh destroyed before parenting (what `build()` did) | unchanged | **0** | **cube** |
| mesh destroyed after parenting | unchanged | **0** | **cube** |
| `Clone()` of a part whose mesh is destroyed | unchanged | **0** | **cube** |

The part keeps its correct `Size`, so the size-only `MeshSanity.check` passed every time. Whether the cube showed up
depended on whether the renderer still had the geometry cached from the moment of creation, which made it look random
("sometimes"). Every `Clone()` (previews copy nothing today, but the hatch, Index, My dinos and the Conditions shop all
build fresh parts the same way) draws from the content, so any preview could become a box.

Measured with the real preview modules (`ModelPreview.add(tile,"egg")` x5, `DinosaurPreview.add(...)` for baryonyx,
archaeopteryx, spinosaurus, pteranodon, compy) in one window `BeDino-Cubes`:

- **Before:** 9 of 9 authored MeshParts had 0 faces and rendered as patterned cubes (the 7 uploaded compy parts were fine).
- **After:** 16 of 16 loaded, 0 cubes, `AuthoredMeshesLive = 5` (one template per species seen).
- **Watchdog:** destroying all 5 template meshes under 9 live previews turned them into 9 zero-face parts; one
  `AuthoredCreatures.sweep()` rebuilt the templates, re-applied the meshes (`MeshPart:ApplyMesh`) and repainted the
  patterns: 9 loaded, 0 cubes.

## Fix

- **Template per species** (`AuthoredCreatures`): the EditableMesh is built once per species and kept alive for the
  session (at most 17 small meshes, 916-2,010 triangles each). Every instance is a `Clone()` of the template part, so the
  per-instance budget pressure that motivated the early `Destroy()` is gone. Bones, the 15 Hz pose interpolation and
  `PatternGenes` painting are unchanged per instance.
- **Content guard, not size** (`MeshSanity.contentLoaded`, `AuthoredCreatures.isLoaded/verify`): a part is accepted only
  if its `MeshContent` object reports faces (or it is an uploaded `Uri`/`MeshId` mesh). Checked when the template is
  built, when every clone is made, and by previews before anything is parented to a `ViewportFrame`.
- **2D fallback, never a box:** `ModelPreview` shows the official egg picture (shell + condition layer, tinted by
  `EggAppearance`) when no loaded 3D egg exists; `DinosaurPreview` shows the flat dino icon (`PreviewFallback = DinoImage`)
  and swaps it for the real model when a retry succeeds. `HatchPresentation` keeps the plain 2D egg until a verified 3D
  egg exists (unchanged). A non-empty egg preview never falls back to the primitive ball.
- **Watchdog** (`AuthoredCreatures.sweep`, every 2 s on the client): if a template mesh dies under live instances they
  get the rebuilt mesh via `ApplyMesh` and a repaint; if that is impossible they are made invisible (`MeshLost`).
- **Uploaded meshes ready** (`src/shared/CreatureMeshAssets.luau`): species -> `meshId` (all empty: no invented IDs).
  When bound, the uploaded mesh is used (`Content.fromUri`), checked with the same extents + content guards, and gets
  the same Bone instances and pattern UVs; an imported `MeshPart` named after the species in
  `ReplicatedStorage.CreatureMeshes` works as a drop-in too. The skinned FBX exports are in
  `assets/blender/creatures/fbx` ([docs/95](95-owner-upload-guide.md) covers uploads).

## Condition marks facing the camera (owner feedback, same session)

In the Conditions shop row the Cracked/Dirty/Rainbow/Astra marks were on the far side of the egg. The overlay is a
`Decal` with `Face = Front` (`ConditionOverlays.apply`), and on a MeshPart that projects onto the part's **front box face
(local -Z)**, not through the UVs: a first attempt that turned the UV-measured side (-X, alpha-weighted mean face normal
(-0.99, 0.10, -0.13)) toward the camera showed nothing, while turning -Z toward it shows every mark. `PreviewCamera`
looks along **(1, .2, -.65)**, so the untouched egg had its -Z face at about 57 degrees from the view axis (marks at the
silhouette edge, or hidden). `EggPreview` now yaws the authored body once (`Egg.FaceYaw` = -0.999 rad, derived from
`DecorationNormal` (0,0,-1) and `CameraDirection`) so -Z points at the camera in every egg preview; shop, hatch and
Index all go through `ModelPreview` -> `EggPreview`. Measured after the turn: dot(-Z in world, direction to the
viewport camera) = **0.99** for all five shop eggs and the hatch egg; screenshot
`docs/evidence/2026-10-16-no-more-cubes/condition-eggs-facing-camera.png` (cracks, smudges, rainbow and astra
visible on the camera side). The Eggs screen uses the 2D picture (`EggPicture`), whose condition layer is drawn on top
and was never affected. Open: the viewport's fixed light (-1,-1,-1) now puts a hard shading terminator down the middle
of the egg; a softer light angle for egg previews is a small follow-up.

## Not verified

- A published place and a real phone (EditableMesh budgets and the "Allow Mesh / Image APIs" setting): the fix removes
  the destroy-after-create bug and adds the guards, but the published-place path still needs the owner's upload or the
  security toggle, as before ([docs/43](43-creature-runtime-integration.md)).
- Only the preview modules were driven by script; the full hatch screen and the Index were not clicked through by hand
  in this session (they call the same `DinosaurPreview` / `ModelPreview` code).
- Upload scale: an uploaded FBX whose size differs from `CreatureData` extents by more than 35% is rejected (warned) and
  the runtime mesh is used instead; check once in Studio after the first upload.
