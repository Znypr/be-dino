# Event mutations and visual upgrade

> **HISTORICAL Build 019 event/cosmetic implementation snapshot.** It accurately records old three-trail cosmetics and 1/2/3 egg thresholds for that build but is **not** the current ten-trail Build 020 scope or the owner's egg-per-catch goal. Use [Build 020 integration](44-main-integration-checklist.md), [reward target](09-reward-economy.md), [full weather task BD-055](45-owner-feedback-shop-hud-world-weather-tasks.md) and [Kanban](07-kanban.md) for current direction.

**Egg-art follow-up:** [Shared egg appearance vision](39-egg-appearance-shared-vision.md) records the latest owner direction: preserve shell colors/patterns, use surrounding engulfing smoke and dimensional anime-like energy for event mutations, and keep condition effects separate. These Blender drafts supersede shell-painted mutation and flat-ring art proposals; they do not certify runtime integration or change the mechanics below.

Follow-up: docs/37-hatching-traits-and-leaderboards.md adds independent Shiny/BIG,
precommitted rarity-ordered reveals and map rankings. These supplement the event
mutations below; newer hatch timing supersedes earlier incubation descriptions.

2026-10-08, Build redesign-019, branch redesign/resources-and-core-fixes.
User direction: focus on weather, auras, trails and 3D visuals. Published non-owner
permissions, physical-phone checks and multiplayer/persistence release tests are
deferred by the user, not passed.

## Implemented mechanics

Seven weighted events: Rain, Thunderstorm, Blizzard, Volcanic Bloom, Northern
Lights, Earthquake and Blood Moon. Clear intervals remain 600 seconds; events
last 180 seconds. No damaging hazards or terrain deformation are implemented.
Event loot bonuses increase food-derived catches. When a food pickup crosses an
egg reward threshold, the server rolls and records that event's mutation once.
The metadata survives return/reset/disconnect settlement, active slots, FIFO
overflow and hatching. The client never rolls rewards. PvP-only earned eggs are
untagged. Eggs show mutation names/tints; catches announce earned eggs; hatching
shows the committed mutation and perks.

| Weather | Weight | Loot | Mutation chance | Mutation | Growth / Speed |
|---|---:|---:|---:|---|---|
| Rain | 50 | 1.10x | 2% | Dewdrop | 1.08x / 1.00x |
| Thunderstorm | 30 | 1.40x | 4% | Charged | 1.00x / 1.10x |
| Blizzard | 20 | 1.25x | 4% | Frost | 1.12x / 1.00x |
| Earthquake | 12 | 1.40x | 5% | Seismic | 1.15x / 1.00x |
| Volcanic Bloom | 6 | 1.65x | 7% | Ember | 1.18x / 1.04x |
| Northern Lights | 6 | 1.50x | 7% | Aurora | 1.12x / 1.08x |
| Blood Moon | 4 | 1.75x | 8% | Blood Moon | 1.10x / 1.12x |

These are provisional private-test values in ProgressionConfig, not approved
public balance. The user's 500 food / 10 eggs example has NOT replaced the
existing economy: 500 raw food points still yields 15 catches before weather;
10/100/500 catches still earns 1/2/3 eggs. Event copies are stored separately
from Base/Gold/Diamond and do not become fusion fodder. The last owned mutation
in EventMutations catalog order auto-applies to that species, without stacking
multiple event perks. Individual variant selection remains future work.

## Cosmetic and 3D direction

Three crystal-priced permanent cosmetic trails: Fern Drift (45), Tidal Wake
(180), Nova Ribbon (650). The existing aura shop now has AURAS/TRAILS tabs,
shared catalog-driven previews, purchase confirmation, owned/equip/unequip
states and larger phone shop targets. Auras use orbiting curved beams and
restrained motes; moving trails use two tapered ribbons. Mutations add a colored
light/glow. Client effects update at 30 Hz, prioritize the local player, and
are bounded to eight players within 180 studs. Reduced effects disables them.

Six new textured models were generated through Studio with a requested 6,000
triangle budget per dinosaur. Real model IDs, exact prompts and map IDs are in
resources/visual-upgrade-bindings.json. All six model creators and all twelve
selected material map creators were checked against owner User 7285577648
(znyprs). Actual triangle totals were not measured. Model imports retain only
geometry/appearance, normalize to packaged heights, preserve controller
collision, and retain native models on import failure or empty binding.

Grass, rock and wood use authored MaterialVariants in
resources/world-materials.rbxmx. Variants cannot be created by ordinary server
scripts: the initial runtime attempt failed and was removed. The builder now
packages MaterialService and its overrides. Run tools/bind_visual_assets.py
after changing the manifest, then tools/build.py. Rojo source-only sync must
also import the authored material service; changing JSON alone is insufficient.
Imported preview cameras fit actual bounds rather than the old native vertices.
Gold/Diamond clones drop painted texture layers and use metal/glass treatment
on the new geometry, so source textures cannot hide their mutation colors.

## New requested expansion (Todo, not implemented)

On 2026-10-08 Znypr requested a broader crystal/egg economy and ten tiered trails. The three **implemented cosmetic** trails listed above remain the current Build 019 baseline; the proposed replacement/extension is tracked under **BD-035–041**. New trails grant increasing speed as well as coloured walking effects, require escalating **persistent account levels** and crystal prices, and end at **Astra** with glitter particles. Existing owned trails require migration, and speed balance/multiplayer safety require fresh tests.

Further planned work: run-end crystals and crystal reveals, Robux-purchasable crystals, crystal-priced random eggs, a five-minute Speed Potion, progressively improved condition odds with Cracked/Dirty/Normal/Rainbow/Astra stat tiers, weighted two-colour eggs, Normal/Big visual sizes, and independent shiny sparkles. **None of these newer mechanics is claimed as implemented** by the event/VFX acceptance evidence above. See [full design and open decisions](36-crystal-shops-egg-genetics-and-progression.md) and [canonical Kanban](07-kanban.md).

## Evidence and remaining work

See evidence/2026-10-08-events-and-cosmetics/README.md. Verification uses a
separate unpublished copy with GameId/PlaceId 0 and unsaved profiles. No
persistent player profile was opened or modified. Forced weather transitions
and deterministic mutated eggs are disposable test fixtures, not natural-event
frequency evidence. Fixtures are not included in repository source/build.

All six models render, but they remain visual drafts requiring art approval,
animation review and measured device performance. Tree/rock/fern mesh generation
failed at publish/insertion; original prop geometry remains. Aurora ribbons,
moon and earthquake dust are a first VFX pass, not finished illustrated assets.
New event PNGs, custom effect textures and environment meshes remain artwork
tasks. Physical-phone readability, all modal touch targets, non-owner loading
and multiplayer performance are not verified in this session.
