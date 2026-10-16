# 97 Dino skins (owner idea, 2026-10-15)

**Status: owner decisions 2026-10-16 recorded below; implementation not started.**

## Owner decisions (2026-10-16)
- **Base look for all dinos: LOW-POLY** (faceted, flat-shaded, made with Roblox's mesh generator, split into body parts for animation). First 3 species in development: Compy, Raptor, Triceratops.
- **Unlockable skins (crystals or a season pass, to decide):** Animated-movie style and Anime style.
- **Robux skins in the shop:** Bricks (toy-brick style, falls apart on defeat), Clay (squishes flat), Plushy (deflates).
- 3D AI-generated potions replaced by owner-made 2D ChatGPT potion icons (glass look).
 Owner direction: every dino has one BASE look (cartoon style, generated with Roblox's mesh generator) and players can buy SKINS that restyle the same dino in a different material world. Each skin has its own personality, including how the dino "falls" when it loses a run.

## Skins (first set)
| Skin | Look | Defeat animation (kid friendly, funny, never violent) | Idle/move flavour |
|---|---|---|---|
| Base (cartoon) | bright cartoon dino, gene colours and patterns shown exactly | dizzy stars, flops over, poof of cartoon smoke, respawn | squash and stretch steps |
| Plushy | soft chibi plush toy, stitched seams, button-like eye shine | deflates with a soft 'pfff', falls over like a toy, a little stuffing puff and floating cotton bits | slight wobble, soft bounce |
| Clay | handmade claymation, fingerprint texture | squished flat like a clay pancake (gets pressed down), then reshapes | slightly squishy footsteps |
| Bricks | studded toy bricks | falls apart into its bricks, bricks bounce and scatter, then click back together on respawn | tiny brick click sounds |

Later candidates: low-poly crystal, golden statue (fusion reward), glow/neon (Mythic).

## Rules that keep it fair and on-vision
- **Cosmetic only.** Skins never change stats, growth or odds (docs/88 rarity stays about genes and fusion). This keeps them safe to sell and keeps the game fair for kids.
- **Direct purchase, not random.** A skin is bought outright (crystals for common skins, Robux later behind the existing release flags), so no paid-random policy issues (docs/43).
- **Genes still matter.** Colours and patterns from the egg must stay visible on every skin, in the skin's own way (bricks recoloured by gene colour per brick region, plush fabric tinted, clay tinted). Technique to prove on one species first.
- **Per species.** A skin is bought per species (or per dino copy, decision open). 22 species x 3 skins = 66 models plus the 22 base models; the generator makes this feasible, each model split into body parts (body, head, tail, legs) for walking animation.
- **Defeat animations are short (about 1.5 s), funny and soft** (docs/87): no gore, no harsh sounds; Reduce Motion shows a simple fade.
- **Fusion tiers** (Gold, Emerald, Diamond) layer on top of any skin as a sheen or trim, so a Gold brick dino looks like gold bricks.

## Open decisions
1. Skin bought per species or per individual dino copy?
2. Price: crystals, Robux, or both (Robux stays off until the release flags allow it).
3. Confirm 'cartoon' as the base look after a 2-3 species pilot.

## Defeat hook and sound brief (BD-249, 2026-10-16)
- Code: `LowPolyPose.sampleDefeat(role, side, lead, ctx, amp, out, class, skin)`; the animator reads the visual attribute `LPSkin` (Base, Plush, Clay, Bricks; anything else is Base). Behind `Config.LowPolyDinos` (off). Reduce Motion: no motion (the fade stays the fallback).
- Sound brief (the owner judges by ear; nothing is made yet): one quiet, short sound per skin, never sharp or loud: Base a soft "poof", Plush a gentle "pfff" air leak, Clay a soft squish "pomp", Bricks two or three tiny brick clicks. Under 1 s, low volume, SFX pack rules (docs/87).
