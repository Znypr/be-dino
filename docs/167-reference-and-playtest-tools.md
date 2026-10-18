# 167 Reference sheet tool and playtest report tool (BD-647, BD-648)

Written 2026-10-18 (owner request, tools 7 and 8 of 8). Status: **Review / test. Offline only.** Two small helper tools and one playbook. Nothing in `src/` changed, no Studio and no Blender were used, and the default build is unchanged. Read [160 Agent brief](160-agent-brief.md) first.

- **Tool A, `tools/reference_sheet.py`** (BD-647): before a helper models a creature or draws an art piece, it collects a SMALL set of real pictures, and this tool turns the folder into one labelled picture and a notes file.
- **Tool B, `tools/playtest_report.py`** (BD-648): after a friends playtest, turns the game's own numbers into a one-page report with traffic lights.

Pictures: the sheet the tool makes is in [evidence/2026-10-18-reference-tools/contact-sheet-example.png](evidence/2026-10-18-reference-tools/contact-sheet-example.png) (copy: [review-2026-10-17/34-reference-sheet-tool-example.png](evidence/review-2026-10-17/34-reference-sheet-tool-example.png); an example from existing budgie pictures, not new art). A sample report is [evidence/2026-10-18-reference-tools/playtest-report-sample.md](evidence/2026-10-18-reference-tools/playtest-report-sample.md). Both were made offline from fixtures and existing files; **not Studio, not phone, not tested with a real playtest.**

---

# Part A: reference collector

## 1. Why
Models made without a good picture set come out as blobs (the first cockatoo tries, [evidence/2026-10-18-cockatoo](evidence/2026-10-18-cockatoo/README.md)). A small, well-sourced set (about 8 pictures: real photos for shape, cartoon or stylised pictures for the "cute" look) lets the helper write down what to copy BEFORE it builds. The tool is a workflow helper, **not an autonomous scraper**: it never goes on the internet. A person or an agent in the owner's browser picks the pictures.

**Art rule (AGENTS.md, repeated on every sheet):** the pictures are REFERENCE ONLY. They are not final art, not textures, not icons. Every picture keeps its own licence.

## 2. Playbook: research a creature in the owner's browser (Claude in Chrome)
1. Load the tools in one `ToolSearch` call (the Chrome tools list in the session instructions). Then `tabs_context_mcp` with `createIfEmpty: true`. Work in a NEW tab; never touch the owner's other tabs.
2. `navigate` to a source with a clear licence box, best first:
   - Wikimedia Commons file search: `https://commons.wikimedia.org/w/index.php?search=<creature>&ns6=1` (every file page shows author and licence).
   - Wikipedia article of the animal (the infobox picture links to its Commons page).
   - Pexels or Pixabay (licence stated on the page) for photos.
   - For the cartoon and stylised look: search for "<creature> cartoon" or "<creature> chibi" on a site whose page states a licence; Commons has CC0 and public-domain clip art. A picture with no licence line is "look only".
   - A general image search is allowed for LOOKING, but record the page the picture sits on and write `unknown` as the licence unless that page says otherwise.
3. Pick **at most 8** pictures: 2 to 3 photos from different angles (side, front, three-quarter), 1 to 2 close-ups of the hard parts (beak, claws, crest, feet), 2 to 3 cartoon or stylised ones. Fewer is better than many near-duplicates.
4. For each pick, write down on the spot: the page address of the PICTURE'S PAGE (not just the site), the licence and author from that page, and one line "what to copy" (shape of the crest, eye size, how the legs bend). Read the page with `get_page_text` or `find`; do not guess a licence.
5. Save a small copy: open the picture (on Commons ask for a thumbnail of about 800 to 1000 px), then use the browser's download. Downloads are pre-approved only when saved inside the project at a sensible size, a handful of files ([160](160-agent-brief.md) section 6). Move the file from the Downloads folder into `docs/reference/<creature>/` and shrink anything over about 1 MB or 1200 px, for example `C:/ffmpeg/bin/ffmpeg.exe -i big.jpg -vf "scale=1000:-1" small.jpg`. Never download more than about 8 files per creature.
6. Write `docs/reference/<creature>/sources.json` (format in section 3), then run `python tools/reference_sheet.py docs/reference/<creature>`. Look at `contact-sheet.png` and fix what `--check` complains about.
7. Close the tabs you opened (`tabs_close_mcp`). Never enter a password, never click through a login, a CAPTCHA or a cookie wall; on one of those, pick another source or stop and say so.
8. Add the creature line to [77 Asset registry](77-asset-registry.md) when a model made from the set is added; link `references.md` from the evidence README.

