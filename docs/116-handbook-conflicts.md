# 116 Handbook conflicts and ambiguities (2026-10-16)

Found while writing [114](114-handbook.md). Each row: the two statements, which is NEWER, resolution, and an **OWNER QUESTION** only where the owner must decide. "RESOLVED" = decided by a newer owner decision and the old text marked SUPERSEDED in place (history kept). Decisions: [115](115-decisions-log.md).

## A. Resolved (owner answers 2026-10-16 and clear supersessions)
| ID | Conflict | Newer / resolution |
|---|---|---|
| C-1 | **Teleport free vs paid perk.** docs/104 15.1 item 4 and 16 item 4 (lead, 2026-10-16): teleport ON by default. BD-391 (owner, same day): maybe purchasable. | RESOLVED by owner answer 2026-10-16: fast travel is a Crystal Shop perk (crystals, not Robux), walking default, default off, Settings toggle only after purchase, glow guide stays free. docs/104 and BD-391 updated. Price PROVISIONAL. |
| C-2 | **First eggs safe vs Cracked 50%.** `SafeEggs = 2` (BD-365) vs condition weights 50/30/15/4.5/0.5 in AGENTS.md and docs/09. | RESOLVED: keep safe eggs; Cracked 50% applies from the third egg on. Handbook s9. |
| C-3 | **Crystal colour.** Cave shop crystal meshes `hub_crystal_s/l` and cave `CrystalColor` (196,170,255) are blue-purple; HUD and packs art and the gold UI colour are amber/yellow. | RESOLVED: amber/yellow everywhere for currency; blue-purple only as cave decoration. Code fix BD-400 plus new BD-401 (audit every currency surface, plus a check). |
| C-4 | **Cave dim vs bright.** docs/104 s4 says "the cave must never be dark" and "no ColorCorrection for the cave"; docs/87 and others say warm light; BD-399 code is warm-dim with a ColorCorrection `CaveGrade`; the owner now says DIM, lamp-lit. | RESOLVED: owner statement is newer: dim, lamp-lit, readable dino. docs/104 s4 is superseded on "never dark" and "no ColorCorrection" (the grade is accepted). Add a floor so the dino stays readable (BD-402 check). |
| C-5 | **Weather inside the cave.** docs/104 s4 (weather stays outside) vs code that leaked weather (BD-383, BD-398). | RESOLVED: owner: weather never affects the inside; BD-383/398 are the fix; add a permanent automated check (BD-403). |
| C-6 | **Catch rate.** docs/03, docs/00 and old kanban text still mention 40/400 or 15/150 eggs; `Config.FoodCatchRate` is 4/500 (AGENTS.md was already corrected). | RESOLVED: 4/500 is newest (docs/89, 2026-10-15). AGENTS.md already carries the strike-throughs; docs/00 now points at the handbook. |
| C-7 | **Fusion ladder.** AGENTS.md was corrected to 6/3/2; docs/46, docs/57, kanban BD-065/BD-057 text say 10, 15/4/2 or 50/10/3; code and docs/90 say 6/3/2. | RESOLVED: 6 Base (any pattern) / 3 Gold / 2 Emerald (owner 2026-10-15, BD-335). AGENTS.md, docs/03 and docs/46 now mark 10, 15/4/2 and 50/10/3 as HISTORICAL in place. |
| C-8 | **Species tiers.** AGENTS.md (2026-10-14) says five tiers with provisional weights tuned to the 40/400 examples; docs/00 says "three species categories Common/Rare/Legendary" and docs/82 sample table is 40/400-based. | RESOLVED: five tiers, run boost {1,1,1.1,1.1,1.1} (docs/89). Old table is history. |

