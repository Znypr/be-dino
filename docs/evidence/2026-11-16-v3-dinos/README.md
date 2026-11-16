# V3 dinos and authored clips (BD-1216, BD-1217), 2026-11-16

Built playtest place (`python tools/build.py --profile playtest`), opened in a separate Studio copy (GameId/PlaceId 0), Play mode, local client.

## BD-1216: the game already rides the V3 dinos (playtest profile)

`01-rest-v3-compy.jpg`: the player's dino is the owner's V3 Compy (same model as the V3 cutout `resources/ui/v2/dinos/v3/compy.png`; registry
`src/shared/LowPolyDinoAssets.luau`, loaded by `LowPolyDinoLoader`, cloned by `LowPolyDinos.clone` for the player, the Index, shop and hatch previews).
Client read: `SpeciesId compy`, visual `LowPoly = true`, parts body, head, tail, 2 arms, 2 legs. The benchmark picture `07-player-dino-lowpoly.jpg`
(docs/242 row 7) shows this same V3 model: the "faceted figure with blank black eyes" IS the V3 style. The default profile (flag off) still shows the
older models, by rule (flags off by default).

Still open, needs the owner: Parasaurolophus uses a pre-V3 model (Place1 has "Parasaurolophus" and a "cannon alt"; a published Model id is needed);
cockatoo and eagle have no V3 folder; Kentrosaurus, Liopleurodon, Archelon, Sauropelta and Styracosaurus have V3 models but are not game species.

## BD-1217: authored clips eat, happy, look-around

Keys: `tools/blender/dino_clips.py` (one source) -> Blender actions in `assets/blender/anim/DinoClips.blend` and the game module
`src/shared/LowPolyClips.luau`. `LowPolyAnimator` adds the playing clip on top of the procedural pose. Idle, walk, run and jump stay procedural:
they follow the real speed and the humanoid state (speed-synced legs, take-off, air tuck, landing), which a fixed clip cannot.

| Clip | When | Studio numbers (head weld, degrees pitch, every 0.1 s) |
|---|---|---|
| eat (1.4 s) | GrowthScore or CatchScore goes up (the dino eats) | rest 0 -> -17, -24, -19, -16, -24, -19, -17, -23, -18, -11, -2, 0 (dip, two chews, back to rest) |
| happy (1.6 s) | VisualScale goes up (growth) or a new species is put on | tail yaw 18, 16, -9, 24, 4, -2, 21, -6, 0, 14, 4, -2, 0 (wag), whole dino lifts twice (`03-happy-hop.jpg`) |
| look (3.0 s) | standing still 8 s, then every 11 to 17 s | head turns about 20 degrees left, then right |

Pictures: `02-eat-clip.jpg` (head down, tail out), `03-happy-hop.jpg` (feet off the ground, head and tail up). Blender contact sheets of the proxy rig:
`blender-*-strip.png`, numbers in `blender-*-report.txt` (tools/animation_strip.py: ground, easing, joint speed all ok; "loop" does not apply,
the clips are one-shots).

Reduce Motion: amp 0 clears the clip (proved in `tools/verify_motion_poses.py` 251.drive_reduce with the clips loaded, and by
`tools/verify_lowpoly_clips.py`); not toggled in Studio (the MCP runs in another module context, so the game's UITheme cannot be switched from it).

Not verified: phone, other species in Studio (the tracks are per role, so every species gets them; only Compy was played), feel judged by the owner.
