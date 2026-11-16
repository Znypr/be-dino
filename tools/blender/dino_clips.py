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

# ------------------------------------------------------------------ Jump overlays (BD-1217 rig follow-up, Config.DinoRigClipsEnabled)
# Played ON TOP of the procedural airborne tuck / landing squash (LowPolyPose.sampleAction keeps the leg fold, BD-555): "jump" starts at
# take-off, "land" at touch-down. Signs: head pitch > 0 = nose up; tail pitch > 0 = tail tip DOWN (the tail hangs back from its root).
JUMP = {
    "length": 0.6, "loop": False,
    "tracks": {
        "head": {"pitch": [(0, 0), (0.15, 9), (0.35, 6), (0.6, 0)]},
        "tail": {"pitch": [(0, 0), (0.18, 12), (0.6, 0)]},
        "arm": {"pitch": [(0, 0), (0.15, -12), (0.6, 0)]},
    },
}
LAND = {
    "length": 0.6, "loop": False,
    "tracks": {
        "head": {"pitch": [(0, 0), (0.18, -6), (0.38, 2), (0.6, 0)]},
        "tail": {"pitch": [(0, 0), (0.18, 7), (0.38, -3), (0.6, 0)],
                 "yaw": [(0, 0), (0.22, 4), (0.42, -2), (0.6, 0)]},
        "arm": {"pitch": [(0, 0), (0.18, 5), (0.6, 0)]},
    },
}

CLIPS = {"eat": EAT, "happy": HAPPY, "look": LOOK, "jump": JUMP, "land": LAND}

# ------------------------------------------------------------------ Locomotion CYCLES (BD-1217 rig follow-up, Config.DinoRigClipsEnabled)
# src/shared/LowPolyGait.luau plays these INSTEAD of the sine poses of LowPolyPose.sample (Water dinos, wings and flippers keep the sine poses).
# They loop: the first and the last value of every channel are equal and the tangents wrap around. "clock":
#   "time"    keys in seconds (idle, length = seconds per loop)
#   "stride"  keys in parts of ONE stride (walk, run: length 1). The animator's step phase drives them, and the phase advances with the REAL
#             planar speed (LowPolyPose.stepRate), so the feet keep time with the ground. Speed blends idle -> walk -> run.
# Leg keys are for the LEFT FRONT leg; the right leg runs half a stride later and a back leg of a quadruped pairs diagonally (LowPolyGait
# offsets), arms swing against the leg on their side. Leg pitch > 0 = foot forward. A walk: the foot is planted for 60% of the stride and swings
# forward fast; the body is highest over the planted foot (bob peaks). A run: shorter contact, a float (bigger bob), tail held up, head low.
IDLE = {
    "length": 4.0, "clock": "time",
    "tracks": {
        "root": {"bob": [(0, 0), (2.0, 0.01), (4.0, 0)]},
        "head": {"pitch": [(0, 0), (1.2, 2.5), (2.6, -1.5), (4.0, 0)],
                 "roll": [(0, -2), (2.0, 2), (4.0, -2)],
                 "yaw": [(0, 0), (1.0, 2), (3.0, -2), (4.0, 0)]},
        "tail": {"yaw": [(0, -7), (2.0, 7), (4.0, -7)],
                 "pitch": [(0, 0), (2.0, 2.5), (4.0, 0)]},
        "arm": {"pitch": [(0, 0), (2.0, -3), (4.0, 0)]},
    },
}
WALK = {
    "length": 1.0, "clock": "stride",
    "tracks": {
        "root": {"bob": [(0, 0), (0.28, 0.02), (0.5, 0), (0.78, 0.02), (1.0, 0)]},
        "head": {"pitch": [(0, -2), (0.28, 1.5), (0.5, -2), (0.78, 1.5), (1.0, -2)],
                 "roll": [(0, -2.5), (0.5, 2.5), (1.0, -2.5)],
                 "fwd": [(0, 0), (0.15, 0.025), (0.4, 0), (0.65, 0.025), (0.9, 0), (1.0, 0)]},
        "tail": {"yaw": [(0, -9), (0.1, -11), (0.6, 11), (1.0, -9)],
                 "pitch": [(0, 2), (0.35, 4), (0.5, 2), (0.85, 4), (1.0, 2)]},
        "leg": {"pitch": [(0, 24), (0.3, 2), (0.6, -24), (0.8, 6), (1.0, 24)]},
        "arm": {"pitch": [(0, -12), (0.5, 12), (1.0, -12)]},
    },
}
RUN = {
    "length": 1.0, "clock": "stride",
    "tracks": {
        "root": {"bob": [(0, 0), (0.22, 0.035), (0.5, 0), (0.72, 0.035), (1.0, 0)]},
        "head": {"pitch": [(0, -7), (0.25, -3), (0.5, -7), (0.75, -3), (1.0, -7)],
                 "roll": [(0, -3), (0.5, 3), (1.0, -3)],
                 "fwd": [(0, 0.03), (0.25, 0.045), (0.5, 0.03), (0.75, 0.045), (1.0, 0.03)]},
        "tail": {"yaw": [(0, -12), (0.1, -14), (0.6, 14), (1.0, -12)],
                 "pitch": [(0, -6), (0.3, -9), (0.5, -6), (0.8, -9), (1.0, -6)]},
        "leg": {"pitch": [(0, 28), (0.45, -28), (0.6, -16), (0.8, 16), (1.0, 28)]},
        "arm": {"pitch": [(0, -26), (0.5, -2), (1.0, -26)]},
    },
}
GAIT = {"idle": IDLE, "walk": WALK, "run": RUN}
GAIT_ROLES = ["root", "head", "neck", "tail", "arm", "leg"]  # wings and flippers keep the sine poses (fold, rowing)

# limits the generator and the tests hold every key to (calm style; Pose.MaxAngle is 0.9 rad = 51.6 degrees)
MAX_DEG = 45
MAX_BOB = 0.08
MAX_FWD = 0.06
