# Reusable potion, mutation and catches artwork
Five individual transparent PNG drafts, generated one at a time on 2026-10-08. Prompts are in item-prompts.json; initial overlay tuning is in item-layouts.json.

| Source | Use |
|---|---|
| potion-speed-base-v1.png | Cyan bottle; overlay existing speed/bolt symbol |
| potion-growth-base-v1.png | Green bottle; overlay existing leaf/growth symbol |
| mutation-gold-v1.png | Smooth metal Gold footprint badge |
| mutation-diamond-v1.png | Faceted cyan crystal Diamond footprint badge |
| catches-mark-v1.png | Neutral ivory footprint, used once or repeated through UI |

Potion emblems are separate to support replacement, sizing, tint and animation without changing bottle artwork. Existing scalable geometry or owned uploaded symbols can supply the overlay. PNG/SVG files in GitHub are sources, not automatically available Roblox image IDs.
Use the same two bottles for all six current potion products, with configurable rarity frames, names, durations, multipliers and quantities. A colored bottle alone is not a sufficient type label: pair it with the distinct emblem and live text.
The catches group is decorative; do not imply a fixed number of rewards from its number of footprints. At very small HUD sizes prefer one mark and the Catches label.
Mutation badges are separate from species rarity. Diamond artwork is prepared for the requested feature; it does not prove that Diamond progression is implemented.
All files have square RGBA canvases and fully transparent surrounding pixels. Visual inspection completed at source size; small-screen legibility, actual uploaded asset access and Studio integration remain pending.
No runtime scripts or product balance were changed. Upload under the experience owner, record actual IDs, and verify thumbnails at 32/48/64px in the real UI.
