# Reusable Be Dino aura layers

Separate transparent PNG masters generated with the built-in image-generation tool on 2026-10-08.

| Logical ID | File | Purpose |
|---|---|---|
| fossil_centerpiece_v1 | fossil-centerpiece-v1.png | Shared neutral fossil footprint centerpiece |
| aura_meadow_ring_v1 | aura-meadow-ring-v1.png | Full green leaf aura with transparent hole |
| aura_tidal_ring_v1 | aura-tidal-ring-v1.png | Full cyan water aura with transparent hole |

## Composition
Use rear ring -> centerpiece -> front ring. Reuse the same ring image twice; transparent clipping Frames select upper/lower regions. A square parent preserves the ring's perspective. Place the rear group at ZIndex 1, center at 2, front at 3 and configure consistent descendant ZIndex behavior. Use the full image at the same parent-relative position and scale in both groups; compensate for each clipping Frame's offset so the halves align.

layout.json provides initial normalized positions, sizes and split. These are adjustable suggestions, not Studio-verified alignment. The fossil extraction was generative and has different proportions from the historical composite; scale and offset it independently.

No actual runtime UI has been changed. Upload under the experience owner, record real IDs and test layer alignment at 48/64/128px on desktop/mobile before marking integrated. Native ImageLabel tint is best used cautiously; cyan water and green leaf silhouettes differ, so use the corresponding ring rather than treating these as exact recolors.

## Reuse and animations
The center is optional: replace it with a real dinosaur/model preview. Ring opacity and subtle scale pulses can animate independently. Do not rotate a flat perspective ellipse and call it real 3D orbiting VFX. Leaves/droplets/glints currently belong to each ring bitmap; independent animated sparkles can be an additional shared overlay later.

## Status
All three assets: Generated draft. RGBA/transparent pixels checked; both ring center pixels are fully transparent. Roblox upload, image permissions, UI integration and device verification remain pending. Original combined drafts in ../items are preserved as reference only.

prompts.json records the exact prompts and sources. ../scalable remains the preferred source for simple functional icons.
