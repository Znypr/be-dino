"""BD-1047 (docs/187 s G): a rough model of how much food a player collects in 5 minutes from a food layout, so the pace can be compared.

NOT a real player and NOT a Studio measurement (the smart test bot of BD-1048 does not exist yet). Three walkers, all at WALK_SPEED studs per
second, picking up every food within PICKUP_RADIUS, a food coming back RESPAWN seconds after it was eaten:

  * 'nearest'  goes to the closest food, eats it, repeats;
  * 'value'    goes to the food with the most points per second of walking;
  * 'around'   just runs around: keeps its heading, turns a little every second, bounces off the arena edge (no seeking at all).

The two seeking walkers start from several points near the run start and the numbers are averaged, 'around' is averaged over several seeds,
so one lucky amber does not decide the answer. Needs numpy (CI installs it).
"""
import math

import numpy as np

POINTS = {'berry': 1, 'fruit': 4, 'egg': 15, 'amber': 50}   # Config / FoodService TYPES
WALK_SPEED = 22.0      # studs per second (docs/187 F)
PICKUP_RADIUS = 2.25   # Config.FoodPickupRadius
RESPAWN = 8.0          # Config.FoodRespawnSeconds
SPAWN = (0.0, 30.0)
STARTS = tuple((round(r * math.cos(a), 1), round(30.0 + r * math.sin(a), 1)) for r, a in [(0.0, 0.0)] + [(60.0 + 25.0 * (k % 3), 2 * math.pi * k / 11) for k in range(11)])  # the run start and 11 spots around it
EDGE = 400.0


def _arrays(points):
    xs = np.array([p[0] for p in points], dtype=float)
    zs = np.array([p[1] for p in points], dtype=float)
    pts = np.array([POINTS[p[2]] for p in points], dtype=float)
    return xs, zs, pts


def greedy_walk(points, seconds=300.0, policy='nearest', start=SPAWN):
    """(foods eaten, points) of one seeking walker in `seconds`."""
    xs, zs, pts = _arrays(points)
    ready = np.zeros(len(points))
    x, z = start
    t, eaten, gained = 0.0, 0, 0.0
    while t < seconds and len(points):
        d = np.maximum(0.0, np.hypot(xs - x, zs - z) - PICKUP_RADIUS)
        score = 1.0 / (d + 1.0) if policy == 'nearest' else pts / (d / WALK_SPEED + 0.25)
        score = np.where(ready <= t, score, -1.0)
        best = int(np.argmax(score))
        if score[best] < 0:
            break
        t += d[best] / WALK_SPEED + 0.1
        x, z = float(xs[best]), float(zs[best])
        ready[best] = t + RESPAWN
        eaten += 1
        gained += pts[best]
    return eaten, float(gained)


def run_around(points, seconds=300.0, seed=1):
    """(foods eaten, points) of one walker that does not look for food."""
    xs, zs, pts = _arrays(points)
    ready = np.zeros(len(points))
    rng = np.random.default_rng(seed)
    x, z = SPAWN
    heading = rng.uniform(0, 2 * math.pi)
    eaten, gained = 0, 0.0
    for step in range(int(seconds)):
        t = float(step)
        heading += rng.normal(0, math.radians(40))
        nx, nz = x + math.cos(heading) * WALK_SPEED, z + math.sin(heading) * WALK_SPEED
        if abs(nx) > EDGE:
            heading, nx = math.pi - heading, x - math.cos(heading) * WALK_SPEED
        if abs(nz) > EDGE:
            heading, nz = -heading, z - math.sin(heading) * WALK_SPEED
        dx, dz = nx - x, nz - z
        length2 = dx * dx + dz * dz
        u = np.clip(((xs - x) * dx + (zs - z) * dz) / length2, 0.0, 1.0) if length2 else np.zeros(len(xs))
        hit = (np.hypot(xs - (x + u * dx), zs - (z + u * dz)) <= PICKUP_RADIUS) & (ready <= t)
        n = int(hit.sum())
        if n:
            eaten += n
            gained += float(pts[hit].sum())
            ready[hit] = t + 1.0 + RESPAWN
        x, z = nx, nz
    return eaten, gained


def pace(points, seconds=300.0, trials=12):
    """{'nearest': (foods, points), 'value': ..., 'around': ...}: averages over STARTS (seeking) or `trials` seeds (running around)."""
    out = {}
    for policy in ('nearest', 'value'):
        runs = [greedy_walk(points, seconds, policy, start) for start in STARTS]
        out[policy] = (sum(r[0] for r in runs) / len(runs), sum(r[1] for r in runs) / len(runs))
    runs = [run_around(points, seconds, seed) for seed in range(1, trials + 1)]
    out['around'] = (sum(r[0] for r in runs) / len(runs), sum(r[1] for r in runs) / len(runs))
    return out