## 3. The tool
```
python tools/reference_sheet.py docs/reference/cockatoo           # writes contact-sheet.png and references.md
python tools/reference_sheet.py docs/reference/cockatoo --check   # only checks sources.json and the files
```
`sources.json` (a list, or an object with `creature` and `images`):

```json
{"creature": "cockatoo",
 "images": [{"file": "side-photo.jpg", "kind": "photo", "title": "Sulphur-crested cockatoo, side",
             "source_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
             "license": "CC BY-SA 4.0, Jane Doe", "date_read": "2026-10-18",
             "copy": "crest swept back, hooked beak, round eye ring"}]}
```
- `kind`: `photo`, `cartoon`, `3d`, `owner` (the owner's own picture, no web address needed) or `ai` (a ChatGPT sheet; give the prompt file as the source note).
- Errors (nothing is written): more than 8 pictures, a missing file, a source that is not a real web address, an empty licence, a picture listed twice, a bad `kind` or date.
- Warnings: no `copy` note, a file over 1.5 MB, a picture in the folder that is not listed.
- `contact-sheet.png`: numbered tiles with title, kind, licence and file name, plus a red "REFERENCE ONLY" line. Made with Pillow (already used in `tools/`) only to tile and label finished pictures; it draws no art.
- `references.md`: per picture the source, licence and author, date read, what to copy, a warning line when the licence is unknown or not free, and the reference-only rules.
- Tests: `tests/test_reference_sheet.py` (generated images).

## 4. Playbook: ChatGPT turnaround sheet (worked on 2026-10-18)
A turnaround sheet shows one creature from the front, the side and the back in the same pose, which is the best input for a 3D generator. Steps:
1. `tabs_context_mcp` with `createIfEmpty`, new tab, `navigate` to `https://chatgpt.com` (the owner is already signed in; if a login page shows, stop).
2. `find` the attach button, then `file_upload` the owner draft (a file inside the project, for example `docs/reference/cockatoo-owner-draft.webp`).
3. Type the prompt and click the send arrow. Template (the exact prompt used for the cockatoo is in [reference/cockatoo-turnaround-chatgpt-v1.txt](reference/cockatoo-turnaround-chatgpt-v1.txt)):
   > Make a character turnaround reference sheet of the <creature> dinosaur creature in the attached image, matching its design exactly: <list the 6 to 8 key features from the draft: colours, crest, beak, eyes, arms, legs, tail>. Show 3 views side by side on a plain light-grey background: front view, side view facing right, back view. Same proportions and size in every view, full body, neutral standing pose, soft even lighting, cute stylised 3D game character, no text, no props, no ground shadow.
4. Wait about 40 seconds. Click the finished picture to open it, click the download arrow, then "Download image".
5. Move the download into `docs/reference/<name>-turnaround-chatgpt-v1.png` (about 1.6 MB was fine), save the prompt next to it as `<name>-turnaround-chatgpt-v1.txt` (source, date, input file, prompt, result), and add a line to [77](77-asset-registry.md) marked "REFERENCE image only, not final art".
6. Add the sheet to the creature's `sources.json` with `kind: "ai"`, then run Tool A.

### What we learned (put this checklist in the evidence README of every creature)
- [ ] Input draft path and who made it (owner draft, owner photo, or earlier AI image).
- [ ] Prompt text file saved next to the result, with date, model (ChatGPT, owner account, Instant model on 2026-10-18) and the number of tries.
- [ ] Result size and path; it is REFERENCE ONLY, not final art, not used at runtime (AGENTS.md art rule).
- [ ] Differences from the draft written as a list (what the sheet got wrong or invented). An AI sheet can invent details: the owner draft always wins.
- [ ] The three views really have the same proportions (hold the sheet next to itself: head size, leg length, tail length).
- [ ] What the 3D generator cannot copy, written BEFORE generating (fine layered feathers, separate crest blades, claws and scaly feet come out simplified, [evidence/2026-10-18-cockatoo](evidence/2026-10-18-cockatoo/README.md)), so nobody fakes detail with floating geometry.
- [ ] The generator prompts were rewritten from the sheet and the draft, not from memory.
- [ ] No password, payment or login was entered; downloads stayed inside the project and under a handful.
- [ ] Registry line added to docs/77.

---

# Part B: playtest report

## 5. What the game records today (read from source, 2026-10-18)
| What | Where | In the log? | Used by the report |
| --- | --- | --- | --- |
| Each run ending: length, end reason (Death, ManualExit, Disconnect, Predation, Other), eggs, nests, crystals, real food, eggs from food, seconds in weather | `src/server/TelemetryService.luau`, `src/shared/RunTelemetry.luau`, one hook in `Bootstrap.server.luau`; [122](122-session-telemetry.md) | Yes: `[BD-TELEMETRY] {json}` | Yes |
| Each visit ending (player leaves): total seconds, runs finished, hub seconds, run seconds | same | Yes | Yes (funnel, runs per visit, hub share) |
| "Tell us!" feedback: fun, difficulty, looks (1 to 3), run count, hub or run, species, filtered text | `src/server/FeedbackService.luau`; [128](128-playtest-feedback.md) | Yes: `[BD-FEEDBACK] {json}` | Yes |
| Phone numbers (fps, memory, ping, step label) | `QaService.luau`, [127](127-phone-qa-kit.md) | Yes: `[BD-QA] {json}`, owner-only, tools/qa/phone_report.py | No (not a friends number) |
| Movement set-backs | `MovementGuard.luau`: player attribute `MovementRejectCount` only | **No** | Gap BD-649 |
| "rate_limited" answers | many services return the word or set a `Last...Status` attribute | **No counter** | Gap BD-650 |
| Script errors, crashes | no listener in the game | **No** | Gap BD-651 |
| Shop opened or bought, eggs hatched, fusions | nothing | **No** | Gap BD-652 |
| First food, first egg, first hatch, tutorial steps; time stamps; server id | nothing (events carry no time) | **No** | Gap BD-653 |

Both flags are off in the default build and on in the playtest profile (`RunTelemetryEnabled`, `PlaytestFeedbackEnabled`, `tools/release_profiles.py`). Privacy by design: no UserId, no name, no session id in any line, so **the game cannot say how many different people played**. Put the number of testers in a `meta` line by hand.

## 6. What a person can export
- **Server log** (best): while the test server is running, the place owner opens the in-game Developer Console (F9), tab "Server Logs", and copies the lines (or in Studio, copies the Output window). Only the lines starting `[BD-TELEMETRY]` and `[BD-FEEDBACK]` matter; the tool ignores everything else. **Copy before the server closes: the log is gone afterwards.** A visit is logged only when the player LEAVES, so tell testers to leave through the normal exit before you copy.
- **Creator Hub dashboards** (Analytics, Performance): the game also sends each event to `AnalyticsService:LogCustomEvent` (inside a `pcall`), and Roblox shows crash and error numbers there. If a dashboard gives a CSV, copy the few numbers you want into a counts file (below). Not verified in this task: no real dashboard was opened.
- **The in-game form** ("Tell us!", bottom-left): its lines are in the server log as above.

## 7. Input format (what `playtest_report.py` reads)
Any mix of files in one command; one line per event. A line can be a raw log line (with the `[BD-...]` tag) or plain JSON. Other log noise is ignored; a line that looks like data but is broken is counted and mentioned at the end of the report.

| `event` | Fields | Source |
| --- | --- | --- |
| `run_end` | `duration_s`, `reason`, `eggs`, `nests`, `crystals`, `food`, `food_raw`, `eggs_food`, `weather_s` | the game |
| `session_end` | `total_s`, `runs`, `hub_s`, `run_s` | the game |
| `feedback` | `fun`, `level`, `looks`, `runs`, `location`, `species`, `text` | the game |
| `count` | `name`, `value`, optional `note`; names: `movement_rejects`, `rate_limited`, `script_errors`, `crashes`, `shop_opens`, `shop_purchases`, `hatches` | by hand (the game cannot count these yet) |
| `funnel` | `step`, `players` (steps are added after the built-in ones, in the order written) | by hand |
| `meta` | any of `build`, `date`, `testers` | by hand |

A `.csv` file with the header `name,value,note` is read as `count` lines. Sample files: [tests/fixtures/playtest_sample.jsonl](../tests/fixtures/playtest_sample.jsonl) (a log with noise and one broken line) and [tests/fixtures/playtest_counts.csv](../tests/fixtures/playtest_counts.csv).

```
python tools/playtest_report.py server.log counts.csv --out report.md      # prints and writes the report
python tools/playtest_report.py server.log --json                          # the same numbers for other tools
```
It reuses `tools/telemetry_report.py` and `tools/feedback_report.py`, so the egg numbers are the same as before; it adds the lights, the drop-off, the plain-word problems and the gap list. Tests: `tests/test_playtest_report.py`.

## 8. Which egg number is current
**CURRENT BUILD:** `Config.FoodCatchRate = 12/500` ([119](119-catch-rate-15-per-run.md), owner 2026-10-16): 500 food gives 12 eggs, and a normal 5-minute run gives about **15** eggs. **HISTORICAL:** 40/500 (docs/59, 2026-10-13), 4/500 (docs/89), 15/150. AGENTS.md in the tree already says 12/500; only the copy that was injected into some sessions may still show 40/500, so read the file, not the memory ([155](155-fusion-ladder-source-vs-docs-audit.md) C-47). The report reads the rate from `src/shared/Config.luau` (else uses 12/500) and prints which one it used. The target of 15 eggs per 5 minutes is the one in `telemetry_report.py`.

## 9. The traffic lights (PROVISIONAL, owner may change any number)
Kept in one table, `LIMITS`, at the top of `tools/playtest_report.py`. Plain words: GREEN fine, YELLOW look at it, RED fix before the next test, GREY not recorded or too few answers.

| Check | GREEN | YELLOW | RED |
| --- | --- | --- | --- |
| Eggs in a 5-minute run (goal 15) | 12 to 18.75 | 7.5 to 12, 18.75 to 30 | outside |
| Eggs for 500 food (setting 12) | 0.75x to 1.5x the setting | 0.5x to 2.5x | outside |
| Middle run length | 3 to 8 min | 1.5 to 3, 8 to 12 min | outside |
| Runs per visit | 2 or more | 1 to 2 | under 1 |
| Visits with no finished run | up to 20% | up to 40% | more |
| Runs ended by leaving the game | up to 15% | up to 30% | more |
| Time in the cave | up to 50% | up to 70% | more |
| Anti-cheat set-backs per visit | up to 0.5 | up to 2 | more |
| "Too fast" answers per visit | up to 1 | up to 5 | more |
| Script errors | 0 | 1 to 3 | more; any crash is RED |
| Fun and looks (1 to 3) | 2.4 or more | 1.8 to 2.4 | under 1.8 |
| Difficulty (2 is just right) | 1.7 to 2.3 | 1.4 to 2.6 | outside |
| Shop opened, hatching | at least once | never (is it easy to find?) | none |

Fewer than 3 feedback answers is GREY. Fewer than 4 visits prints "treat every light as a hint, not a result". The drop-off funnel is: came in, finished 1 run, 2 runs, 3 runs (all from the visit lines), then any `funnel` lines written by hand; the report names the biggest loss. Owner target for pace comes from [114](114-handbook.md) s1.1 (runs of about 5 minutes, several runs per visit, [122](122-session-telemetry.md)).

## 10. Gaps (a kanban row each; `src/` was not changed)
- **BD-649** movement set-backs only in a player attribute.
- **BD-650** "rate_limited" is not counted anywhere.
- **BD-651** no script-error listener; crashes only on the Creator Hub dashboard.
- **BD-652** no shop, hatch or fusion counters.
- **BD-653** no funnel steps before the first run, no time stamp, no server id, and the server log vanishes when the server closes.

Until they exist, fill the numbers by hand with `count` lines (section 7); the report marks every missing number GREY with its row id.

## 11. Not covered
No real playtest was run; no real Creator Hub export was opened; Studio and phone were not used. Only the fixture lines and the existing budgie pictures were used for the examples. The lights are a first guess and need one real playtest to settle.
