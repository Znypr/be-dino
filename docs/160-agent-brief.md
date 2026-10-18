# 160 Agent brief: read this first (every helper agent)

Written 2026-10-18 (BD-634). Owner request: "use more project notes so make sure the helpers are aware of the handbook and such". This is the short version of the rules; it links to the long ones and does not replace them. If this page and a linked document disagree, the linked document wins and this page has a bug: say so in your report. Label every statement you make as **OWNER TARGET** (what the owner wants), **CURRENT BUILD** (what the source does today) or **HISTORICAL** (old spec or test record).

## 1. Read order (do this before you plan or edit)

1. [AGENTS.md](../AGENTS.md): game vision, reward loop, what is owner-approved. The text injected at session start can be days old: read the file in your worktree before quoting a number (docs/155 C-47).
2. [00 Documentation guide](00-documentation-guide.md): which document owns which question.
3. [114 Handbook](114-handbook.md): vision words, design language, palette, lighting, sound, quality bars, economy cheat sheet, section 13 PR checklist. Read only the sections your task touches, but always section 0 (the vibe words) and section 12 (process).
4. [115 Decisions log](115-decisions-log.md): dated owner decisions. The newest owner decision wins.
5. [116 Conflicts](116-handbook-conflicts.md): known mismatches and open owner questions.
6. Your row in [07-kanban.md](07-kanban.md), then the document it links.

```
git fetch origin && git merge origin/main      # before you read anything: the tree moves all day
grep -n "BD-NNN" docs/07-kanban.md             # your row
```

**Mismatches become questions.** If two sources disagree (doc vs code, doc vs doc, handbook vs the task text), do not pick silently. Write the mismatch down in your PR body and your report, add an OWNER QUESTION row to docs/116 if it is new, and continue with the safest reading (usually: the newest owner statement; the flag stays off).

## 2. Decisions: what you may decide, what you may not

- **Delegated (owner, 2026-10-16: "take full autonomy, do decisions for me").** Product and design choices, merges of green reviewed PRs, balance numbers marked PROVISIONAL: pick the option you would recommend and record it in [115](115-decisions-log.md) and the kanban owner log as **"LEAD decision (owner delegated 2026-10-16)"** with the options you did not pick and how to overturn it. The owner may overrule it later.
- **Needs the owner (stop and say so, never do it):** publishing to Roblox, anything with Robux or purchases, account settings, deleting data, and turning a release flag on for real players (`CombatEnabled`, `CaveHub`, low-poly dinos in the default profile and similar). The owner pre-approved uploading essential, high-certainty test assets (textures, meshes, images) to his account; nothing else.
- **Always off, in every profile:** paid lines (`CrystalPacksEnabled`, `PaidRandomItemsEnabled`, developer products) and every debug, test, demo, QA or admin switch.
- **Standing rule (owner 2026-10-18, docs/157):** test and playtest builds always get the newest built features ON (fusion, food models, dino models, vegetation, map and so on), in the `playtest` profile of `tools/release_profiles.py`, never in the default (Build 020 parity) profile. When a feature merges flag-off, add it to the playtest profile in the same or the next change unless you document why not (missing final asset, policy risk, no offline proof). Record each flip as a LEAD decision citing this rule and run the rehearsal ([152](152-switch-on-rehearsal.md)). If docs/157 is not in your tree yet, this paragraph is the rule.

## 3. Git and PR workflow

