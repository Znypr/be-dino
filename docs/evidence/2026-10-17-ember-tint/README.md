# Ember dino looked pale in the world: does the mutation tint replace the dino's colours? (BD-518, 2026-10-17)

Question (from `review-2026-10-17/49-ember-world-ring.jpg`): the equipped Ember dino looked cream/white under the "warm tint".

## Answer
By design the tint does NOT replace colours: `MutationLook` pulls each colour 22 to 26 percent toward the tint, hard ceiling 0.35 (`Look.MaxAmount`, docs/114 s4.3 and s5.6; `tools/verify_mutation_look.py`). The pale body in image 49 came from the dino's OWN genes (a cream/white dominant gene mix, for example blue primary at blend 19 with white secondary), not from the tint.

But there was a real bug next to it: on a low-poly dino the tint never rendered at all. A low-poly body part wears a baked texture (`TextureContent`, `LowPolyTexture`) and `MeshPart.Color` is ignored on it, so `MutationLook.apply` set `Color` (the part attributes `MutBase` = 1,1,1 and `MutOut` = 1,0.89,0.84 were written) and nothing changed on screen. Proof, same dino, real Ember catch:
- A-hub-ember-compy-as-is.jpg: hub, equipped Ember Compy (`EventMutationId = ember`, `Color` set to the tint by the old code).
- C-hub-same-dino-mutation-cleared-control.jpg: the same dino with the mutation cleared on the server (diagnostic control only). Identical look: the tint had no effect.
(The ring, motes and badge do work; only the body tint was missing.)

## Fix (BD-518)
The event mutation is now baked into the body pixels: `MutationLook.pull` (same maths as `Look.blend`, per pixel) is applied in `LowPolyTexture.paint` after the gene colours; the container attribute `LPMutation` carries the id (`LowPoly.setMutation`), the bake cache key includes it, fused tiers never get it. Wired for the world dino (`CosmeticVisuals`), the equip path (`ResourceVisuals`), previews (`DinosaurPreview`, `PreviewTraits`: hatch, Index, details). Legacy (non-low-poly) models keep `MutationLook.apply`.

After (new build, real Ember catch via admin Volcanic Bloom + Mutation chance x10, hatch, equip):
- D-after-fix-hatch-raptor-ember-baked.jpg: hatch preview, `LPLookKey = raptor|08_freckles|...|m:ember`.
- E-control-same-preview-ember-removed.jpg: the same preview with the ember bake removed on the client (control): bluer, no warm pull.
- F-after-fix-world-hub-ember-raptor.jpg and G-control-world-hub-ember-bake-removed.jpg: the equipped Ember Raptor in the hub with and without the bake. The difference is gentle on purpose (blue-grey pulled warm, patterns and eyes intact).
- 01-hatch-preview-blue-gallimimus-ember.jpg: BEFORE, hatch preview of an Ember dino on the old build (no warm pull visible).

Not covered: phone, other species one by one, Reduce Motion (the tint is static), a second player seeing it (the attribute replicates; each client bakes its own copy).

Verifier: `python tools/verify_mutation_look.py --runner <luau>` (pull equals blend, gentle, visible on cream, wiring scan for key, paint, world, equip, previews, PreviewTraits).