## B. Open conflicts and ambiguities
| ID | Statement A | Statement B | Newer | Proposed resolution |
|---|---|---|---|---|
| C-9 | Handbook lighting for island: Bootstrap sets ClockTime 14, Brightness 2. | docs/87 says each biome has a palette; no per-biome lighting doc (volcanic, marsh) | unknown | Keep island base; per-biome rules are an owner/art task. OWNER QUESTION Q6 |
| C-10 | docs/87: weather tone "calm to be inside", effects "gentle". | docs/84 owner 2026-10-14/15: "stronger, more aggressive, boring" and the Blood Moon, Volcano, Thunder looks | 84 owner feedback is stronger | Read as: look dramatic, behaviour calm. Keep both; handbook s3 states it. OWNER QUESTION Q4 |
| C-11 | **Skins:** docs/97 base look "cartoon" in the table but "LOW-POLY" in the decisions; Robux skins Bricks, Clay, Plushy; "Animated-movie and Anime" unlockables. | New **Balloon** skin idea (lead session) is not in any doc. docs/87: "Robux off" until policy passes | 97 decisions newer | Do not add Balloon to docs/97 until the owner confirms (it needs a defeat animation, a pop, and must stay kid-gentle). OWNER QUESTION Q5 |
| C-12 | **Aura/trail ownership:** docs/46 and BD-059: per-dino, lost at fusion. Code (`ProgressionConfig`, profile) and BD-393: per account / the equipped dino. | | docs/46 is the target; code is per account today | Shops say "For: <dino>" (BD-393) now; per-dino migration is BD-059. **RESOLVED 2026-10-16:** per dino instance, lost on fusion; migration still BD-059 (docs/115). |
| C-13 | **Eyes:** docs/100 prompts: solid glossy black eyes with white highlight. docs/87 and docs/105: dinos are matte and gloss only on fused tiers. | | both current | Read: matte body, eyes may have a small glossy highlight (baked in the mesh texture, not a material). Handbook 4.2 says so; confirm. OWNER QUESTION Q7 |
| C-14 | AGENTS.md "reveal approx five seconds each" and "5-slot ordinary egg queue" vs `HatchRevealSeconds` 1 s and bank 1,000. | | docs/09 (2026-10-13) newer | Mark five seconds historical in AGENTS.md; handbook says 1 s. |
| C-15 | AGENTS.md owner example "6 nests offered, max 5 claimable" vs code `NestMaxPerRun` 3 (docs/90). | | docs/90 newer | Treat the 6/5 example as history; owner should confirm nest cap per run. **RESOLVED 2026-10-16:** unlimited nests per run, 5 spots, extras become crystals (docs/115). |
| C-16 | docs/00 header "Reviewed 2026-10-08 against Build 020", still names Build 020 as current and "40/400 eggs" text. | | 89/90 newer | Add a pointer to the handbook (done) and refresh the stale lines when the next build is cut. |
| C-17 | Conditions have no colour table in code or docs (overlay textures only). | handbook wants every colour decision listed | n/a | BD-406: add one condition colour table (Cracked, Dirty, Normal, Rainbow, Astra) for UI chips. |
| C-18 (RESOLVED 2026-10-16: Nature set, see docs/114 s5.11) | No per-class colour table (Ground, Fly, Water, Armored), the owner asked for palette per class. | docs/101 only defines the HP bar colours | n/a | Proposal: Ground = green #5DED1F, Fly = blue #2ECEFF, Water = teal #16AA97, Armored = amber-brown #BA7A50. OWNER QUESTION Q2 |
| C-19 | Agent counts and models: [78](78-lead-handoff.md) "Sonnet or Haiku only, never Opus, at most 2 agents"; kanban log "keep 3-4 agents"; lead brief "keep 3, Sonnet default, Fable for hard tasks" (BD-397). | | lead brief newest | Handbook uses 3 agents, Sonnet default, Fable for hard tasks; 78 is historical on usage limits. |
| C-20 | "Children 7-10" is not written anywhere. docs say only "children and their parents". | | n/a | Handbook adopts 7-10 as LEAD reading. OWNER QUESTION Q1 |
| C-21 | Cave floor colour: docs/104 s4 "light grey-blue so dark dinos read, lava side warm, crystal side cool" vs BD-384 "hot orange floor" found in Studio vs BD-384 fix "cool grey-lilac". | | BD-384 newer (code) | Palette 5.10 says floor must not be hot orange; BD-402 adds an automated colour check (hue band). |
| C-22 | docs/104 s4: crystals use "lavender/teal" inner lights; owner D24: no blue-purple in shop contexts. | | owner newer | Decoration crystals may stay lavender; the Style Grotto is a SHOP (shop crystals amber). Confirm the grotto crystals count as shop. OWNER QUESTION Q9 |

