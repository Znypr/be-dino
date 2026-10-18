# 168 Work log and retrospectives

Written 2026-10-18 (BD-654). Owner request, 2026-10-18: check not only the quality of the agents' work and the lead's work, but also **how long it took, what the quality was and what steps were involved**; then break down what went wrong or could be better, so we work faster and better and **do not spend hours on the same mistake twice**.

This page is the whole system. It is small on purpose.

- The log: [`docs/retro/work-log.jsonl`](retro/work-log.jsonl), one line per task, append only.
- The tool: `python tools/retro_log.py add | list | summary | render`.
- The rules that came out of it: [160 Agent brief](160-agent-brief.md), section 9 (learned rules).

## 1. What to record after every agent task

The lead records it when the agent reports back (the numbers are in the completion note). Also record **lead mistakes** (use `--agent-kind lead`): a lead mistake that cost time is worth as much as an agent's.

| Field | What goes in it |
| --- | --- |
| task, date, pr | what it was, when, the PR number |
| duration_min, tool_calls, tokens_k | from the completion note (tokens in thousands). Leave empty if not known |
| quality_verdict | `good` (checked, nothing to fix), `ok` (works, small things fixed or unrated), `rework` (had to be done again) |
| fact_check | one line: what you checked the work against (handbook, code, a measured number) and what you found |
| steps | the main steps, 2 to 5 short items |
| problems | tags from the list below, plus a few words: `conflict: kanban row 612` |
| lesson | one plain sentence: what to do next time |
| action, action_ref | what we changed so it cannot happen again: `tool`, `brief` (a rule in docs/160), `memory` (a memory note) or `none`; and where |
| rework_cycles | how many times it had to be redone (merge, conflict, red CI, second run) |
| lost_min | optional: your honest estimate of the minutes lost to the problems. Say it is an estimate |

**Problem tags** (small list on purpose; use `other: ...` only when nothing fits):
`conflict`, `stacked-pr`, `doc-number-collision`, `stale-context`, `studio-window`, `tool-missing`, `wrong-recipient`, `ci-red`, `scope-creep`, `unverified-claim`, `other`.

Put the **main cause first** in `problems`: the lost minutes are counted under the first tag.

```
python tools/retro_log.py add --task "Fair write budget BD-614" --pr 448 --duration-min 6.4 \
  --tool-calls 28 --tokens-k 103 --verdict good --fact-check "0% honest players limited (measured)" \
  --step "build budget" --step "measure honest rate"
python tools/retro_log.py add --agent-kind lead --task "..." --verdict rework --rework-cycles 1 \
  --problem "unverified-claim: said X was missing without a probe" --lesson "Probe first" \
  --action brief --action-ref "docs/160 section 9" --lost-min 15
python tools/retro_log.py render      # then commit docs/retro/work-log.jsonl and this page
```

## 2. When to stop and fix the cause

- **Same problem twice = stop.** The second time a tag shows up (same cause, new task), do not just fix the case. Spend the time on the cause first: a tool, a rule in the brief or a memory note. Record it in `action` and `action_ref`.
- **Long task, no result:** if a task passes about twice its usual time (the median in the summary) with no output, stop it, write down what blocked it, and park it. Never wait on a denied window or tool call.
- **A fix is a real fix only if something changed in a file** (tool, brief, memory). "We will be careful" is `action none` and does not count.
- Keep the fixes small. A one-line rule beats a long document nobody reads.

## 3. Weekly routine (10 minutes, every Monday, or after a big PR wave)

1. `python tools/retro_log.py summary`.
2. Read the **top 3 time sinks** and the line "problems with no fix yet". Pick the biggest one with no fix and make the fix (tool, brief rule, memory note).
3. Check the redo share for agent tasks. If it is above 30%, ask why: stacked PRs, a moving main, unclear task text?
4. Look at the longest tasks. Could they have been split in two, run in parallel, or started from a better brief?
5. Add any new rule to [160](160-agent-brief.md) section 9 with a link back to the evidence here. Remove rules that no longer happen.
6. `python tools/retro_log.py render`, commit.

