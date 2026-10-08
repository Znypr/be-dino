# Be Dino redesign, 2026-10-04

> **HISTORICAL 2026-10-04 redesign request.** The phrase below saying main was Build 013 was true at the time, **not today**. Mountain-island art direction remains relevant. Current build: [README](../README.md); current map tasks: [BD-049–050/053](45-owner-feedback-shop-hud-world-weather-tasks.md).

> **HISTORICAL 2026-10-04 redesign request.** The assertion below that GitHub main "is still Build 013" was true **at this document's creation**, not after Build 020 was merged to main. The mountain-island direction remains relevant; for current status, see [README](../README.md), [Build 020 integration](44-main-integration-checklist.md) and [new map-art task BD-049](45-owner-feedback-shop-hud-world-weather-tasks.md).

## Direction
Znypr rejects the primitive blockout. The new target is a coherent stylized prehistoric island with proper reusable mesh assets, intentional landmarks and spacious, dimensional menus. The supplied screenshot shows a newer layout than GitHub main (main is still Build 013). This change is based on the actual repository; uncommitted local work is not assumed to exist here.

## Acceptance
- Trees and rocks block the dinosaur body, while food, foliage and VFX do not. Visual growth must not create a giant invisible collider or move the feet below ground.
- Small pickups cover every navigable map sector, in scattered clusters. Common berries have low value; larger fruit and rare amber award more. Respawning relocates food within its sector.
- Startup removes Roblox's default loading screen independently of character spawn. Profile/character failure becomes a readable error. Unpublished Studio uses disposable memory profiles; published servers never silently replace failed saves with blank data.
- `resources/` contains editable UI vectors/raster exports, real OBJ/MTL mesh sources, import instructions and a rights/ID manifest. Runtime models resolve through stable logical names.
- Dimensional popup shells use layered borders, gradients, animated scale and real 3D dinosaur previews. Inventory displays grouped counts and rarity, keeps equip/mutation actions and works on small screens.

## Map plan
Open central meadow with curved landmark clusters: fern groves, rocky outcrops, amber ridge. Keep wide navigation lanes and starter clearance. Hide rectangular collision boundaries behind natural rock/tree dressing. Do not distribute trees in an evenly spaced line or use a test obstacle lane as the map.

## UI reference study
Study Pet Simulator 99 for readable collection cards and large primary actions; RIVALS for hierarchy, item previews and separated categories. Reuse interaction patterns and dimensions, with original prehistoric colors and artwork. No copied logos, extracted textures or bundled third-party assets.
References consulted: https://www.roblox.com/games/87224703310554/RIVALS ; https://db.biggames.io/ ; Roblox importer https://create.roblox.com/docs/studio/importer .

## Asset integration
Generate actual triangulated meshes and material sources. Import OBJ through Studio's 3D Importer and put resulting Models under ReplicatedStorage/Resources using the manifest logical names. The build loads these when present; unimported objects explicitly use the procedural fallback. OBJ files in GitHub are source assets, not automatically published Roblox asset IDs. EditableMesh is not a production dependency because permissions and replication require extra setup.

## Verification
Run packaging/economy regression, validate all generated mesh indices and bounds, verify sector distributions with deterministic seeds. Studio runtime checks: first start unpublished; API failure in published test; walk into tree/rock from multiple angles; collect food in all quadrants; resize to max growth; inspect preview/equip/mutate/chest menus on desktop and phone. Runtime acceptance remains pending until actually played.

## Superseding Build 015
Large mountainous island, jumping and crystal/egg food are now requested and implemented in source. Client-local mesh/icon generation embeds the original source assets for supported API sessions; permanent imports remain optional. See docs/27-mountain-island.md for current status and remaining Studio checks.
