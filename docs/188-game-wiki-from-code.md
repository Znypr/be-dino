# 188 Game catalogue (team wiki) generated from the code (owner intake 2026-10-18)

Status: **SPEC, nothing built (updated after the owner's answer, see below).** Rows BD-1052 and BD-1053 in [docs/07](07-kanban.md).

## What the owner said
The project has no wiki pages yet. Wanted: a page for **every dinosaur** with its picture, name, rarity, type (class) and the **chance of getting it**; the same for **colours, patterns, mutations** and so on. (The message was cut off after "mutation,", so the list of page types below is my best reading; the owner can add to it.)

## OWNER ANSWER 2026-10-18 (replaces the player-wiki assumption)
For now the wiki is **for the owner and the team only**, so everyone (including Codex and other helpers) has ONE consistent place to read the current facts: which dinosaurs, colours, patterns and mutations exist, their pictures and icons, **what is missing**, and the odds. Example: when Codex creates new patterns or pattern icons for the Index, it checks the catalogue first and drops its files where the catalogue says. Later the same pages can be reused for a website or Discord.

**Consequences (LEAD decision):**
- The catalogue lives **in the repository as generated Markdown under `docs/catalog/`** (works offline, versioned with the code, readable by every agent without a GitHub wiki). A GitHub wiki is NOT needed for now (BD-1053 is parked as P4).
- `tools/build_wiki.py` becomes `tools/build_catalog.py`; CI checks that `docs/catalog/` is up to date (a stale page fails, like the other generated files).
- Every page has a **status column**: picture/icon present (path), asset id bound, mask present, odds source. A **"Missing" page** lists every gap (for example "pattern 05 has no index icon") with the exact file name and folder to use, so a helper or Codex knows what to deliver. New art still gets its docs/77 line.
- Because it is internal, **secret species and PROVISIONAL numbers may appear, clearly marked** ("SECRET, internal only", "PROVISIONAL"). The player-safe filter (no secrets, no off-flag features) is kept as a switch (`--public`) for the day the pages are reused for a website or Discord.

**IMPORTANT, flagged to the owner:** the owner believes the GitHub repository is private. GitHub reports `Znypr/be-dino` as **PUBLIC** (checked 2026-10-18 with `gh repo view`). Everything in the repo, including this catalogue, the secret species roster, design docs and uploaded asset ids, is therefore readable by anyone. Changing repository visibility is an account setting and is the owner's decision; nothing was changed.

## OWNER ANSWER 2 2026-10-18: a catalogue for everything, but few pages
Cover **everything**: dinosaurs, colours, patterns, conditions, mutations, potions, auras, trails, food, weather, biomes and wind ("breeze"), statues and other landmarks. **Rule: no page per item.** Twelve potions are not a section of their own; each item is a *section inside* its category page (heading, small picture, a few lines, a table row), reachable by an anchor link.

**Page layout (about 12 pages, hard cap 14):**
| # | Page | Sections inside |
|---:|---|---|
| 1 | Home | what the catalogue is, links, the five biggest gaps |
| 2 | Dinosaurs | one table (picture, name, class, rarity, odds), then one section per dino |
| 3 | Colours | table by tier, one section per colour |
| 4 | Patterns | table by tier, one section per pattern (after BD-1039) |
| 5 | Eggs and conditions | conditions, nests, hatch rules |
| 6 | Mutations and events | Shiny, BIG, event mutations, weather events |
| 7 | Fusion | tiers, the ladder, what is kept and rolled |
| 8 | Shop items | Potions, Auras, Trails as three sections, one row/section per item |
| 9 | Food | normal and special foods, points, spawn rule |
| 10 | World | weather, biomes, wind, statues, landmarks |
| 11 | Odds | every chance in the game in one table |
| 12 | Missing | every gap with the file name and folder to deliver |
If one category passes about 40 items, it stays ONE page with a contents list and tier headings; it is not split into per-item pages. A test fails if the tool writes more than 14 pages or a page for a single item.

## Facts checked (2026-10-18)
- The repository `Znypr/be-dino` is **public** and its GitHub wiki feature is **enabled** (empty). A GitHub wiki is its own git repository (`be-dino.wiki.git`); anything pushed there is public at once.
- All numbers the pages need already live in code: species and tiers (`ProgressionConfig`, docs/82), egg colours (`EggColors`), patterns (`EggGenetics`), conditions, mutations (`MutationLook`), class (`ClassInfo`), odds (`ShopOdds`, docs/85), pictures (`docs/evidence`, `resources/ui`).

## Proposal (LEAD decision, owner delegated 2026-10-16)
1. **Generate, never hand-write.** `tools/build_wiki.py` reads the same Luau data files the game and `verify_rewards` use and writes Markdown pages into `build/wiki/` (not committed): `Home`, `Dinosaurs` (table plus one page per dino: picture, name, class icon + word, rarity colour, chance per egg, size, notes), `Colours`, `Patterns`, `Egg conditions`, `Mutations`, `Fusion tiers`, `Odds`. Numbers therefore can never drift from the game. A test fails when a page shows a number that differs from the code.
2. **Pictures:** one reviewed picture per dino from the existing evidence/box renders; a missing picture shows a plain placeholder line and is listed in the tool's report. New art follows docs/77.
3. **Kid-friendly voice** (docs/72): short sentences, same names as in the game ("Ground", not "G"), no internal ids.
4. **Pattern and colour pages** come after the Index exists (BD-1039): same cards, same boost pips, same rarity colours.
5. **What must NOT go on a public wiki:** the **secret species** (docs/43, `SecretSpeciesEnabled`), anything behind an off flag (combat, paid packs, gifting), debug/admin/test features, unreleased odds that are still PROVISIONAL, asset ids and keys. The tool reads the flags and skips those; a test lists what it skipped. Odds stay "about" values until the owner approves publishing them (docs/43 odds disclosure rules).
6. **Publishing is the owner's call (BD-1053).** The tool only builds and previews locally. Pushing to the wiki repo (a public action) needs the owner's yes, and a refresh rule (rebuild on each release, not on each merge).

## Open questions (for the owner, short)
- Is the wiki for **players** (public, friendly) or for the **team** (internal reference, could live in `docs/` instead)? The plan above assumes players.
- Which page types besides dinosaurs, colours, patterns, mutations: potions, auras, trails, food, weather?
