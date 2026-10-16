"""BD-412 LIGHTING gate (docs/114 s6): mean luminance of a rendered screenshot per place.

Luminance = mean of 0.2126 R + 0.7152 G + 0.0722 B on the sRGB values scaled to 0..1 (display luminance, NOT linearised), taken over the
3D viewport region only (Studio chrome and HUD are excluded: capture with the ScreenGuis hidden, see docs/117 s3).
Ranges (LEAD, provisional until the owner confirms them; the handbook says "bright daylight" and "DIM, lamp-lit" without numbers):
  island        0.35 - 0.75   bright daylight (ClockTime 14, Brightness 1.8 since BD-460)
  cave_heart    0.15 - 0.35   DIM warm cave, dino still readable
  cave_station  0.15 - 0.35   same, standing at a station
Fails (exit 1) when a mean is outside its range. Also reports the 5th/95th percentile so a flat-black or burnt-out frame is visible.
Usage: python tools/qa/luminance.py --place cave_heart shot.png [--roi x0 y0 x1 y1 as fractions]
       python tools/qa/luminance.py --check-dir DIR      (files named <place>__<anything>.png)
"""
from pathlib import Path
import argparse, sys
import numpy as np
from PIL import Image

RANGES = {'island': (0.35, 0.75), 'cave_heart': (0.15, 0.35), 'cave_station': (0.15, 0.35)}
# The 3D viewport of a maximised Studio window at 1936 x 1048 as fractions (left, top, right, bottom); override with --roi.
DEFAULT_ROI = (0.062, 0.172, 0.803, 0.922)


def luminance(arr):
    """arr: H x W x 3 uint8 (or float 0..255). Returns the per-pixel display luminance 0..1."""
    a = np.asarray(arr, dtype=np.float64)[..., :3] / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def measure(path, roi=DEFAULT_ROI):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    box = (int(roi[0] * w), int(roi[1] * h), int(roi[2] * w), int(roi[3] * h))
    y = luminance(np.asarray(im.crop(box)))
    return float(y.mean()), float(np.percentile(y, 5)), float(np.percentile(y, 95))


def verdict(place, mean):
    lo, hi = RANGES[place]
    return lo <= mean <= hi, lo, hi


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('image', nargs='?')
    ap.add_argument('--place', choices=sorted(RANGES))
    ap.add_argument('--check-dir')
    ap.add_argument('--roi', nargs=4, type=float, default=list(DEFAULT_ROI))
    args = ap.parse_args(argv)
    jobs = []
    if args.check_dir:
        for f in sorted(Path(args.check_dir).glob('*.png')):
            place = f.name.split('__')[0]
            if place in RANGES:
                jobs.append((place, f))
    elif args.image and args.place:
        jobs.append((args.place, Path(args.image)))
    else:
        ap.error('give IMAGE --place P, or --check-dir DIR')
    if not jobs:
        raise SystemExit('no screenshots found')
    bad = 0
    for place, f in jobs:
        mean, p5, p95 = measure(f, tuple(args.roi))
        ok, lo, hi = verdict(place, mean)
        print('%s %s %s: mean luminance %.3f (range %.2f-%.2f), p5 %.3f p95 %.3f' % ('OK  ' if ok else 'FAIL', place, f.name, mean, lo, hi, p5, p95))
        bad += 0 if ok else 1
    if bad:
        raise SystemExit('lighting FAIL: %d screenshot(s) outside their luminance range' % bad)
    print('lighting ok')


if __name__ == '__main__':
    main()
