#!/usr/bin/env python3
"""One command to prepare a playtest release, so publishing takes minutes once the owner has answered BD-004 (docs/148).

    python tools/release_playtest.py --dry-run          # rehearsal: runs everything, shows what would block a real run
    python tools/release_playtest.py                    # the real preparation (still never publishes anything)

What it does, in order (docs/55 s1, s3, s6, s8; docs/111; docs/115 RB1, ST1, ST4, MR6; docs/145 s7 finding 6):

  1. GATES. A real run stops here, before building anything, when one of these fails:
       * the working tree is dirty (any tracked change or untracked file; `git status --porcelain` must be empty);
       * HEAD is not on origin/main, or CI did not finish green on this exact commit (gh; --skip-ci-check to override);
       * the BD-004 ids in tools/release_ids.json are empty, or do not match src/shared/Config.luau, or they belong to the
         legacy experience while Config.DeveloperProducts still lists Robux products (HARD STOP, tools/verify_release_ids.py);
       * any SHIPPED profile (every profile in tools/release_profiles.py that is not a scratch profile) has Workspace
         StreamingEnabled on (ST1: streaming stays OFF in every shipped profile), or turns PaidRandomItemsEnabled /
         CrystalPacksEnabled on.
  2. Builds the default and the playtest profile (`tools/build.py`), then `verify_release.py` for both against the built places.
  3. Runs the session-1 smoke, `verify_kanban_merge`, the playtest `verify_load --gate-playtest` and EVERY command of the CI job
     (read from .github/workflows/build-generated-place.yml, so this list cannot drift), then the unit tests.
  4. Writes the release manifest build/release/<tag>.release.json: git sha, profile, flag table (read from the BUILT places),
     asset id count, build hash (place_sha256), ids, verifier results, a ready-to-paste docs/55 s6 release-record row.
  5. Prints the annotated tag NAME proposal (playtest-m1-bNNN-rK) with the exact commands. It never creates or pushes a tag
     and never publishes: the owner publishes (docs/148).
  6. Prints the exact rollback target: the PREVIOUS playtest tag (RB1), never Build 020.

--dry-run runs every step even when a gate would refuse (so you see the whole picture), writes build/release/<tag>.dry-run.json
instead of the manifest, and exits 0 when no step FAILED (gate refusals are reported as "a real run would be refused").
Exit codes: 0 ok, 1 a step failed, 2 a real run refused by a gate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build as packager  # noqa: E402
import release_profiles  # noqa: E402
import verify_release  # noqa: E402
import verify_release_ids  # noqa: E402

WORKFLOW = ROOT / ".github/workflows/build-generated-place.yml"
RELEASE_DIR = ROOT / "build/release"
CONFIG = ROOT / packager.CONFIG_PATH
TAG_PATTERN = re.compile(r"^playtest-m1-b(\d+)-r(\d+)$")
PAID_FLAGS = ("PaidRandomItemsEnabled", "CrystalPacksEnabled")
CI_WORKFLOW_NAME = "build-generated-place.yml"
# Run explicitly by this script, or not meaningful locally: excluded when reading the CI command list.
CI_EXCLUDED_SCRIPTS = {"build.py", "verify_release.py", "verify_kanban_merge.py", "board_summary.py", "verify_session1_smoke.py"}
# The flags shown in the manifest, in the order of docs/145 s3.
FLAG_KEYS = [
    "ReleaseProfile", "ProfileDataStoreName", "PlaytestUniverseId", "PlaytestPlaceId",
    "PaidRandomItemsEnabled", "CrystalPacksEnabled",
    "CollectionTestGrantEnabled", "ChestTestGrantEnabled", "MutationTestSetupEnabled",
    "CaveHub", "LowPolyDinos", "ClassMovementEnabled", "WorldArtMode", "FoodArtMode", "WorldArtDensity",
    "IdentityPersistentEnabled", "IdentityFusionPreviewEnabled", "RunTelemetryEnabled", "PlaytestFeedbackEnabled",
    "CombatEnabled", "SpecialFoodsEnabled", "PerDinoCosmeticsEnabled", "FastTravelPerk", "GeneBoostEnabled", "FoodLayerEnabled", "PatternColourIndexEnabled", "FoodRespawnTiersEnabled", "ShopPromptBubbleEnabled", "RareFindBannerEnabled", "HudRailWordsEnabled",
    "HatchV2", "HatchV2Preview", "QaOverlayEnabled", "DemoDirectorEnabled", "FoodPickupAtMouth",
    "PredationAtMouth", "ObjectivesEnabled", "GiftClaimEnabled", "GiftingEnabled", "AdminGiftsEnabled",
    "SecretSpeciesEnabled", "DinoSkinsEnabled",  # docs/157: shown so the manifest records every decision
]


# ------------------------------------------------------------------------------------------------ small helpers
def git(*args: str, cwd: Path = ROOT) -> tuple[int, str]:
    try:
        p = subprocess.run(["git", "-C", str(cwd), "-c", "core.quotepath=off", *args], capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Gate:
    """One pre-build refusal check."""

    def __init__(self, name: str, ok: bool, detail: str = "", warning: bool = False):
        self.name, self.ok, self.detail, self.warning = name, ok, detail, warning

    def line(self) -> str:
        tag = "PASS " if self.ok else ("WARN " if self.warning else "BLOCK")
        return f"[{tag}] {self.name}" + (f": {self.detail}" if self.detail else "")

    @property
    def blocks(self) -> bool:
        return not self.ok and not self.warning


# ------------------------------------------------------------------------------------------------ gates
def working_tree_problems(cwd: Path = ROOT) -> list[str]:
    """Anything `git status --porcelain` lists (modified, staged, deleted or untracked) makes the tree dirty."""
    rc, out = git("status", "--porcelain", cwd=cwd)
    if rc != 0:
        return [f"git status failed: {out}"]
    lines = [line for line in out.splitlines() if line.strip()]
    if not lines:
        return []
    shown = lines[:8]
    more = f" (+{len(lines) - len(shown)} more)" if len(lines) > len(shown) else ""
    return [f"{len(lines)} path(s) differ from HEAD: " + "; ".join(shown) + more]


def shipped_profiles() -> list[str]:
    """Every profile that is not a scratch profile: default, playtest and anything added later."""
    return [name for name in release_profiles.PROFILES if not release_profiles.streaming_for(name).scratch]


def shipped_flag_problems(config_source: str) -> list[str]:
    """StreamingEnabled and the paid-random flags must be off in every shipped profile (ST1; docs/43)."""
    problems: list[str] = []
    for name in shipped_profiles():
        if release_profiles.streaming_for(name).enabled:
            problems.append(f"shipped profile {name!r} has StreamingEnabled ON (ST1/ST4: streaming stays OFF in every shipped profile; "
                            "a flip is its own row, BD-502, behind a phone run)")
        rewritten, _report = release_profiles.apply_profile(config_source, name)
        entries = release_profiles.config_entries(rewritten)
        for flag in PAID_FLAGS:
            found = entries.get(flag)
            if not found:
                problems.append(f"shipped profile {name!r}: {flag} is missing from Config (cannot prove the paid-random line)")
            elif found[-1][1] is not False:
                problems.append(f"shipped profile {name!r} has {flag} = {found[-1][1]!r} (paid-random/Robux flags must be false, docs/43)")
    return problems


def on_main_problem() -> str | None:
    rc, _ = git("rev-parse", "--verify", "--quiet", "origin/main^{commit}")
    if rc != 0:
        return "origin/main does not exist locally (run `git fetch origin main`)"
    rc, _ = git("merge-base", "--is-ancestor", "HEAD", "origin/main")
    if rc != 0:
        return "HEAD is not on origin/main: tag a green commit of main (docs/55 s6)"
    return None


def ci_state(sha: str) -> tuple[str, str]:
    """('success'|'failure'|'pending'|'none'|'unknown', detail) from the GitHub run of the workflow on this exact commit."""
    if not shutil.which("gh"):
        return "unknown", "gh not installed: CI was not checked"
    try:
        p = subprocess.run(["gh", "run", "list", "--workflow", CI_WORKFLOW_NAME, "--commit", sha, "--limit", "10",
                            "--json", "status,conclusion,databaseId"], cwd=ROOT, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        return "unknown", f"gh failed: {error}"
    if p.returncode != 0:
        return "unknown", "gh run list failed: " + p.stderr.decode("utf-8", "replace").strip()[:200]
    try:
        runs = json.loads(p.stdout.decode("utf-8", "replace") or "[]")
    except ValueError:
        return "unknown", "gh returned unreadable JSON"
    return classify_runs(runs)


def classify_runs(runs: list[dict]) -> tuple[str, str]:
    if not runs:
        return "none", f"no CI run of {CI_WORKFLOW_NAME} found for this commit (push it and wait for the workflow)"
    if any(r.get("conclusion") == "success" for r in runs):
        return "success", "CI green on this commit"
    if any(r.get("status") != "completed" for r in runs):
        return "pending", "CI is still running on this commit"
    return "failure", "latest CI run on this commit did not succeed: " + ", ".join(str(r.get("conclusion")) for r in runs[:3])


def evaluate_gates(*, skip_ci_check: bool = False, slot_path: Path = verify_release_ids.SLOT_PATH,
                   config_path: Path = CONFIG, cwd: Path = ROOT) -> list[Gate]:
    gates: list[Gate] = []
    dirty = working_tree_problems(cwd)
    gates.append(Gate("working tree is clean", not dirty, "; ".join(dirty)))
    problem = on_main_problem()
    gates.append(Gate("HEAD is on origin/main", problem is None, problem or ""))
    if skip_ci_check:
        gates.append(Gate("CI green on this commit", True, "skipped (--skip-ci-check)"))
    else:
        rc, sha = git("rev-parse", "HEAD", cwd=cwd)
        state, detail = ci_state(sha) if rc == 0 else ("unknown", "no HEAD commit")
        gates.append(Gate("CI green on this commit", state == "success", detail))
    errors, warnings, state = verify_release_ids.check(slot_path, config_path, require_filled=True)
    gates.append(Gate("BD-004 ids filled, match Config, not a legacy experience with products", not errors,
                      " | ".join(errors) if errors else f"slot {state}" + ("; " + "; ".join(warnings) if warnings else "")))
    config_source = config_path.read_text(encoding="utf-8")
    flag_problems = shipped_flag_problems(config_source)
    gates.append(Gate("no shipped profile has StreamingEnabled or paid-random flags on", not flag_problems, "; ".join(flag_problems)))
    return gates


# ------------------------------------------------------------------------------------------------ tag, rollback
def build_number() -> str:
    return packager.build_version(ROOT)


def playtest_tags(cwd: Path = ROOT) -> list[str]:
    """Existing playtest tags, oldest first (by tag creation date, then name)."""
    rc, out = git("tag", "--list", "playtest-m1-*", "--sort=creatordate", cwd=cwd)
    return [t for t in out.splitlines() if TAG_PATTERN.match(t)] if rc == 0 else []


def propose_tag(build: str, existing: list[str]) -> tuple[str, str | None]:
    """(proposed tag, previous playtest tag). K counts up per build; the previous tag is the newest one that exists (RB1)."""
    prefix = f"playtest-m1-b{build}-r"
    taken = [int(m.group(2)) for t in existing if (m := TAG_PATTERN.match(t)) and m.group(1) == build]
    proposal = f"{prefix}{max(taken, default=0) + 1}"
    previous = [t for t in existing if t != proposal]
    return proposal, (previous[-1] if previous else None)


def rollback_plan(previous: str | None, proposal: str, cwd: Path = ROOT) -> list[str]:
    """Plain lines naming the exact rollback target (docs/115 RB1, docs/111 s3, docs/55 s8)."""
    if previous is None:
        return [
            "Rollback target: NONE YET. No playtest tag exists, so this is the first playtest publish and there is no previous tag to go back to.",
            "  RB1: a rollback never goes to Build 020 once anyone has caught an Epic/Legendary or bought a newer potion (Build 020 fails closed: SchemaError).",
            f"  First publish: stop the damage by setting the experience to Private / shutting down all servers; do the BD-320 drill as docs/148 step 5 says",
            f"  (publish {proposal}, publish the same file again as a second Roblox version, restore the first in Version History, roll forward).",
            f"  From the next release on, the target is {proposal}.",
        ]
    rc, commit = git("rev-list", "-n", "1", previous, cwd=cwd)
    sha = commit if rc == 0 and commit else "(unknown: tag not found locally)"
    record = RELEASE_DIR / f"{previous}.release.json"
    place = ""
    if record.is_file():
        try:
            place = json.loads(record.read_text(encoding="utf-8")).get("playtest_place_sha256", "")
        except ValueError:
            place = ""
    return [
        f"Rollback target (RB1: the PREVIOUS playtest tag, never Build 020): {previous}  (commit {sha})",
        "  1. Creator Hub: set the experience to Private or shut down all servers.",
        f"  2. Creator Hub > Places > Version History > Restore the Roblox version recorded for {previous} in the docs/55 s6 release record,",
        f"     OR: git checkout {previous}; python tools/build.py --profile playtest; place_sha256 must equal "
        + (place if place else "the one in the release record") + "; publish it.",
        "  3. Shut down all servers, join with a test account, expect ProfileState = Loaded, add a rollback row to the release record (docs/111 s3).",
    ]


def tag_commands(tag: str, sha: str, message: str) -> list[str]:
    return [f'git tag -a {tag} -m "{message}" {sha}', f"git push origin {tag}   # owner only: this script never pushes a tag"]


# ------------------------------------------------------------------------------------------------ CI command list
def ci_commands(workflow_text: str, luau: str, luau_compile: str) -> list[list[str]]:
    """Every `python tools/...` command of the CI job, in order, with the CI luau paths replaced by the local runner."""
    commands: list[list[str]] = []
    seen: set[str] = set()
    for raw in workflow_text.splitlines():
        line = raw.strip()
        if line.startswith("run: "):
            line = line[5:].strip()
        if not line.startswith("python tools/") or "${{" in line:
            continue
        line = line.replace("/tmp/luau/luau-compile", luau_compile).replace("/tmp/luau/luau", luau)
        if line in seen:
            continue
        seen.add(line)
        parts = line.split()
        if Path(parts[1]).name in CI_EXCLUDED_SCRIPTS:
            continue
        commands.append([sys.executable] + parts[1:])
    return commands


def find_luau(explicit: str | None) -> tuple[str | None, str | None]:
    """(luau, luau-compile) paths, or (None, None)."""
    candidates = [explicit, os.environ.get("LUAU_RUNNER"), shutil.which("luau")]
    cache = Path.home() / ".cache/be-dino"
    if cache.is_dir():
        candidates += [str(p) for p in sorted(cache.glob("luau-*/luau*"), reverse=True) if p.stem == "luau"]
    luau = next((c for c in candidates if c and Path(c).is_file()), None)
    if luau is None:
        return None, None
    compiler = None
    for name in ("luau-compile", "luau-compile.exe"):
        if (Path(luau).parent / name).is_file():
            compiler = str(Path(luau).parent / name)
            break
    return luau, compiler or shutil.which("luau-compile") or luau


# ------------------------------------------------------------------------------------------------ steps
class Step:
    def __init__(self, name: str, ok: bool, seconds: float = 0.0, detail: str = ""):
        self.name, self.ok, self.seconds, self.detail = name, ok, seconds, detail

    def as_dict(self) -> dict:
        return {"step": self.name, "ok": self.ok, "seconds": round(self.seconds, 1), "detail": self.detail}


def run_command(name: str, command: list[str], env: dict, log_dir: Path, index: int, timeout: int = 1500) -> Step:
    started = time.monotonic()
    log = log_dir / f"{index:03d}-{re.sub(r'[^A-Za-z0-9_.-]+', '_', name)[:60]}.log"
    try:
        p = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=timeout)
        output = (p.stdout + b"\n" + p.stderr).decode("utf-8", "replace")
        ok = p.returncode == 0
    except subprocess.TimeoutExpired:
        output, ok = f"TIMEOUT after {timeout}s", False
    except OSError as error:
        output, ok = f"could not start: {error}", False
    log.write_text(output, encoding="utf-8")
    tail = " / ".join(line.strip() for line in output.strip().splitlines()[-3:])[:300]
    return Step(name, ok, time.monotonic() - started, "" if ok else f"{tail} (log: {log.relative_to(ROOT).as_posix()})")


def asset_id_stats(place_text: str) -> dict:
    ids = re.findall(r"rbxassetid://(\d+)", place_text)
    return {"distinct_asset_ids": len(set(ids)), "asset_id_references": len(ids)}


def flag_table(default_place: bytes, playtest_place: bytes) -> dict:
    """Effective Config values of the two BUILT places, plus the Workspace streaming flag."""
    table: dict[str, dict] = {}
    entries = {"default": release_profiles.config_entries(verify_release.config_from_place(default_place)),
               "playtest": release_profiles.config_entries(verify_release.config_from_place(playtest_place))}
    for key in FLAG_KEYS:
        row = {}
        for profile, found in entries.items():
            value = found.get(key, [(0, None)])[-1][1]
            row[profile] = None if value is None else (str(value) if isinstance(value, release_profiles.RawLiteral) else value)
        table[key] = row
    table["StreamingEnabled"] = {"default": verify_release.workspace_streaming_from_place(default_place)["enabled"],
                                 "playtest": verify_release.workspace_streaming_from_place(playtest_place)["enabled"]}
    products = {p: len(verify_release_ids.developer_product_ids(verify_release.config_from_place(d)))
                for p, d in (("default", default_place), ("playtest", playtest_place))}
    table["DeveloperProducts (count)"] = products
    return table


def flag_warnings(table: dict) -> list[str]:
    warnings = []
    if table.get("FoodPickupAtMouth", {}).get("playtest") is not False:
        warnings.append("FoodPickupAtMouth is not false in the playtest build; docs/115 MR6 keeps it false until BD-527 is decided")
    if table.get("StreamingEnabled", {}).get("playtest") is not False:
        warnings.append("Workspace StreamingEnabled is on in the playtest place")
    return warnings


def release_record_row(date: str, tag: str, commit: str, place_sha: str, store: str, universe, place, action: str) -> str:
    return f"| {date} | {tag} | {commit[:10]} | {place_sha} | `{store}` | {universe} / {place} | _fill after publish_ | {action} | Znypr |"


# ------------------------------------------------------------------------------------------------ main flow
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="run every step even if a gate would refuse; write <tag>.dry-run.json")
    parser.add_argument("--luau", help="path to the luau runner (default: $LUAU_RUNNER, PATH, ~/.cache/be-dino/luau-*)")
    parser.add_argument("--skip-ci-check", action="store_true", help="do not ask GitHub whether CI is green on this commit")
    parser.add_argument("--skip-verifiers", action="store_true", help="dry-run only: skip the CI command list and unit tests (gates, builds, verify_release still run)")
    parser.add_argument("--no-fetch", action="store_true", help="do not run `git fetch origin main` first")
    args = parser.parse_args(argv)
    if args.skip_verifiers and not args.dry_run:
        parser.error("--skip-verifiers is only allowed with --dry-run: a real release runs the whole CI list")

    started = time.monotonic()
    print(f"Be Dino! playtest release preparation{' (DRY RUN)' if args.dry_run else ''}")
    if not args.no_fetch:
        rc, out = git("fetch", "--quiet", "origin", "main")
        if rc != 0:
            print(f"note: git fetch origin main failed ({out[:120]}); using the local origin/main")
    rc, sha = git("rev-parse", "HEAD")
    rc2, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    _, main_sha = git("rev-parse", "origin/main")
    print(f"HEAD {sha[:12]} on {branch}; origin/main {main_sha[:12]}")

    # 1. gates
    print("\n== 1. Gates ==")
    gates = evaluate_gates(skip_ci_check=args.skip_ci_check)
    for gate in gates:
        print(gate.line())
    blockers = [g for g in gates if g.blocks]
    if blockers and not args.dry_run:
        print(f"\nREFUSED: {len(blockers)} gate(s) failed. Nothing was built. Fix them and run again (rehearse with --dry-run).")
        return 2

    luau, luau_compile = find_luau(args.luau)
    if luau is None:
        print("ERROR: no luau runner found (pass --luau PATH or set LUAU_RUNNER); the CI verifier list needs it.")
        if not args.skip_verifiers:
            return 1
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    if luau:
        env["LUAU_RUNNER"] = luau
    log_dir = RELEASE_DIR / "logs"
    shutil.rmtree(log_dir, ignore_errors=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    steps: list[Step] = []
    counter = [0]

    def run(name, command):
        counter[0] += 1
        step = run_command(name, command, env, log_dir, counter[0])
        steps.append(step)
        print(f"[{'PASS' if step.ok else 'FAIL'}] {name} ({step.seconds:.1f}s)" + (f"\n       {step.detail}" if step.detail else ""))
        return step

    py = sys.executable
    # 2. builds and release verification
    print("\n== 2. Build and verify_release ==")
    run("build default profile", [py, "tools/build.py"])
    run("build playtest profile", [py, "tools/build.py", "--profile", "playtest"])
    build = build_number()
    default_place = ROOT / f"build/BeDino-Build{build}.rbxlx"
    playtest_place = ROOT / f"build/BeDino-Build{build}-playtest.rbxlx"
    run("verify_release (default)", [py, "tools/verify_release.py", "--profile", "default", "--place", str(default_place)])
    run("verify_release (playtest)", [py, "tools/verify_release.py", "--profile", "playtest", "--place", str(playtest_place)])

    # 3. smoke, kanban, CI list, tests
    if args.skip_verifiers:
        print("\n== 3. Verifiers: SKIPPED (--skip-verifiers, dry-run only) ==")
    else:
        print("\n== 3. Session-1 smoke, kanban merge check, CI verifier list, unit tests ==")
        run("session-1 smoke", [py, "tools/verify_session1_smoke.py", "--runner", luau])
        run("verify_kanban_merge (origin/main..HEAD)", [py, "tools/verify_kanban_merge.py", "--base", "origin/main", "--head", "HEAD"])
        commands = ci_commands(WORKFLOW.read_text(encoding="utf-8"), luau, luau_compile)
        print(f"CI list: {len(commands)} commands read from {WORKFLOW.name}")
        for command in commands:
            run(" ".join(["python"] + command[1:]).replace(luau, "<luau>").replace(luau_compile, "<luau-compile>"), command)
        run("unit tests (python -m unittest discover -s tests)", [py, "-m", "unittest", "discover", "-s", "tests"])

    # 4. clean again, manifest
    print("\n== 4. Manifest ==")
    dirty_after = working_tree_problems()
    steps.append(Step("working tree still clean after the run", not dirty_after, 0, "; ".join(dirty_after)))
    print(f"[{'PASS' if not dirty_after else 'FAIL'}] working tree still clean after the run" + (f": {dirty_after[0]}" if dirty_after else ""))

    manifest: dict = {"format": 1, "dry_run": args.dry_run}
    failed = [s for s in steps if not s.ok]
    try:
        playtest_bytes, default_bytes = playtest_place.read_bytes(), default_place.read_bytes()
        play_manifest = json.loads(playtest_place.with_suffix(".manifest.json").read_text(encoding="utf-8"))
        if play_manifest.get("git_commit") != sha or play_manifest.get("git_dirty") is not False:
            failed.append(Step("playtest manifest matches HEAD and is clean", False, 0,
                               f"manifest git_commit={play_manifest.get('git_commit')!r} git_dirty={play_manifest.get('git_dirty')!r}"))
        table = flag_table(default_bytes, playtest_bytes)
        for warning in flag_warnings(table):
            print(f"WARNING: {warning}")
        slot = verify_release_ids.load_slot()
        tag, previous = propose_tag(build, playtest_tags())
        date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
        store = release_profiles.config_entries(verify_release.config_from_place(playtest_bytes))["ProfileDataStoreName"][-1][1]
        sources_hash = sha256_bytes(json.dumps(play_manifest.get("sources", {}), sort_keys=True).encode())
        message = f"Be Dino! playtest {tag}: build redesign-{build}, profile playtest, place_sha256 {sha256_bytes(playtest_bytes)[:12]}"
        manifest.update({
            "tag_proposal": tag, "previous_playtest_tag": previous, "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "git_sha": sha, "git_branch": branch, "origin_main_sha": main_sha, "profile": "playtest", "build": f"redesign-{build}",
            "playtest_place_sha256": sha256_bytes(playtest_bytes), "default_place_sha256": sha256_bytes(default_bytes),
            "sources_sha256": sources_hash, "script_count": len(play_manifest.get("sources", {})),
            "config_overrides": play_manifest.get("config_overrides", {}), "build_warnings": play_manifest.get("warnings", []),
            "ids": {"PlaytestUniverseId": slot.get("PlaytestUniverseId"), "PlaytestPlaceId": slot.get("PlaytestPlaceId"),
                    "ExperienceKind": slot.get("ExperienceKind")},
            "ids_embedded_in_place": {"PlaytestUniverseId": table["PlaytestUniverseId"]["playtest"], "PlaytestPlaceId": table["PlaytestPlaceId"]["playtest"]},
            "datastore": store, "flag_table": table, "assets": asset_id_stats(playtest_bytes.decode("utf-8", "replace")),
            "gates": [{"gate": g.name, "ok": g.ok, "detail": g.detail} for g in gates],
            "steps": [s.as_dict() for s in steps],
            "release_record_row": release_record_row(date, tag, sha, sha256_bytes(playtest_bytes), store,
                                                     slot.get("PlaytestUniverseId") or "BD-004 unanswered", slot.get("PlaytestPlaceId") or "BD-004 unanswered",
                                                     "first publish" if previous is None else "publish"),
            "tag_commands": tag_commands(tag, sha, message), "rollback": rollback_plan(previous, tag),
        })
        RELEASE_DIR.mkdir(parents=True, exist_ok=True)
        target = RELEASE_DIR / (f"{tag}.dry-run.json" if args.dry_run else f"{tag}.release.json")
        will_write = args.dry_run or (not failed and not blockers)
        if will_write:
            target.write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
            print(f"Manifest written: {target.relative_to(ROOT).as_posix()}")
        show_summary(manifest, table)
    except (OSError, ValueError, KeyError) as error:
        failed.append(Step("manifest", False, 0, f"{type(error).__name__}: {error}"))
        print(f"[FAIL] manifest: {error}")

    elapsed = time.monotonic() - started
    failed_names = [s.name for s in failed]
    print(f"\nSteps: {sum(1 for s in steps if s.ok)} passed, {len([s for s in steps if not s.ok])} failed of {len(steps)} ({elapsed / 60:.1f} min)")
    if failed:
        print("FAILED STEPS: " + "; ".join(failed_names))
        return 1
    if blockers:
        print(f"DRY RUN OK, but a real run would be REFUSED by {len(blockers)} gate(s):")
        for gate in blockers:
            print(f"  - {gate.name}: {gate.detail[:240]}")
        return 0
    print("READY: all gates and steps passed. Nothing was published or tagged." if not args.dry_run else "DRY RUN OK: a real run would be allowed.")
    return 0


def show_summary(manifest: dict, table: dict) -> None:
    print("Flag table (values read from the BUILT places; default | playtest):")
    for key, row in table.items():
        print(f"  {key:34} {row.get('default')!s:28} | {row.get('playtest')!s}")
    assets = manifest["assets"]
    print(f"Assets: {assets['distinct_asset_ids']} distinct rbxassetid ids ({assets['asset_id_references']} references) in the playtest place")
    print(f"Build hash: playtest place_sha256 {manifest['playtest_place_sha256']}")
    print(f"            default  place_sha256 {manifest['default_place_sha256']}")
    print(f"            {manifest['script_count']} scripts, sources_sha256 {manifest['sources_sha256'][:16]}")
    print(f"BD-004 ids: universe {manifest['ids']['PlaytestUniverseId']}, place {manifest['ids']['PlaytestPlaceId']}, kind {manifest['ids']['ExperienceKind']}; store {manifest['datastore']}")
    print("\n== 5. Annotated tag PROPOSAL (not created, not pushed) ==")
    print(f"Proposed tag: {manifest['tag_proposal']}")
    for command in manifest["tag_commands"]:
        print(f"  {command}")
    print("\n== 6. Rollback target ==")
    for line in manifest["rollback"]:
        print(line)
    print("\nRelease record row (docs/55 s6):")
    print(manifest["release_record_row"])


if __name__ == "__main__":
    sys.exit(main())
