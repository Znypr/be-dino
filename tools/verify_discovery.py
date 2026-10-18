"""BD-436: permanent discovery log (progression.discovered) rules in the pinned Luau runtime, plus static wiring checks.
Repository-level load/hatch/rollback behaviour is asserted in verify_rollback (docs/111). Not Studio evidence."""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_sources  # noqa: E402  (docs/150: ProfileRepository plus its parts)


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
local function count(t) local n = 0 for _ in t do n += 1 end return n end
local profile = {collection = {
    compy = {base = 1, events = {ember = 2, frost = 0}, variants = {
        a = {count = 1, mutationId = "", genes = {primaryColorId = "green", patternId = "p1"}},
        b = {count = 0, mutationId = "gold", genes = {primaryColorId = "red", patternId = "p2"}},
    }},
    rex = {base = 0, variants = {c = {count = 2, mutationId = "aurora", genes = {primaryColorId = "blue", patternId = "p1"}}}},
}, dinosaurIdentity = {instances = {x = {genes = {primaryColorId = "pink", patternId = "p3"}, mutationId = "none"}}}}

local log = Rules.backfillDiscovered(profile)
assert(profile.progression.discovered == log, "stored on progression")
assert(log.colours.green and log.colours.blue and log.colours.pink and not log.colours.red, "owned colours only (count > 0)")
assert(log.patterns.p1 and log.patterns.p3 and not log.patterns.p2)
assert(log.mutations.ember and log.mutations.aurora and not log.mutations.frost and not log.mutations.none and not log.mutations.gold)
local snapshot = {count(log.colours), count(log.patterns), count(log.mutations)}
Rules.backfillDiscovered(profile)
assert(count(log.colours) == snapshot[1] and count(log.patterns) == snapshot[2] and count(log.mutations) == snapshot[3], "idempotent")

-- add-only: removing the owned dino (fusion) never removes the discovery
profile.collection.rex.variants.c.count = 0
profile.dinosaurIdentity.instances.x = nil
Rules.backfillDiscovered(profile)
assert(log.colours.blue and log.colours.pink and log.mutations.aurora, "fused-away dino stays discovered")

-- discover(): first-time flags only
local fresh = Rules.discover(profile, {primaryColorId = "gold", patternId = "p1"}, "")
assert(fresh.colour and not fresh.pattern and not fresh.mutation, "new colour only")
fresh = Rules.discover(profile, {primaryColorId = "gold", patternId = "p9"}, "snow")
assert(not fresh.colour and fresh.pattern and fresh.mutation)
assert(next(Rules.discover(profile, {primaryColorId = "gold", patternId = "p9"}, "snow")) == nil, "second time is not new")
assert(next(Rules.discover(profile, nil, nil)) == nil and next(Rules.discover(profile, {primaryColorId = 5}, "none")) == nil, "junk and none are ignored")

-- junk in the field is replaced; an old profile without the field starts empty
local junk = {collection = {}, progression = {crystals = 0, auras = {}, equippedAura = "", potions = {}, buffs = {}, discovered = "junk"}}
Rules.discover(junk, {primaryColorId = "green"}, "")
assert(type(junk.progression.discovered) == "table" and junk.progression.discovered.colours.green)
assert(Rules.valid(junk.progression), "progression stays valid with the log")
local none = {collection = {}}
assert(Rules.discoveryCounts(none).colours == 0, "absent log reads as zero")

-- bounded growth
local big = {collection = {}}
for i = 1, 100 do Rules.discover(big, {primaryColorId = "c" .. i}, "") end
assert(count(big.progression.discovered.colours) == Rules.DiscoveredMaxPerKind, "capped")
assert(Rules.discoveryCounts(big).colours == Rules.DiscoveredMaxPerKind)
local counts = Rules.discoveryCounts(profile)
assert(counts.colours == count(log.colours) and counts.patterns == count(log.patterns) and counts.mutations == count(log.mutations))
print("discovery rules passed")
'''


def script():
    s = 'local ProgressionConfig=' + module('src/shared/ProgressionConfig.luau') + '\n'
    s += 'local script={Parent={ProgressionConfig="ProgressionConfig",EggGenetics="Genetics"}}\n'
    s += 'local require=function(_) return ProgressionConfig end\n'
    s += 'local Genetics=' + module('src/shared/EggGenetics.luau') + '\n'
    s += 'local require=function(id) return if id=="Genetics" then Genetics else ProgressionConfig end\n'
    s += 'local Rules=' + module('src/shared/ProgressionRules.luau') + '\n' + BODY
    return s


def static_checks():
    repo = profile_sources.repository_text()
    assert 'ProgressionRules.backfillDiscovered(profileValue, Config.PatternColourIndexEnabled == true)' in repo, 'backfill on load'
    assert 'ProgressionRules.discover(profileValue,chest.genes,mutationId,Config.PatternColourIndexEnabled==true)' in repo, 'hatch records discovery'
    assert 'ProgressionRules.discover(nextProfile' in repo, 'fusion result records discovery'
    assert '"DiscoveryJson"' in repo and '"LastChestNewJson"' in repo
    core = (ROOT / 'src/shared/PrivateStateCore.luau').read_text(encoding='utf-8')
    assert '"DiscoveryJson"' in core and '"LastChestNewJson"' in core, 'owner-only names'
    hatch = (ROOT / 'src/client/HatchSequence.luau').read_text(encoding='utf-8')
    assert 'r.newFind' in hatch and '"NEW!"' in hatch
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    hud = (ROOT / 'src/client/GoalHud.luau').read_text(encoding='utf-8')  # goal HUD lives in GoalHud (register limit)
    assert 'decoded("DiscoveryJson"' in hud and 'newFind=' in boot


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    static_checks()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'discovery.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            raise SystemExit(result.stderr or 'failed')
