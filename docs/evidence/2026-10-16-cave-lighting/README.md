# Cave lighting QA (BD-286, BD-295, BD-296), 2026-10-16

Studio copy of the playtest build with `Config.CaveHub = true` in the COPY only (never committed). Camera forced from a client script; the modal blur and HUD were hidden for the shots (QA artefacts, not the cave look).

"Before" for the hall is `../2026-10-16-cave-shell/` (same shell, no shafts, weather blur on).

| File | What it shows |
| --- | --- |
| 01-light-shaft-from-heart-after.jpg | Soft shaft under the Heart hole, no depth-of-field blur, warm hall |
| 02-wall-limestone-178-158-138-before.jpg | Wall at the old Limestone colour |
| 03-wall-limestone-200-176-152-test.jpg | Lighter Limestone (shipped 196/172/150): grid a little softer |
| 04-wall-rock-option-rejected-dark.jpg | Rock replaced for Limestone/Sandstone: dark, cold, rejected |
| 05-gate-before-glow-tweak.jpg / 06-gate-after-light-and-mist.jpg | Gate arch light 1.0 then 2.0 plus mist: reads, still only a niche until the frame mesh exists |
| 07-lava-falls-32-high-under-ceiling.jpg | Lava vein and sheet fit under the back-wall ceiling |

Honest rating against docs/87 (calm, bubbly, readable): **5.5 / 10**. Warm and calm, the shaft and weather-blur fix work and nothing is dark. Held back by the flat yellow-tan walls with a visible fine grid and dark smudges, no rock forms, an over-saturated yellow floor glare near fill lights and a gate that is still only a faint niche. Those need the BD-282/283 meshes; owner judges by eye.
