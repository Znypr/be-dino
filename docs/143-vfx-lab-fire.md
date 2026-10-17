# 143 Fire VFX lab: aura, trail and footprint approaches (BD-492, owner request 2026-10-17)

Status: RESEARCH + TRIAL, **owner verdict: overall extremely poor, three small pieces kept (3.0, 4.1)**. Labels: **CURRENT** (what exists now), **MEASURED** (seen in Studio), **ESTIMATE** (craft knowledge, no phone run), **PROPOSED**. Nothing here is bound to a game slot and no `src/` file changed. Builds on [123](123-anime-3d-fx-research-and-plan.md) (technique catalogue T1-T11), [87](87-vision-and-feel-guide.md) (calm, bubbly, readable) and `tools/qa/phone_budgets.json` (phone: 24 beams, 16 lights, PROVISIONAL).

Owner target images: `docs/reference/vfx-fire-aura-ref.webp`, `vfx-fire-trail-ref.webp`, `vfx-fire-footsteps-ref.webp` (ChatGPT references, a look target, not an exact spec).

## 1. What was built

A separate Studio place, kept OUTSIDE the repo: `C:/Users/znypr/dtmp/VFXLab.rbxlx` (bright daylight, no weather, no haze, a walkway in front of every row, spawn at the left). Three rows (Auras, Trails, Footprints) of six cells. Every cell has the published low-poly Compy (`LowPolyDinoAssets.compy`, scaled to 5.4 studs tall) as the stand-in; in the trail and footprint rows the driver walks it a 24-stud loop back and forth, turning to face the viewer at each end (the owner watched this live; I did not inspect the motion myself). Each cell has a sign on posts behind it (technique, what it uses, an automatic count of emitters / live sprites / beams / trails / parts / decals / lights, a phone rating and a one-line note). Column 1 of every row is the no-limits HERO.

Rebuild it: serve `tools/vfx_lab/` on `127.0.0.1:8766` (`python -I -m http.server 8766 --bind 127.0.0.1`), open any empty place in Studio and run `lab_build.luau` in the command bar (it loads the dino models, builds ground, signs and cells, and installs `ReplicatedStorage.VFXLabDriver` and a LocalScript that starts it in Play). Every dino and effect helper part is anchored and moved by CFrame from the driver (client side), so trails and beams behave exactly like on a moving dino. Textures are the test uploads listed in [77](77-asset-registry.md) (`vfx_lab_*`).

## 2. The textures (Blender renders, no code-drawn pixels)

`tools/blender/build_vfx_lab_fire.py` (run by `python tools/render_vfx_lab_fire.py`): real Cycles renders of modelled geometry. A flame is a tapered ribbon along an integrated, curling centre line; an emission shader bands a heat value into the cel colours of the reference (deep red-orange rim, orange body, yellow, pale-yellow hot core); side licks branch off the main tongue and curl back; a soft glow sits underneath. Pillow only pastes the finished frames into sheets. Contact sheet: `docs/evidence/review-2026-10-17/31-vfx-lab-textures.png`.

| Texture | Layout | Used for |
|---|---|---|
| fireTongueBig | 2x2 of 512, 4 bold tongues, random frame | aura tongues, trail flames (hero) |
| fireTongueSwirl | 2x2 of 512, tongues leaning and curling sideways | aura swirl, trail flames |
| fireTongueSheet / fireClusterSheet | 4x4 of 256, 16-frame loops | cheap flipbooks, footprint flames, billboard stamps |
| fireSparkSheet | 4x4 of 128 | sparks and embers |
| firePuffSheet | 4x4 of 256, neutral grey-white | smoke (tinted warm cream-orange) and dust (tan) at runtime |
| fireStreakStrip, fireFlameStrip | 1024x256, tile in U | Beams, SurfaceGui flame cage |
| fireTrailFlame | 1024x512 | thick Trail ribbon with peeling tongues |
| fireRingGround | 1024x1024 | ground ring decal |
| fireFootprintL / R | 256x256 | footprint decals |

