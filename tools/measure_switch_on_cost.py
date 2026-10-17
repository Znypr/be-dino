#!/usr/bin/env python3
"""Server cost of switching the built-but-off features on (docs/152 s5): DataStore requests, repository calls per minute.

    python tools/measure_switch_on_cost.py --runner C:/.../luau.exe [--seeds 3] [--json out.json]

Runs the 12-player load harness of tools/verify_load.py (real ProfileRepository, mocked DataStore with the per-server
60 + 10 x players request budget, virtual clock) once per variant and seed. Variant 0 is the PLAYTEST (identity flags on), the
others add ONE feature, the last adds all of them. Everything but the Config overrides is identical, and the same seeds are used for
every variant, so a difference is the feature. Numbers are averaged over the seeds and printed per minute for the whole server.

What it measures (offline, virtual time):
  * DataStore UpdateAsync requests on the profile key (loads, renews, settlements, hatch pages, purchases; objectives ride the renew since BD-625);
  * repository calls ("ops"): every call a remote or a server loop makes into ProfileRepository, the closest offline number to
    "remotes per minute" (the harness has no RemoteEvent layer);
  * the share of the per-server budget used at the peak 60 s window.
What it cannot measure: server frame time (no MicroProfiler offline), the Gifts store reads (GiftService needs a second DataStore and
Instances; its cost is derived from GiftService.ClaimSeconds below), OrderedDataStore leaderboards, real latency, other servers.
A variant that adds more than THRESHOLD_PERCENT of the base request volume is flagged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_load  # noqa: E402

THRESHOLD_PERCENT = 10.0
PLAYERS = 12
CATCHES = 8  # the harness' catches per minute (40 per 5 minutes, FoodCatchRate 40/500)

# Variant name -> (config overrides, scenario overrides, note)
BASE_OVERRIDES = dict(verify_load.PLAYTEST_OVERRIDES)


def variants() -> list[tuple[str, dict, dict, str]]:
    def with_(flags: dict) -> dict:
        return {**BASE_OVERRIDES, **flags}
    gifts = {"GiftClaimEnabled": True, "AdminGiftsEnabled": True, "GiftingEnabled": True}
    everything = {"ObjectivesEnabled": True, "PerDinoCosmeticsEnabled": True, "FastTravelPerk": True, "CaveHub": True,
                  "FoodPickupAtMouth": True, "PredationAtMouth": True, "SpecialFoodsEnabled": True, "CombatEnabled": True,
                  "ClassMovementEnabled": True, "HatchV2": True, "LowPolyDinos": True, "RunTelemetryEnabled": True, **gifts}
    burst = {"duration": 1200, "catchesPerMinute": 100}  # egg-burst-400-x12 of verify_load: 400-egg hatches at once
    return [
        ("playtest (base)", with_({}), {}, "the profile the friends would get"),
        ("+ObjectivesEnabled", with_({"ObjectivesEnabled": True}), {}, "food/run/hatch events queue in memory and ride the lease renew write (BD-625); no write of their own"),
        ("+gifts (3 flags)", with_(gifts), {}, "harness cannot run GiftService; see the derived Gifts-store reads below"),
        ("+PerDinoCosmeticsEnabled", with_({"PerDinoCosmeticsEnabled": True}), {}, "same purchase write as the account-wide one"),
        ("+FastTravelPerk+CaveHub", with_({"FastTravelPerk": True, "CaveHub": True}), {}, "one buyPerk write per player, ever (harness does not buy it)"),
        ("+mouth eating (x1.18 eggs)", with_({"FoodPickupAtMouth": True}), {"catchesPerMinute": CATCHES * 1.18}, "docs/145 s3 range low end; more eggs, more hatch pages"),
        ("+mouth eating (x1.37 eggs)", with_({"FoodPickupAtMouth": True}), {"catchesPerMinute": CATCHES * 1.37}, "docs/145 s3 range high end"),
        ("+CombatEnabled (runs half as long)", with_({"CombatEnabled": True}), {"runMin": 45, "runMax": 120}, "no writes of its own; a defeat settles the run, so assume twice the settlements"),
        ("all flags on (x1.37 eggs, runs half as long)", with_(everything), {"catchesPerMinute": CATCHES * 1.37, "runMin": 45, "runMax": 120}, "worst case of the above together"),
        ("burst 400 eggs: playtest", with_({}), burst, "everybody reveals a 400-egg run at once (hatch pages dominate)"),
        ("burst 400 eggs: all flags on", with_(everything), {**burst, "runMin": 45, "runMax": 120}, "same, all flags on"),
    ]


def run(runner: str, scenarios: list[dict]) -> list[dict]:
    verify_load.SCENARIOS = scenarios
    with tempfile.TemporaryDirectory() as folder:
        script = Path(folder) / "cost.luau"
        script.write_text(verify_load.harness(), encoding="utf-8")
        done = subprocess.run([runner, str(script)], capture_output=True, text=True)
    results = [json.loads(line[7:]) for line in done.stdout.splitlines() if line.startswith("RESULT ")]
    if done.returncode != 0 or len(results) != len(scenarios):
        print(done.stdout[-3000:])
        print(done.stderr[-3000:])
        raise SystemExit("cost harness did not complete")
    for line in done.stdout.splitlines():
        if line.startswith("CRASH "):
            raise SystemExit(line)
    return results


TICK_LUAU = r'''
local Config = (function()
@CONFIG@
end)()
local ScaleLadder = (function()
@LADDER@
end)()
local PointGrid = (function()
@GRID@
end)()
local MouthReach = (function()
local script = {Parent = {Config = "Config", ScaleLadder = "ScaleLadder"}}
local require = function(id) if id == "ScaleLadder" then return ScaleLadder end return Config end
@MOUTH@
end)()
local seed = 7
local function rnd() seed = (seed * 1103515245 + 12345) % 2147483648 return seed / 2147483648 end
local half = Config.ArenaHalfWidth
local grid, foods = PointGrid.new(8), {}
for i = 1, Config.FoodSectorCount * Config.FoodSectorCount * Config.FoodClusterItems do
    local f = {x = (rnd() * 2 - 1) * half, z = (rnd() * 2 - 1) * half}
    foods[i] = f
    PointGrid.insert(grid, f, f.x, f.z)
end
local ids = {}
for id in ScaleLadder.Dino.species do ids[#ids + 1] = id end
table.sort(ids)
local function run(label, mouth, ticks)
    seed = 99
    local visited, inRange = 0, 0
    local started = os.clock()
    for _ = 1, ticks do
        for _ = 1, 12 do -- 12 players, the same per-candidate work as FoodService's tick (point, radius, grid query, exact test)
            local x, z = (rnd() * 2 - 1) * half, (rnd() * 2 - 1) * half
            local ang = rnd() * 6.2832
            local scale = 1 + rnd() * 3.8
            local species = if mouth then ids[1 + math.floor(rnd() * #ids)] else nil
            local headX, headZ = MouthReach.point(x, z, math.cos(ang), math.sin(ang), species, scale)
            local radius = MouthReach.radius(species, scale)
            local r2 = radius * radius
            PointGrid.query(grid, headX, headZ, radius, function(food)
                visited += 1
                local dx, dz = food.x - headX, food.z - headZ
                if dx * dx + dz * dz <= r2 then inRange += 1 end
            end)
        end
    end
    local seconds = os.clock() - started
    print(string.format("TICK|%s|%.2f|%.2f|%.3f", label, seconds / ticks * 1e6, visited / ticks, inRange / ticks))
end
run("warm", false, 2000)
run("root", false, 20000)
run("mouth", true, 20000)
'''


def tick_benchmark(runner: str) -> str:
    """Luau CPU of FoodService's per-tick pickup work for 12 players, root rule against mouth rule. Not Roblox server time."""
    def module(path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8")
    code = (TICK_LUAU.replace("@CONFIG@", module("src/shared/Config.luau")).replace("@LADDER@", module("src/shared/ScaleLadder.luau"))
            .replace("@GRID@", module("src/shared/PointGrid.luau")).replace("@MOUTH@", module("src/shared/MouthReach.luau")))
    with tempfile.TemporaryDirectory() as folder:
        script = Path(folder) / "tick.luau"
        script.write_text(code, encoding="utf-8")
        done = subprocess.run([runner, str(script)], capture_output=True, text=True)
    rows = {line.split("|")[1]: line.split("|")[2:] for line in done.stdout.splitlines() if line.startswith("TICK|")}
    if done.returncode != 0 or "root" not in rows or "mouth" not in rows:
        print(done.stdout[-2000:], done.stderr[-2000:])
        raise SystemExit("tick benchmark did not complete")
    root, mouth = (float(rows["root"][0]), float(rows["root"][1]), float(rows["root"][2])), (float(rows["mouth"][0]), float(rows["mouth"][1]), float(rows["mouth"][2]))
    budget_us = 0.08 * 1e6  # Config.FoodTickSeconds
    return (f"tick (FoodService pickup work for 12 players, Luau CPU on this PC, no raycasts): root rule {root[0]:.1f} us/tick, {root[1]:.1f} foods visited, "
            f"{root[2]:.2f} in range; mouth rule {mouth[0]:.1f} us/tick, {mouth[1]:.1f} visited, {mouth[2]:.2f} in range "
            f"({mouth[0] / root[0]:.2f}x); each tick has {budget_us / 1000:.0f} ms, so the mouth rule uses {mouth[0] / budget_us:.3%} of it; "
            f"each food in range costs one Raycast on the server ({mouth[2]:.2f} per tick against {root[2]:.2f})")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runner", required=True)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)

    rows = variants()
    scenarios = []
    for name, config, scenario, _note in rows:
        for k in range(args.seeds):
            scenarios.append(dict(verify_load.BASE, name=f"{name}#{k}", players=PLAYERS, seed=1212 + k, configOverrides=config,
                                  gated=False, **scenario))
    results = run(args.runner, scenarios)

    table = []
    for index, (name, _config, _scenario, note) in enumerate(rows):
        chunk = results[index * args.seeds:(index + 1) * args.seeds]
        minutes = chunk[0]["duration"] / 60
        total = [(r["requestsA"] + r["requestsB"]) / minutes for r in chunk]
        calls = [sum(r["ops"].values()) / minutes for r in chunk]
        peak = [r["ratioA"] for r in chunk]
        by_label: dict[str, float] = {}
        for r in chunk:
            for label, count in r["byLabel"].items():
                by_label[label] = by_label.get(label, 0) + count / minutes / len(chunk)
        table.append({"variant": name, "note": note, "requests_per_min": statistics.mean(total), "spread": (max(total) - min(total)),
                      "calls_per_min": statistics.mean(calls), "peak_ratio": max(peak), "by_label": by_label,
                      "writes_per_min": statistics.mean(r["writes"] / minutes for r in chunk)})
    base = table[0]
    burst_base = table[-2]
    print(f"{PLAYERS} players, {verify_load.BASE['duration']} s (burst rows 1200 s), mean of {args.seeds} seeds; whole-server numbers per minute; base spread +-{base['spread'] / 2:.1f} requests/min")
    print(f"{'variant':46s} {'requests/min':>12s} {'vs base':>8s} {'writes/min':>10s} {'calls/min':>9s} {'peak window':>11s}  by operation (requests/min)")
    flagged = []
    for row in table:
        reference = burst_base if row["variant"].startswith("burst") else base
        delta = (row["requests_per_min"] / reference["requests_per_min"] - 1) * 100
        row["delta_percent"] = delta
        marker = ""
        if row not in (base, burst_base) and delta > THRESHOLD_PERCENT:
            marker = "  <-- more than +10%"
            flagged.append(row["variant"])
        labels = ", ".join(f"{k} {v:.1f}" for k, v in sorted(row["by_label"].items(), key=lambda kv: -kv[1]))
        print(f"{row['variant']:46s} {row['requests_per_min']:12.1f} {delta:+7.1f}% {row['writes_per_min']:10.1f} {row['calls_per_min']:9.1f} {row['peak_ratio']:10.0%}  {labels}{marker}")

    # Derived (not simulated): the Gifts store. GiftService polls every ClaimSeconds per loaded player with one GetAsync on its own store.
    gift = re.search(r"GiftService\.ClaimSeconds = (\d+)", (ROOT / "src/server/GiftService.luau").read_text(encoding="utf-8"))
    claim_seconds = int(gift.group(1)) if gift else 60
    reads = PLAYERS * 60 / claim_seconds
    print(f"derived: GiftService inbox polls = {PLAYERS} players x 60 / {claim_seconds} s = {reads:.0f} GetAsync/min on the Gifts store, "
          f"{reads / (60 + 10 * PLAYERS):.1%} of the per-server read budget of {60 + 10 * PLAYERS}/min (no profile write unless a gift is applied)")
    tick = tick_benchmark(args.runner)
    print(tick)
    print("flagged (> +10% requests/min): " + (", ".join(flagged) if flagged else "none"))
    if args.json:
        args.json.write_text(json.dumps({"players": PLAYERS, "seeds": args.seeds, "rows": table, "giftReadsPerMin": reads}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
