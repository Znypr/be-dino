# Authored runtime creature exports

These JSON files are the delivered geometry and eight-pattern masks for 16 authored creatures plus the canonical egg. Their editable Blender masters remain in the workspace's `Dino_Models` and `Premium_Egg/Color_Genetics` directories; original `.blend` files and high-detail/LOD exports were preserved.

`*-genes.json` contains 128px rank masks and fixed facial RGB samples. Geometry JSON contains LOD1 triangles, face UVs/normals, up to four skinning weights, rest bones and five sampled poses per Idle/Move clip. The egg is static, at 1,400 triangles.

Run `python tools/integrate_creatures.py` to regenerate `src/shared/CreatureData` and `CreatureGenes`. Generated strings are split into chunks below Studio's 200,000-character Source assignment limit. No runtime HTTP server is needed: all geometry and masks are packaged in the place.

The shared texture uploads are real owner assets:

| Effect | Asset |
|---|---|
| Soft mutation mist | `rbxassetid://105629313112163` |
| Warm-white Shiny glint | `rbxassetid://70885382548001` |

Both returned successful owner-Studio fetch status. New static mesh publishing was unavailable; the game uses bounded editable geometry for these exports. See [integration and release limits](../../docs/43-creature-runtime-integration.md).

The `previews` images are Blender authoring comparisons, not gameplay screenshots or phone performance evidence.