What the numbers can and cannot tell you: durations and token counts come from the completion notes and are good. `lost_min` is a human estimate. The verdict is the lead's fact-check against the handbook and code; it is not a measurement.

## 4. First read of the log (2026-10-17/18, 23 entries)

Agent tasks: 18, about 421 minutes in total, median 18.5 minutes, 39% needed at least one redo (merge round, conflict, red check, second run). Lead entries: 5, all of them redo.

**Top time sinks, and where each one stands:**

| # | Time sink | About | Fix | Status |
| --- | --- | --- | --- | --- |
| 1 | Studio windows minimised or displays asleep; the owner's Place1 "lost unsaved work" scare | hours (rough guess 120 min) | memory rule "owner Place1 window"; virtual display plan in docs/158 (PR 457) | Rule in place. Virtual display not built yet |
| 2 | Kanban merge conflicts: about 12 by hand by the lead (about 3 min each) plus about 10 agent rounds | about 57 min | `tools/merge_main_into_pr.py` | Being built, not merged. Per-row rule is in docs/160 |
| 3 | Long tasks while main moves (remote audit: 3 merge rounds; rehearsal; WeatherVisuals) | about 9 min (the audit alone) | brief rule: merge main early and again before the PR | Rule added in this PR |
| 4 | Stacked PRs and renamed kanban rows (BD-625 conflicted after the squash and `verify_kanban_merge` rejected a renamed title) | about 6 min | brief rules: base on `origin/main`, keep row titles, append outcomes | Rules added in this PR |
| 5 | Stale or unchecked claims: old AGENTS.md copy (15/4/2 instead of 6/3/2), "browser unavailable" without a probe, movement window shipped ON with unmeasured margins | small in minutes, big in risk | brief rules: read AGENTS.md from the repo, probe tools first, measure before ON; `dev_env_check` planned | Rules added in this PR. `dev_env_check` not built yet |

Also fixed already: doc-number collisions between parallel agents (`tools/next_bd_id.py --doc`), messages sent to the wrong agent (message by exact id), `verify_kanban_merge` run before committing (it reads committed state).

**Things that went well and should stay:** short audit and research tasks (4 to 12 minutes, one clear question) were all rated good; the fair-write-budget task measured its claim (0% of honest players limited) instead of asserting it.

## 5. The log as a table

Rewritten by `python tools/retro_log.py render`; do not edit by hand. A test fails if the table is stale.

