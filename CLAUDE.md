# Be Dino!
Roblox dinosaur growth, collection and hatching game: Luau game code built into a place file by Python tools (Python 3, Pillow, numpy; pinned Luau 0.741 runner for the Luau checks).

## Layout
- `src/` Luau game code (`client/`, `server/`, `shared/`, `loading/`); `src/shared/Config.luau` holds the build id and feature flags. `default.project.json` maps it into the place.
- `tools/` Python build, bind, verify (about 180 `verify_*.py`), kanban and art scripts; `tests/` Python unittest suite.
- `resources/` and `assets/` art, meshes, sounds; `build/` generated places (current build is ignored, older Build016-019 files are tracked history).
- `docs/` design docs: start with `AGENTS.md`, the handbook `docs/114-handbook.md` and the agent brief `docs/160-agent-brief.md`. Task board = one file per task in `docs/kanban/rows/` (entry page `docs/07-kanban.md`).
- `.github/workflows/build-generated-place.yml` is the single CI job; `.claude/skills/` holds project skills.

## Checks (what "checks pass" means)
- Fast, every change (each under about 10 s): `python tools/verify_no_conflict_markers.py`, `verify_doc_ids.py`, `verify_kanban_rows.py`, `verify_handbook.py`, `python tools/lint_kid_text.py --baseline`, `python tools/bind_artwork.py --check`.
- Luau changes: `python tools/verify_sources.py --compiler <luau-compile>` (about 10 s) plus the `verify_*.py --runner <luau>` checks your change touches (a few seconds each; full list in the CI file; runner paths in docs/160).
- Before a PR: `python tools/build.py` (about 5 s) then `python tools/verify_release.py --profile default` (about 2 s), and `python -m unittest discover -s tests` with `LUAU_RUNNER` set (742 tests, about 9 min: run it in the background with a timeout).
- Profile, save or flag work: also `verify_rollback.py`, `verify_profile_golden.py`, `verify_switch_on.py`, `verify_robux_line.py --selftest`, and `python tools/run_rehearsal.py --runner <luau> --compiler <luau-compile> --profile all-on-rehearsal` (about 90 s).
- After committing, for board changes: `python tools/verify_kanban_merge.py --base origin/main --head HEAD`. CI runs everything above on every PR.

## Rules
- `main` is protected: work on a branch in your own worktree, open a PR, merge only with the owner's OK. Never rebase or force-push; catch up with `git merge origin/main`. No `git stash` (shared between worktrees).
- Public repo: never commit secrets, sign-ins, personal data, local paths, third-party screenshots (`be-dino-reference-shots/`), `*.rbxl` places or generated builds (`build/BeDino-Build*.rbxlx`, manifests, Blender frame folders). The Roblox Open Cloud key comes only from the environment, never printed.
- Never touch the owner's `Place1.rbxl` or its Studio window. Never claim Studio or phone acceptance without evidence.
- BD ids and doc numbers only from `python tools/next_bd_id.py` (`--doc`); rows via `python tools/kanban.py`; never mark Done without evidence.
- Feature flags stay off by default; paid lines and debug/test switches are always off. Never rewrite stored player profiles (additive fields only).
- Final art is made in Blender or by the owner, never code-drawn or code-built; new assets get a line in `docs/77-asset-registry.md`.