- Work in your own **worktree** (never the owner's checkout). Do not `cd` out of it.
- **Worktrees (docs/170): one folder only**, `<repo>/.claude/worktrees` (or the session scratchpad); never a sibling folder in Documents. **When your PR is merged, remove your own worktree:** `git -C C:/Users/znypr/Documents/be-dino worktree remove <your-worktree-path>` (no `--force`; if git refuses, something is unsaved). The lead runs `python tools/worktree_hygiene.py clean --go` weekly.
- `git fetch origin`, base on `origin/main`. **Never rebase, never force-push.** To catch up: `git merge origin/main`.
- Commit trailer: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. PR body footer: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- Paste the handbook checklist ([114](114-handbook.md) section 13, same text as `.github/pull_request_template.md`) into the PR body and tick it honestly.
- Auto-merge: `gh pr merge N --repo Znypr/be-dino --squash --auto` (CI must be green).
- Do not leave `git stash` entries (the stash is shared between worktrees); use a WIP commit.

**Numbers and the kanban** (one board only: [07-kanban.md](07-kanban.md); status lives only there; never mark Done without recorded evidence):

```
python tools/next_bd_id.py              # next free BD id (reserved 48 h); --reserve 3 for several; --peek just looks
python tools/next_bd_id.py --doc        # next free docs/NN number
python tools/board_summary.py           # counts (the kanban stores no counts; nobody commits them)
```

- **Conflict rule for docs/07-kanban.md, per row:** keep YOUR version of a row only if you changed it versus the merge base; otherwise take main's. Keep row titles unchanged and append outcomes to the end of the row. Never put back an older copy of a row. **A script does this for you:** `python tools/merge_main_into_pr.py <PR number or branch>` (dry run; `--push` to push, never forced), see [166](166-merge-helper.md).
- Run the board check **only after committing** (it reads commits, not your working copy): `python tools/verify_kanban_merge.py --base origin/main --head HEAD` (`--fix` rewrites stale rows from main).
- Also before pushing: `python tools/verify_doc_ids.py` (unique doc numbers and BD ids) and `python tools/verify_handbook.py` (UI floors, sound cap, palette, PR template).

**Verifiers.** CI (`.github/workflows/build-generated-place.yml`) runs about 150 `python tools/verify_*.py` checks plus the bind checks. Run the ones your change touches (`ls tools | grep verify_`), and always for profile, save or flag work: `verify_rollback.py`, `verify_profile_golden.py`, `verify_switch_on.py`, `verify_robux_line.py --selftest`. Luau checks need the pinned runner on this PC:

```
C:/Users/znypr/AppData/Local/Temp/bd057/luau/luau.exe          # --runner for verify_*.py
C:/Users/znypr/AppData/Local/Temp/bd057/luau/luau-compile.exe  # --compiler
C:/Users/znypr/AppData/Local/Temp/bd057/luau/luau-ast.exe      # --ast
python tools/verify_fusion.py --runner C:/Users/znypr/AppData/Local/Temp/bd057/luau/luau.exe
python tools/run_rehearsal.py --runner <luau.exe> --compiler <luau-compile.exe> --profile all-on-rehearsal   # about 90 s
```

## 4. Safety (players' saves come first)

- **Never rewrite stored profiles.** Only additive, lazily created fields. Every Build 020 profile must still load: `verify_rollback.py` and `verify_profile_golden.py` prove it ([111](111-rollback-drill.md), [150](150-profile-repository-split.md)).
- **Server-authoritative:** the client asks, the server decides and credits exactly once (idempotent). A remote validates every argument and takes ids, time and rewards from the server ([151](151-remote-audit-2026-10-17.md)).
- Do not flip a feature flag except under the standing rule in section 2. A new built-but-off flag must be added to the rehearsal list or excluded with a reason (`verify_switch_on.py` fails otherwise).
- Randomised or paid items follow [43](43-player-access-and-paid-random-policy.md): disclosed odds, `PolicyService`, paid flags off.
- QA agents never touch `Place1.rbxl`. No Studio or `src/` change belongs in a docs-only task.

## 5. Evidence rules

- **Every visual change is reported with an image path**, and a copy goes into `docs/evidence/review-2026-10-17/` (numbered files; find the next number with `ls docs/evidence/review-2026-10-17 | sort -n | tail`). Worktrees get deleted, the copy is what the owner can open.
- Honest ratings: say what you looked at and what you did not. **Never claim Studio or phone acceptance without evidence** (a screenshot from that device or a measured number). Offline tests prove logic only.
- **UI copy is for children** ([72](72-ui-copy-and-asset-standards.md)): short, obvious words, "5 min" not "5m 0s", "Speed +20%" not "1.2x", text at least 14 px, targets at least 44 px.
- **Art rule:** final art is made in Blender, or by the owner (also with ChatGPT). No Python- or code-drawn final art, generated meshes for 3D. Every new art asset gets a line in [77-asset-registry.md](77-asset-registry.md) when it is added. Check the vibe words in [114](114-handbook.md) section 0 on every picture.
- Flag-off features: one picture or number from the flag-ON state, plus the statement that the default build is unchanged.

## 6. Tools you may have

- **Claude in Chrome** (the owner's logged-in Chrome). Creator Hub: read-only checks only. ChatGPT image workflow that worked on 2026-10-18: `tabs_context_mcp` with `createIfEmpty`, `navigate` to chatgpt.com, `find` the attach button and `file_upload` the reference, type the prompt, click the send arrow, wait about 40 s, click the image, then the download arrow, then "Download image". Downloads are pre-approved only when saved inside the project, at a sensible size, and a handful of files. Never enter passwords or payment details; stop and ask on a login or CAPTCHA.
- **ffmpeg** at `C:/ffmpeg/bin`: cut frames from clips (section 7), audio spectrograms.
- **Blender MCP:** there is one Blender; one agent at a time.
- **Roblox Studio MCP:** one agent per Studio window. The owner's `Place1.rbxl` window is the owner's: never minimise, move, make topmost or close it, and work done in it is UNSAVED until the owner presses Ctrl+S. A denied window-placement call is never retried or worked around. The owner said to ignore window-placement problems and do other work.
- **No OS-level screenshots, never `SetForegroundWindow`.** Use the Studio MCP capture or the Browser pane.

## 7. Judging motion and sound without watching or listening

You cannot see a clip or hear a sound, so measure it, and say plainly what you could not judge.

- **Animation:** extract frames with ffmpeg and read them as a key-frame strip, for example `C:/ffmpeg/bin/ffmpeg.exe -i clip.mp4 -vf "fps=8,scale=240:-1,tile=8x2" strip.png`. Add numbers: joint angles and timings from the animation data, **loop continuity** (first pose equals last pose, speed does not jump at the seam), **foot-slide** (foot world speed near zero during stance, compare with body speed). See `tools/verify_dino_motion.py`, `tools/verify_motion_poses.py` and [74](74-dino-motion.md).
- **Sound:** waveform and spectrogram numbers (peak and RMS level, length, clipping, silence at the ends, loudest frequency band; `ffmpeg ... -lavfi showspectrumpic=s=800x300 spec.png`). Check against [124](124-sound-style-guide.md): soft, quiet, short, at most two cues. `tools/verify_audio.py` and `tools/verify_sound_lab.py` guard the cue table.
- **Report it as "measured, not heard / not watched".** The owner judges taste.

## 8. Reporting to the owner

Owner questions live in the Decisions dashboard (artifact https://claude.ai/artifact/2pgxwiaVoxvcxZkFp9KgSu, BD-661, source copy in `docs/evidence/2026-10-18-decision-dashboard/`); read the answers with `ArtifactData` (action list, collection `answers`, one document per question) and record each in [115](115-decisions-log.md). Add a new open question as a card there instead of asking in a message. The owner reads simple words. Keep it short. No jargon, no ids without a plain sentence beside them, no questions buried in the text (an owner decision is a separate, one-line ask). Say three things: **what exists**, **what is unverified** (Studio, phone, hearing), and **where the pictures are** (paths). Link the PR in three lines or fewer. If you found a mismatch, name the two sources.