<!-- retro-table:start -->
| Date | Task | Who | PR | Min | Calls | Tokens (k) | Verdict | Redo | Problems | Lesson / action |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-17 | Remote audit BD-608 | worker | #439 | 70.7 | 290 | 771 | good | 3 | conflict: main moved (ProfileRepository split landed mid-work) | Long audits meet a moving main: merge main early and again before the PR, not only at the end. (brief: docs/160 section 3 (git merge origin/main first)) |
| 2026-10-17 | Switch-on rehearsal BD-624 | worker | #441 | 78.8 | 216 | 533 | good | 1 | conflict: PR conflicted with main afterwards | - |
| 2026-10-17 | WeatherVisuals split BD-627 | worker | #442 | 34.9 | 94 | 235 | ok | 2 | conflict: kanban conflicts twice, other: another session pushed merge commits to the agent's branch | Only one session writes to a branch; kanban conflicts are the most common redo. (tool: tools/merge_main_into_pr.py (being built, not in repo yet)) |
| 2026-10-17 | Hygiene bundle BD-618/615 | worker | #445 | 33.5 | 149 | 302 | good | - | - | - |
| 2026-10-17 | Equip-next-run and objective rewards BD-613/616 | worker | #450 | 28.6 | 120 | 237 | ok | 2 | wrong-recipient: lead sent it two messages meant for another agent, conflict: conflicts with main twice | Message agents by their exact id, never by guessing which one is running. (brief: docs/160 section 9 (learned rules)) |
| 2026-10-17 | Fair write budget BD-614 | worker | #448 | 6.4 | 28 | 103 | good | - | - | - |
| 2026-10-17 | Movement window BD-611 | worker | #449 | 13.4 | 69 | 202 | ok | 1 | conflict: a conflict marker was committed once and fixed, unverified-claim: shipped default ON with unmeasured margins | Never commit with a marker in the tree; a setting that weakens security needs measured margins before it ships ON. (brief: docs/160 section 9 (learned rules)) |
| 2026-10-17 | Objective batching BD-625 | worker | #444 | 18.5 | 45 | 139 | ok | 2 | stacked-pr: stacked on unmerged PR 441, conflicted after the squash, conflict: kanban row conflict, ci-red: renamed an existing kanban row title; verify_kanban_merge rejected it | Do not stack on an unmerged PR; keep existing kanban row titles and append the outcome. (brief: docs/160 section 9 (learned rules)) |
| 2026-10-17 | Fusion audit | worker | #446 | 4.2 | 43 | 157 | good | - | stale-context: the injected copy of AGENTS.md was days old | Read AGENTS.md from the repo, not from the session text. (brief: docs/160 section 1 (read order)) |
| 2026-10-17 | Fusion docs fix | worker | #447 | 2.3 | 9 | 80 | ok | - | stacked-pr: based on an unmerged branch | Base on origin/main. (brief: docs/160 section 9 (learned rules)) |
| 2026-10-17 | Readiness doc | worker | #451 | 2.2 | 20 | 155 | ok | - | - | - |
| 2026-10-18 | Integration sweep | worker | #453 | 43.0 | 131 | 275 | good | - | other: an allowlist edit was refused by the auto classifier | Edits that widen an allowlist need the owner: write them up instead of retrying. |
| 2026-10-18 | Rehearsal flag-on coverage BD-626 | worker | #452 | 39.7 | 196 | 363 | ok | - | - | - |
| 2026-10-18 | Objectives isolation and predation tick BD-631/632 | worker | #454 | 25.2 | 78 | 257 | good | - | - | - |
| 2026-10-18 | Audio report tool | worker | #458 | 11.7 | 54 | 186 | good | - | - | - |
| 2026-10-18 | Virtual display and emulator research | worker | #457 | 5.2 | 43 | 145 | good | - | - | - |
| 2026-10-18 | Agent brief | worker | #456 | 2.3 | 25 | 114 | good | - | - | - |
| 2026-10-18 | Cockatoo special bird BD-621 (first run) | worker | - | - | - | - | rework | 1 | studio-window: first run blocked by a denied window-placement call | Park render-dependent work instead of waiting on a denied window call. (brief: docs/160 section 6 (tools)) |
| 2026-10-18 | Lead: manual kanban conflict fixes (about 12) | lead | - | 36 | - | - | rework | 12 | conflict: about 12 manual docs/07-kanban.md conflicts, about 3 min each | The same conflict twelve times is a tool job. (tool: tools/merge_main_into_pr.py (being built, not in repo yet)) |
| 2026-10-18 | Lead: Studio windows minimised, displays asleep, Place1 'lost work' scare | lead | - | - | - | - | rework | 1 | studio-window: windows minimised or displays asleep; Place1 unsaved-work scare | Work in the owner's Studio window is unsaved until he saves; plan a virtual display. (memory: owner-place1-window rule; virtual display plan in docs/158 (PR 457)) |
| 2026-10-18 | Lead: said a browser was unavailable before probing it | lead | - | - | - | - | rework | 1 | unverified-claim: browser called unavailable without a probe, tool-missing: tool probe not run at session start | Probe a tool before saying it is missing. (tool: dev_env_check (planned, not in repo yet); docs/160 section 9) |
| 2026-10-18 | Lead: ran verify_kanban_merge before committing | lead | - | - | - | - | rework | 1 | other: verifier run before committing | Commit first, then run verify_kanban_merge. (brief: docs/160 section 3 (numbers and the kanban)) |
| 2026-10-18 | Lead: doc-number collisions between parallel agents | lead | - | - | - | - | rework | 1 | doc-number-collision: two agents took the same docs number | Get numbers from the tool, never by eye. (tool: tools/next_bd_id.py --doc) |
| 2026-10-18 | merge-train tool | lead | - | - | - | - | good | - | ci-red: serial merges restart CI for every waiting PR | serial merges restart CI N times; batch with one CI run (tool: tools/merge_train.py) |
| 2026-10-18 | Telemetry gaps (BD-649..653) | worker | #474 | 45.7 | 166 | 291.0 | good | - | conflict: BD-617 removed the handler 474 edited | PRs touching the same function conflict even without kanban; merge train caught it (tool: tools/merge_train.py) |
| 2026-10-18 | Remove old fusion screen (BD-617) | worker | #473 | 30.9 | 83 | 215.0 | ok | - | stacked-pr: based on 466, merged into its branch | stack only with the lead's ok (brief: docs/160) |
| 2026-10-18 | Owner answers: T-Rex size, phone weather, V3 Compy | worker | #475 | 26.4 | 86 | 273.0 | good | - | stacked-pr: stacked under 471 | closing the stacked PR needed by hand |
| 2026-10-18 | Studio acceptance round 1 (BD-663) | worker | #472 | 29.6 | 241 | 325.0 | good | 1 | studio-window: could not open a place; lead launched Studio with the file as argument, tool-missing: viewport 296x304 | launch Studio with the .rbxlx as an argument; owner maximises the window (brief: docs/160) |
| 2026-10-18 | Cockatoo pipeline run (BD-659/621) | worker | #470 | 12.9 | 77 | 214.0 | good | - | - | rig and animation do not survive the API upload; use parts + joints + Luau animation (tool: tools/blender_export_roblox.py) |
| 2026-10-18 | Cockatoo generation rounds (BD-621) | worker | #477 | 21.5 | 132 | 195.0 | ok | - | - | generated meshes plateau around 6/10 for legs: budget the generations (11) and decide early |
| 2026-10-18 | Decisions dashboard (BD-661) | worker | #469 | 6.4 | 50 | 228.0 | good | - | - | pictures plus one-click answers beat chat questions |
| 2026-10-18 | Merge train tool (BD-993) | worker | #478 | 9.0 | 28 | 128.0 | good | - | - |  (tool: tools/merge_train.py) |
| 2026-10-18 | Calmer sounds (BD-166) | worker | #479 | 8.0 | 43 | 160.0 | good | - | - | audio tool lets the lead judge loudness/harshness without ears (tool: tools/audio_report.py) |
| 2026-10-18 | Kid-friendly text (BD-998) | worker | #480 | 28.6 | 120 | 275.0 | ok | 1 | conflict: Bootstrap edits vs the removal in the train | hold auto-merge on PRs that touch the same big file as a train |
| 2026-10-18 | Lead: misread GitHub UTC times as 90 min without merges | lead | - | - | - | - | ok | - | unverified-claim: time zones | convert GitHub times (UTC) before saying how long |
| 2026-10-18 | Lead: committed leftover conflict markers | lead | - | 5.0 | - | - | rework | 1 | unverified-claim: assumed the regex worked | check for markers before every commit; CI check being built (tool: tools/verify_no_conflict_markers.py) |
| 2026-10-18 | Lead: both-sides-edited kanban row lost main notes | lead | - | 15.0 | - | - | rework | 1 | conflict: BD-621 row edited on main and in the train | merge helpers must merge both texts, not keep one (tool: tools/kanban_merge_lib.py) |
| 2026-10-18 | Lead: committed leftover conflict markers (CRLF regex); kanban rows edited on both sides lost main's notes | lead | - | - | - | - | rework | 1 | conflict: conflict markers committed in docs; both-sides-edited kanban rows dropped main's notes | a check must treat CRLF like LF, and a both-edited row must keep both sides (tool: tools/verify_no_conflict_markers.py) |
| 2026-10-18 | Faster fights BD-1025 | worker | #496 | 20.0 | 40 | - | good | - | other: first worktree created as a sibling folder (docs/170 says .claude/worktrees); fetch hit a stale ref lock, doc-number-collision: reserved BD-1026 and doc 184 by mistake, unused | Create the worktree under .claude/worktrees; call next_bd_id once per kind and use the result |
| 2026-10-18 | Faster fights part 2: size-difference curve BD-1025 | worker | #496 | 35.0 | 30 | - | ok | 1 | ci-red: forgot retro_log render so docs/168 table was stale, conflict: kanban and 115 append conflicts | Run retro_log.py render right after retro_log.py add, before the first push |
| 2026-10-18 | Class icons + clearer Eggs card (BD-1022/1023) | worker | #497 | 40.0 | 75 | - | ok | - | other: kanban append conflict on merge, fixed by taking main and re-appending my rows | Image icons via Open Cloud are Decals; docs/120 wants Image: needs a Studio check. Appending kanban rows at the file end conflicts with every parallel PR; insert near the end of an existing section instead or use merge_main_into_pr.py. |
| 2026-10-18 | BD-1030 fill BD-004 slot for newbuild, off-sale field in verify_release_ids | worker | #499 | 45.0 | - | - | good | 1 | conflict: kanban and docs/115 append conflicts at file end | dry-run redirect path was relative and wrote outside the repo; use the scratchpad absolute path |
| 2026-10-18 | BD-1043 playtest build stamp + freshness check (PR 502) | worker | #502 | 25.0 | 45 | - | good | - | other: BD-1043 row not on main yet (PR 498 open), status change deferred | Reuse the existing on-screen label instead of editing the byte-limited Bootstrap file. |
| 2026-10-18 | BD-1032 new species much rarer + species timing simulation (PR 505) | worker | #505 | 80.0 | 90 | - | good | 2 | other: hard-coded old odds in verify_eggs, verify_secret_species golden hash and HatchTimeline.pct (would show 0%) | Grep for the old numbers and for display formats before changing rarity; tiny percents need more decimals. |
| 2026-10-18 | BD-1052 team catalogue generated from the code (docs/catalog) | worker | - | 55.0 | 85 | 330.0 | good | - | other: bash heredocs ate double backslashes in generated Python and Luau (three syntax errors) | Write code with backslashes through the file tools, never through a bash heredoc; and a generated catalogue goes stale whenever main changes data, so merge main and rebuild before the PR. |
| 2026-10-18 | BD-1034 pattern discovery part 1: ChatGPT tile sheets, seam checker, similarity tool, ruler tool | worker | - | 95.0 | 120 | - | ok | 2 | scope-creep: three owner messages mid-task added labelling tool, seam tool, cluster check, unverified-claim: first seam metric (average baseline) failed good stripe tiles; fixed after tests | A generator saying seamless is not proof: 30 of 32 tiles had seams; test the metric on synthetic good and bad tiles before trusting a table (tool: tools/tile_seam_check.py) |
| 2026-10-18 | BD-1033 pattern rarity tiers on the 8 existing patterns (helper, 1st of 3 PRs) | worker | #512 | 75.0 | 95 | 450.0 | good | 1 | other: first design put an extra key in the pattern list, which every loop then iterated (caught by verify_outcomes) | never add a hash key to an array table that others iterate; use a metatable or a separate table |
| 2026-10-18 | layer_stats tool, offline food dump, first food measurement BD-1049 | worker | #508 | 32.0 | 40 | 150.0 | good | - | other: Roblox Random and terrain raycasts cannot run offline, so positions are a faithful model not the real ones | A random-scatter reference on the same ground (not the theoretical 1.0) is needed for an honest spread verdict |
| 2026-10-18 | WorldLayer class, Python mirror, layer_stats --layer (BD-1047 first half) | worker | #509 | 22.0 | 30 | 120.0 | good | - | conflict: CI workflow list line next to the other PR's line | Both PRs add a line at the same spot of the CI list; append new verifiers at different places |
| 2026-10-18 | BD-1055 OPEN EGGS, BD-1054 check, BD-1057 skip rule | worker | - | 30.0 | 55 | - | good | - | conflict: kanban rows 1054-1057 were only on the unmerged PR #503, waited for its merge | rows from an open PR: do code first, edit rows after it merges |
| 2026-10-18 | BD-1036 colour ladder retune: equal split, rarer-of-two, colour timing tool (helper, 2nd of 3 PRs) | worker | #513 | 45.0 | 50 | 250.0 | good | 1 | ci-red: verify_eggs hard-coded Black weight 512 (caught by the full local run) | run the whole verify suite before pushing, one-number asserts hide in old verifiers |
| 2026-10-18 | BD-1038 pattern and colour boost behind GeneBoostEnabled (helper, 3rd of 3 PRs) | worker | #516 | 50.0 | 55 | 250.0 | good | - | conflict: merge of main into docs/115 and kanban (solved with tools/merge_main_into_pr.py) | open the PR first, then let the merge helper do main merges |
| 2026-10-18 | BD-1047 designed food map (generator, FoodLayer, FoodService flag, verify, evidence) | worker | #518 | 95.0 | 110 | 400.0 | good | 1 | other: bash heredocs swallowed backslashes twice (a Luau string and a python marker); kid-text lint flagged a data key called Text | use the file-writing tools for code with backslashes; name data keys so the kid-text lint does not read them as player text |
| 2026-10-18 | BD-1039 Pattern Index and Colour Index (tabs, cards, ribbons, dot, flag, tests) | worker | - | 150.0 | 140 | 600.0 | good | 1 | conflict: Bootstrap alias broke verify_hud and verify_phone_scale (no new top-level locals for ModalCompact) | Bootstrap is guarded by string-level tests: read the verifiers before shortening code; reverted the alias and trimmed a comment instead |
| 2026-10-18 | BD-1061 kanban rows as files: one file per task, converter, PR replay, merge-tool changes, cutover plan | worker | #515 | 150.0 | 190 | - | good | - | conflict: main moved three times during the work (docs/07 rows); solved by the new --resync command, which is now the cutover step, other: heredoc python lost backslash escapes in code twice (syntax errors); wrote code with the Write/Edit tools instead | when a change touches every reader of a shared file, keep both layouts readable (old tests stay valid) and prove the move with a round trip plus real PRs in a throwaway repo (tool: tools/kanban_migrate.py) |
| 2026-10-18 | Studio QA round 4 (BD-1027, BD-1042, BD-1045): close paths, walkthrough, hatch audit | worker | - | 150.0 | 330 | - | good | - | studio-window: window opened on a real screen, later landed on the virtual monitor and shrank to 848x481 mid-session, every click map had to be re-read, tool-missing: Escape key does not reach the game and VirtualInputManager is blocked, so Escape and regression_walk could not be tested | read button positions with a script (AbsolutePosition) after every window change; sample UI sizes with a waiting loop instead of guessing from pictures; admin F2 clicks start weather by accident |
| 2026-10-18 | BD-1047 food map v2: small clusters, pace model, merge of PR 519 flags | worker | #518 | 110.0 | 90 | 300.0 | ok | 1 | other: first version spread single foods and cut a seeker's food by 41 percent; heredoc backslashes again | model the pace effect before spreading foods out; measure with several layouts and starts because one walker is noisy |
| 2026-10-18 | BD-1066/1068/1074 round 4 fixes: class icon image ids, mutant dino floor, key toggle | worker | - | 190.0 | - | - | good | - | studio-window: window sizes and camera relock cost time, unverified-claim: black dino root cause not reproduced | execute_luau require() can give a second module instance, so cache stats from it are not the game's |
| 2026-10-18 | Hatch polish BD-1069..1073 (bucket colour, chip style, egg size, rainbow, card layout) | worker | #520 | 150.0 | 230 | - | good | 1 | studio-window: Studio window shrank to 500x465, test grant eggs had no genes | calibrate pixel constants from a measurement in the same window, not from an older QA picture (zoom 1.65 was 16 percent too big) |
| 2026-10-18 | BD-1077 one chunky tag style everywhere (inventory, conversion, CI check) | worker | - | 60.0 | 80 | - | good | - | - | Mocks in other verifiers stub required modules: adding a require to a client file needs the stub added in the same change. (tool: tools/verify_chip_style.py) |
| 2026-10-18 | BD-1041 starter goals + BD-1065 follow-ups (card detail, saved Index dot) | worker | #522 | 150.0 | 190 | - | good | 1 | other: the full local CI loop has a slow world verifier (22 s to 7 min); skipped world and cave ones | an accent-colour mutant is invisible when the all-on rehearsal logs accent colours, so aim a mutant at the pure rule, not only the end-to-end test |
| 2026-10-18 | Studio helper: Pattern/Colour Index check and smart test bot (BD-1063, BD-1048, BD-575, BD-1076) | worker | #523 | 100.0 | 200 | - | good | 1 | other: input tool clicked the rail button under the Index tab, took a while to understand, unverified-claim: no phone size window, no human run | Paste of the whole bot costs 10 KB per Studio session: install once per session; a status call that waits more than 60 s times out (tool: tools/studio/run_player_bot.py) |
| 2026-10-18 | BD-1067 small-window layouts (Eggs screen, hatch card, reveal), offline layout mock | worker | - | 75.0 | 110 | - | good | - | - | A picture that the mock cannot reproduce at the stated size means the screen was drawn at another size: test resizes, not only fixed sizes. (tool: tools/verify_small_window.py) |
| 2026-10-18 | BD-1081 respawn time by food kind (flag, tests, playtest on) and Studio bot re-measure | worker | #524 | 110.0 | 130 | 600.0 | good | 2 | other: bash tool turned double backslashes in heredocs into single ones, patch scripts failed twice, other: worktree HEAD became detached after commit, PR create said no commits | Respawn time stops a loop but not a first-visit sweep: measure repeat-eat points, not only the total (tool: tools/studio/player_bot.luau) |
| 2026-10-18 | BD-1088 slim Bootstrap.client.luau: shop screens to ShopScreens.luau, toast stack to Toasts.luau, ceilings lowered | worker | #528 | 150.0 | 110 | - | good | - | other: first code comments cited a guessed row number (BD-1020) before the real BD-1088 was reserved; fixed in PR 2 | reserve the BD id before writing comments that cite it |
| 2026-10-18 | Studio round 5: verify the merges of 2026-10-18 (hatch polish, goals, food, gene boost) | worker | - | 75.0 | 190 | - | ok | - | other: mouse tool wants GUI coordinates, first clicks hit the backdrop and I chased a false bug for about 15 min | mouse tool coordinates are AbsolutePosition space, not screenshot pixels (brief: docs/197-studio-round5-verification.md) |
<!-- retro-table:end -->

## 6. Open items

- Unrated tasks (PR 451, PR 452) were logged `ok` because the lead did not record a verdict at the time. Rate tasks when they report.
- `lost_min` for the Studio entry is a rough guess for "hours". Replace it when the owner or the lead has a real number.
- Not built, on purpose: charts, automatic parsing of completion notes, a dashboard. Add them only if the weekly routine shows the table is not enough.
