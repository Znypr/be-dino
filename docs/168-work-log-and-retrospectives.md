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
<!-- retro-table:end -->

## 6. Open items

- Unrated tasks (PR 451, PR 452) were logged `ok` because the lead did not record a verdict at the time. Rate tasks when they report.
- `lost_min` for the Studio entry is a rough guess for "hours". Replace it when the owner or the lead has a real number.
- Not built, on purpose: charts, automatic parsing of completion notes, a dashboard. Add them only if the weekly routine shows the table is not enough.