Lessons: a freshly uploaded image is "being generated" for a short while and renders as nothing (console: "Asset content representation is being generated"); an emitter that was created before it finished can stay blank until the texture is preloaded (`ContentProvider:PreloadAsync`). Small round or diamond sprites read as confetti: only big shapes (2-6 studs) with a clear silhouette read as fire.

## 3. Findings per approach

### 3.0 Owner verdict (2026-10-17, seen live on screen 3)

"F3 somewhat usable, T2 only the smoke good, we can maybe work with A3 smoke attempt. But overall extremely poor." An earlier owner remark on a first scaffold window: "it looks coded, like circles and really low quality small sprites." This is the honest outcome: **the lab as built does NOT reach the reference images.** Flat sprites, decals and beams, however well they are rendered, read as "coded" next to the concept art; only three small pieces are worth keeping (section 4).

Two facts that shaped what the owner saw (MEASURED in the Studio console): (1) a fresh upload logs "Asset content representation is being generated" and draws nothing for a while, so for part of the session the tongue emitters were invisible and only sparks showed; once the textures loaded (`ContentProvider:PreloadAsync`), A1 showed big banded tongues, but too many of them (they hid the dino). (2) A first scaffold window that the owner also saw held only emission-shape test plates with sparks, not the lab.

### 3.1 Per cell: what it is, what I actually saw, verdict

"Seen" = I looked at a Studio capture of it. "Not inspected" = built and counted by the sign scanner, but I never looked at it before the owner asked me to stop touching Studio; no claim is made about how it looks.

| Cell | Approach | Cost (sign scanner, instance counts) | Seen? | Verdict |
|---|---|---|---|---|
| A1 HERO layered | ring decal x2, 4 orbiting tongue emitters (hero + swirl sheets), 6 beams in 2 rings, 2 warm puff emitters, sparks, 1 PointLight | 7 emitters (about 33 live sprites), 6 beams, 14 parts, 2 decals, 1 light | yes | Ring decal on the ground: strong, the closest thing to the reference (`30-vfx-lab-a1-ring-tongues-not-loaded.jpg`). Tongues after the texture loaded: bold and readable but far too dense, they cover the dino (`30-vfx-lab-a1-hero-tongues.jpg`). Beams not seen. Owner: poor overall. |
| A2 tongue particles | 3 orbit emitters + puffs + sparks | 5 emitters (about 27 live), 4 parts | sparks only (tongues not yet loaded) | Not judged. |
| A3 beam swirls | 2 rings x 3 Beams with the streak strip + sparks | 1 emitter, 6 beams, 6 parts | yes | Beams read as thin zigzag slivers around the body, not flames (`30-vfx-lab-a3-beams-sparks.jpg`). A3 has no smoke layer in this build: see question 1 in 4.3. |
| A4 orbit trails | 3 Trails on orbiting anchors | 3 trails, 3 parts, 1 emitter | no | Not inspected. |
| A5 ring + flame cage | spinning ring decal + 8 SurfaceGui panels | 9 parts, 1 decal, 16 gui planes | no | Not inspected. |
| A6 cheap | ring decal + 2 tongue emitters + sparks | 3 emitters (about 9 live), 1 decal | no | Not inspected. |
| T1 HERO thick ribbon | 2.8-stud Trail (fireTrailFlame) + 2 follower beams + tongue shed + dust + sparks | 3 emitters, 2 beams, 1 trail, 2 parts | no | Not inspected. Owner: poor overall. |
| T2 ribbon (cheap) | 1 thick Trail + dust puffs | 1 emitter (about 6 live), 1 trail | owner yes | **Dust/smoke: good (owner).** The ribbon itself: not good enough (owner). |
| T3 tongue particles | tongues shed at the tail + dust | 3 emitters (about 21 live) | no | Not inspected. |
| T4 follower beams | 3 Beams to lagging followers | 3 beams, 1 emitter, 3 parts | no | Not inspected. |
| T5 stacked trails | 3 Trails (ribbon, streak, flame strip) | 3 trails | no | Not inspected. |
| T6 billboard flames | 16 pooled BillboardGuis, flipbook by script | 16 gui planes, 16 parts | no | Not inspected. |
| F1 HERO fire prints | decal + scorch pad + cluster flipbook + embers + smoke + light per print | 10 prints: 20 parts, 10 decals, 31 emitters, 10 lights | no | Not inspected. |
| F2 decal only | 10 pooled decal prints | 10 parts, 10 decals | no | Not inspected. |
| F3 decal + embers | decal prints + a 5-spark ember burst per step | 10 parts, 10 decals, 10 emitters (bursts, about 14 live) | owner yes | **Somewhat usable (owner).** Kept: recipe in 4.1. |
| F4 print + scorch | decal + dark scorch pad | 20 parts, 10 decals | no | Not inspected. |
| F5 flame cluster | decal + cluster flipbook per print | 10 parts, 10 decals, 10 emitters | no | Not inspected. |
| F6 glow light | decal + PointLight per print | 10 parts, 10 decals, 10 lights | no | Not inspected; lights are the likeliest phone frame cliff (ESTIMATE). |

