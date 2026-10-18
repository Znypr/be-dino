# 188 Game wiki generated from the code (owner intake 2026-10-18)

Status: **SPEC, nothing built.** Rows BD-1052 and BD-1053 in [docs/07](07-kanban.md).

## What the owner said
The project has no wiki pages yet. Wanted: a page for **every dinosaur** with its picture, name, rarity, type (class) and the **chance of getting it**; the same for **colours, patterns, mutations** and so on. (The message was cut off after "mutation,", so the list of page types below is my best reading; the owner can add to it.)

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
