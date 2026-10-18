"""Cockatoo HQ animation data (BD-621 test model): ONE source for the Blender actions and the Luau module.

Frame of reference is the Blender model frame (creature faces +Y, Z up, X = creature's right). Per part (rigid, pivot at its joint):
  pos  = (t, x, y, z) offset in studs from the rest pose
  rot  = (t, pitch, roll, yaw) degrees, Euler XYZ (matrix Rz * Ry * Rx): pitch about +X (positive = nose/toes up, a hanging leg swings FORWARD),
         roll about +Y (positive moves a hanging limb toward -X), yaw about +Z.
Times are seconds. Loop animations repeat; the last key equals the first.
"""

PARTS = ["Body", "Head", "Crest", "Tail", "ArmR", "ArmL", "LegR", "LegL", "FootR", "FootL"]
PARENT = {"Body": None, "Head": "Body", "Crest": "Head", "Tail": "Body", "ArmR": "Body", "ArmL": "Body", "LegR": "Body", "LegL": "Body", "FootR": "LegR", "FootL": "LegL"}


def _mirror(track):
    """swap sides: roll and yaw change sign, x offset changes sign."""
    out = {}
    if "pos" in track:
        out["pos"] = [(t, -x, y, z) for (t, x, y, z) in track["pos"]]
    if "rot" in track:
        out["rot"] = [(t, p, -r, -w) for (t, p, r, w) in track["rot"]]
    return out


# ------------------------------------------------------------------ Idle: breathing, crest bob, head tilt (3.0 s loop)
IDLE = {
    "length": 3.0, "loop": True,
    "tracks": {
        "Body": {"pos": [(0, 0, 0, 0), (0.75, 0, 0, 0.045), (1.5, 0, 0, 0), (2.25, 0, 0, 0.045), (3.0, 0, 0, 0)],
                 "rot": [(0, 0, 0, 0), (0.75, 1.0, 0, 0), (1.5, 0, 0, 0), (2.25, 1.0, 0, 0), (3.0, 0, 0, 0)]},
        "Head": {"rot": [(0, 0, 0, 0), (0.75, -2, 7, 6), (1.5, 0, 0, 0), (2.25, -2, -5, -5), (3.0, 0, 0, 0)],
                 "pos": [(0, 0, 0, 0), (0.75, 0, 0.02, 0.03), (1.5, 0, 0, 0), (2.25, 0, 0.02, 0.03), (3.0, 0, 0, 0)]},
        "Crest": {"rot": [(0, 0, 0, 0), (0.45, 7, 0, 0), (0.9, 0, 0, 0), (1.5, 3, 0, 0), (1.95, 8, 0, 0), (2.4, 0, 0, 0), (3.0, 0, 0, 0)]},
        "Tail": {"rot": [(0, 0, 0, 5), (0.75, 2, 0, 0), (1.5, 0, 0, -5), (2.25, 2, 0, 0), (3.0, 0, 0, 5)]},
        "ArmR": {"rot": [(0, 0, 0, 0), (0.75, 3, -2, 0), (1.5, 0, 0, 0), (2.25, 3, -2, 0), (3.0, 0, 0, 0)]},
        "ArmL": {"rot": [(0, 0, 0, 0), (0.75, 3, 2, 0), (1.5, 0, 0, 0), (2.25, 3, 2, 0), (3.0, 0, 0, 0)]},
    },
}