### 3.2 What worked, what did not (technique level)

| Technique (docs/123) | Worked | Did not |
|---|---|---|
| Ground-ring decal on a flat part (spinning) | Read at once, almost free (1 part, 1 decal), the best match to the aura reference. | Needs a large flat area; it is a ring only, not volume. |
| Big flipbook tongues (2x2 of 512, random frame) | Silhouette and cel banding match the reference when the texture is loaded. | Several emitters at 4-5 studs smother the dino; no interaction between tongues, so it reads as stickers, not one flame body. |
| Beams with a scrolling streak strip | Cheap (6 beams) and flowing. | Thin lines, not flames; zigzag at short range. |
| Thick Trail with a ribbon texture | One object, cheap. | Owner: not convincing; a flat textured strip has no depth or tongue motion. |
| Pooled Part+Decal footprints with a cooling colour | Cheapest readable "burning ground" (F2/F3 family). | Static image; looks stamped. |
| Dust/smoke puffs (neutral sheet, tinted at runtime) | The one thing the owner liked: soft, calm, the tint decides warm smoke or tan dust. | n/a |

Not tried (needs owner action in Studio): real 3D flame meshes with scrolling UV (cone / shell / ribbon) imported as MeshParts. Roblox cannot offset UVs on a MeshPart, and the Studio MCP cannot import an FBX, so the lab used flat panels instead. The three FX meshes already in `assets/blender/fx/` (shock dome, shaft cone, aura shell) are not uploaded yet. This is the most likely next step to close the gap to the reference (PROPOSED, untested).


## 4. Recommendation

### 4.1 Keep (owner picks), with the exact recipes

All three share the dino stand-in and run on the client; the numbers are what the lab used.

**F3 footprints (decal + embers).** Textures `fireFootprintL.png` / `fireFootprintR.png` (256x256: solid glowing pads for heel and three toes with claw tips, banded dark-red rim / orange / yellow / pale core, one small flame tongue curling off each pad; Blender, `footprint_scene`) and `fireSparkSheet.png` (4x4 of 128: six four-point sparks, five curved embers, three round glows, two slim streaks). Pool of 10 anchored, non-colliding Parts 3.1 x 0.1 x 3.1 studs (Transparency 1), each with one Decal on the Top face. A stamp every 3.4 studs of travel (the dino runs 13 studs per second, so about 3.8 per second), alternating left and right at 0.9 x leg half-width from the path and 0.5 stud ahead or behind, at y 0.07, turned to the heading, 1.8 s life. Decal colour cools from white to (255,170,90) at 35 percent of life to (110,45,35); decal transparency stays 0 until 45 percent and then smoothsteps to 1. Embers: one ParticleEmitter per print on an Attachment (0,0.2,0), Rate 0, `Emit(5)` at each stamp: texture the spark sheet, Grid4x4, FlipbookMode Random, LightEmission 0.5, Lifetime 0.7 to 1.3 s, Speed 1.5 to 3, SpreadAngle 40, Size 0.5, 0.7 at 30 percent, 0, Transparency 0, 0.2 at 70 percent, 1, Acceleration (0,3,0). Cost: 10 parts, 10 decals, 10 emitters used only as bursts (about 19 sprites per second, about 14 alive), 0 lights, 0 beams. Phone rating on the sign: OK (ESTIMATE, not measured).

