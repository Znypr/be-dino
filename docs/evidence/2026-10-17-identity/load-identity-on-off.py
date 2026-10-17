import sys, json, subprocess, tempfile
from pathlib import Path
sys.path.insert(0, r"C:/Users/znypr/Documents/be-dino-wt-identity/tools")
import verify_load as V
V.ROOT = Path(r"C:/Users/znypr/Documents/be-dino-wt-identity")
B = V.BASE; P = V.PLAYTEST_OVERRIDES
V.SCENARIOS[:] = [
 dict(B, name="long-1h-x4-OFF", players=4, seed=7, catchesPerMinute=100, duration=3600, revealSeconds=1, gated=False),
 dict(B, name="long-1h-x4-ON", players=4, seed=7, catchesPerMinute=100, duration=3600, revealSeconds=1, configOverrides=P, gated=False),
 dict(B, name="long-2h-x4-ON", players=4, seed=7, catchesPerMinute=100, duration=7200, revealSeconds=1, configOverrides=P, gated=False),
 dict(B, name="long-2h-x4-OFF", players=4, seed=7, catchesPerMinute=100, duration=7200, revealSeconds=1, gated=False),
]
with tempfile.TemporaryDirectory() as f:
    p = Path(f)/"l.luau"; p.write_text(V.harness(), encoding="utf-8")
    c = subprocess.run([sys.argv[1], str(p)], capture_output=True, text=True)
print(c.stderr[-1500:])
for line in c.stdout.splitlines():
    if line.startswith("RESULT "):
        r = json.loads(line[7:])
        print(r["name"], "maxKeyBytes/min", r["maxKeyBytesPerMinute"], "maxProfile", r["maxProfileBytes"], "writes/min", r["maxKeyWritesPerMinute"],
              "failures", r["failures"], "throttled", r["throttled"], "peak", r["peakWindowA"], "/", r["budgetA"], "undrained", r["undrainedEggs"])
