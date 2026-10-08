# Build 020: authored creatures, genes and stacked variants

8 October 2026. This is a Studio-tested integration build, with published release and physical-phone acceptance still open.

The catalog contains the original six species plus Brachiosaurus, Parasaurolophus, Pachycephalosaurus, Therizinosaurus, Gallimimus, Spinosaurus, Baryonyx, Microraptor, Archaeopteryx, Pteranodon, Quetzalcoatlus, Dimorphodon, Plesiosaurus, Ichthyosaurus, Mosasaurus and Elasmosaurus. Hatching, collection, equip, rarity multipliers and additive saved-profile migration recognize all 22 IDs. Existing balances, committed eggs and legacy gene keys are preserved.

These additions currently use the game's ground controller. Flight, diving, swimming, aquatic habitats and species-specific abilities are separate gameplay work. Pterosaurs and marine reptiles are included as prehistoric creatures; they are not classified as dinosaurs here.

## Appearance

- Eight patterns are baked from the accepted egg material graphs onto each new creature's UVs. The earlier six uploaded species use the shared egg masks on their existing UV layouts and retain their neutral texture shading.
- Two genes remain distinct. Mixed coverage is uniformly rolled from 1–99%; matching genes use their single colour family with lighter/darker pattern regions. Coverage calibration measures usable UV pixels, not the percentage seen from every camera angle.
- Eyes and mouths on the new creatures are fixed pixels. Dark facial pixels in older uploaded textures are retained. The canonical authored egg is packaged at 1,400 triangles and uses the same genes in nest/hatch previews.
- Nine palette families are available. Legacy IDs `white`, `gold`, `violet` remain valid aliases for Cream, Amber, Purple. Private-test per-slot weights total 10,000: Cream 5,000; Blue 2,600; Green 1,200; Pink 500; Teal 400; Amber 250; Purple 45; Red 4; Black 1. These are implementation defaults, not approved production balance.
- BIG stays at **1.2×**. Shiny uses four warm-white glints at **six particles/second total**. Event mutations use the owner-preferred broad wisps, coloured mist and elemental details. Colour genes, BIG, Shiny and event mutation can coexist. Gold/Diamond fusion appearance remains a separate system.
- Shiny previews have four glints. Viewport particles/beams are not presented as a substitute for the world effect; existing mutation labels identify the event in UI.

The canonical 3D egg takes priority over the older average-tinted 2D shell when editable geometry is available. Existing reveal timing and sound/flash logic remain; the authored native path does not use the older cropped 2D shell fragments. A proper split of the authored 3D shell remains a visual follow-up.

## Performance and lifetime

New world meshes use authored LOD1: **916–2,010 triangles**, one MeshPart, 10–18 bones, and at most four bone weights per vertex. Idle/Move poses are interpolated at 15 Hz. These budgets do not certify FPS.

Growth reuses the mesh, bones and image. It changes scale around the current ground pivot while temporarily releasing visual welds; it does not rebuild geometry at every food pickup. Gene changes repaint the existing image. Shiny resizes without restarting its emitters, and mutation wisps adapt to the current bounds.

The client caps authored mesh allocations at 12, editable painted images at 32, and each expensive world effect at eight nearby players. Images are 128×128: the pixel storage cap is 2 MiB before engine overhead and source-mask caches. Offscreen/hidden index previews release meshes, images and camera connections. Index buttons maintain a minimum 45-pixel scaled touch height. Reduced-effects settings remove world mutation/Shiny animation. API or budget failures retain existing fallback paths.

Common/Rare/Legendary aggregate egg weights remain **70/25/5**. Species weights are redistributed within those tiers to make the added species obtainable; individual old species odds therefore change for future rolls. Current in-game odds enumerate the actual configuration, including nine colours, eight patterns and uniform mixed shares.

## Verification

- Every new creature and the canonical egg constructed successfully in unpublished Studio, with skinned bones and EditableImage textures.
- The actual server reward/claim/equip path produced an **Archaeopteryx + Black/Black emerald pattern + BIG + Shiny + Ember**. The client reported scale 1.2, four Shiny emitters at total rate six, and the Ember FX folder.
- All seven mutation adapters stacked with Shiny/BIG and cleaned up their folders. Each mutation has four beams and four mist emitters at total rate 16. Uploaded glint and mist textures returned `AssetFetchStatus.Success` in owner Studio.
- Offline checks cover 22-species reward reachability and save migration; immutable claims/retries; exact gene UV coverage and facial pixels; same-family tonal contrast; 100 growth resizes retaining one mesh; geometry/weight budgets; source chunk roundtrips; compilation and packaging.

The local Latest Studio instance was later closed. The connected `newbuild` place's Edit copy was synced to Build 020, preserving its prior scripts in `ServerStorage.BeDinoBuild019ScriptsBackup` with runnable scripts disabled. No test reward was granted in that published place. This integration did not publish the experience. The generated `build/BeDino-Latest.rbxlx` is the durable clean build and contains no QA fixture or Studio backup folder.

## Release limitations

Studio's documented `CreateAssetAsync` returned **“CreateAssetAsync and CreateAssetVersionAsync are not available yet”**. No new mesh IDs have been invented or claimed uploaded. The bounded runtime path is usable in Studio; static uploaded meshes remain the preferred release route after real phone profiling.

Published use of editable meshes/images needs the verified-owner **Allow Mesh & Image APIs** security setting. Its state and non-owner client access have not been certified for this build. See [Roblox's published-game requirements and memory limits](https://create.roblox.com/docs/reference/engine/classes/EditableMesh/RaycastLocal). Do not publish on the assumption that Studio success proves this setting or device budgets.

Still required: physical-phone frame time/memory/thermal tests; maximum growth/BIG collision acceptance; published non-owner assets/API access; current persistent migration/rejoin; and visual review of legacy face preservation and the native egg reveal. Public drop balance remains provisional. The earlier shared egg/retention/species design documents remain the reference for work beyond this integration.
