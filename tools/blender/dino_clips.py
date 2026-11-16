"""BD-1217: authored clips for the V3 low-poly dinos (eat, happy, look-around). ONE source for the Blender actions
(tools/blender/build_dino_clips.py -> assets/blender/anim/DinoClips.blend) and the game data (tools/blender/gen_dino_clips_luau.py ->
src/shared/LowPolyClips.luau). Same pattern as the cockatoo test (docs/169: animations reach Roblox as a Luau module, not as an upload).

The V3 dinos are rigid generated parts, one per body role (src/shared/LowPolyPose.luau Roles), so a clip has one TRACK PER ROLE, not per
species: the same keys fit every dino. src/client/LowPolyAnimator.client.luau adds a playing clip ON TOP of the procedural idle / walk / run /
jump pose (those follow the real speed and the humanoid state, so they stay procedural).

Channels (in the part's own frame, the joint pivot of LowPolyAnimator.pivotFor):
  pitch, yaw, roll  degrees. Head pitch < 0 = nose down; tail yaw = side sway. For wing / flipper / arm, roll is multiplied by the part's side
                    (LPSide), so roll > 0 opens a wing on both sides.
  bob               root track only: whole-dino lift, fraction of the dino's height (every part moves together, nothing slides).
  fwd               head track only: head thrust forward, fraction of the dino's height.
Keys are (time s, value); bob never goes below 0 (a rigid leg cannot bend, so a dip would sink the feet). Every clip starts and ends at 0 so it fades in and out by itself. Curves: cubic Hermite with monotone-clamped tangents
(Fritsch-Carlson, like Blender's auto-clamped Bezier: a curve never overshoots its keys). Calm kid style (docs/240): small angles, soft timing, no snaps.
"""

FPS = 30
ROLES = ["root", "head", "neck", "tail", "arm", "leg", "wing", "flipper"]
CHANNELS = ["pitch", "yaw", "roll", "bob", "fwd"]
NECK_SHARE = 0.6  # a separate neck part follows the head track at this share (the head part is the one with the eyes)

# ------------------------------------------------------------------ Eat: dip to the food, two chews, back up (1.4 s, plays while walking too)
EAT = {
    "length": 1.4, "loop": False,
    "tracks": {
        "head": {"pitch": [(0, 0), (0.3, -26), (0.5, -17), (0.65, -26), (0.82, -17), (0.98, -24), (1.4, 0)],
                 "roll": [(0, 0), (0.5, 4), (0.82, -4), (1.15, 0), (1.4, 0)],
                 "fwd": [(0, 0), (0.3, 0.05), (0.98, 0.05), (1.4, 0)]},
        "tail": {"yaw": [(0, 0), (0.4, 9), (0.7, -9), (1.0, 7), (1.4, 0)]},
        "wing": {"roll": [(0, 0), (0.5, 8), (0.9, 0), (1.4, 0)]},
    },
}

# ------------------------------------------------------------------ Happy: two soft hops (no crouch: rigid legs cannot bend, a dip sinks the feet), tail wag, head tilt (1.6 s)
HAPPY = {
    "length": 1.6, "loop": False,
    "tracks": {
        "root": {"bob": [(0, 0), (0.3, 0.07), (0.48, 0), (0.74, 0.05), (0.9, 0), (1.6, 0)]},
        "head": {"pitch": [(0, 0), (0.3, 12), (0.9, 8), (1.2, 10), (1.6, 0)],
                 "roll": [(0, 0), (0.9, 0), (1.08, 9), (1.32, -6), (1.6, 0)]},
        "tail": {"yaw": [(0, 0), (0.15, 18), (0.3, -18), (0.45, 18), (0.6, -18), (0.75, 16), (0.9, -14), (1.1, 10), (1.3, -6), (1.6, 0)],
                 "pitch": [(0, 0), (0.3, 10), (0.9, 6), (1.6, 0)]},
        "leg": {"pitch": [(0, 0), (0.3, 8), (0.48, 0), (0.74, 6), (0.9, 0), (1.6, 0)]},
        "arm": {"pitch": [(0, 0), (0.3, -22), (0.9, -18), (1.3, 0), (1.6, 0)]},
        "wing": {"roll": [(0, 0), (0.2, 40), (0.35, 15), (0.5, 40), (0.65, 15), (0.8, 34), (1.1, 0), (1.6, 0)]},
        "flipper": {"pitch": [(0, 0), (0.2, 20), (0.4, -20), (0.6, 20), (0.8, -15), (1.1, 0), (1.6, 0)]},
    },
}

# ------------------------------------------------------------------ Look around: the idle fidget after standing still a while (3.0 s)
LOOK = {
    "length": 3.0, "loop": False,
    "tracks": {
        "head": {"yaw": [(0, 0), (0.7, 18), (1.2, 21), (1.9, -14), (2.4, -17), (3.0, 0)],
                 "roll": [(0, 0), (0.7, 4), (1.2, 5), (1.9, -3), (2.4, -4), (3.0, 0)],
                 "pitch": [(0, 0), (0.6, 4), (1.8, 2), (3.0, 0)]},
        "tail": {"yaw": [(0, 0), (0.8, -8), (1.6, 8), (2.4, -6), (3.0, 0)]},
    },
}

CLIPS = {"eat": EAT, "happy": HAPPY, "look": LOOK}

# limits the generator and the tests hold every key to (calm style; Pose.MaxAngle is 0.9 rad = 51.6 degrees)
MAX_DEG = 45
MAX_BOB = 0.08
MAX_FWD = 0.06