**T2 dust (the smoke the owner liked).** Texture `firePuffSheet.png` (4x4 of 256: 16 cartoon puffs, spheres clustered with banded NEUTRAL toon shading, grey-white so Color decides the tint; Blender, `puff_frame`). Emitter on an Attachment at the dino's feet (0, hip height minus 0.3 below, 0.6 behind): Grid4x4, FlipbookMode Random, **Color (214,184,140)** tan, Rate 7, Lifetime 0.7 to 1.1 s, Speed 1 to 2, SpreadAngle 40, Size 1.0, 2.0 at 40 percent, 2.7 studs, Transparency 1, 0.4 at 15 percent, 1, Acceleration (0,0.5,0), Rotation 0 to 360, RotSpeed -20 to 20, LightEmission 0, LightInfluence 0. Cost: 1 emitter, about 6 live sprites.

**A3 smoke attempt (warm puff).** Same `firePuffSheet.png`. In the lab the warm puff lives on an invisible orbiting carrier part (cells A1 and A2, not A3, see 4.3): radius 3.9, height 0.9, 0.9 rad per second, **Color (255,176,104)** warm cream-orange, Grid4x4 Random, Rate 2.4 to 3, Lifetime 1.0 to 1.5 s, Speed 0.4 to 0.9, SpreadAngle 25, Size 1.7, 3.4 at 40 percent, 4.6 studs, Transparency 1, 0.5 at 15 percent, 0.65 at 60 percent, 1, Acceleration (0,0.6,0), RotSpeed -20 to 20, LightEmission 0. Cost: 1 emitter, about 7 live sprites.

### 4.2 Recommendation per effect (honest)

- **Aura:** keep the ground-ring decal (the one piece that matches the reference at near-zero cost) plus the warm smoke puff at a low rate; drop the stacked tongue emitters and the beams as the main look. A plain flat-sprite aura will not reach the concept art.
- **Trail:** keep the dust puff. The thick ribbon Trail did not convince; do not ship it as the trail look.
- **Footprints:** F3 (decal + embers) is the base; F2 (decal only, same textures) is the Lite fallback (PROPOSED).
- **Next experiment (PROPOSED):** real Blender-modelled flame volume (a few layered, curled shells with a baked cel gradient, imported as MeshParts) for the aura and the trail head, with the sprites only as accents; this needs the owner to import the FBX in Studio.

### 4.3 Open questions for the owner

1. "A3 smoke attempt": the A3 cell in this build (Beam swirls) has no smoke; the only smoke in the lab is the warm puff in A1/A2 and the tan dust in rows 2 and 3. I assumed you meant the warm puff recipe above. Is that right?
2. Keep the ring decal as the aura base even though the tongues were rejected?


## 5. Not verified

- No real phone run: every cost is a count of instances (the sign shows the same numbers) and an ESTIMATE of draw cost.
- Studio edit-mode captures only (driver run from the command bar); not a Play session through the full client. Most cells were never inspected by me (table 3.1) because the owner asked me to stop touching Studio.
- The lab place is NOT saved to `C:/Users/znypr/dtmp/VFXLab.rbxlx` (that file is an empty stub): the live lab is the open window `VFXLab-Fire.rbxlx`, also unsaved. The builder scripts recreate it in a minute.
- The final `.blend` (`tools/blender/vfx_lab_fire_v1.blend`, 8 MB) is not committed; rerun `tools/render_vfx_lab_fire.py` to regenerate it.
- Nothing was bound to `FxRecipes` / `FxRig`; Full / Lite / Off and Reduce Motion variants of the chosen looks still have to be built.
- The `.rbxlx` is not in the repo (size and ids); the builder scripts are.
