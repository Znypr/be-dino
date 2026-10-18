"""BD-632 (docs/152 s9): offline run of the REAL PredationService tick, so `Config.PredationAtMouth` is proved through the loop and not only as a pure rule.

Before this, tools/ had text scans of src/server/PredationService.luau (verify_gameplay, verify_mutations, verify_class_movement), two harnesses that imitate its
call (session1_smoke, multiplayer_sim) and the pure rule (verify_mouth_reach). Nothing ran a kill through the tick. This builds the remote-fuzz harness
(tools/verify_remote_fuzz.py: virtual clock, mocked Players / workspace / DataStore, the real RunLifecycle and ProfileRepository) with the scenarios in
tools/predation_tick_cases.luau and checks, with the head circle of the species with the longest head (far from its root):

  predation-at-mouth        PredationAtMouth on, LowPolyDinos on, CombatEnabled off: a victim at the mouth is eaten, one only near the root is not; a victim just outside the
                            circle, above the vertical limit, of equal size or bigger is never eaten; one kill = one bite cue, one quarter-egg bonus, one growth add, one
                            settlement (no double catch); the victim's spawn protection is respected (also for a run that starts later); the nearest mouth wins (not the
                            lower id), an equal distance goes to the lower id with one bonus; an attacker too small cannot eat; an implausible step (a teleport) is skipped for a
                            tick; the same victim eaten again inside RepeatVictimCatchCooldownSeconds pays no second kill egg, after it the bonus is paid again
  predation-at-root         the same cells with the flag off: the opposite answer for the mouth and root victims (the flag is what switches the rule)
  predation-flag-without-lowpoly   flag on, LowPolyDinos off: the speciesId is not read, the root rule applies
  predation-combat-on       CombatEnabled on: the instant rule is replaced, nobody is eaten whatever the geometry

    python tools/verify_predation_tick.py --runner /path/to/luau
    python tools/verify_predation_tick.py --runner /path/to/luau --selftest    # each mutant of PredationService must make a named check fail

Limits: mocks. A character is a root part at a position (no physics, no real raycast, no bite animation, no client). Whether the kill FEELS right (reach, pace, the
BD-527 comparison) stays with Studio; this proves the server tick uses the rule it claims to use and does not pay twice.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_remote_fuzz as fuzz  # noqa: E402

CASES = ["predation_tick_cases.luau", "remote_fuzz_tail.luau"]
SCENARIOS = ["predation-at-mouth", "predation-at-root", "predation-flag-without-lowpoly", "predation-combat-on"]

P = "src/server/PredationService"
MUTANTS = [
    ("the mouth branch is gone (head point never used)", {P: ("if attacker.speciesId ~= nil then", "if false then")},
     "predation-at-mouth: a victim at the MOUTH is eaten"),
    ("the size rule is gone (anybody eats anybody)", {P: ("if not canEat(attacker.score, victim.score) then continue end", "")},
     "predation-at-mouth: a victim of the same size is never eaten"),
    ("the repeat-victim cooldown is gone", {P: ('if not victimMemory.allow(attacker.player.UserId, "victim" .. victimUserId, now, Config.RepeatVictimCatchCooldownSeconds) then', "if false then")},
     "predation-at-mouth: the repeat inside"),
    ("spawn protection is ignored for the victim", {P: ("or runLifecycle.isProtected(victim.character, serverNow)", "")},
     "predation-at-mouth: the kill came after the spawn protection"),
    ("the speciesId is read without the LowPolyDinos flag", {P: ("if Config.PredationAtMouth == true and lowPolyOn() then", "if Config.PredationAtMouth == true then")},
     "predation-flag-without-lowpoly: a victim at the MOUTH is not eaten"),
    ("the combat guard is gone (instant rule runs beside HP combat)", {P: ("if Config.CombatEnabled then return end", "")},
     "predation-combat-on: a victim at the"),
    ("the movement plausibility skip is gone", {P: ("if plausible then", "if true then")},
     "predation-at-mouth: after a 560 stud jump"),
    ("the nearest attacker is no longer chosen (first in id order wins)", {P: ("if horizontal < nearest or (horizontal == nearest and winner and attacker.player.UserId < winner.player.UserId) then", "if winner == nil then")},
     "predation-at-mouth: the NEAREST attacker eats"),
]


def run(runner: str, mutants: dict | None = None):
    completed, checks, report, times, done = fuzz.run_luau(runner, "", mutants, None, 60, CASES)
    return completed, checks, report, times, done


def selftest(runner: str) -> int:
    failed = 0
    for label, mutants, expect in MUTANTS:
        completed, checks, report, times, done = run(runner, mutants)
        broken = [name for ok, name, _ in checks if not ok]
        hit = any(expect in name for name in broken)
        print(f"  mutant {'CAUGHT' if hit else 'MISSED'}: {label} -> {len(broken)} failing check(s)" + ("" if hit else f"; wanted '{expect}', got {broken[:3]}"))
        if not hit:
            failed += 1
    if failed:
        print(f"Predation tick self-test FAILED: {failed} mutant(s) were not caught")
        return 1
    print(f"Predation tick self-test passed: all {len(MUTANTS)} mutants were caught")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runner", required=True, help="path to the pinned luau executable")
    parser.add_argument("--selftest", action="store_true", help="prove the checks bite: each source mutant must fail a named check")
    parser.add_argument("--verbose", action="store_true", help="print every check")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest(args.runner)
    completed, checks, report, times, done = run(args.runner)
    if done is None:
        print(completed.stdout[-3000:])
        print(completed.stderr[-3000:])
        print("Predation tick harness did not complete.")
        return 1
    problems = []
    scenarios = {name.split(":")[0] for _, name, _ in checks}
    for scenario in SCENARIOS:
        if scenario not in scenarios:
            problems.append(f"scenario {scenario} produced no checks")
    failures = [(name, detail) for ok, name, detail in checks if not ok]
    for line in report:
        print("  " + line)
    if args.verbose:
        for ok, name, detail in checks:
            print(f"  {'PASS' if ok else 'FAIL'} {name} {detail[:160]}")
    for name, detail in failures:
        print(f"FAIL: {name} {detail[:400]}")
    for problem in problems:
        print(f"FAIL: {problem}")
    if failures or problems or completed.returncode != 0:
        print(f"Predation tick FAILED: {len(failures)} failing check(s), {len(problems)} scenario problem(s)")
        return 1
    print(f"Predation tick passed: {len(checks)} checks in {len(scenarios)} scenarios (the real PredationService loop, {len(MUTANTS)} mutants in --selftest)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
