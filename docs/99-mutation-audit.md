# 99 Event mutation audit (BD-154)

Owner 2026-10-15: "not sure mutations work yet: 1 visible, 2 gettable". Audit date 2026-10-16, branch `claude/audit-mutations-and-nests`. **CURRENT BUILD BEHAVIOR** unless marked otherwise. No Studio play check was run (see "Not verified").

## (a) Gettable: PROVEN offline
Path: weather (`ProgressionService` sets `workspace.WeatherId`) -> `FoodService` catch loop rolls `ProgressionRules.eventEgg(weatherId, roll)` once per catch ordinal and stores `{eventId, mutationId, n}` in the character attribute `RunEggEvents` -> `RunLifecycle.settlementSnapshot` -> `commitRunSettlement` (`placeEggTags`, exactly once, validated by `validEgg`) -> run egg / bank -> `claimChest` -> collection variant key (`EggTraits.key`) -> save. Weather nests (BD-156) roll the same chance at open.

| Check | Evidence |
| --- | --- |
| All 7 weathers roll their own mutation at the configured chance (2-8%), 20,000 eggs each within 4.5 sigma; every mutation has a source weather; clear/purchased eggs never mutate; a forged mutation is rejected | `tools/verify_mutations.py` |
| Tag placed on the right catch ordinal, kept through queue/bank, claim, hatch, variant count, reload; forged tags rejected | `tools/verify_rewards.py`, `tools/verify_progression.py` |
| Weather nests mutate at the run-egg chance, clear nests never (4,500 eggs) | `tools/verify_nests.py` |

## (b) Visible: wired everywhere, one gap fixed
| Surface | Where | Status |
| --- | --- | --- |
| Toast when caught | `Bootstrap.client` run-egg watcher | **Gap fixed**: only the newest tag was checked, so with several eggs in one tick (Food worth x10, big pickups) an earlier mutated egg got no toast. Now every new tag is scanned. |
| Egg card badge + soft live glow | `EggsScreen` (BD-162) | wired |
| Hatch reveal ribbon + tinted dino | `Bootstrap` result -> `HatchSequence` `r.mutationName` | wired (not shown for a failed Cracked egg, see G2) |
| Dino Index card line, details, My dinos tags | `Bootstrap`, `DinoIndexPanels`, `MyDinos` | wired |
| World dino tint, glow, particles, previews | `CosmeticVisuals`, `MutationLook` (BD-155), `PreviewTraits` | wired, `verify_mutation_look.py` |

`verify_mutation_look.py` now also scans that each of these hooks is still present, so a refactor cannot silently drop one.

## Findings
| ID | Finding | Severity | Action |
| --- | --- | --- | --- |
| G1 | Only newest egg tag toasted (above) | small | fixed here |
| G2 | A Cracked egg that fails to hatch also loses its weather mutation with no hint to the player (the egg was earned in weather for nothing) | design | owner decision, BD-235 |
| G3 | The tagging step in `FoodService` (ordinal loop, carry, cap) lives inside a server script and has no unit test; offline tests start from `eventEgg` and from `commitRunSettlement`, not the glue | medium | BD-236 (extract a pure `RunEggTags` module + test) |
| G4 | Weather nests take the weather active **at settlement**, not the weather during the run, so a run in clear weather settled during a storm gives mutation chances and the reverse loses them | design, deliberate in BD-156 | **Decided (owner 2026-10-16, BD-235): the nest carries the weather from the moment it was FOUND. Fixed in code by BD-479** (Review / test): `RunLifecycle` keeps a server-only per-nest weather ledger filled after every catch and at the minimum-run-time mark, the settlement snapshot carries it, `commitRunSettlement` stamps nest N with ledger entry N (legacy single id = every nest, as before). Tests: `tools/verify_gameplay.py`, `tools/verify_nests.py`, scans in `tools/verify_mutations.py`. Studio check still open |
| G5 | No in-game way for a tester to see the odds or confirm a mutation without playing long (admin panel starts weather and Food x10 but cannot force a mutation roll) | small | BD-237 (admin "mutation chance x10", built: `mutationChanceMultiplier`, docs/79; per player since 2026-10-17, admin's own catches only, docs/115; lead Studio check still open) |

## Studio check (2026-10-17, unseeded): PASSED
The lead check was run on a fresh `--profile playtest` Studio copy (claude/bd154-unseeded): Volcanic Bloom, Food worth x10 and Mutation chance x10 set by mouse in the real admin panel, then a real run. `FoodService` itself filled `RunEggEvents` (85 eggs, 51 Ember, no hand-written tag); toast, Eggs card badge, settle, hatch ribbon, Dino Index and Dino Details chips, preview and world tint/ring were all seen. Images and the step table: [docs/evidence/2026-10-17-bd154-unseeded/](evidence/2026-10-17-bd154-unseeded/README.md). One nit: the toast does not name the mutation when several eggs land in one tick (BD-508).

## Not verified
Second-player behaviour with the admin slider on a live multi-client server (offline cross-player sim only), a phone-size window, and persistence of the mutation through a real save (the playtest profile is memory-only).