## C. OWNER QUESTIONS (precise)
- **Q1 Audience.** Is the audience children aged 7-10 as the handbook assumes? Options: (a) 7-10; (b) 6-12; (c) all ages with kid-safe tone.
- **Q2 (RESOLVED 2026-10-16: (a) Nature set, hex in docs/114 s5.11) Class colours.** Approve per-class colours: (a) Ground green / Fly blue / Water teal / Armored amber-brown as proposed; (b) other; (c) no class colours (icons only).
- **Q3 (RESOLVED 2026-10-16: per dino instance, lost on fusion) Aura/trail ownership.** Per dino as docs/46 (buy again per dino, lost at fusion) or per account (simpler, matches code)? Options: (a) per dino; (b) per account; (c) per account now, per dino after Fusion launch.
- **Q4 Weather tone.** Keep strong dramatic looks (docs/84) with calm audio, or soften visuals to match docs/87? Options: (a) keep strong; (b) soften; (c) strong only for rare events.
- **Q5 Balloon skin.** Add a Balloon skin to the skin set (Robux, defeat = pops and flutters away softly)? Options: (a) yes, Robux later; (b) yes, crystals; (c) no.
- **Q6 Per-biome lighting.** Should each biome (volcanic, marsh, conifer) have its own daylight tint, or one bright island light with only terrain colour changing? Options: (a) one light; (b) subtle tint per biome.
- **Q7 Eyes.** Confirm glossy black eyes with a white highlight are the one allowed shiny spot on matte dinos. Options: (a) yes; (b) fully matte eyes with a painted highlight.
- **Q8 (RESOLVED 2026-10-16: unlimited per run, 5 spots, extras become crystals) Nest cap.** Max bonus nests per run: 3 (code) or the old example of 6 offered / 5 claimable?
- **Q9 Style Grotto crystals.** Are the cave Style Grotto crystals a shop context (amber) or scenery (may stay blue-purple)?
- **Q10 Fast travel price.** Starting price in crystals for the perk (PROVISIONAL): options 300 / 600 / 1,200; unlocked also by account level?

Resolved by owner 2026-10-16: fast travel perk (Q-travel), first two eggs safe, amber crystals.

## D. Stale statements in AGENTS.md
Checked: catch-rate examples and the ladder were already corrected by earlier PRs. Fixed here in place: "approximately five seconds each" (reveal is 1 s, C-14) marked SUPERSEDED with a pointer; the handbook is linked first. Left as history: the 'Build 020 config' bullets, the 6-nests-offered example (C-15, Q8) and the 'six trail rarity categories proposed' line.

## E. Vision answers 2026-10-16 (owner)
Audit against code and docs: eggs kept when eaten = match. Mismatches (kanban): ~~Peaceful hard to find and absent with combat off (BD-421)~~ (SUPERSEDED 2026-10-16: owner correction, there is no Peaceful, docs/115), play-as-any class feel unproven (BD-423), no server rare-hatch announcement or confetti (BD-424), Robux line needs a guard check (BD-425). Audience (Q1) is still open: the answers say play and Robux but not an age band. docs/101 Q "PvP always on or optional" is answered: optional.

## F. Giant dinos vs the jungle (spec [139](139-giant-dino-vegetation-scale.md), 2026-10-16; C-24, C-25 (part) and C-26 resolved by owner answers 2026-10-16; C-23 and C-27 OPEN; questions are Q1-Q12 in docs/139 s14)
| ID | Statement A | Statement B | Question |
| --- | --- | --- | --- |
| C-23 | docs/87 and handbook 8.1 item 3: a grown dino still feels small next to big trees | owner 2026-10-16: the dino should be gigantic at the end; only colossal ancient trees stay taller | docs/139 Q3 |
| C-24 | D19 / BD-386: growth 5x slower; a 5-minute run reaches only about 1.5x size | owner wants "gigantic at the end" | docs/139 Q1: **RESOLVED 2026-10-16 (OWNER): keep current pacing; gigantic is a rare long-run reward** |
| C-25 | handbook 0 and 3: friendly, calm, readable at a glance; BD-312 / BD-253: big bodies and foliage that fill the camera were a defect | owner wants small players "intimidated"; a max dino fills up to 55% of the screen | docs/139 Q2: **RESOLVED 2026-10-16 (OWNER): awe only, no fear mechanics**; Q8 (screen share) stays OPEN |
| C-26 | D8 / D15: generated meshes only; Blender models wait for owner uploads | colossal tree art requested "in Blender"; the running tree-quality-test uses scripted Blender trees | docs/139 Q5: **RESOLVED 2026-10-16 (OWNER): Blender allowed for colossal and redesigned tree art; V3 trees approved as a scoped exception** |
| C-27 | handbook 3 weather: about 25-30 studs readable around the dino; fog starts 25-100 studs from the camera | the camera sits 40-60 studs from a big dino | docs/139 Q9 |