# ------------------------------------------------------------------ Walk: 1.0 s cycle = two steps (right leg forward at t=0, left at t=0.5)
_leg_r = [(0, 24, 0, 0), (0.25, 0, 0, 0), (0.5, -24, 0, 0), (0.75, -6, 0, 0), (1.0, 24, 0, 0)]
_leg_l = [(0, -24, 0, 0), (0.25, -6, 0, 0), (0.5, 24, 0, 0), (0.75, 0, 0, 0), (1.0, -24, 0, 0)]
_leg_r_pos = [(0, 0, 0, 0), (0.25, 0, 0, 0), (0.5, 0, 0, 0), (0.75, 0, 0.0, 0.2), (1.0, 0, 0, 0)]
_leg_l_pos = [(0, 0, 0, 0), (0.25, 0, 0, 0.2), (0.5, 0, 0, 0), (0.75, 0, 0, 0), (1.0, 0, 0, 0)]
# feet keep flat on the ground in stance (counter-rotate) and point the toes up a little in the swing
_foot_r = [(0, -24, 0, 0), (0.25, 0, 0, 0), (0.5, 24, 0, 0), (0.75, 30, 0, 0), (1.0, -24, 0, 0)]
_foot_l = [(0, 24, 0, 0), (0.25, 30, 0, 0), (0.5, -24, 0, 0), (0.75, 0, 0, 0), (1.0, 24, 0, 0)]
WALK = {
    "length": 1.0, "loop": True,
    "tracks": {
        "Body": {"pos": [(0, 0, 0, -0.1), (0.25, 0, 0, 0.02), (0.5, 0, 0, -0.1), (0.75, 0, 0, 0.02), (1.0, 0, 0, -0.1)],
                 "rot": [(0, 2, -3, 3), (0.25, 3, 0, 0), (0.5, 2, 3, -3), (0.75, 3, 0, 0), (1.0, 2, -3, 3)]},
        "Head": {"pos": [(0, 0, 0.08, 0), (0.25, 0, -0.05, 0.02), (0.5, 0, 0.08, 0), (0.75, 0, -0.05, 0.02), (1.0, 0, 0.08, 0)],
                 "rot": [(0, -3, 0, -3), (0.25, 0, 0, 0), (0.5, -3, 0, 3), (0.75, 0, 0, 0), (1.0, -3, 0, -3)]},
        "Crest": {"rot": [(0, 0, 0, 0), (0.25, 7, 0, 0), (0.5, 0, 0, 0), (0.75, 7, 0, 0), (1.0, 0, 0, 0)]},
        "Tail": {"rot": [(0, 0, 0, 9), (0.25, 4, 0, 0), (0.5, 0, 0, -9), (0.75, 4, 0, 0), (1.0, 0, 0, 9)]},
        "ArmR": {"rot": [(0, -10, 0, 0), (0.5, 10, 0, 0), (1.0, -10, 0, 0)]},
        "ArmL": {"rot": [(0, 10, 0, 0), (0.5, -10, 0, 0), (1.0, 10, 0, 0)]},
        "LegR": {"rot": _leg_r, "pos": _leg_r_pos},
        "LegL": {"rot": _leg_l, "pos": _leg_l_pos},
        "FootR": {"rot": _foot_r},
        "FootL": {"rot": _foot_l},
    },
}

# ------------------------------------------------------------------ Jump: crouch, launch, wings flare, land (1.4 s, not looping)
_t = [0.0, 0.22, 0.38, 0.6, 0.9, 1.08, 1.4]
JUMP = {
    "length": 1.4, "loop": False,
    "tracks": {
        "Body": {"pos": list(zip(_t, [0] * 7, [0, 0, 0.0, 0.0, 0.0, 0.0, 0.0], [0, -0.55, 0.75, 1.15, 0.45, -0.38, 0])),
                 "rot": list(zip(_t, [0, -12, 6, -4, 6, -9, 0], [0] * 7, [0] * 7))},
        "Head": {"rot": list(zip(_t, [0, 10, -10, -6, 4, 8, 0], [0] * 7, [0] * 7))},
        "Crest": {"rot": list(zip(_t, [0, -10, 18, 24, 6, -10, 0], [0] * 7, [0] * 7))},
        "Tail": {"rot": list(zip(_t, [0, 14, 22, 26, 12, 10, 0], [0] * 7, [0] * 7))},
        "ArmR": {"rot": list(zip(_t, [0, 14, 22, 30, 16, 4, 0], [0, 0, -50, -72, -48, -14, 0], [0] * 7))},
        "ArmL": {"rot": list(zip(_t, [0, 14, 22, 30, 16, 4, 0], [0, 0, 50, 72, 48, 14, 0], [0] * 7))},
        "LegR": {"rot": list(zip(_t, [0, 34, -14, 22, 20, 32, 0], [0] * 7, [0] * 7))},
        "LegL": {"rot": list(zip(_t, [0, 34, -14, 22, 20, 32, 0], [0] * 7, [0] * 7))},
        "FootR": {"rot": list(zip(_t, [0, -34, -22, -12, -20, -32, 0], [0] * 7, [0] * 7))},
        "FootL": {"rot": list(zip(_t, [0, -34, -22, -12, -20, -32, 0], [0] * 7, [0] * 7))},
    },
}

ANIMS = {"Idle": IDLE, "Walk": WALK, "Jump": JUMP}
