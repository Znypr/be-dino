"""BD-1217: proof of the authored low-poly dino clips (eat, happy, look) in the pinned Luau runner.

    python tools/verify_lowpoly_clips.py --runner <luau.exe>

1. src/shared/LowPolyClips.luau is generated from tools/blender/dino_clips.py and up to date, and every key is inside the calm limits
   (tools/blender/gen_dino_clips_luau.py --check).
2. The real module, run bare: every clip starts and ends at rest, stays inside the limits between keys (no overshoot), a wing / flipper / arm
   roll mirrors by side, a neck follows the head at NeckShare, bob comes only from the root, an unknown clip or role gives all zero.
3. The animator plays them: LowPolyAnimator requires LowPolyClips, triggers eat / happy / look from the replicated attributes and clears the
   clip under Reduce Motion (amp 0). The full animator run with the clips loaded is tools/verify_motion_poses.py.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import gen_dino_clips_luau  # noqa: E402

BODY = r'''
local ns = DATA
local maxRad = MAX_DEG * math.pi / 180 + 1e-6
local o = Clips.new()
local names = {}
for name, clip in Clips.Data do
    table.insert(names, name)
    assert(Clips.length(name) == clip.length and clip.length > 0.5 and clip.length <= 4, name .. ": length")
    for _, role in {"root", "head", "neck", "tail", "arm", "leg", "wing", "flipper", "body"} do
        for _, side in {-1, 1} do
            for _, t in {0, clip.length, clip.length + 1, -1} do
                Clips.sample(name, role, side, t, o)
                assert(math.abs(o.pitch) + math.abs(o.yaw) + math.abs(o.roll) + math.abs(o.bob) + math.abs(o.fwd) < 1e-9, name .. "." .. role .. " not at rest at " .. t)
            end
            local steps = math.floor(clip.length * 120)
            for i = 0, steps do
                local t = clip.length * i / steps
                Clips.sample(name, role, side, t, o)
                for _, v in {o.pitch, o.yaw, o.roll} do assert(v == v and math.abs(v) <= maxRad, name .. "." .. role .. " angle over the limit at " .. t) end
                assert(o.bob >= -1e-9 and o.bob <= MAX_BOB + 1e-6, name .. " bob out of range at " .. t)
                assert(o.fwd >= -1e-9 and o.fwd <= MAX_FWD + 1e-6, name .. " fwd out of range at " .. t)
                if role ~= "head" then assert(o.fwd == 0, "fwd only on the head") end
                if role == "body" then assert(o.pitch == 0 and o.yaw == 0 and o.roll == 0, "the body never turns (bob moves it)") end
            end
        end
    end
end
table.sort(names)
assert(table.concat(names, ",") == "eat,happy,look", "clips: " .. table.concat(names, ","))
-- side mirror and neck share
local a, b = Clips.new(), Clips.new()
Clips.sample("happy", "wing", -1, 0.2, a) Clips.sample("happy", "wing", 1, 0.2, b)
assert(b.roll > 0.3 and math.abs(a.roll + b.roll) < 1e-9, "a wing opens on both sides")
Clips.sample("happy", "leg", -1, 0.3, a) Clips.sample("happy", "leg", 1, 0.3, b)
assert(a.pitch ~= 0 and a.pitch == b.pitch, "legs swing together in the hop")
Clips.sample("eat", "head", 1, 0.3, a) Clips.sample("eat", "neck", 1, 0.3, b)
assert(a.pitch < -0.3 and math.abs(b.pitch - a.pitch * Clips.NeckShare) < 1e-9, "eat: nose down, neck follows at NeckShare")
assert(a.fwd > 0 and b.fwd == 0, "eat: only the head reaches forward")
Clips.sample("happy", "root", 1, 0.3, a)
assert(a.bob > 0.05 and a.pitch == 0, "happy hops (bob from the root)")
Clips.sample("look", "head", 1, 1.2, a)
assert(a.yaw > 0.3, "look turns the head")
Clips.sample("nope", "head", 1, 0.3, a)
assert(a.pitch == 0 and a.bob == 0, "unknown clip = rest")
Clips.sample("eat", "head", 1, 0 / 0, a)
assert(a.pitch == 0, "NaN time = rest")
print("clip checks passed")
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runner", required=True)
    args = ap.parse_args()
    fails = []
    if gen_dino_clips_luau.main(["--check"]) != 0:
        fails.append("LowPolyClips.luau is out of date or a key breaks the limits")
    ns = gen_dino_clips_luau.load()
    clips = (ROOT / "src/shared/LowPolyClips.luau").read_text(encoding="utf-8")
    prelude = "local Clips = (function()\n%s\nend)()\nlocal MAX_DEG, MAX_BOB, MAX_FWD = %r, %r, %r\nlocal DATA = nil\n" % (clips, ns["MAX_DEG"], ns["MAX_BOB"], ns["MAX_FWD"])
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "clips.luau"
        path.write_text(prelude + BODY, encoding="utf-8")
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding="utf-8")
    print((result.stdout + result.stderr).strip())
    if result.returncode != 0 or "clip checks passed" not in result.stdout:
        fails.append("Luau clip checks")
    anim = (ROOT / "src/client/LowPolyAnimator.client.luau").read_text(encoding="utf-8")
    for needle, why in [
        ("require(Shared.LowPolyClips)", "the animator loads the clips"),
        ('playClip(rig, "eat", now)', "eat plays when the dino eats"),
        ('playClip(rig, "happy", now)', "happy plays on growth / a new species"),
        ('playClip(rig, "look", now)', "look plays after standing still"),
        ('"GrowthScore"', "eat trigger reads GrowthScore"),
        ('"VisualScale"', "happy trigger reads VisualScale"),
        ("if amp == 0 then rig.act, rig.clip = nil, nil", "Reduce Motion clears the clip"),
    ]:
        if needle not in anim:
            fails.append("LowPolyAnimator: " + why)
    for f in fails:
        print("FAIL:", f)
    if fails:
        return 1
    print("verify_lowpoly_clips ok: %d clips (%s)" % (len(ns["CLIPS"]), ", ".join(ns["CLIPS"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
