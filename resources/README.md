# Reusable Be Dino resources

Start with the [2D asset gallery](ui/README.md). Build 015 embeds the real mesh sources and icon pixel data for automatic client-local creation when Roblox Mesh/Image APIs are available. Manual OBJ import below remains the permanent-asset fallback. Current implementation/checks: [Build 015](../docs/27-mountain-island.md).


Original mesh and interface sources, versioned alongside the game. These are the new asset sources, not finished rigged characters or already uploaded Roblox content.

- `models/`: 10 real triangulated OBJ meshes with MTL colors, facing -Z, Y up, in studs.
- `ui/icons/`: six editable SVGs and transparent 256px PNG exports.
- `concepts/mesh-lineup.png`: rendered from the actual OBJ files, not generated concept art.
- `manifest.json`: logical names, source paths, geometry counts, provenance and Roblox upload status.

## First mesh import
1. Open `build/BeDino-Prototype.rbxlx` in Studio, before starting Play.
2. Use **File > Import 3D** for `models/compy.obj`. Keep its MTL beside the OBJ. Import the mesh/materials at source scale, with front facing -Z and Y up. Inspect colors: if the importer separates material pieces, group them into one Model.
3. Name the Model **compy** and move it into **ReplicatedStorage > Resources**. Remove imported scripts. Keep all mesh parts inside that Model; model geometry is cloned and sanitized at runtime.
4. Press F5. The dinosaur should be a mesh, not the rounded primitive fallback. Runtime normalizes the ground pivot, scales the model, and welds it to the controller. Check `Character.VisualSource` for `Imported mesh`.
5. Repeat for **triceratops**, **tyrannosaurus**, **tree**, **rock**, **fern**, **egg**, **berry**, **fruit**, **amber**. Logical names must match exactly.
6. Save the imported place under a new filename. The dependency-free build packages code, not uploaded meshes; rebuilding the base `.rbxlx` does not preserve manual imports. Save the imported Models as `.rbxm` sources here and record upload IDs in the manifest for the next integration step.

The game runs before import, but uses fallback primitives. Imported tree/rock visuals have separate simple solid colliders. Small foliage, food and VFX stay non-solid. Meshes currently use rigid whole-body movement, not skeletal animation.

## UI image upload
Upload the six `ui/icons/*.png` images to the experience owner using Studio's Asset Manager. Set the returned `rbxassetid://...` strings in `src/shared/UITheme.luau` under `ImageIds` and record them in the manifest. Until then, buttons retain their text labels. Keep text/buttons native and editable; do not bake functional menus into one image.

## Rebuild sources
`python tools/generate_resources.py` generates geometry and SVGs without dependencies.
`python tools/render_resources.py` exports transparent PNGs and the mesh lineup using Pillow, NumPy and Matplotlib. Commit source and exports together.

## Model budgets and editing
Starter and T-Rex are ~2,000 triangles; Triceratops ~3,000. Fern meshes are a first-pass asset and need mobile profiling if instanced heavily. Generated anatomy is an initial mesh pass, with visible faceting and rigid joints. Edit the geometry generator or open OBJ/MTL in Blender to refine silhouette/materials, then export back to the same logical ID. Rigging and idle/walk/eat animation are the next art pass, not claimed complete in this build.
