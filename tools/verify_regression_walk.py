#!/usr/bin/env python3
"""Offline self-test of the first-session regression walk scripts (BD-541, docs/145 s9, tools/qa/regression_walk/).

The walk scripts are Studio execute_luau snippets, so CI cannot run them in Studio. This verifier does three things with the pinned
Luau runtime (no Studio, no network):

1. CONTRACT: every game name a script depends on (remote, attribute, GUI name, screen title, button text, module function) must still
   exist in src/. A rename in the game fails here with the name, instead of failing silently in front of the lead.
2. RUN: the real scripts run, in README order, against selftest/sim.luau (a Roblox mock with a tiny Be Dino simulation that uses the
   same remote, attribute, button and screen names; real pure modules from src/shared are loaded). The happy path must print 13 PASS
   lines in step order, a CAPTURE line per step and four PASS server checkpoints.
3. JUDGE: broken scenarios must NOT pass: no input service (steps print where to click, ODD), a window that does not render (FAIL),
   overlapping HUD rectangles (FAIL), a logged error (FAIL), a dino cut off by the camera (FAIL).

It proves the scripts parse, order their steps and judge as intended. It proves nothing about Studio, a phone or a published server.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WALK = ROOT / "tools" / "qa" / "regression_walk"
SCRIPTS = {
    "lib": "00-lib.client.luau",
    "c1": "10-steps-1-4.client.luau",
    "c2": "20-steps-5-8.client.luau",
    "c3": "30-steps-9-13.client.luau",
    "server": "40-checkpoints.server.luau",
}
REAL_MODULES = ["Config", "ProgressionConfig", "EggGenetics", "ProgressionRules", "RevealSkip", "FtueP1", "SettingsModel",
                "CaveGateRules", "CaveHubLayout", "SpawnGeometry"]


def src_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "src").rglob("*.luau")))


def contract(failures: list) -> int:
    """Every literal a walk script hands to a game-facing helper must still appear in src/."""
    text = src_text()
    checked = 0
    exact = r'(?:modalOpen|hasExact|W\.remote|W\.priv|W\.num|W\.json|W\.rail|W\.mod)\('
    prefix = r'(?:GetAttribute|FindFirstChild|W\.btn|W\.hasMatch|GetAttributeChangedSignal)\('
    skip = {"PlayerGui", "PlayerScripts", "Client", "Shared", "Toasts", "Rail"}  # Roblox built-ins or covered below
    literals = set()
    for name in SCRIPTS.values():
        body = (WALK / name).read_text(encoding="utf-8")
        for m in re.finditer(r'(?:modalOpen|hasExact)\((?:[^"()]*,\s*)?"([^"]+)"', body):
            literals.add((m.group(1), True))
        for m in re.finditer(r'(?:W\.remote|W\.priv|W\.num|W\.json|W\.rail)\("([^"]+)"', body):
            literals.add((m.group(1), True))
        for m in re.finditer(r'(?:GetAttribute|SetAttribute|GetAttributeChangedSignal)\("([^"]+)"', body):
            literals.add((m.group(1), True))
        for m in re.finditer(r'FindFirstChild\("([^"]+)"', body):
            if m.group(1) not in skip:
                literals.add((m.group(1), False))
        for m in re.finditer(r'W\.btn\((?:[^"()]|\([^()]*\))*?,\s*"([^"]+)"', body):
            literals.add((m.group(1), False))
        for m in re.finditer(r'(?:d|\w)\.Name == "([^"]+)"', body):
            literals.add((m.group(1), False))
    built = {"Tab_": "Tab_", "Toggle_": "Toggle_", "ShopTile_": "ShopTile_", "NestSlot": "NestSlot", "Admin_": "Admin_"}  # names the game builds as prefix .. value
    for lit, is_exact in sorted(literals):
        checked += 1
        prefix = next((p for p in built if lit.startswith(p)), None)
        if prefix:
            needle, is_exact = '"%s' % prefix, False
            rest = lit[len(prefix):]
            if prefix == "Toggle_" and ('"%s"' % rest) not in text:
                failures.append("CONTRACT: the label %r of the toggle %r is gone from src/" % (rest, lit))
            if prefix == "Admin_" and ('%s =' % rest) not in (ROOT / "src" / "shared" / "AdminRules.luau").read_text(encoding="utf-8"):
                failures.append("CONTRACT: admin setting %r is gone from AdminRules" % rest)
        else:
            needle = '"%s"' % lit if is_exact else '"%s' % lit
        if needle not in text and lit.isupper() and lit.isalpha():
            needle = '"%s"' % lit.lower()  # shop tab buttons are string.upper(tab) of the tab ids
        if needle not in text and lit.isupper():
            needle = '"%s"' % lit.capitalize()  # buttons that show an upper-cased sentence, e.g. COMING SOON from "Coming soon"
        if needle not in text:
            failures.append("CONTRACT: the walk uses %r but src/ no longer has it" % lit)
    # names built at run time are covered by their prefix above; titles and tab words below are upper-cased or compared by value
    for lit in ("Run Complete!", "Oops! Good try!", "Welcome to Be Dino!", "LET'S PLAY", "GO HOME", "OPEN EGGS", "BACK TO SANCTUARY",
                "An egg is hatching...", "Auto-opened eggs", "Skip the rest", "Tell us!", "BUY EGG", "Random Egg", "You have", "HELP",
                "Common", "AUTO", "ManualExit", "Sanctuary", "Island", "startWeather", "stopWeather", "foodMultiplier", "buyPotion", "usePotion"):
        checked += 1
        if lit not in text:
            failures.append("CONTRACT: text %r is gone from src/" % lit)
    shared = {p.stem for p in (ROOT / "src" / "shared").glob("*.luau")}
    client = {p.stem for p in (ROOT / "src" / "client").glob("*.luau")}
    for name in ("CaveGateRules", "SpawnGeometry", "ProgressionRules", "ProgressionConfig", "RevealSkip", "SettingsModel", "FtueP1", "UITheme", "Config"):
        checked += 1
        if name not in shared:
            failures.append("CONTRACT: src/shared/%s.luau is gone" % name)
    for name in ("CameraFit", "SettingsMenu", "FusionMenu", "PrivateState"):
        checked += 1
        if name not in client:
            failures.append("CONTRACT: src/client/%s.luau is gone" % name)
    functions = [
        ("src/shared/CaveGateRules.luau", r"function CaveGateRules\.zone\("), ("src/shared/CaveGateRules.luau", r"function CaveGateRules\.inZone\("),
        ("src/shared/SpawnGeometry.luau", r"function SpawnGeometry\.inHub\("), ("src/shared/ProgressionRules.luau", r"function Rules\.shopWindow\("),
        ("src/shared/ProgressionRules.luau", r"function Rules\.shopOffers\("), ("src/shared/ProgressionRules.luau", r"function Rules\.shopRemaining\("),
        ("src/shared/ProgressionRules.luau", r"function Rules\.item\("), ("src/shared/RevealSkip.luau", r"function Skip\.toggle\("),
        ("src/shared/SettingsModel.luau", r"function Model\.calm\("), ("src/shared/SettingsModel.luau", r"function Model\.set\("),
        ("src/shared/FtueP1.luau", r"function P\.shopTabs\("), ("src/shared/FtueP1.luau", r"P\.ConditionsTabLevel"),
        ("src/client/CameraFit.luau", r"function CameraFit\.box\("), ("src/client/CameraFit.luau", r"function CameraFit\.minZoom\("),
        ("src/client/FusionMenu.luau", r"function FusionMenu\.open\("), ("src/client/FusionMenu.luau", r"function FusionMenu\.close\("),
        ("src/client/FusionMenu.luau", r"function FusionMenu\.isOpen\("), ("src/client/SettingsMenu.luau", r"function Menu\.tab\("),
        ("src/client/PrivateState.luau", r"function PrivateState\.get\("), ("src/server/PrivateState.luau", r"function PrivateState\.get\("),
    ]
    for path, pattern in functions:
        checked += 1
        if not re.search(pattern, (ROOT / path).read_text(encoding="utf-8")):
            failures.append("CONTRACT: %s no longer matches %s" % (path, pattern))
    # the remotes the walk fires or listens to are created by the server
    server = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "src" / "server").glob("*.luau"))
    for name in ("RequestStartRun", "RequestEndRun", "RequestLeap", "EquipSpecies", "SetRevealSkip", "ProgressionAction", "ProgressionResult", "AdminAction", "ClaimChest"):
        checked += 1
        if '"%s"' % name not in server:
            failures.append("CONTRACT: no server code creates the remote %s" % name)
    return checked


def lua_function(source: str) -> str:
    return "function(...)\n" + source + "\nend"


def build_sim(scenario: str) -> str:
    sim = (WALK / "selftest" / "sim.luau").read_text(encoding="utf-8")
    scripts = "{\n" + "".join("%s = %s,\n" % (key, lua_function((WALK / name).read_text(encoding="utf-8"))) for key, name in SCRIPTS.items()) + "}"
    modules = "{\n"
    for name in REAL_MODULES:
        source = (ROOT / "src" / "shared" / (name + ".luau")).read_text(encoding="utf-8")
        if name == "Config":
            assert "CaveHub = false," in source, "Config no longer has 'CaveHub = false,': update the self-test"
            source = source.replace("CaveHub = false,", "CaveHub = true,", 1)
        modules += "%s = function(script, require)\n%s\nend,\n" % (name, source)
    modules += "}"
    for token in ("SCRIPTS_INJECTED", "MODULES_INJECTED", "SCENARIO_INJECTED"):
        assert sim.count(token) == 1, token
    return sim.replace("SCRIPTS_INJECTED", scripts).replace("MODULES_INJECTED", modules).replace("SCENARIO_INJECTED", '"%s"' % scenario)


def run_scenario(runner: str, scenario: str) -> list:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / ("walk_%s.luau" % scenario)
        path.write_text(build_sim(scenario), encoding="utf-8")
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding="utf-8", timeout=300)
    lines = [l for l in result.stdout.splitlines()]
    if result.returncode != 0 or "SIM done" not in result.stdout:
        print("\n".join(lines[-40:]))
        print(result.stderr)
        raise SystemExit("scenario %s: the sim did not finish (exit %s)" % (scenario, result.returncode))
    return lines


def verdicts(lines: list) -> dict:
    out = {}
    for line in lines:
        m = re.match(r"WALK (\d\d) (PASS|FAIL|ODD) ", line)
        if m:
            out[int(m.group(1))] = (m.group(2), line)
    return out


def expect(failures: list, ok: bool, text: str):
    if not ok:
        failures.append(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    args = parser.parse_args()
    failures: list = []
    checked = contract(failures)
    print("contract: %d names checked against src/" % checked)

    # ---- happy path
    lines = run_scenario(args.runner, "happy")
    walk_lines = [l for l in lines if re.match(r"WALK \d\d (PASS|FAIL|ODD) ", l)]
    order = [int(re.match(r"WALK (\d\d)", l).group(1)) for l in walk_lines]
    expect(failures, order == list(range(1, 14)), "happy: the 13 verdict lines must come once each in step order, got %s" % order)
    for n, (v, line) in verdicts(lines).items():
        expect(failures, v == "PASS", "happy: step %d is %s: %s" % (n, v, line[:400]))
    captures = [int(m.group(1)) for l in lines for m in [re.match(r"CAPTURE (\d\d) screen_capture now", l)] if m]
    expect(failures, captures == list(range(1, 14)), "happy: one CAPTURE line per step in order, got %s" % captures)
    expect(failures, not any("step crashed" in l for l in lines), "happy: a step crashed")
    server = [l for l in lines if l.startswith("WALKS ")]
    expect(failures, len(server) == 4 and all(" PASS " in l for l in server), "happy: four PASS server checkpoints expected, got %s" % server)
    expect(failures, any(l.startswith("WALK ") and " CONTINUE " in l for l in lines), "happy: the eat step should have asked to be run again (CONTINUE path untested)")
    summary = [l for l in lines if l.startswith("SUMMARY ")]
    expect(failures, bool(summary) and all("PASS" in part for part in summary[-1].split(", ")), "happy: the final SUMMARY is not all PASS")
    expect(failures, any(l.startswith("WALK lib ready") for l in lines), "happy: the library prints its capabilities")
    print("happy path: %d verdict lines, %d captures, %d server checkpoints" % (len(walk_lines), len(captures), len(server)))

    # ---- broken scenarios must be caught
    lines = run_scenario(args.runner, "novim")
    v = verdicts(lines)
    expect(failures, v.get(1, ("", ""))[0] == "ODD" and "VirtualInputManager" in v.get(1, ("", ""))[1], "novim: step 1 must be ODD and name the missing input service")
    expect(failures, any(l.startswith("NEEDS ") for l in lines), "novim: a NEEDS line (where to click by hand) must be printed")
    expect(failures, not any("step crashed" in l for l in lines), "novim: a step crashed")
    expect(failures, "PASS" != v.get(4, ("PASS", ""))[0], "novim: the leap cannot be PASS when only the remote was fired")
    print("novim: input service missing is reported as ODD with click positions")

    lines = run_scenario(args.runner, "blind")
    v = verdicts(lines)
    expect(failures, v.get(1, ("", ""))[0] == "FAIL" and "viewport" in v.get(1, ("", ""))[1] and "frames" in v.get(1, ("", ""))[1], "blind: a 1x1 window with no frames must FAIL step 1")
    print("blind: a window that does not render fails step 1")

    lines = run_scenario(args.runner, "overlap")
    v = verdicts(lines)
    expect(failures, v.get(1, ("", ""))[0] == "FAIL" and "eggs/feedback" in v.get(1, ("", ""))[1], "overlap: the EGGS plate under 'Tell us!' must FAIL step 1")
    print("overlap: overlapping HUD rectangles fail step 1")

    lines = run_scenario(args.runner, "errors")
    expect(failures, any(" FAIL " in l and "new error" in l for l in lines if l.startswith("WALK ")), "errors: a logged error must FAIL the step it happened in")
    print("errors: a logged error fails its step")

    lines = run_scenario(args.runner, "studionoise")
    expect(failures, not any(" FAIL " in l and "new error" in l for l in lines if l.startswith("WALK ")), "studionoise: Studio's own TexturePack upload lines must not fail a step (BD-596)")
    expect(failures, any("TexturePack" in l and "not counted" in l for l in lines if l.startswith("WALK ")), "studionoise: the lines are named in the report, not silently dropped")
    print("studionoise: Studio TexturePack lines are named, not counted as game errors")

    lines = run_scenario(args.runner, "clipped")
    v = verdicts(lines)
    expect(failures, v.get(8, ("", ""))[0] == "FAIL" and "corners" in v.get(8, ("", ""))[1], "clipped: a dino cut off by the camera must FAIL step 8")
    print("clipped: a dino outside the screen fails step 8")

    readme = (WALK / "README.md").read_text(encoding="utf-8")
    for name in list(SCRIPTS.values()) + ["selftest/sim.luau"]:
        expect(failures, name in readme, "README.md does not mention %s" % name)

    for f in failures:
        print("FAIL:", f)
    if failures:
        return 1
    print("regression walk self-test passed: contract, 13-step order, 5 broken scenarios caught")
    return 0


if __name__ == "__main__":
    sys.exit(main())
