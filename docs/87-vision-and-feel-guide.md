# 87 Vision and feel guide (owner, 2026-10-15)

The one place that says **how Be Dino! should feel**. It applies to game behaviour, UI, looks, sounds, motion, effects and copy. Every agent and contributor reads it before touching any of those. Task status lives only in [the Kanban](07-kanban.md); rules for reward numbers live in [AGENTS.md](../AGENTS.md).

> **Project name:** the working title is still "Be Dino!". The owner wants a proper name for the whole project (game, brand, tone). Open decision, see BD-182.

## The feeling in one line
**Calm, bubbly, friendly, and a little magical.** A child (and the parent next to them) should feel safe, curious and rewarded, never startled, pressured or overwhelmed. Excitement comes from colour, motion and discovery, not from loudness or sharpness.

## Five pillars
1. **Cozy before flashy.** Soft shapes, warm light, rounded corners, matte surfaces. Spectacle is allowed, but it must be pleasant to sit in for 30 minutes.
2. **Bubbly and playful.** Things pop, wobble, bounce and sparkle softly. Feedback feels like a bubble, a chime, a squish, not a buzzer.
3. **Readable at a glance.** One idea per screen, big shapes, few words (see [docs/72](72-ui-copy-and-asset-standards.md)). The dino and the next action are always clear, even during effects and weather.
4. **Rewarding, never harsh.** Wins are celebrated with warmth and colour. Losses and failures (Cracked egg, being eaten) are funny or gentle, not punishing.
5. **Handmade and consistent.** Original art with one style across eggs, dinos, world and UI. No placeholder, code-drawn or off-style art as final.

## Sound (lessons from playtest 2)
The first sound pack was synthesized and was far too loud and sharp (a lawnmower-like spawn sound, a harsh run-end sting, a loud weather start). Rules from now on:
- **Character:** soft, round, bubbly, warm. Think marimba, kalimba, glass bubbles, soft pops, gentle chimes, rubbery squeaks, airy whooshes. No saw/square buzz, no clipping, no harsh high-frequency transients, no sustained noise bursts.
- **Attack:** slow enough to feel soft (about 10-30 ms fade-in), no hard clicks. Short tails, no abrupt cut-offs.
- **Loudness:** UI sounds are quiet (target peak about -12 dBFS before the in-game gain; in game most cues play at volume 0.15-0.35). The loudest sound in the game is a legendary hatch, and even that stays gentle. A global gain (`Sfx.Master`) exists and nothing may bypass it.
- **No stacking:** at most one reward-style cue at a time. Chain by timing, not by volume.
- **Ambience:** weather and world beds are quiet loops (volume about 0.15-0.3) that fade in and out. Weather events are never silent and never startling.
- **Rarity** is expressed by richer harmony and more sparkle, not by being louder.
- Every new sound gets a brief (character, length, loudness) before it is made, an asset-registry line ([docs/77](77-asset-registry.md)), and is judged by ear by the owner before it ships. Agents cannot listen: they must say so and never claim a sound is "fine".

## Looks
- **Style:** friendly low-poly with soft rounded forms, clean colour, matte materials. Dinos are matte; shine and metal are reserved for fused tiers (Gold, Emerald, Diamond) and Mythic effects.
- **Colour:** saturated but harmonious, no muddy greys, no single-colour walls. Each biome and weather event has a palette that still keeps the dino and food readable.
- **World:** lush and varied (biomes, many tree/bush/rock types, flowers, soft grass), never geometric blobs or repeated tiles, sized so a grown dino still feels small next to big trees.
- **Eggs and dinos are the heroes:** lit warmly, shown on the tile-floor/stage look from the egg art, never as cubes or placeholders.
- **Conditions are egg-only:** they make eggs look richer and limit how many dinos are given out. Dinos never show a condition.

## Motion and feel (behaviour)
- **Movement:** responsive but grounded and weighty, never floaty or top-heavy. The camera follows smoothly, no rattling over terrain.
- **Animations:** ease in/out, slight squash and stretch, soft overshoot. Nothing snaps. Reveals take their time (a hatch is a moment) but can always be skipped by the player.
- **Camera effects:** gentle zooms and shakes only, scaled by intent, off with Reduce Motion.
- **Pressure:** no countdown panic, no fear copy, no forced actions. The player is always in control.

## UI and copy
- Short, warm, plain words. One fact per line. Colourful cards and tiles instead of vertical lists. Big tappable targets, readable icons at 64 px.
- Names and sounds of buttons feel like toys, not tools. Menu names say what the player gets ("Shop", not "Auras").
- Children are the audience; parents are nearby. Randomised and paid features follow [docs/43](43-player-access-and-paid-random-policy.md) and are never pushed.

## Effects (auras, trails, mutations, weather)
- **Anime-inspired but gentle:** layered smoke, rim light, glow, rings and particles with real depth and bright colour, but soft edges and slow rhythm. Think "magical sparkle" not "explosion". Details in the upcoming FX direction (BD-161).
- **Always readable:** an effect never hides the dino, food or controls. Weather keeps at least about 25-30 studs clearly visible around the dino and uses colour, particles and soft haze, not opaque walls or full-screen tint.
- **Natural over geometric:** sky and fog blend by soft gradients, never visible boxes, hard silhouettes or duplicated celestial objects.
- **Budgeted:** every effect has a particle and part budget, a phone rate and a Reduce Motion version.

## Weather tone
Events are dramatic to look at and calm to be inside: strong colour, big sky, rich particles, soft audio beds. A scary-looking storm should still feel cozy. See [docs/84](84-weather-events-v2.md).

## Review checklist (agents and lead)
Before a PR that changes anything players see or hear:
1. Does it match the feeling line above on a screenshot or a real play session?
2. Is every sound quiet, soft and non-stacking, and was it judged by the owner (or marked "unheard")?
3. Is the dino/food/next action still readable during the effect?
4. Does it have a Reduce Motion and phone version, and a part/particle budget?
5. Is any text short and child-friendly, and any art non-placeholder or labelled `PLACEHOLDER`?
6. Did you say plainly what you could not verify?

## Maintenance
- Owner remarks about feel are feedback: record them here and in the Kanban, do not leave them only in chat.
- Older documents may describe loud/harsh sounds or flashy effects as targets. This guide wins for feel; older docs are historical on those points.
